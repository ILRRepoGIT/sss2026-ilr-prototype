# -*- coding: utf-8 -*-
"""Regenerate the translator's handoff workbook ("Strings" sheet) so that the
static lane can be BOUND (Framework v2.2, D79 / D80).

    python -m pipeline.make_translation_handoff <framework.xlsx> <out.xlsx>
                                                [<previous_handoff.xlsx>]

The ui### numbering is the team's existing numbering, carried from the
previous handoff (or, when that workbook is not to hand, from the rows
already embedded in config/welsh_lexicon.json). A row keeps its key when its
English still appears on the page (exactly, or — because the V4.2 listing
truncated long strings — as a prefix of the page text; a truncated string
that is a prefix of several page texts is resolved in document order). A
page string with no row receives the next free key AFTER the sixteen fixed
attribute strings of sheet 28 (ui217–ui230, one key per distinct string,
in sheet order). A row whose English no longer occurs as a static text node
is RETIRED: listed on its own sheet with the reason, and no longer a
translator row — it has nowhere to land (gate CAT-static-manifest).

Every retained Welsh value is carried over unchanged. Nothing here writes a
Welsh word.
"""
from __future__ import annotations

import io
import json
import re
import sys
from collections import Counter
from pathlib import Path

import openpyxl

from . import static_lane as SL
from .common import CONFIG_DIR, ROOT

ATTR_SHEET28 = [(a, r"\(" + a + r"\)") for a in SL.ATTR_KEYS]


def previous_rows(handoff_path: str | None):
    """[{cat, owner, key, en, cy}] from the previous handoff workbook, else
    from the rows embedded in the current lexicon."""
    if handoff_path:
        wb = openpyxl.load_workbook(handoff_path, data_only=True)
        out = []
        for r in wb["Strings"].iter_rows(values_only=True):
            r = ["" if v is None else str(v) for v in r]
            if len(r) < 6 or not r[0] or r[0] == "#":
                continue
            out.append({"cat": r[1], "owner": r[2], "key": r[3],
                        "en": r[4], "cy": r[5] or None})
        return out
    lex = json.load(io.open(CONFIG_DIR / "welsh_lexicon.json", encoding="utf-8"))
    return [dict(s) for s in lex.get("handoff", [])]


def sheet28_attribute_strings(framework_path: str):
    """The sixteen v2.2 rows of sheet 28, reduced to distinct strings in
    sheet order, with the attribute each belongs to."""
    wb = openpyxl.load_workbook(framework_path, read_only=True, data_only=True)
    out, seen = [], set()
    for r in wb["28 Interface strings"].iter_rows(values_only=True):
        if not r or not r[0] or not r[1]:
            continue
        where, en = str(r[0]), SL.norm(str(r[1]))
        for attr, pat in ATTR_SHEET28:
            if re.search(pat, where):
                if en not in seen:
                    seen.add(en)
                    out.append((attr, en, where))
                break
    if len(out) != 14:
        raise SystemExit(f"sheet 28: expected 14 distinct attribute strings "
                         f"(16 rows), read {len(out)}")
    return out


def reconcile(page_strings, ui_rows):
    """-> (en_to_key for matched page strings, retired rows, new strings)."""
    exact = {r["en"]: r["key"] for r in ui_rows}
    matched, unmatched, amb = {}, [], {}
    for s in page_strings:
        if s in exact:
            matched[s] = exact[s]
            continue
        pref = [r["key"] for r in ui_rows if len(r["en"]) >= 50 and s.startswith(r["en"])]
        if len(pref) == 1:
            matched[s] = pref[0]
        elif len(pref) > 1:
            amb.setdefault(tuple(pref), []).append(s)
        else:
            unmatched.append(s)
    for ks, ss in amb.items():
        if len(ks) != len(ss):
            raise SystemExit(f"ambiguous truncated rows {ks} cannot be resolved "
                             f"by document order ({len(ss)} page strings)")
        for k, s in zip(ks, ss):
            matched[s] = k
    used = set(matched.values())
    retired = [r for r in ui_rows if r["key"] not in used]
    return matched, retired, unmatched


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    fw, out_path = sys.argv[1], Path(sys.argv[2])
    prev = sys.argv[3] if len(sys.argv) > 3 else None
    rows = previous_rows(prev)
    ui_rows = [r for r in rows if SL.STATIC_KEY.match(str(r["key"]))]
    other_rows = [r for r in rows if not SL.STATIC_KEY.match(str(r["key"]))]
    tpl = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    nodes = SL.extract(tpl)
    page_strings, seen = [], set()
    for nd in nodes:
        if nd.text not in seen:
            seen.add(nd.text)
            page_strings.append(nd.text)
    matched, retired, new_strings = reconcile(page_strings, ui_rows)
    prev_cy = {r["key"]: r["cy"] for r in ui_rows}
    # sheet 28 attribute strings: ui217 … (one key per distinct string)
    attrs = sheet28_attribute_strings(fw)
    next_key = max([int(r["key"][2:]) for r in ui_rows] + [216]) + 1
    attr_rows = []
    en_to_key = dict(matched)
    for attr, en, where in attrs:
        if en in en_to_key:
            k = en_to_key[en]
        else:
            k = f"ui{next_key:03d}"; next_key += 1
            en_to_key[en] = k
        attr_rows.append({"cat": f"fixed attribute ({attr}, D80)",
                          "owner": "Translator", "key": k, "en": en,
                          "cy": prev_cy.get(k)})
    new_rows = []
    for s in new_strings:
        k = f"ui{next_key:03d}"; next_key += 1
        en_to_key[s] = k
        new_rows.append({"cat": "page furniture", "owner": "Translator",
                         "key": k, "en": s, "cy": None})
    consumer = {}
    for nd in nodes:
        consumer.setdefault(en_to_key[nd.text], nd.consumer)
    static_rows = ([{"cat": "page furniture", "owner": "Translator",
                     "key": en_to_key[s], "en": s, "cy": prev_cy.get(en_to_key[s])}
                    for s in page_strings if en_to_key[s] not in {a["key"] for a in attr_rows}]
                   + attr_rows)
    static_rows.sort(key=lambda r: r["key"])
    # ---- write --------------------------------------------------------------
    wb = openpyxl.Workbook()
    ws = wb.active; ws.title = "Strings"
    ws.append(["#", "Category", "Owner", "Key", "English", "Welsh"])
    n = 0
    for r in other_rows + static_rows:
        n += 1
        ws.append([n, r["cat"], r["owner"], r["key"], r["en"], r["cy"]])
    wr = wb.create_sheet("Retired")
    # V4.18: the translator's Welsh for a retired row is carried on this sheet
    # verbatim (it was returned; it is simply no longer consumed by the page)
    wr.append(["Key", "English (as listed in the previous handoff)", "Reason",
               "Welsh (as returned by the translator — kept for the record, no longer on the page)"])
    for r in retired:
        en = r["en"]
        if SL.PLACEHOLDER.match(en) or en == "Ysgol Penrhyn Dewi":
            why = "school name — data, not translator text"
        elif en in ("Cenedl Actif i Bawb", "Mwynhad Gydol Oes o Chwaraeon", "Chwaraeon"):
            why = "chapter-band Welsh subtitle — already Welsh; not a translator row (raised for the owner)"
        elif en in ("Explore results ▾", "None — select a highlighted chart value to add one"):
            why = "client-owned control text served by a sheet-43 frame (ui.rail_toggle / ui.chip_none)"
        elif en in ("Club Sports", "This section brings together sport done in a", "school sports club",
                    "(extracurricular) and/or a", "club outside of school"):
            why = "Club Sports section removed from the report (EN-09, V4.18, owner instruction 22 Sep 2026) — the translator's Welsh kept here"
        else:
            why = "string no longer occurs on the page (V4.1 sanctioned English edits)"
        wr.append([r["key"], en, why, r.get("cy") or ""])
    rm = wb.create_sheet("Read me")
    for line in __doc__.strip().split("\n"):
        rm.append([line])
    rm.append([""])
    rm.append([f"Generated from {Path(fw).name} (sheet 28) and web/template.html; "
               f"{len(page_strings)} distinct static strings ({len(matched)} keys kept, "
               f"{len(new_rows)} new), {len(attr_rows)} attribute strings, "
               f"{len(retired)} rows retired; {len(other_rows)} non-static rows carried verbatim."])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    summary = {"page_strings": len(page_strings), "kept": len(matched),
               "new": [r["key"] for r in new_rows], "attribute_keys": [r["key"] for r in attr_rows],
               "retired": [r["key"] for r in retired], "other_rows": len(other_rows),
               "static_rows": len(static_rows), "consumers": consumer}
    print(json.dumps({k: v for k, v in summary.items() if k != "consumers"}, ensure_ascii=False))
    print("handoff written:", out_path)
    return summary


if __name__ == "__main__":
    main()
