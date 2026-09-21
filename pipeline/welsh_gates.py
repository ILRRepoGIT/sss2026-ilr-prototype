# -*- coding: utf-8 -*-
"""Corpus acceptance gates for the Welsh narrative (Framework v1.6 sheet 36,
decision D45): the appraisal's runnable gate script, applied at BUILD time to
the in-memory package so a failing corpus never becomes a shipped file.

The gate logic itself is the vendored, unmodified appraisal script
(vendor_welsh_gates.py) — the release contract is their implementation, not a
reimplementation. This wrapper only adapts the input (package states instead
of a built HTML file) and applies the thresholds:

  * every gate must return zero, except
  * G3a+ — report-only by the gate's own definition (linguist ruling), and
  * G4 zero-figure residue: where the LOCKED English renders a nil count as
    the digit 0 ('…, 0 said yes.'), the framework (FT-01, NUM-N0-NEG)
    requires a Welsh negative clause with no figure, so the English 0 can
    have no Welsh counterpart. Those paragraphs — and only those — are
    excluded from G4 with a note, and reported for the appraiser
    (a one-line amendment to the gate script is proposed in the reply).
"""
from __future__ import annotations

import collections
import re

from . import vendor_welsh_gates as V

_EN_ZERO = re.compile(r"(?<!\d)0 (said|did)\b")


def rows_from_states(states):
    seen = collections.Counter()
    for sk, st in states.items():
        for mid, m in (st.get("mod") or {}).items():
            for p in (m.get("p") or []):
                seen[(mid, sk.split("|")[1],
                      p.get("t") or "", p.get("c") or "")] += 1
    return [{"m": k[0], "gender": k[1], "t": k[2], "c": k[3], "n": v}
            for k, v in seen.items()]


def run(states):
    """Returns (failures, results, notes). failures is a list of strings for
    the build's QA error list; empty means releasable."""
    R = rows_from_states(states)
    results = V.gates(R)
    failures, notes = [], []
    for g in results:
        if g["id"] == "G3a+":
            if g["paragraphs"]:
                notes.append(f"G3a+ mixed-magnitude figures before nouns: "
                             f"{g['paragraphs']} paragraphs (report-only, "
                             f"linguist ruling)")
            continue
        if g["id"] == "G4" and not g["pass"]:
            # split the locked-English digit-zero residue from real failures
            zero_rows, real = [], []
            for r in R:
                if V.numset(r["t"], V.EN_NUM, True) - V.numset(r["c"], V.CY_NUM):
                    (zero_rows if (_EN_ZERO.search(r["t"]) and
                                   V.numset(r["t"], V.EN_NUM, True)
                                   - V.numset(r["c"], V.CY_NUM) == {0})
                     else real).append(r)
            if zero_rows:
                notes.append(
                    f"G4 excluded {sum(r['n'] for r in zero_rows)} paragraphs "
                    f"where the locked English digit 0 becomes the required "
                    f"Welsh negative clause (FT-01 N=0) — proposed gate-script "
                    f"amendment sent to the appraiser")
            if real:
                ex = real[0]
                failures.append(
                    f"welsh gate G4: {sum(r['n'] for r in real)} paragraphs "
                    f"({len(real)} unique) | EN: {ex['t'][:90]} | CY: "
                    f"{ex['c'][:90]}")
            continue
        if not g["pass"]:
            ex = g["examples"][0] if g["examples"] else {"en": "", "cy": ""}
            failures.append(
                f"welsh gate {g['id']} ({g['title']}): {g['paragraphs']} "
                f"paragraphs | EN: {ex['en'][:90]} | CY: {ex['cy'][:90]}")
    return failures, results, notes
