# -*- coding: utf-8 -*-
"""Assemble the assurance bundle beside the report and run the two stock
reruns (D81, sheet 52) — the V4.9 procedure, scripted for V4.10 onwards.

    python -m pipeline.make_bundle <version>   e.g. V4.10

Steps: copy generated/report.html to generated/SSS2026_ILR_Report_<v>_Bilingual.html;
refresh generated/bundle (stock runner, framework, baseline lock, the
PHASE-1 evidence the build wrote, the browser harness, write_verify.py,
RUN.md); write manifest.json with every sha256; run the stock runner in dev
(--emit-lock lock_<v>_v8.json) and release mode with the bundle asserted;
write verify.json. Prints the headlines. Nothing here changes a gate.
"""
from __future__ import annotations

import hashlib
import re
import json
import shutil
import subprocess
import sys
from pathlib import Path

from .common import CONFIG_DIR, GENERATED_DIR, ROOT

PIPE = ROOT / "pipeline"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    v = sys.argv[1]
    vtag = v.replace(".", "")            # V4.10 -> V410
    rep = GENERATED_DIR / f"SSS2026_ILR_Report_{v}_Bilingual.html"
    shutil.copyfile(GENERATED_DIR / "report.html", rep)
    b = GENERATED_DIR / "bundle"
    b.mkdir(exist_ok=True)
    for old in b.glob("results_*.json"):
        old.unlink()
    for old in list(b.glob("evidence_rerun_*")) + list(b.glob("runner_bundle_*")) + [b / "verify.json"]:
        if old.exists():
            old.unlink()
    for old in list(b.glob("lock_V*_v7.json")) + list(b.glob("lock_V*_v8.json")) + list(b.glob("welsh_acceptance_gates_v*.py")):
        old.unlink()
    # V4.15: gate pack v8 (CONJ-06 read from sheet 11, D84); the baseline is
    # the V4.15 lock once emitted (its English part equals the V4.8 lock's),
    # else the V4.8 lock for the very first emission
    shutil.copyfile(PIPE / "vendor_welsh_gates_v8.py", b / "welsh_acceptance_gates_v8.py")
    shutil.copyfile(PIPE / "vendor_browser_gate_v3.py", b / "browser_gate_provenance.py")
    from .common import latest_framework
    fw = latest_framework(CONFIG_DIR)
    for old in b.glob("01_Framework_v*.xlsx"):
        old.unlink()
    shutil.copyfile(fw, b / fw.name)
    baseline_src = (CONFIG_DIR / "02c_lock_V415_v8.json"
                    if (CONFIG_DIR / "02c_lock_V415_v8.json").exists() else CONFIG_DIR / "02c_lock_V48_v7.json")
    baseline = "lock_V415_v8.json" if baseline_src.name.endswith("V415_v8.json") else "lock_V48_v7.json"
    shutil.copyfile(baseline_src, b / baseline)
    shutil.copyfile(GENERATED_DIR / "welsh_gate_evidence_build.ndjson.gz", b / "evidence.ndjson.gz")
    stamp = json.load(open(GENERATED_DIR / "ysgol-penrhyn-dewi.report.json", encoding="utf-8"))["buildMetadata"]["gateResults"]
    assert sha(b / "evidence.ndjson.gz") == stamp["evidenceSha256"], "phase-1 evidence is not the file the stamp names"
    files = {
        "runner": "welsh_acceptance_gates_v8.py", "framework": fw.name,
        "baseline": baseline, "evidence": "evidence.ndjson.gz",
        "browserHarness": "browser_gate_provenance.py",
    }
    man = {"report": f"../{rep.name}", "runner": "8.0.0", "manifestHash": stamp["manifestHash"],
           "mode": "release",
           "command": (f"python welsh_acceptance_gates_v8.py ../{rep.name} --framework {fw.name} "
                       f"--mode release --baseline {baseline} --bundle-dir . --json results_release.json "
                       f"--evidence evidence_rerun_release.ndjson.gz"),
           "files": {k: {"path": p, "sha256": sha(b / p)} for k, p in files.items()}}
    man["files"]["report"] = {"path": f"../{rep.name}", "sha256": sha(rep)}
    (b / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    run_md = (b / "RUN.md").read_text(encoding="utf-8")
    run_md = re.sub(r"V4\.\d+", v, run_md)
    run_md = re.sub(r"lock_V\d+_v8_emitted\.json", f"lock_{vtag}_v8_emitted.json", run_md)
    run_md = run_md.replace("welsh_acceptance_gates_v7.py", "welsh_acceptance_gates_v8.py")
    run_md = re.sub(r"--baseline lock_V\d+_v[78]\.json", f"--baseline {baseline}", run_md)
    run_md = re.sub(r"01_Framework_v2\.\d+\.xlsx", fw.name, run_md)
    (b / "RUN.md").write_text(run_md, encoding="utf-8")
    out = {}
    for mode in ("dev", "release"):
        cmd = [sys.executable, "welsh_acceptance_gates_v8.py", f"../{rep.name}", "--framework", fw.name,
               "--mode", mode, "--baseline", baseline, "--bundle-dir", ".", "--json", f"results_{mode}.json",
               "--evidence", f"evidence_rerun_{mode}.ndjson.gz"]
        if mode == "dev":
            # the emitted lock must never overwrite the baseline it is
            # compared with (V4.15: the baseline IS this version's lock)
            emitted = f"lock_{vtag}_v8.json" if baseline != f"lock_{vtag}_v8.json" else f"lock_{vtag}_v8_emitted.json"
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
    out["reportSha256"] = man["files"]["report"]["sha256"]
    out["lock"] = sha(b / emitted)
    out["emitted"] = emitted
    out["baseline"] = baseline
    # the three locked parts of the emitted lock must equal the baseline's
    e, bl = json.load(open(b / emitted, encoding="utf-8")), json.load(open(b / baseline, encoding="utf-8"))
    out["emittedEqualsBaseline"] = {k: e.get(k) == bl.get(k) for k in ("english", "welsh", "ft11")}
    old = CONFIG_DIR / "02c_lock_V48_v7.json"
    if old.exists():
        v48 = json.load(open(old, encoding="utf-8"))
        out["englishEqualsV48"] = e.get("english") == v48.get("english")
        out["ft11EqualsV48"] = e.get("ft11") == v48.get("ft11")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
