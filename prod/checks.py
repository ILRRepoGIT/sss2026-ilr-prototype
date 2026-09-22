# -*- coding: utf-8 -*-
"""Checking at scale (deployment plan §8; review G02–G04, G09, G11, G14):
the machine-checkable properties, checked on every report without exception.

    python -m prod.checks rollup      --evidence <root> --release <tag>
    python -m prod.checks reconcile   --evidence <root> --release <tag> --register <register.json> --dataset <parquet>
    python -m prod.checks served-gate --evidence <root> --release <tag> --site <dir | https://host> [--sample N] [--all-chunks]
    python -m prod.checks link-export --evidence <root> --release <tag> --base-url https://reports.example --out links.csv

rollup       every attestation of the release must carry the SAME identity
             (release manifest, framework, gate runner, pipeline, served
             schema, mode) and the SAME gate outcome (headline, pending,
             disputed), and every per-report check must be clean (served
             package verified, figures reconciled, provenance 0/0/0, the
             rerun's lock equal to the build's). Writes rollup.json and
             rollup.md; exit 1 if the set is not uniform and clean.
reconcile    the universe (G02): every eligible register row has exactly one
             attestation and nothing else does; and the counts (G04, set
             level): each report's accepted responses equal the dataset's
             rows for that school, and the sum over built + held + below-
             threshold schools equals the dataset's matched-school rows.
served-gate  the artefact actually served (G09/G11): for each report, fetch
             the entry page, read its embedded core payload, check the
             envelope and chunk map against the attestation, fetch the
             chunks (all, or a stratified sample of reports with all their
             chunks), verify each file's sha256 and envelope, rebuild the
             per-state hashes and compare with the private package index;
             over HTTP also check the response headers, that a wrong token
             and a directory listing return 404, and that the shared assets
             match assets.json. Writes served_gate.json.
link-export  the CMS / distribution list: one row per report with its URL.
             The file carries bearer links — it is written read-only to the
             owner and must be handled as confidential.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

from prod.chunker import canon, group_of
from prod.ledger import now, Ledger

REQUIRED_HEADERS = {"x-robots-tag": "noindex", "x-content-type-options": "nosniff",
                    "referrer-policy": "no-referrer", "content-security-policy": "script-src 'self'"}


def load_attestations(evidence: Path, release: str) -> dict:
    L = Ledger(evidence / release / "ledger.sqlite")
    return L.attestations(release), L


# --------------------------------------------------------------------------- rollup
def rollup(evidence: Path, release: str) -> dict:
    atts, L = load_attestations(evidence, release)
    jobs = {j["school_id"]: j for j in L.jobs(release)}
    ident_keys = ("release", "manifestSha256", "commit", "prodVersion", "schema", "pipelineVersion", "reportVersion", "mode")
    # V6.0 (owner instruction, 22 Sep 2026): a school with fewer than five accepted
    # responses receives a report whose whole-school view is suppressed. Its gate
    # outcomes legitimately differ from a standard report's (no captions to
    # dispute, every renderer path trivially complete), so the set is checked for
    # uniformity within each of the two classes — standard, whole-school
    # suppressed — and both expected groups are reported.
    groups = Counter()
    per = {}
    problems = []
    classes = {}
    for sid, a in atts.items():
        cls = "whole-school suppressed" if "suppressedWholeSchool" in (a.get("figures") or {}).get("checked", []) else "standard"
        classes[sid] = cls
        ident = (cls,) + tuple(a.get(k) for k in ident_keys) + (
            a["identity"].get("frameworkSha256"), a["identity"].get("manifestHash"), a["identity"].get("runnerVersion"),
            a["gateStamp"].get("headline"), tuple(sorted(a["gateStamp"].get("pending") or [])),
            tuple(sorted(a["gateStamp"].get("disputed") or [])),
            a["bundle"]["dev"]["headline"], a["bundle"]["release"]["headline"], a["bundle"]["dev"]["paths"],
            tuple(sorted(g for g, _ in a["bundle"]["dev"]["failing"])), tuple(sorted(g for g, _ in a["bundle"]["release"]["failing"])))
        groups[ident] += 1
        clean = []
        if not a["servedVerify"]["ok"] or a["servedVerify"]["statesMoved"]:
            clean.append("served package not verified")
        if not a["figures"].get("allMatch"):
            clean.append("independent figures do not match")
        if not all(a["bundle"]["emittedEqualsBaseline"].values()):
            clean.append("rerun lock differs from the build's baseline")
        pv = a["jsdom"]["provenance"]
        if pv.get("englishWithoutProvenance") or pv.get("welshWithoutProvenance") or pv.get("typographyFaults") or pv.get("toggleFailures"):
            clean.append("provenance port not clean")
        js = a["jsdom"]["school"]
        if js.get("fail"):
            clean.append(f"jsdom school regression {js.get('fail')} failures")
        if a["largestChunkBytes"] > 7.5 * 1024 * 1024:
            clean.append(f"chunk above 7.5 MiB ({a['largestChunkBytes']})")
        per[sid] = {"slug": a["slug"], "class": cls, "status": jobs.get(sid, {}).get("status"), "problems": clean,
                    "seconds": a["seconds"], "states": a["states"], "chunks": a["chunks"], "entryBytes": a["entryBytes"]}
        problems.extend(f"{a['slug']}: {p}" for p in clean)
    names = ["class"] + list(ident_keys) + ["frameworkSha256", "gateManifestHash", "runnerVersion", "stampHeadline", "pending", "disputed",
                                            "rerunDev", "rerunRelease", "paths", "failingDev", "failingRelease"]
    by_class = {}
    for key in groups:
        by_class.setdefault(key[0], []).append(key)
    uniform = all(len(v) == 1 for v in by_class.values())
    if not uniform:
        for cls, keys in by_class.items():
            if len(keys) > 1:
                cols = list(zip(*keys))
                varying = [names[i] for i, c in enumerate(cols) if len(set(c)) > 1]
                problems.insert(0, f"the {cls} set is NOT uniform: {len(keys)} identity/outcome groups; varying: {varying}")
    # identity (everything but the gate outcomes) must agree ACROSS the classes too
    ident_span = {key[1:1 + len(ident_keys) + 3] for key in groups}
    if len(ident_span) > 1:
        uniform = False
        problems.insert(0, f"release identity differs across the classes: {len(ident_span)} identities")
    modes = Counter(a["mode"] for a in atts.values())
    secs = [a["seconds"] for a in atts.values()]
    expected = {cls: {k: v for k, v in zip(names, keys[0])} for cls, keys in by_class.items() if len(keys) == 1}
    out = {"release": release, "reports": len(atts), "uniform": uniform, "groups": len(groups),
           "classes": dict(Counter(classes.values())),
           "modes": dict(modes), "jobStatus": dict(Counter(j["status"] for j in jobs.values())),
           "expected": expected.get("standard", {}), "expectedByClass": expected,
           "seconds": {"total": round(sum(secs), 1), "mean": round(sum(secs) / len(secs), 1) if secs else None,
                       "max": max(secs) if secs else None},
           "chunkBytesTotal": sum(a["chunkBytes"] for a in atts.values()),
           "problems": problems, "ok": uniform and not problems, "reports_detail": per}
    root = evidence / release
    (root / "rollup.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    md = [f"# Rollup — {release}", "", f"Reports with an attestation: {len(atts)} · uniform: {uniform} · clean: {out['ok']}",
          f"Modes: {dict(modes)} · job status: {out['jobStatus']}",
          f"Build seconds: total {out['seconds']['total']}, mean {out['seconds']['mean']}, max {out['seconds']['max']}",
          f"Served bytes (chunks): {out['chunkBytesTotal'] / 1e9:.2f} GB", ""]
    md += [f"Classes: {out['classes']}", ""]
    for cls, exp in expected.items():
        md += [f"Expected (uniform) values — {cls} ({out['classes'].get(cls, 0)} reports):", ""] + [f"- {k}: {v}" for k, v in exp.items()] + [""]
    md += ["Problems:", ""] + ([f"- {p}" for p in problems] or ["- none"])
    (root / "rollup.md").write_text("\n".join(md), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- reconcile
def reconcile(evidence: Path, release: str, register: Path, dataset: Path) -> dict:
    import pyarrow.parquet as pq
    atts, L = load_attestations(evidence, release)
    reg = json.loads(register.read_text(encoding="utf-8"))
    rows = {r["school_id"]: r for r in reg["schools"]}
    t = pq.ParquetFile(dataset).read(columns=["school_id", "school_ref_status", "analytical_inclusion_flag", "year_group_num"]).to_pandas()
    t = t[t["analytical_inclusion_flag"].astype(bool)]
    matched = t[t["school_ref_status"] == "Matched school"]
    counts = matched.groupby("school_id").size().to_dict()
    problems = []
    eligible = {sid for sid, r in rows.items() if r["status"] == "eligible"}
    built = set(atts)
    missing = sorted(eligible - built)
    extra = sorted(built - eligible)
    for sid, a in atts.items():
        n = int(counts.get(sid, 0))
        # the report's own accepted count (buildMetadata.acceptedRows, written by the pipeline)
        # against a fresh count from the dataset, and against the rows the export received
        if a["acceptedResponses"] != n or a.get("exportRows", n) != n:
            problems.append(f"{a['slug']}: report accepted {a['acceptedResponses']} / export rows {a.get('exportRows')} != dataset {n}")
        if a["recipient"] != sid or a["profile"]["schoolId"] != sid:
            problems.append(f"{a['slug']}: recipient/profile id mismatch")
        if a["profile"]["availableYears"] != rows[sid]["years"] if sid in rows else True:
            problems.append(f"{a['slug']}: profile years differ from the register")
    total_reg = sum(r["n"] for r in rows.values())
    total_ds = int(len(matched))
    if total_reg != total_ds:
        problems.append(f"register rows {total_reg} != dataset matched-school rows {total_ds}")
    by_status = Counter(r["status"] for r in rows.values())
    out = {"release": release, "eligible": len(eligible), "built": len(built), "missing": missing, "extra": extra,
           "registerStatus": dict(by_status), "responsesRegister": total_reg, "responsesDataset": total_ds,
           "responsesBuilt": sum(a["acceptedResponses"] for a in atts.values()),
           "responsesHeldOrBelow": sum(r["n"] for r in rows.values() if r["status"] != "eligible"),
           "problems": problems, "universeComplete": not missing and not extra, "ok": not problems and not extra}
    (evidence / release / "reconcile.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- served-package gate
class Source:
    """Reads a served tree either from a directory or over HTTP."""
    def __init__(self, site: str):
        self.http = site.startswith("http://") or site.startswith("https://")
        self.site = site.rstrip("/")

    def get(self, path: str) -> tuple[int, bytes, dict]:
        if self.http:
            req = urllib.request.Request(self.site + path, headers={"Accept-Encoding": "identity", "User-Agent": "ILR-served-gate/1"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return r.status, r.read(), {k.lower(): v for k, v in r.headers.items()}
            except urllib.error.HTTPError as e:
                return e.code, b"", {k.lower(): v for k, v in (e.headers or {}).items()}
        p = Path(self.site) / path.lstrip("/")
        if path.endswith("/"):
            p = p / "index.html"
        if not p.is_file():
            return 404, b"", {}
        return 200, p.read_bytes(), {}


def _core_from_entry(html: bytes) -> dict:
    m = re.search(rb'<script id="report-data" type="application/json">(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("entry page has no report-data block")
    return json.loads(m.group(1).replace(b"<\\/", b"</").decode("utf-8"))


def served_gate(evidence: Path, release: str, site: str, sample: int | None, all_chunks: bool, seed: int = 2026) -> dict:
    atts, L = load_attestations(evidence, release)
    src = Source(site)
    ids = sorted(atts)
    rnd = random.Random(seed)
    if all_chunks or not sample or sample >= len(ids):
        full = set(ids)
    else:
        # stratified: order by profile family then size, take evenly spaced reports
        order = sorted(ids, key=lambda s: (atts[s]["profile"]["schoolType"], atts[s]["acceptedResponses"], s))
        step = len(order) / sample
        full = {order[min(len(order) - 1, int(i * step + rnd.random() * step))] for i in range(sample)}
    results = []
    problems = []
    # shared assets
    st, body, _ = src.get(f"/r/{release}/assets/assets.json")
    assets = json.loads(body) if st == 200 else None
    if not assets:
        problems.append("assets.json not served")
    else:
        for k, f in assets["files"].items():
            st, b, _ = src.get(f"/r/{release}/" + f["path"])
            if st != 200 or hashlib.sha256(b).hexdigest() != f["sha256"]:
                problems.append(f"asset {f['path']}: {'missing' if st != 200 else 'sha256 differs'}")
    if src.http:
        st, _, h = src.get("/2026/nosuchtoken0000000000000000/")
        if st != 404:
            problems.append(f"unknown token returned {st}, not 404")
        st, _, _ = src.get(f"/r/{release}/")
        if st != 404:
            problems.append(f"directory listing of /r/{release}/ returned {st}, not 404")
    for sid in ids:
        a = atts[sid]
        tok = a["token"]
        r = {"school_id": sid, "slug": a["slug"], "problems": [], "chunksChecked": 0}
        st, html, headers = src.get(f"/2026/{tok}/")
        if st != 200:
            r["problems"].append(f"entry page HTTP {st}"); results.append(r); continue
        inv = {f["path"]: f for f in a["inventory"]}
        entry_sha = hashlib.sha256(html).hexdigest()
        if inv[f"2026/{tok}/index.html"]["sha256"] != entry_sha:
            r["problems"].append("entry page bytes differ from the attestation")
        if src.http:
            for k, want in REQUIRED_HEADERS.items():
                if want not in (headers.get(k) or ""):
                    r["problems"].append(f"header {k} missing or wrong")
            cc = headers.get("cache-control") or ""
            if "no-cache" not in cc:
                r["problems"].append(f"entry page cache-control {cc!r}")
        try:
            core = _core_from_entry(html)
        except Exception as e:  # noqa: BLE001
            r["problems"].append(f"core payload unreadable: {e}"); results.append(r); continue
        ch = core.get("chunked") or {}
        if ch.get("envelope") != a["envelope"]:
            r["problems"].append("envelope in the entry page differs from the attestation")
        if core["school"]["id"] != sid or core["school"]["name"] != a["name"]:
            r["problems"].append("school identity in the core differs from the attestation")
        if core["buildMetadata"]["generatedAt"] != a["releasedAt"]:
            r["problems"].append("served generatedAt is not the release timestamp")
        chunk_files = [(g, f) for g, e in ch.get("map", {}).items() for f in e["files"]]
        if len(chunk_files) != a["chunks"]:
            r["problems"].append(f"chunk map lists {len(chunk_files)} files, attestation {a['chunks']}")
        index = json.loads((evidence / release / a["slug"] / "package_index.json").read_text(encoding="utf-8"))
        if sid in full:
            rebuilt = {}
            for g, f in chunk_files:
                st, b, h2 = src.get(f"/r/{release}/{tok}/{f['path']}")
                if st != 200:
                    r["problems"].append(f"chunk {f['path']} HTTP {st}"); continue
                if hashlib.sha256(b).hexdigest() != f["sha256"] or inv.get(f"r/{release}/{tok}/{f['path']}", {}).get("sha256") != f["sha256"]:
                    r["problems"].append(f"chunk {f['path']} sha256 differs"); continue
                if src.http and "immutable" not in (h2.get("cache-control") or ""):
                    r["problems"].append(f"chunk {f['path']} cache-control not immutable")
                body = json.loads(b.decode("utf-8"))
                if body["env"] != a["envelope"] or body["group"] != g:
                    r["problems"].append(f"chunk {f['path']} envelope/group wrong")
                for k, stt in body["states"].items():
                    if group_of(k) != g or k in rebuilt:
                        r["problems"].append(f"chunk {f['path']} key {k} misplaced or duplicated")
                    rebuilt[k] = hashlib.sha256(canon(stt)).hexdigest()
                r["chunksChecked"] += 1
            for k, st_ in core["states"].items():
                if hashlib.sha256(canon(st_)).hexdigest() != index["stateSha256"].get(k):
                    r["problems"].append(f"inline state {k} differs from the index")
            if not r["problems"]:
                if set(rebuilt) != set(index["stateSha256"]):
                    r["problems"].append(f"state set differs: {len(rebuilt)} served vs {len(index['stateSha256'])} indexed")
                else:
                    moved = sum(1 for k, h in rebuilt.items() if index["stateSha256"][k] != h)
                    if moved:
                        r["problems"].append(f"{moved} states differ from the index")
        results.append(r)
        problems.extend(f"{a['slug']}: {p}" for p in r["problems"])
    out = {"release": release, "site": site, "reports": len(ids), "fullyChecked": len(full),
           "chunksChecked": sum(r["chunksChecked"] for r in results), "problems": problems,
           "ok": not problems, "reports_detail": results}
    (evidence / release / "served_gate.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- link export
def link_export(evidence: Path, release: str, base_url: str, out: Path, register: Path | None) -> int:
    atts, L = load_attestations(evidence, release)
    jobs = {j["school_id"]: j for j in L.jobs(release)}
    reg = {r["school_id"]: r for r in json.loads(register.read_text(encoding="utf-8"))["schools"]} if register else {}
    rows = []
    for sid, a in sorted(atts.items()):
        r = reg.get(sid, {})
        rows.append([sid, a["name"], r.get("name_cy", a["name"]), a["la"], r.get("la_cy", ""), a["profile"]["schoolType"],
                     a["acceptedResponses"], jobs.get(sid, {}).get("status"), release,
                     f"{base_url.rstrip('/')}/2026/{a['token']}/"])
    for sid, r in sorted(reg.items()):
        if sid not in atts:
            rows.append([sid, r["name"], r.get("name_cy", r["name"]), r["la"], r.get("la_cy", ""), r["family"], r["n"],
                         r["status"], release, ""])
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["school_id", "name_en", "name_cy", "local_authority_en", "local_authority_cy", "profile",
                    "accepted_responses", "status", "release", "url"])
        w.writerows(rows)
    return len(rows)


def publication_register(evidence: Path, release: str, base_url: str, out: Path, register: Path | None) -> dict:
    """The website's publication register (the hosting note of 22 Sep 2026): one row per
    report the website may route to, with the fields the website's dynamic route
    /reports/{report-family}/{public_slug}/ needs — derived from the attestations
    and the recipient register, never typed. public_slug = the register's name
    slug (school name, lower-case, hyphenated) + the first 8 characters of the
    report's link token, so that two schools with one name never collide and a
    slug cannot be assigned by hand; azure_target_path is the report's entry page;
    package_hash is the sha256 over the report's file inventory (path + sha256 of
    every served file, sorted). publication_status follows the ledger: built /
    staged / verified / published / withdrawn. A publication index, when it
    exists, restricts the rows to the approved reports and stamps its sha256."""
    atts, L = load_attestations(evidence, release)
    jobs = {j["school_id"]: j for j in L.jobs(release)}
    reg = {r["school_id"]: r for r in json.loads(register.read_text(encoding="utf-8"))["schools"]} if register else {}
    idx_p = evidence / release / "publication_index.json"
    idx = json.loads(idx_p.read_text(encoding="utf-8")) if idx_p.exists() else None
    approved = {r["school_id"] for r in idx["reports"]} if idx else None
    rows, slugs, targets = [], {}, {}
    for sid, a in sorted(atts.items()):
        r = reg.get(sid, {})
        name_slug = a["slug"].rsplit("-", 1)[0] if a["slug"].rsplit("-", 1)[-1] == sid else a["slug"]
        public_slug = f"{name_slug}-{a['token'][:8].lower()}"
        entry = f"2026/{a['token']}/index.html"
        inv = sorted((f["path"], f["sha256"]) for f in a["inventory"])
        package_hash = hashlib.sha256("\n".join(f"{p}  {h}" for p, h in inv).encode("utf-8")).hexdigest()
        status = jobs.get(sid, {}).get("status", "")
        if approved is not None and sid not in approved and status not in ("withdrawn",):
            status = "not_in_publication_index"
        row = {"report_id": f"{release}:{a['family']}:{sid}", "report_family": a["family"], "entity_id": sid,
               "title_en": a["name"], "title_cy": r.get("name_cy", a["name"]),
               "public_slug": public_slug, "release_id": release,
               "azure_target_path": entry, "target_url": f"{base_url.rstrip('/')}/{entry.rsplit('/', 1)[0]}/",
               "package_hash": package_hash, "files": len(inv), "publication_status": status,
               "local_authority_en": a["la"], "local_authority_cy": r.get("la_cy", ""), "accepted_responses": a["acceptedResponses"]}
        slugs.setdefault(public_slug, []).append(sid); targets.setdefault(entry, []).append(sid)
        rows.append(row)
    problems = [f"duplicate public_slug {k}: {v}" for k, v in slugs.items() if len(v) > 1]
    problems += [f"duplicate azure_target_path {k}: {v}" for k, v in targets.items() if len(v) > 1]
    for sid, r in sorted(reg.items()):
        if sid not in atts:
            rows.append({"report_id": "", "report_family": r["family"], "entity_id": sid, "title_en": r["name"],
                         "title_cy": r.get("name_cy", r["name"]), "public_slug": "", "release_id": release,
                         "azure_target_path": "", "target_url": "", "package_hash": "", "files": 0,
                         "publication_status": r["status"], "local_authority_en": r["la"], "local_authority_cy": r.get("la_cy", ""),
                         "accepted_responses": r["n"]})
    cols = ["report_id", "report_family", "entity_id", "title_en", "title_cy", "public_slug", "release_id", "azure_target_path",
            "target_url", "package_hash", "files", "publication_status", "local_authority_en", "local_authority_cy", "accepted_responses"]
    fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(rows)
    body = {"release": release, "generatedAt": now(), "publicationIndexSha256": idx["sha256"] if idx else None,
            "routable": sum(1 for r in rows if r["public_slug"]), "rows": len(rows), "problems": problems, "reports": rows}
    jp = out.with_suffix(".json")
    fd = os.open(jp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(body, f, ensure_ascii=False, indent=1)
    return body


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("rollup", "reconcile", "served-gate", "link-export", "publication-register"):
        p = sub.add_parser(name); p.add_argument("--evidence", required=True); p.add_argument("--release", required=True)
        if name == "reconcile":
            p.add_argument("--register", required=True); p.add_argument("--dataset", required=True)
        if name == "served-gate":
            p.add_argument("--site", required=True); p.add_argument("--sample", type=int); p.add_argument("--all-chunks", action="store_true")
            p.add_argument("--seed", type=int, default=2026)
        if name in ("link-export", "publication-register"):
            p.add_argument("--base-url", required=True); p.add_argument("--out", required=True); p.add_argument("--register")
    a = ap.parse_args(argv)
    ev = Path(a.evidence)
    if a.cmd == "rollup":
        out = rollup(ev, a.release)
        print(json.dumps({k: v for k, v in out.items() if k != "reports_detail"}, indent=1, default=str))
        sys.exit(0 if out["ok"] else 1)
    if a.cmd == "reconcile":
        out = reconcile(ev, a.release, Path(a.register), Path(a.dataset))
        print(json.dumps(out, indent=1)); sys.exit(0 if out["ok"] else 1)
    if a.cmd == "served-gate":
        out = served_gate(ev, a.release, a.site, a.sample, a.all_chunks, a.seed)
        print(json.dumps({k: v for k, v in out.items() if k != "reports_detail"}, indent=1)); sys.exit(0 if out["ok"] else 1)
    if a.cmd == "link-export":
        n = link_export(ev, a.release, a.base_url, Path(a.out), Path(a.register) if a.register else None)
        print(f"{n} rows -> {a.out} (mode 0600; contains bearer links)")
    if a.cmd == "publication-register":
        out = publication_register(ev, a.release, a.base_url, Path(a.out), Path(a.register) if a.register else None)
        print(json.dumps({k: v for k, v in out.items() if k != "reports"}, indent=1))
        print(f"{out['rows']} rows ({out['routable']} routable) -> {a.out} and {Path(a.out).with_suffix('.json')} (mode 0600; contains bearer targets)")
        sys.exit(0 if not out["problems"] else 1)


if __name__ == "__main__":
    main()
