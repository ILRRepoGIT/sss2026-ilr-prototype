# -*- coding: utf-8 -*-
"""Assemble one real school's assurance bundle beside its report and run
the two stock reruns (D81, sheet 52) — the V4.15 procedure (make_bundle)
applied to a per-school build tree (pipeline 0.28.0, V5.0 real-school round).

    SSS_GENERATED_DIR=<school build tree> python -m pipeline.make_school_bundle <slug> <version>
        e.g. SSS_GENERATED_DIR=/…/schools/new-inn-primary-school/generated \\
             python -m pipeline.make_school_bundle new-inn-primary-school V5.0

Steps: copy <tree>/report.html to <tree>/SSS2026_ILR_Report_<version>_<slug>_Bilingual.html;
write <tree>/bundle (stock runner, framework, the school's own baseline lock
— the lock the build EMITTED, since a school's first build has no earlier
lock — the PHASE-1 evidence the build wrote, the browser harness,
write_verify.py, RUN.md); write manifest.json with every sha256; run the
stock runner in dev (--emit-lock lock_<slug>_v8_emitted.json) and release
mode with the bundle asserted; write verify.json. Prints the headlines and
whether the rerun's emitted lock equals the build's in all three locked
parts. Nothing here changes a gate.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .common import CONFIG_DIR, GENERATED_DIR, ROOT

PIPE = ROOT / "pipeline"
PROTO_BUNDLE = ROOT / "generated" / "bundle"     # the V4.15 bundle: write_verify.py is reused verbatim


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


RUN_MD = """# {v} assurance bundle — {school} — one command reproduces everything (D81, sheet 52)

Ships beside `{rep}`. `manifest.json` lists the runner, framework, baseline, phase-1 evidence, browser
harness and the report with their sha256 values; the runner, framework, baseline and evidence hashes equal
the values stamped in the report's `buildMetadata.gateResults` / `identity`. Prerequisites: Python 3.10+,
`pip install openpyxl`; for the browser gate `pip install playwright && playwright install chromium`.

    cd <this directory>
    python welsh_acceptance_gates_v8.py --selftest                                    # 68/68 + CONJ-06 modes OK
    python welsh_acceptance_gates_v8.py ../{rep} --framework {fw} \\
        --mode dev     --baseline {baseline} --bundle-dir . --json results_dev.json \\
        --evidence evidence_rerun_dev.ndjson.gz --emit-lock {emitted}
    python welsh_acceptance_gates_v8.py ../{rep} --framework {fw} \\
        --mode release --baseline {baseline} --bundle-dir . --json results_release.json \\
        --evidence evidence_rerun_release.ndjson.gz
    python write_verify.py ../{rep} results_release.json results_dev.json
    python browser_gate_provenance.py ../{rep} --states 60 --fixture auto --json browser_gate.json

Gate pack v8 (unchanged since V4.15, sha256 in the manifest): CONJ-06 asserted against the reading the
Framework names on sheet 11 (`MODE=figure`, D84). The Framework this build read is `{fw}` (sha256
{fw_sha}); its own README row (sheet 00) states what changed in it and the round's entry in
`sw-feedback-compliance-record.md` names the ruling, if any, under which the corpus moved.

Baseline (D82): `{baseline}` is this school's OWN corpus lock, EMITTED by the build's QA stage
({lock_para}). The reruns here assert GOV-lock-cy and FT11-keyset against it. A rebuild of this school
asserts against this lock; a change must cite a ruling.

Two-phase stamp (D81): the build ran the vendored, byte-identical v8 runner on the unstamped package,
stamped `gateResults {{blockingPass, blockingTotal, headline, pending, disputed}}`, and the runs above re-run
the same runner on the stamped file with the bundle asserted. `verify.json` is written from that rerun and
is the only statement of the final status. STK-caption-case (disputed, pack defect, V4.9 register),
CAT-values in release mode (the 72 engine- and client-owned catalogue rows with no Welsh value) and
GOV-mode (the owner's unsigned D69) are the same known items as on the V4.15 prototype.

The pupil-level export this report was built from is INPUT DATA and is not part of this bundle; the
`sourceChecksum` in `buildMetadata` is its sha256, and `config/schools/{slug}.json` records the dataset,
its sha256 and the inclusion rule.
"""


def lock_paragraph(lock: dict) -> str:
    """One sentence from the lock's own `emitted` part: first emission, or a
    re-emission under a recorded ruling, or asserted against a previous lock."""
    e = lock.get("emitted") or {}
    ruling = (e.get("ruling") or "").strip()
    sup = e.get("supersedes")
    if sup:
        return (f"asserted against the previous lock `{sup}` during the build — "
                f"{e.get('englishStatesMoved', 0)} English and {e.get('welshStatesMoved', 0)} Welsh states moved; "
                f"ruling recorded: {ruling}" if ruling else
                f"asserted against the previous lock `{sup}` during the build — "
                f"{e.get('englishStatesMoved', 0)} English and {e.get('welshStatesMoved', 0)} Welsh states moved")
    if ruling:
        return ("a re-emission with no previous lock asserted (SSS_PREVIOUS_LOCK=none; GOV-lock is REPORT for that run) "
                f"under the recorded ruling: {ruling}")
    return ("a real school's first build has no earlier lock to assert against (SSS_PREVIOUS_LOCK=none; "
            "GOV-lock is REPORT for that run)")


def write_run_md(b: Path, v: str, pkg: dict, rep: Path, fw: Path, baseline: str, emitted: str, slug: str) -> None:
    lock = json.load(open(b / baseline, encoding="utf-8"))
    (b / "RUN.md").write_text(RUN_MD.format(v=v, school=pkg["school"]["name"], rep=rep.name, fw=fw.name,
                                            fw_sha=sha(b / fw.name), lock_para=lock_paragraph(lock),
                                            baseline=baseline, emitted=emitted, slug=slug), encoding="utf-8")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    slug, v = args[0], args[1]
    tree = GENERATED_DIR
    rep = tree / f"SSS2026_ILR_Report_{v}_{slug}_Bilingual.html"
    if "--run-md-only" in sys.argv:
        # rewrite RUN.md of an existing bundle from the files it already holds (RUN.md is not in the manifest)
        from .common import latest_framework
        b = tree / "bundle"
        pkg = json.load(open(tree / f"{slug}.report.json", encoding="utf-8"))
        write_run_md(b, v, pkg, rep, latest_framework(CONFIG_DIR), f"lock_{slug}_v8.json",
                     f"lock_{slug}_v8_emitted.json", slug)
        print("RUN.md rewritten:", b / "RUN.md")
        return
    shutil.copyfile(tree / "report.html", rep)
    b = tree / "bundle"
    if b.exists():
        shutil.rmtree(b)
    b.mkdir()
    shutil.copyfile(PIPE / "vendor_welsh_gates_v8.py", b / "welsh_acceptance_gates_v8.py")
    shutil.copyfile(PIPE / "vendor_browser_gate_v3.py", b / "browser_gate_provenance.py")
    shutil.copyfile(PROTO_BUNDLE / "write_verify.py", b / "write_verify.py")
    from .common import latest_framework
    fw = latest_framework(CONFIG_DIR)
    shutil.copyfile(fw, b / fw.name)
    baseline_src = tree / f"lock_{slug}_v8.json"
    assert baseline_src.exists(), f"the build did not emit {baseline_src.name}"
    baseline = baseline_src.name
    emitted = f"lock_{slug}_v8_emitted.json"
    shutil.copyfile(baseline_src, b / baseline)
    shutil.copyfile(tree / "welsh_gate_evidence_build.ndjson.gz", b / "evidence.ndjson.gz")
    pkg = json.load(open(tree / f"{slug}.report.json", encoding="utf-8"))
    stamp = pkg["buildMetadata"]["gateResults"]
    assert sha(b / "evidence.ndjson.gz") == stamp["evidenceSha256"], "phase-1 evidence is not the file the stamp names"
    assert sha(b / baseline) == stamp["baselineSha256"], "the stamp was not taken against this school's emitted lock"
    files = {"runner": "welsh_acceptance_gates_v8.py", "framework": fw.name, "baseline": baseline,
             "evidence": "evidence.ndjson.gz", "browserHarness": "browser_gate_provenance.py"}
    man = {"report": f"../{rep.name}", "runner": "8.0.0", "manifestHash": stamp["manifestHash"], "mode": "release",
           "school": {"slug": slug, "id": pkg["school"]["id"], "name": pkg["school"]["name"]},
           "command": (f"python welsh_acceptance_gates_v8.py ../{rep.name} --framework {fw.name} "
                       f"--mode release --baseline {baseline} --bundle-dir . --json results_release.json "
                       f"--evidence evidence_rerun_release.ndjson.gz"),
           "files": {k: {"path": p, "sha256": sha(b / p)} for k, p in files.items()}}
    man["files"]["report"] = {"path": f"../{rep.name}", "sha256": sha(rep)}
    (b / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    write_run_md(b, v, pkg, rep, fw, baseline, emitted, slug)
    out = {}
    for mode in ("dev", "release"):
        cmd = [sys.executable, "welsh_acceptance_gates_v8.py", f"../{rep.name}", "--framework", fw.name,
               "--mode", mode, "--baseline", baseline, "--bundle-dir", ".", "--json", f"results_{mode}.json",
               "--evidence", f"evidence_rerun_{mode}.ndjson.gz"]
        if mode == "dev":
            cmd += ["--emit-lock", emitted]
        r = subprocess.run(cmd, cwd=b, capture_output=True, text=True)
        (b / f"runner_bundle_{mode}.json").write_text(json.dumps({"cmd": cmd, "rc": r.returncode,
                                                                   "stdout_tail": r.stdout[-3000:], "stderr_tail": r.stderr[-2000:]}, indent=1))
        res = json.load(open(b / f"results_{mode}.json", encoding="utf-8"))
        s = res["summary"]
        out[mode] = {"headline": f'{s["blocking_pass"]}/{s["blocking_total"]}',
                     "paths": f'{s["paths"]["complete"]}/{s["paths"]["total"]}',
                     "failing": [(g["id"], g["occurrences"]) for g in res["gates"] if g["status"] == "FAIL"]}
    subprocess.run([sys.executable, "write_verify.py", f"../{rep.name}", "results_release.json", "results_dev.json"],
                   cwd=b, check=True, capture_output=True)
    out["report"] = rep.name
    out["reportSha256"] = man["files"]["report"]["sha256"]
    out["reportBytes"] = rep.stat().st_size
    out["baseline"] = baseline
    out["baselineSha256"] = sha(b / baseline)
    e, bl = json.load(open(b / emitted, encoding="utf-8")), json.load(open(b / baseline, encoding="utf-8"))
    out["emittedEqualsBaseline"] = {k: e.get(k) == bl.get(k) for k in ("english", "welsh", "ft11")}
    out["states"] = len(bl["english"])
    (tree / "bundle_summary.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
