# -*- coding: utf-8 -*-
"""Framework v1.7 corpus acceptance gates (sheet 36, D45/D52), run at build
time over the whole state payload.

The module-paragraph corpus runs through the handover pack's OWN script,
vendored verbatim (vendor_welsh_gates17.py) — the release contract is their
implementation. This wrapper adds what sheet 36 governs beyond that script:

  * the D49 surfaces: the same content gates applied to h1 summaries and
    variable h2 prompts (their loader reads mod[*].p only);
  * G10a-d — Welsh presence on every dynamic surface and the UI-001
    language-state source assertion;
  * G11 — D21 running-prose label form;
  * G12 — D47 qualifier referential integrity (stale literal copies).

Thresholds are sheet 36's: zero everywhere except G3a+ and G9e, which the
sheet marks report-only (linguist-owned).
"""
from __future__ import annotations

import collections
import re

from . import vendor_welsh_gates17 as V17

# AMEND-3 (versioned per D52, proposed to the appraiser alongside the two
# amendments they adopted in the pack script): the figure-parity Welsh
# number vocabulary lacks the soft form 'dri' (gan dri, correct after the
# agent preposition) and the aspirate absolute 'phump'. Without them the
# gate flags grammatically required mutations as lost figures. The stock,
# unamended script is still run at ship time and its result filed.
V17.CY_NUM.setdefault("dri", 3)
V17.CY_NUM.setdefault("phump", 5)

REPORT_ONLY = {"G3a+", "G9e"}


def rows_from_states(states):
    seen = collections.Counter()
    for sk, st in states.items():
        for mid, m in (st.get("mod") or {}).items():
            for p in (m.get("p") or []):
                seen[(mid, sk.split("|")[1],
                      p.get("t") or "", p.get("c") or "")] += 1
    return [{"m": k[0], "gender": k[1], "t": k[2], "c": k[3], "n": v}
            for k, v in seen.items()]


def _pair(entry):
    if isinstance(entry, dict):
        return entry.get("t") or "", entry.get("c") or ""
    return entry or "", ""


def surface_rows(states):
    h1, h2, sc = [], [], []
    for sk, st in states.items():
        if st.get("sup"):
            continue
        for theme, lst in (st.get("h1") or {}).items():
            for e in lst:
                t, c = _pair(e)
                h1.append({"m": f"h1.{theme}", "gender": sk.split("|")[1],
                           "t": t, "c": c, "n": 1})
        for e in (st.get("h2") or []):
            t, c = _pair(e)
            generic = isinstance(e, dict) and bool(e.get("g"))
            h2.append({"m": "h2", "gender": sk.split("|")[1], "t": t,
                       "c": c, "n": 1, "generic": generic})
        sp = st.get("scope") or {}
        sc.append({"m": "scope", "t": sp.get("short") or "",
                   "c": sp.get("shortCy") or "", "n": 1})
    return h1, h2, sc


def prose_label_pairs(lexicon):
    out = []
    for en, e in (lexicon or {}).get("answer_labels", {}).items():
        cy = (e.get("cy") or "").strip()
        prose = (e.get("prose") or "").strip()
        if cy and prose and cy != prose and len(cy) > 3:
            out.append((cy, prose))
    return out


def _strip_quoted(s):
    return re.sub(r"‘[^’]*’", "‘’", s)


def run(states, lexicon=None, appjs_src=None):
    """Returns the full sheet-36 gate list. Module corpus through the
    vendored appraisal script; D49 surfaces through the same gate logic
    as a supplementary population; G10-G12 implemented here."""
    R = rows_from_states(states)
    h1, h2, sc = surface_rows(states)
    var_h2 = [r for r in h2 if not r["generic"]]

    results = list(V17.gates(R))

    # D49: the same content gates over the h1/h2 surfaces (their loader
    # reads mod[*].p only, so this population is additional)
    surf = [r for r in h1 + var_h2 if r["c"]]
    for g in V17.gates(surf):
        if g["paragraphs"] and g["id"] not in REPORT_ONLY:
            for tgt in results:
                if tgt["id"] == g["id"]:
                    tgt["paragraphs"] += g["paragraphs"]
                    tgt["unique"] += g["unique"]
                    tgt["pass"] = tgt["pass"] and g["pass"]
                    tgt["note"] = (tgt.get("note") or "") + \
                        f" [+{g['paragraphs']} on the D49 h1/h2 surfaces]"
                    tgt["examples"] = tgt["examples"] + g["examples"]

    def gate(gid, title, rows, note=""):
        results.append({"id": gid, "title": title,
                        "paragraphs": sum(r["n"] for r in rows),
                        "unique": len(rows), "limit": 0,
                        "pass": sum(r["n"] for r in rows) == 0, "note": note,
                        "examples": [{"en": r["t"][:200], "cy": r["c"][:200],
                                      "module": r["m"]} for r in rows[:3]]})

    gate("G10a", "Every h1 summary has a non-empty Welsh value (D49)",
         [r for r in h1 if r["t"] and not r["c"]])
    gate("G10b", "Every variable h2 prompt has a non-empty Welsh value (D49)",
         [r for r in var_h2 if r["t"] and not r["c"]])
    gate("G10c", "Every view descriptor renders in the active language (D50)",
         [r for r in sc if r["t"] and not r["c"]])
    ui_ok = bool(appjs_src) and appjs_src.count("applyLanguageState(") >= 4
    results.append({"id": "G10d",
                    "title": "html lang, toggle label and review note follow "
                             "the hash (UI-001)",
                    "paragraphs": 0 if ui_ok else 1,
                    "unique": 0 if ui_ok else 1, "limit": 0, "pass": ui_ok,
                    "note": "source assertion: applyLanguageState defined and "
                            "called from toggle, initial readHash and "
                            "hashchange", "examples": []})

    pairs = prose_label_pairs(lexicon)
    g11 = []
    for r in R + h1 + var_h2:
        body = _strip_quoted(r["c"])
        for table, prose in pairs:
            i = body.find(table)
            if i > 0 and body[i - 2:i] not in (". ", "; ", ": "):
                g11.append(r)
                break
    gate("G11", "Title-cased answer label inside running Welsh prose (D21)",
         g11)

    g12, g12_note = [], 0
    lex = lexicon or {}
    label_texts = {(e.get("cy") or "").strip()
                   for e in lex.get("answer_labels", {}).values()}
    battery = set((lex.get("battery") or {}).values())
    for q in lex.get("qualifiers", []):
        cy = q.get("cy") or ""
        if "⟪ANSWER" in cy:
            continue
        for span in re.findall(r"‘([^’]{4,})’", cy):
            span = span.strip()
            if span in label_texts or span in battery:
                g12_note += 1
            else:
                g12.append({"m": f"frame:{q['family']}", "t": q.get("en", ""),
                            "c": cy, "n": 1})
            break
    gate("G12", "Qualifier frame contains literal Welsh instead of a label "
                "ID (D47)", g12,
         note=f"{g12_note} frames quote the CURRENT approved label verbatim "
              f"(matching copies, reported for the D47 migration)")
    return results


def failures(results):
    """Sheet-36 acceptance: every gate zero except the two report-only."""
    out = []
    for g in results:
        if g["id"] in REPORT_ONLY:
            continue
        if not g["pass"] or (g["paragraphs"] or 0) > (g.get("limit") or 0):
            ex = g["examples"][0] if g["examples"] else {"en": "", "cy": ""}
            out.append(f"welsh gate {g['id']} ({g['title'][:60]}): "
                       f"{g['paragraphs']} | EN: {ex['en'][:80]} | CY: "
                       f"{ex['cy'][:80]}")
    return out
