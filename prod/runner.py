# -*- coding: utf-8 -*-
"""The production build runner (deployment plan §6 — the fresh-start build
contract, rules 1–11 — and §2; review P0.4, P0.7, §11, §12).

    python -m prod.runner run --release <tag> --register <register.json> --dataset <stage2.parquet> \\
        --out <out_root> --evidence <evidence_root> --work <work_root> [--concurrency 12] \\
        [--schools 6782320,6644017 | --sample 20 --seed 2026 | --all] [--probe] [--keep-work] \\
        [--previous-locks <dir> --lock-ruling "<text>"] [--site-prefix /] [--force]
    python -m prod.runner rebuild --release <tag> ... --fraction 0.05 --seed 2026 --compare <first_out_root>
    python -m prod.runner status --evidence <evidence_root> --release <tag>

One job = one school = exactly the V5.1 procedure (build_school.sh: export →
three state slices → assemble → QA with the school's lock → write → single-
file HTML) followed by the per-school assurance the V5.0/V5.1 rounds ran
(the stock gate-pack reruns in the bundle, the independent figure check, the
jsdom regression and provenance port, optionally the Chromium render probe),
then the production steps: the served package (chunks + entry page) and its
verifier, the attestation, the evidence copy, the ledger row. Nothing in
the report is produced differently from the prototype rounds.

The rules, as enforced here:
  1  frozen release   prod.release.verify must pass before any job starts
  2  empty workdir    the job's work tree must not exist; it is created, and
                      deleted after the evidence is copied (unless --keep-work)
  3  input allowlist  a job reads the release tree, the dataset (filtered to
                      its school inside the export), and its register row;
                      the runner passes nothing else, and SSS_PREVIOUS_LOCK is
                      only ever a lock the ledger already holds for the school
  4  no intermediates the state slices, the package pickle and the export live
                      only in the job's own work tree
  5  full gates       QA + the bundle's two stock reruns + jsdom + provenance +
                      figures on every job; a blocking failure outside the
                      recorded pending/disputed lists fails the job
  6  write-once       the school's served tree and evidence are written once and
                      made read-only; a second build of the same school under
                      the same release is refused unless --force
  7  one identity     attestation.json is the single statement of the identity
  8  change = new tag the ledger and the output tree are keyed by release
  9  dev until signed the pipeline's own mode is recorded; publish refuses dev
 10  reproduction     `rebuild` builds a random fraction again into a second tree
                      and compares every served file byte for byte
 11  workbook         nothing here writes under config/
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import gzip
import hashlib
import json
import os
import platform
import random
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from prod import PROD_VERSION, SCHEMA_VERSION            # noqa: E402
from prod import chunker, htmlcore, release as release_mod, tokens as tokens_mod   # noqa: E402
from prod.ledger import Ledger, now                       # noqa: E402
from prod.register import profile_for                     # noqa: E402

PY = sys.executable
MIN_FREE_GB = 3.0
CONTENT_TYPES = {".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
                 ".js": "application/javascript; charset=utf-8", ".woff2": "font/woff2", ".webp": "image/webp",
                 ".txt": "text/plain; charset=utf-8", ".css": "text/css; charset=utf-8"}


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def md5b64(p: Path) -> str:
    import base64
    h = hashlib.md5()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return base64.b64encode(h.digest()).decode("ascii")


def mem_available_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / (1024 * 1024)
    except Exception:
        pass
    return 1e9


def run(cmd, cwd, env, log: Path, timeout=3600):
    with log.open("ab") as f:
        f.write(("\n$ " + " ".join(map(str, cmd)) + "\n").encode())
        r = subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=env, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
    if r.returncode != 0:
        tail = log.read_text(encoding="utf-8", errors="replace")[-3000:]
        raise RuntimeError(f"{cmd[0]} {cmd[1] if len(cmd) > 1 else ''} failed (rc {r.returncode}):\n{tail}")


# --------------------------------------------------------------------------- one job
def build_one(spec: dict) -> dict:
    """Runs in a worker process. Returns the attestation, or raises RuntimeError.
    On failure every partial output of the job is removed (served tree, evidence,
    work tree including the pupil-level export) so that a retry starts clean."""
    row = spec["row"]; release = spec["release"]; slug = row["slug"]
    work = Path(spec["work"]) / release / slug
    try:
        return _build_one(spec)
    except BaseException as e:            # SystemExit from a pipeline helper included
        try:
            _cleanup_partial(spec, row, release, slug, work)
        except Exception:                 # noqa: BLE001
            pass
        raise RuntimeError(f"{type(e).__name__}: {str(e)[:2000]}") from None


def _cleanup_partial(spec, row, release, slug, work):
    out_root = Path(spec["out"]) / release
    evid = Path(spec["evidence"]) / release / slug
    for d in (out_root / "r" / release / spec.get("_token", "__none__"), out_root / "2026" / spec.get("_token", "__none__"), evid):
        if d.exists():
            for p in d.rglob("*"):
                if p.is_file():
                    os.chmod(p, 0o644)
            shutil.rmtree(d, ignore_errors=True)
    priv = work / "private"
    if priv.exists():
        shutil.rmtree(priv, ignore_errors=True)         # the export never outlives its job
    if not spec["keep_work"] and work.exists():
        shutil.rmtree(work, ignore_errors=True)


def _build_one(spec: dict) -> dict:
    t0 = time.time()
    row = spec["row"]; release = spec["release"]; sid = row["school_id"]; slug = row["slug"]
    work = Path(spec["work"]) / release / slug
    out_root = Path(spec["out"]) / release
    evid = Path(spec["evidence"]) / release / slug
    if work.exists():
        raise RuntimeError(f"rule 2: work tree exists: {work}")
    if evid.exists() and not spec["force"]:
        raise RuntimeError(f"rule 6: evidence already exists for {slug} under {release}: {evid}")
    wd = work / "wd"; gen = work / "generated"; priv = work / "private"
    for d in (wd, gen, priv):
        d.mkdir(parents=True)
    os.chmod(priv, 0o700)
    log = work / "job.log"
    timings = {}

    # rule 3: the job's inputs — the register row (profile), the dataset, the release tree
    profile = profile_for(row, release, spec["dataset_sha256"], spec["dataset_file"])
    profile_path = priv / "profile.json"
    profile_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    profile_sha = sha(profile_path)
    env = dict(os.environ)
    env.update({"SSS_SCHOOL_PROFILE": str(profile_path), "SSS_GENERATED_DIR": str(gen), "PYTHONUNBUFFERED": "1",
                "SSS_ASSET_CACHE": str(Path(spec["work"]) / release / "_asset_cache")})
    parquet = spec["dataset"]

    # 1. export (free text withheld; pupil-level data stays in private/)
    export = priv / f"SSS2026_cleansed_export_{sid}.xlsx"
    t = time.time()
    run([PY, "-m", "pipeline.cleansed_to_export", parquet, sid, export], ROOT, env, log)
    timings["export"] = round(time.time() - t, 1)
    # membership: the response ids of this school's accepted rows (from the dataset itself)
    import pyarrow.parquet as pq
    tbl = pq.read_table(parquet, columns=["response_id", "school_id"], filters=[("school_id", "=", sid)])
    ids = [str(x) for x in tbl.column("response_id").to_pylist()]      # exactly the rows the export wrote
    membership = tokens_mod.membership_fingerprint(spec["membership_key"], release, sid, ids)

    # 2. states (three slices, in parallel when allowed), assemble
    t = time.time()
    slices = [(0, 4), (4, 8), (8, 12)]
    if spec["slice_parallel"]:
        procs = []
        for lo, hi in slices:
            lf = (wd / f"s_{lo}_{hi}.log").open("wb")
            procs.append((subprocess.Popen([PY, "-m", "pipeline.staged_build", "states", str(export), str(wd), str(lo), str(hi)],
                                           cwd=str(ROOT), env=env, stdout=lf, stderr=subprocess.STDOUT), lf, lo, hi))
        for p, lf, lo, hi in procs:
            p.wait(); lf.close()
            if p.returncode != 0:
                raise RuntimeError(f"states {lo}:{hi} failed:\n" + (wd / f"s_{lo}_{hi}.log").read_text(errors="replace")[-2000:])
    else:
        for lo, hi in slices:
            run([PY, "-m", "pipeline.staged_build", "states", export, wd, lo, hi], ROOT, env, log)
    timings["states"] = round(time.time() - t, 1)
    t = time.time()
    run([PY, "-m", "pipeline.staged_build", "assemble", export, wd], ROOT, env, log)
    timings["assemble"] = round(time.time() - t, 1)

    # 3. QA with the school's corpus lock (rule 3: only a lock the ledger/caller already holds)
    prev = spec.get("previous_lock") or "none"
    ruling = spec.get("lock_ruling") or f"first emission for {slug}: the corpus lock of this school, {spec['framework']}, pipeline {spec['pipeline_version']}"
    env_qa = dict(env, SSS_PREVIOUS_LOCK=str(prev), SSS_EMIT_LOCK=str(gen / f"lock_{slug}_v8.json"), SSS_EMIT_LOCK_RULING=ruling)
    t = time.time()
    run([PY, "-m", "pipeline.staged_build", "qa", export, wd], ROOT, env_qa, log)
    run([PY, "-m", "pipeline.staged_build", "write", export, wd], ROOT, env, log)
    timings["qa_write"] = round(time.time() - t, 1)

    # 4. the monolithic HTML (the assurance copy the stock gates read)
    t = time.time()
    run([PY, "-m", "pipeline.build_html", gen / f"{slug}.report.json", spec["yac"], spec["fonts"], ROOT / "config" / "cover_media",
         gen / "report.html"], ROOT, env, log)
    timings["html"] = round(time.time() - t, 1)

    # 5. assurance: bundle + stock reruns, independent figures, jsdom, provenance, (probe)
    t = time.time()
    run([PY, "-m", "pipeline.make_school_bundle", slug, spec["label"]], ROOT, env, log)
    bundle_summary = json.loads((gen / "bundle_summary.json").read_text(encoding="utf-8"))
    run([PY, "-m", "pipeline.verify_school", parquet, profile_path, gen / f"{slug}.report.json", gen / "verify_figures.json"], ROOT, env, log)
    figures = json.loads((gen / "verify_figures.json").read_text(encoding="utf-8"))
    mini = work / "mini"
    run([PY, "-m", "tests.jsdom.make_mini", mini], ROOT, dict(env, REPORT=str(gen / f"{slug}.report.json")), log)
    jenv = dict(env, JSDOM=spec["jsdom"], WD=str(mini), REPO=str(ROOT))
    run(["node", ROOT / "tests" / "jsdom" / "jsdom_school.js"], ROOT, jenv, log)
    run(["node", ROOT / "tests" / "jsdom" / "jsdom_provenance.js"], ROOT, dict(jenv, OUT="browser_gate_jsdom.json"), log)
    jsdom_school = json.loads((mini / "jsdom_school.json").read_text(encoding="utf-8")) if (mini / "jsdom_school.json").exists() else {}
    provenance = json.loads((mini / "browser_gate_jsdom.json").read_text(encoding="utf-8"))
    probe = None
    if spec["probe"]:
        run([PY, "-m", "tests.browser.render_probe", mini, gen / "probe"], ROOT, env, log, timeout=1800)
        probe = json.loads((gen / "probe" / "probe.json").read_text(encoding="utf-8"))
    timings["assurance"] = round(time.time() - t, 1)

    # gate evaluation (rule 5)
    pkg = json.loads((gen / f"{slug}.report.json").read_text(encoding="utf-8"))
    stamp = pkg["buildMetadata"]["gateResults"]
    mode = pkg["buildMetadata"]["identity"]["mode"]
    known = set(spec["known_failures"])
    failing_dev = {g for g, _ in bundle_summary["dev"]["failing"]}
    failing_rel = {g for g, _ in bundle_summary["release"]["failing"]}
    unexpected = sorted((failing_dev | failing_rel) - known)
    if unexpected:
        raise RuntimeError(f"rule 5: gate failures outside the recorded list: {unexpected}")
    if not all(bundle_summary["emittedEqualsBaseline"].values()):
        raise RuntimeError("rule 5: the rerun's emitted lock differs from the build's baseline")
    if not figures.get("allMatch"):
        raise RuntimeError("rule 5: independent figure check found mismatches: " + json.dumps(figures)[:500])
    prov_bad = (len(provenance.get("english_without_provenance") or []) or provenance.get("welsh_without_provenance", 0)
                or provenance.get("typography_faults", 0) or (provenance.get("toggle") or {}).get("failures", 0))
    if prov_bad:
        raise RuntimeError("rule 5: provenance port failed: " + json.dumps(provenance)[:400])

    # 6. the served package: chunks, entry page, verifier
    t = time.time()
    token = tokens_mod.token(spec["key"], sid)
    spec["_token"] = token
    binding = tokens_mod.binding_hash(spec["manifest_sha256"], spec["dataset_sha256"], "school", sid, profile_sha, membership)
    env_ = chunker.envelope("school", sid, release, binding)
    served_dir = out_root / "r" / release / token
    entry_dir = out_root / "2026" / token
    if served_dir.exists() or entry_dir.exists():
        if not spec["force"]:
            raise RuntimeError(f"rule 6: served tree exists for {slug}: {served_dir}")
        shutil.rmtree(served_dir, ignore_errors=True); shutil.rmtree(entry_dir, ignore_errors=True)
    core, index = chunker.split(pkg, served_dir, env_)
    core["chunked"]["base"] = f"{spec['site_prefix'].rstrip('/')}/r/{release}/{token}/"
    # the served core is deterministic: a fixed release timestamp instead of the
    # build time, and the gate stamp without the two hashes that change with every
    # build (the evidence gzip carries a write time; the lock carries the ruling
    # text). Both stay in the assurance copy and the attestation.
    core["buildMetadata"]["generatedAt"] = spec["released_at"]
    _gr = core["buildMetadata"].get("gateResults") or {}
    core["buildMetadata"]["gateResults"] = {k: _gr[k] for k in ("runner", "runnerSha256", "manifestHash", "mode",
                                                                 "blockingPass", "blockingTotal", "headline", "pending",
                                                                 "disputed", "pathsComplete", "pathsTotal") if k in _gr}
    verify_res = chunker.verify(pkg, served_dir, env_)
    assets = json.loads((out_root / "r" / release / "assets" / "assets.json").read_text(encoding="utf-8"))
    html = htmlcore.build_entry(core, assets, release, spec["site_prefix"])
    entry_dir.mkdir(parents=True, exist_ok=True)
    (entry_dir / "index.html").write_text(html, encoding="utf-8")
    # the private index never sits in the served tree
    (served_dir / "package_index.json").replace(gen / "package_index.json")
    timings["served"] = round(time.time() - t, 1)

    inventory = []
    for p in sorted(served_dir.rglob("*")) + [entry_dir / "index.html"]:
        if p.is_file():
            rel = p.relative_to(out_root).as_posix()
            inventory.append({"path": rel, "sha256": sha(p), "md5": md5b64(p), "bytes": p.stat().st_size,
                              "contentType": CONTENT_TYPES.get(p.suffix, "application/octet-stream")})
    for p in list(served_dir.rglob("*")) + [entry_dir / "index.html"]:
        if p.is_file():
            os.chmod(p, 0o444)

    # 7. attestation (rule 7) + evidence
    monolith = gen / "report.html"
    attestation = {
        "schema": SCHEMA_VERSION, "prodVersion": PROD_VERSION,
        "release": release, "commit": spec["commit"], "manifestSha256": spec["manifest_sha256"],
        "family": "school", "recipient": sid, "slug": slug, "name": row["name"], "la": row["la"],
        "profileSha256": profile_sha, "profile": profile,
        "datasetSha256": spec["dataset_sha256"], "sourceChecksum": pkg["buildMetadata"]["sourceChecksum"],
        "membershipFingerprint": membership, "exportRows": len(ids),
        "acceptedResponses": pkg["buildMetadata"]["acceptedRows"], "sourceRows": pkg["buildMetadata"]["sourceRows"],
        "releaseVerified": spec["release_verified"], "previousLock": prev if prev != "none" else None,
        "previousLockSha256": (sha(Path(prev)) if prev != "none" else None), "lockRuling": ruling,
        "binding": binding, "token": token, "envelope": env_,
        "identity": pkg["buildMetadata"]["identity"], "mode": mode,
        "pipelineVersion": pkg["buildMetadata"].get("pipelineVersion"), "reportVersion": pkg.get("reportVersion"),
        "gateStamp": {k: stamp.get(k) for k in ("blockingPass", "blockingTotal", "headline", "pending", "disputed", "manifestHash")},
        "bundle": bundle_summary, "figures": {"allMatch": figures.get("allMatch"), "checked": [k for k in figures if isinstance(figures[k], dict)]},
        "jsdom": {"school": {k: jsdom_school.get(k) for k in ("pass", "fail")}, "provenance": {"englishWithoutProvenance": len(provenance.get("english_without_provenance") or []),
                                 "welshWithoutProvenance": provenance.get("welsh_without_provenance", 0),
                                 "typographyFaults": provenance.get("typography_faults", 0),
                                 "toggleFailures": (provenance.get("toggle") or {}).get("failures", 0),
                                 "toggleChecks": (provenance.get("toggle") or {}).get("en_ok", 0)}},
        "probe": probe,
        "states": index["stateCount"], "chunks": len(index["chunks"]), "chunkBytes": index["totalChunkBytes"],
        "largestChunkBytes": verify_res["largestChunkBytes"], "servedVerify": {k: verify_res[k] for k in ("ok", "statesMoved", "rebuilt")},
        "monolith": {"path": monolith.name, "sha256": sha(monolith), "bytes": monolith.stat().st_size},
        "entryBytes": (entry_dir / "index.html").stat().st_size, "inventory": inventory,
        "generatedAt": pkg["buildMetadata"]["generatedAt"], "releasedAt": spec["released_at"],
        "builtAt": now(), "host": socket.gethostname(), "python": platform.python_version(),
        "node": spec["node_version"], "seconds": round(time.time() - t0, 1), "timings": timings,
        "runId": spec["run_id"],
    }
    if evid.exists():
        shutil.rmtree(evid)
    evid.mkdir(parents=True)
    (evid / "attestation.json").write_text(json.dumps(attestation, ensure_ascii=False, indent=1), encoding="utf-8")
    for f in ("validation-summary.txt", "verify_figures.json", "bundle_summary.json", "package_index.json",
              f"lock_{slug}_v8.json", "narrative-templates.md"):
        if (gen / f).exists():
            shutil.copy2(gen / f, evid / f)
    shutil.copy2(mini / "jsdom_school.json", evid / "jsdom_school.json") if (mini / "jsdom_school.json").exists() else None
    shutil.copy2(mini / "browser_gate_jsdom.json", evid / "browser_gate_jsdom.json")
    shutil.copytree(gen / "bundle", evid / "bundle")
    if probe:
        shutil.copytree(gen / "probe", evid / "probe")
    with gzip.open(evid / "report.html.gz", "wb", compresslevel=6) as gz, monolith.open("rb") as f:
        shutil.copyfileobj(f, gz)
    with gzip.open(evid / f"{slug}.narrative-audit.csv.gz", "wb", compresslevel=6) as gz, (gen / f"{slug}.narrative-audit.csv").open("rb") as f:
        shutil.copyfileobj(f, gz)
    shutil.copy2(log, evid / "job.log")
    for p in evid.rglob("*"):
        if p.is_file():
            os.chmod(p, 0o444)
    shutil.rmtree(priv, ignore_errors=True)   # the pupil-level export never outlives its job
    if not spec["keep_work"]:
        shutil.rmtree(work)            # rule 2/4: nothing survives
    return attestation


# --------------------------------------------------------------------------- the run
def prepare(a) -> dict:
    ok, problems = release_mod.verify(ROOT, a.release)
    if not ok and not a.allow_dirty:
        raise SystemExit("rule 1: release manifest NOT verified:\n  " + "\n  ".join(problems))
    if (ROOT / release_mod.MANIFEST).exists():
        man = release_mod.load(ROOT)
    else:
        man = release_mod.build(ROOT, a.release)          # development only (--allow-dirty): an in-memory manifest
    if not ok:
        print("WARNING: release not verified (--allow-dirty): every attestation of this run is marked releaseVerified=false "
              "and cannot be published", flush=True)
    # the release-scoped membership key: a random secret kept with the private
    # evidence, independent of the link key, so that rotating the link key changes
    # paths but not a single served byte
    evid_root = Path(a.evidence).resolve() / a.release
    evid_root.mkdir(parents=True, exist_ok=True)
    mk = evid_root / "membership_key.bin"
    if not mk.exists():
        import secrets
        fd = os.open(mk, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(secrets.token_bytes(32))
    membership_key = mk.read_bytes()
    dataset = Path(a.dataset).resolve()
    dsha = sha(dataset)
    expected = a.dataset_sha256 or "802eda98fdeef512cce11e11aa38a45df5b0f33beb81b505acfc4ce9bbe13625"
    if dsha != expected:
        raise SystemExit(f"dataset sha256 {dsha[:16]}… is not the expected {expected[:16]}… — refusing to build")
    key = tokens_mod.load_key(a.key_vault, a.link_secret)
    node = subprocess.run(["node", "-v"], capture_output=True, text=True).stdout.strip()
    from pipeline.build_report_package import PIPELINE_VERSION_V2
    return {"release": a.release, "commit": release_mod.git(ROOT, "rev-parse", "HEAD"), "manifest_sha256": man["manifestSha256"],
            "release_verified": ok, "membership_key": membership_key,
            "framework": man["framework"], "pipeline_version": PIPELINE_VERSION_V2,
            "released_at": man.get("releasedAt") or "2026-09-22T00:00:00+00:00",
            "dataset": str(dataset), "dataset_sha256": dsha, "dataset_file": dataset.name, "key": key,
            "out": str(Path(a.out).resolve()), "evidence": str(Path(a.evidence).resolve()), "work": str(Path(a.work).resolve()),
            "yac": str(ROOT / "inputs" / "yac images V4.16"), "fonts": str(ROOT / "inputs" / "fonts"),
            "jsdom": a.jsdom or os.environ.get("JSDOM", "jsdom"), "node_version": node,
            "label": a.label or a.release.upper().replace("V", "V", 1), "site_prefix": a.site_prefix,
            "probe": a.probe, "keep_work": a.keep_work, "force": a.force,
            "known_failures": [x for x in a.known_failures.split(",") if x],
            "slice_parallel": a.slice_parallel}


def select_rows(reg: dict, a) -> list[dict]:
    rows = [r for r in reg["schools"] if r["status"] == "eligible"]
    if a.schools:
        want = set(a.schools.split(","))
        rows = [r for r in reg["schools"] if r["school_id"] in want]
        held = [r["school_id"] for r in rows if r["status"] != "eligible"]
        if held:
            raise SystemExit(f"not eligible in the register: {held}")
    elif a.sample:
        rnd = random.Random(a.seed)
        # stratified by family and size band so the pilot spans the estate
        bands = {}
        for r in rows:
            band = "s" if r["n"] < 40 else "m" if r["n"] < 150 else "l"
            bands.setdefault((r["family"], band), []).append(r)
        picked = []
        keys = sorted(bands)
        i = 0
        while len(picked) < min(a.sample, len(rows)):
            k = keys[i % len(keys)]; i += 1
            if bands[k]:
                picked.append(bands[k].pop(rnd.randrange(len(bands[k]))))
        rows = sorted(picked, key=lambda r: r["school_id"])
    elif not a.all:
        raise SystemExit("choose --schools, --sample N or --all")
    return rows


def cmd_run(a):
    spec = prepare(a)
    reg = json.loads(Path(a.register).read_text(encoding="utf-8"))
    rows = select_rows(reg, a)
    out_root = Path(spec["out"]) / a.release
    evid_root = Path(spec["evidence"]) / a.release
    evid_root.mkdir(parents=True, exist_ok=True)
    # one run per release at a time (the crash clean-up below must never race a live run)
    import fcntl
    lock_path = evid_root / "run.lock"
    lock_fh = open(lock_path, "a+")
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        raise SystemExit(f"another run holds {lock_path} — one run per release at a time")
    lock_fh.seek(0); lock_fh.truncate(); lock_fh.write(f"{os.getpid()} {now()}\n"); lock_fh.flush()
    L = Ledger(evid_root / "ledger.sqlite")
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + socket.gethostname()
    L.start_run(run_id, a.release, socket.gethostname(), spec["dataset_sha256"], spec["manifest_sha256"],
                {k: v for k, v in vars(a).items() if k not in ("func",)})
    # shared release assets, once
    assets_dir = out_root / "r" / a.release / "assets"
    if not (assets_dir / "assets.json").exists():
        htmlcore.build_assets(out_root, a.release, Path(spec["yac"]), Path(spec["fonts"]), ROOT / "config" / "cover_media")
        L.event(a.release, None, "assets.built", str(assets_dir))
    shutil.copy2(ROOT / "infra" / "404.html", out_root / "404.html")
    shutil.copy2(ROOT / "infra" / "robots.txt", out_root / "robots.txt")
    (out_root / "health.txt").write_text("ok\n")
    # register snapshot beside the evidence (the build specification)
    shutil.copy2(a.register, evid_root / "register.json")

    todo = []
    for r in rows:
        L.ensure_job(a.release, r["school_id"], r["slug"], r["family"])
        j = L.job(a.release, r["school_id"])
        if j["status"] in ("built", "staged", "verified", "published") and not a.force:
            continue
        if j["status"] in ("building", "failed"):
            # an interrupted or failed job: its partial trees are removed so the retry starts clean (rules 2 and 6)
            work = Path(spec["work"]) / a.release / r["slug"]
            att_dir = evid_root / r["slug"]
            tok_guess = tokens_mod.token(spec["key"], r["school_id"])
            for d in (work, att_dir, out_root / "r" / a.release / tok_guess, out_root / "2026" / tok_guess):
                if d.exists():
                    for p in d.rglob("*"):
                        if p.is_file():
                            os.chmod(p, 0o644)
                    shutil.rmtree(d, ignore_errors=True)
            L.event(a.release, r["school_id"], "job.cleaned", f"previous status {j['status']}")
        todo.append(r)
    print(f"run {run_id}: {len(rows)} selected, {len(todo)} to build, concurrency {a.concurrency}, "
          f"slice-parallel {spec['slice_parallel']}", flush=True)
    prev_locks = Path(a.previous_locks) if a.previous_locks else None
    results = {"built": 0, "failed": 0}
    t0 = time.time()
    with cf.ProcessPoolExecutor(max_workers=a.concurrency) as ex:
        futures = {}
        queue = list(todo)
        def submit_next():
            r = queue.pop(0)
            js = dict(spec, row=r, run_id=run_id)
            if prev_locks:
                cand = prev_locks / f"lock_{r['slug']}_v8.json"
                if not cand.exists():
                    cand = prev_locks / f"lock_{r['slug'].rsplit('-', 1)[0]}_v8.json"
                if cand.exists():
                    js["previous_lock"] = str(cand); js["lock_ruling"] = a.lock_ruling
            L.mark(a.release, r["school_id"], "building", host=socket.gethostname(), run_id=run_id, started=True)
            futures[ex.submit(build_one, js)] = r
        while queue and len(futures) < a.concurrency:
            submit_next()
        while futures:
            done, _ = cf.wait(list(futures), return_when=cf.FIRST_COMPLETED)
            for fut in done:
                r = futures.pop(fut)
                try:
                    att = fut.result()
                    L.attest(a.release, r["school_id"], att)
                    L.mark(a.release, r["school_id"], "built", seconds=att["seconds"], mode=att["mode"])
                    results["built"] += 1
                    print(f"  built {r['slug']} ({att['seconds']}s, {att['gateStamp']['headline']}, mode {att['mode']}) "
                          f"[{results['built']}/{len(todo)}]", flush=True)
                except BaseException as e:  # noqa: BLE001
                    L.mark(a.release, r["school_id"], "failed", error=str(e)[:1500])
                    results["failed"] += 1
                    print(f"  FAILED {r['slug']}: {str(e).splitlines()[0][:200]}", flush=True)
                while queue and len(futures) < a.concurrency:
                    while mem_available_gb() < MIN_FREE_GB and futures:
                        time.sleep(15)
                    submit_next()
    summary = {**results, "seconds": round(time.time() - t0, 1), "selected": len(rows), "todo": len(todo)}
    L.finish_run(run_id, a.release, summary)
    print(json.dumps(summary))
    if results["failed"]:
        sys.exit(2)


def cmd_rebuild(a):
    """Rule 10: rebuild a random fraction into a second tree and compare every served file."""
    spec = prepare(a)
    evid_first = Path(spec["evidence"]) / a.release
    L = Ledger(evid_first / "ledger.sqlite")
    built = [j for j in L.jobs(a.release) if j["status"] in ("built", "staged", "verified", "published")]
    rnd = random.Random(a.seed)
    k = max(1, round(len(built) * a.fraction))
    picked = sorted(rnd.sample(built, k), key=lambda j: j["school_id"])
    reg = json.loads(Path(a.register).read_text(encoding="utf-8"))
    rows = {r["school_id"]: r for r in reg["schools"]}
    a.out = a.out + "_rebuild"; a.evidence = a.evidence + "_rebuild"; a.work = a.work + "_rebuild"
    spec2 = prepare(a)
    spec2["membership_key"] = spec["membership_key"]     # the first tree's key, so the bindings can match
    out2 = Path(spec2["out"]) / a.release
    if not (out2 / "r" / a.release / "assets" / "assets.json").exists():
        htmlcore.build_assets(out2, a.release, Path(spec2["yac"]), Path(spec2["fonts"]), ROOT / "config" / "cover_media")
    report = {"release": a.release, "fraction": a.fraction, "seed": a.seed, "schools": [], "identical": 0, "different": 0}
    for j in picked:
        js = dict(spec2, row=rows[j["school_id"]], run_id="rebuild-" + a.seed.__str__())
        first = L.attestation(a.release, j["school_id"])
        # the same inputs as the first build: its previous lock (or none) and its ruling text
        js["previous_lock"] = first.get("previousLock")
        js["lock_ruling"] = first.get("lockRuling")
        js["membership_key"] = spec["membership_key"]
        att = build_one(js)
        a_inv = {f["path"]: f["sha256"] for f in first["inventory"]}
        b_inv = {f["path"]: f["sha256"] for f in att["inventory"]}
        diff = sorted(p for p in set(a_inv) | set(b_inv) if a_inv.get(p) != b_inv.get(p))
        same = not diff and first["binding"] == att["binding"] and first["membershipFingerprint"] == att["membershipFingerprint"]
        report["schools"].append({"school_id": j["school_id"], "slug": j["slug"], "identical": same, "differing": diff[:10],
                                  "firstHost": first.get("host"), "secondHost": att.get("host")})
        report["identical" if same else "different"] += 1
        print(f"  {j['slug']}: {'identical' if same else 'DIFFERENT ' + str(diff[:3])}", flush=True)
    (Path(spec2["evidence"]) / a.release / "rebuild_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "schools"}))
    if report["different"]:
        sys.exit(3)


def cmd_status(a):
    L = Ledger(Path(a.evidence) / a.release / "ledger.sqlite")
    print(json.dumps(L.status(a.release), indent=1))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p):
        p.add_argument("--release", required=True); p.add_argument("--register", required=True)
        p.add_argument("--dataset", required=True); p.add_argument("--dataset-sha256")
        p.add_argument("--out", required=True); p.add_argument("--evidence", required=True); p.add_argument("--work", required=True)
        p.add_argument("--key-vault"); p.add_argument("--link-secret")
        p.add_argument("--jsdom"); p.add_argument("--label"); p.add_argument("--site-prefix", default="/")
        p.add_argument("--probe", action="store_true"); p.add_argument("--keep-work", action="store_true")
        p.add_argument("--force", action="store_true"); p.add_argument("--allow-dirty", action="store_true",
                                                                       help="development only: skip rule 1")
        p.add_argument("--known-failures", default="STK-caption-case,CAT-values,GOV-mode",
                       help="gate ids allowed to fail in the stock reruns (the recorded disputed/pending items)")
        p.add_argument("--slice-parallel", action="store_true", help="run the three state slices concurrently inside a job")
        p.add_argument("--previous-locks"); p.add_argument("--lock-ruling", default="")

    r = sub.add_parser("run"); common(r)
    r.add_argument("--concurrency", type=int, default=max(1, (os.cpu_count() or 2) - 2))
    r.add_argument("--schools"); r.add_argument("--sample", type=int); r.add_argument("--seed", type=int, default=2026)
    r.add_argument("--all", action="store_true")
    r.set_defaults(func=cmd_run)
    rb = sub.add_parser("rebuild"); common(rb)
    rb.add_argument("--fraction", type=float, default=0.05); rb.add_argument("--seed", type=int, default=2026)
    rb.set_defaults(func=cmd_rebuild)
    st = sub.add_parser("status"); st.add_argument("--evidence", required=True); st.add_argument("--release", required=True)
    st.set_defaults(func=cmd_status)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
