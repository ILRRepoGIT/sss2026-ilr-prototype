# -*- coding: utf-8 -*-
"""Framework v1.8 acceptance (D58): the handover pack's gate script v3, run
at build time over the in-memory package — every generated surface plus the
client source — so a failing corpus never becomes a shipped file. The gate
logic is the vendored, unmodified pack script; this wrapper only adapts the
input. Blocking = every gate the script itself marks blocking; report-only
gates are surfaced as warnings with their counts."""
from __future__ import annotations

import collections
from pathlib import Path

from . import vendor_welsh_gates_v3 as V3


def surfaces(package):
    S = {"module": [], "h1": [], "h2": [], "scope": [], "opts": []}
    seen = collections.Counter()
    for sk, st in package["states"].items():
        sex = sk.split("|")[1]
        for mid, m in (st.get("mod") or {}).items():
            for p in (m.get("p") or []):
                seen[(mid, sex, p.get("t") or "", p.get("c") or "")] += 1

        def pair(x):
            if isinstance(x, dict):
                return x.get("t") or "", x.get("c") or ""
            return (x or ""), ""
        for k, v in (st.get("h1") or {}).items():
            for e in v:
                en, cy = pair(e)
                S["h1"].append({"s": sk, "sex": sex, "t": en, "c": cy,
                                "n": 1, "m": "h1"})
        for e in (st.get("h2") or []):
            en, cy = pair(e)
            if cy:
                S["h2"].append({"s": sk, "sex": sex, "t": en, "c": cy,
                                "n": 1, "m": "h2"})
        sc = st.get("scope") or {}
        S["scope"].append({"s": sk, "sex": sex, "t": sc.get("short") or "",
                           "c": sc.get("shortCy") or "", "n": 1,
                           "m": "scope"})
    for k, v in seen.items():
        S["module"].append({"m": k[0], "sex": k[1], "t": k[2], "c": k[3],
                            "n": v})
    for mid, md in (package.get("metricDefs") or {}).items():
        cy = md.get("optsCy") or []
        for i, o in enumerate(md.get("opts") or []):
            en = o[1] if isinstance(o, (list, tuple)) else o
            w = cy[i] if i < len(cy) else None
            S["opts"].append({"m": mid, "sex": "all", "t": en or "",
                              "c": w or "", "n": 1})
    return S


def run(package, appjs_src=None):
    if appjs_src is None:
        appjs_src = (Path(__file__).resolve().parent.parent / "web"
                     / "app.js").read_text(encoding="utf-8")
    S = surfaces(package)
    G = V3.gates(package, S, appjs_src)
    failures, notes = [], []
    for g in G:
        if g["limit"] is None:
            if g["occurrences"]:
                notes.append(f"{g['id']} report-only: {g['occurrences']} "
                             f"({g['title'][:60]})")
            continue
        if not g["pass"]:
            ex = g["examples"][0] if g["examples"] else {"en": "", "cy": ""}
            failures.append(f"welsh gate {g['id']} ({g['title'][:55]}): "
                            f"{g['occurrences']} | EN: {ex['en'][:80]} | "
                            f"CY: {ex['cy'][:80]}")
    return failures, G, notes
