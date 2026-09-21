# -*- coding: utf-8 -*-
"""Framework v2.0 acceptance (D68/D65): the V4.7 handover pack's gate
script v5, run at build time over the in-memory package — every generated
surface, the stacked/derived data rows, and the client source. The gate
logic is the vendored, unmodified pack script (vendor_welsh_gates_v5);
this wrapper adapts the input and, per D68, returns the values the build
stamps into buildMetadata.gateResults so the build carries its own
evidence.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from . import vendor_welsh_gates_v5 as V5
from .common import CONFIG_DIR

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
RUNNER_PATH = Path(__file__).resolve().parent / "vendor_welsh_gates_v5.py"


def framework_path():
    cand = sorted(CONFIG_DIR.glob("*Framework*v2.0*.xlsx"))
    if cand:
        return str(cand[0])
    for c in (Path("/tmp/v47pack/01_Framework_v2.0.xlsx"),):
        if c.exists():
            return str(c)
    return None


def run(package, mode="dev", evidence_path=None, baseline_path=None):
    """-> (blocking_failures, results, notes, gate_results_stamp)."""
    fw = framework_path()
    if fw:
        V5.load_framework(fw)
    S = V5.surfaces_from_states(package["states"], package.get("metricDefs"))
    js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    baseline = (json.load(open(baseline_path, encoding="utf-8"))
                if baseline_path else None)
    V5.EVIDENCE.clear()
    G = V5.run(package, S, js, mode=mode, baseline=baseline)
    paths = next((g for g in G if g.get("id") == "_paths"),
                 {"paths": [], "notes": []})
    G = [g for g in G if g.get("id") != "_paths"]
    if baseline is None:
        for g in G:
            if g["id"] == "GOV-lock":
                g["status"] = "REPORT"
                g["note"] = "no baseline supplied; lock not asserted this run"
    failures, notes = [], []
    for g in G:
        if g["blocking"] is True and g["status"] == "FAIL":
            ex = g["examples"][0] if g["examples"] else {}
            failures.append(
                f"welsh gate v5 {g['id']}: {g['occurrences']} occurrences "
                f"({g['records']} records) — {g['title']}"
                + (f" e.g. {ex.get('where')} «{ex.get('matched')}»"
                   if ex else ""))
        elif g["blocking"] is False and g["occurrences"]:
            notes.append(f"welsh gate v5 {g['id']} (report-only): "
                         f"{g['occurrences']} occurrences — {g['title']}")
    blocking = [g for g in G if g["blocking"] is True]
    passed = sum(1 for g in blocking if g["status"] == "PASS")
    complete = sum(1 for p in paths["paths"] if p["status"] == "complete")
    notes.append(f"welsh gates v5: {passed}/{len(blocking)} blocking pass · "
                 f"renderer paths complete {complete}/{len(paths['paths'])} "
                 f"(manifest {V5.MANIFEST_HASH}, mode {mode}, "
                 f"config {V5.CFG.get('source')})")
    evidence_sha = None
    if evidence_path:
        with gzip.open(evidence_path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps({"record_type": "metadata",
                                 "runner": V5.VERSION,
                                 "manifest_hash": V5.MANIFEST_HASH,
                                 "mode": mode}, ensure_ascii=False) + "\n")
            for e in V5.EVIDENCE:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        evidence_sha = hashlib.sha256(
            Path(evidence_path).read_bytes()).hexdigest()
    # D68: the values the build stamps into buildMetadata.gateResults —
    # the same values the runner's own --bundle holds.
    stamp = {
        "runner": V5.VERSION,
        "runnerSha256": hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest(),
        "manifestHash": V5.MANIFEST_HASH,
        "mode": mode,
        "blockingPass": passed,
        "blockingTotal": len(blocking),
        "pathsComplete": complete,
        "pathsTotal": len(paths["paths"]),
        "evidenceSha256": evidence_sha,
        "baselineSha256": (hashlib.sha256(
            Path(baseline_path).read_bytes()).hexdigest()
            if baseline_path else None),
    }
    return failures, G, notes, stamp
