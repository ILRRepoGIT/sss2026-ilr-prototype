# -*- coding: utf-8 -*-
"""Framework v1.9 acceptance (D60/D65): the V4.6 handover pack's gate
script v4, run at build time over the in-memory package — every generated
surface plus the client source — so a failing corpus never becomes a
shipped file. The gate logic is the vendored, unmodified pack script
(vendor_welsh_gates_v4); this wrapper only adapts the input: it feeds the
package as the script's payload, derives the surfaces with the script's
OWN loader, points the config loader at the framework workbook, and reads
the client source from the repo. v4 supersedes the v3 set (the pack's own
manifest correction: 47 blocking + 6 report-only + 2 manual).

Build modes (D64): in 'dev' CAT-values is report-only (the translator's
outstanding values render as ⟪missing:key⟫ markers in the client); in
'release' it blocks. The build itself is a dev build until the translator
returns; both gate runs are shipped with it.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import vendor_welsh_gates_v4 as V4
from .common import CONFIG_DIR

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def framework_path():
    """The framework workbook the lexicon was built from, if present next
    to the repo; falls back to the copy recorded in config."""
    cand = sorted(CONFIG_DIR.glob("*Framework*v1.9*.xlsx"))
    if cand:
        return str(cand[0])
    for c in (Path("/tmp/v46pack/01_Framework_v1.9.xlsx"),):
        if c.exists():
            return str(c)
    return None


def run(package, mode="dev"):
    """-> (blocking_failures, results, notes) in the shape run_qa_checks
    expects. Every gate the stock script marks blocking that FAILs
    becomes a build error; report-only gates become warnings."""
    fw = framework_path()
    if fw:
        V4.load_framework(fw)
    S = V4.surfaces_from_states(package["states"], package.get("metricDefs"))
    js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    G = V4.run(package, S, js, mode=mode)
    failures, notes = [], []
    for g in G:
        if g["blocking"] is True and g["status"] == "FAIL":
            ex = g["examples"][0] if g["examples"] else {}
            failures.append(
                f"welsh gate v4 {g['id']}: {g['occurrences']} occurrences "
                f"({g['records']} records) — {g['title']}"
                + (f" e.g. {ex.get('where')} «{ex.get('matched')}»"
                   if ex else ""))
        elif g["blocking"] is False and g["occurrences"]:
            notes.append(f"welsh gate v4 {g['id']} (report-only): "
                         f"{g['occurrences']} occurrences — {g['title']}")
    blocking = [g for g in G if g["blocking"] is True]
    passed = sum(1 for g in blocking if g["status"] == "PASS")
    notes.append(f"welsh gates v4: {passed}/{len(blocking)} blocking pass "
                 f"(manifest {V4.MANIFEST_HASH}, mode {mode}, "
                 f"config {V4.CFG.get('source')})")
    return failures, G, notes
