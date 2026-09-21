# -*- coding: utf-8 -*-
"""Framework v2.6 — the chip prefixes and filter labels move out of code.

    python -m pipeline.make_framework_v26 config/01_Framework_v2.5.xlsx config/01_Framework_v2.6.xlsx

Until v2.5 the Welsh PREFIX of every filter-group chip ("Byddai’n gwneud mwy
o chwaraeon: {x}"), the three scope labels ("Yr ysgol gyfan" …) and the three
gender labels ("Pob disgybl" …) lived in pipeline/welsh_render.py as Python
constants (decision D50, "derived — listed for the linguist"). The V4.14
fidelity audit found they had never been checked by a Welsh speaker and could
not be edited by the translator like everything else. v2.6 creates sheet
"58 Chip prefixes" carrying exactly those values, so the build reads them
from the workbook; the output is byte-identical to V4.14 by construction, and
the translator's decisions on the handover (sheet 2b, prefix column) are then
ordinary workbook edits. Nothing else changes. Logged on sheet 59.
"""
from __future__ import annotations
import datetime, sys
import openpyxl

PREFIX_EN = {
    "sp": "Selected {x}", "ep": "Enjoys PE: {x}", "ji": "Joins in easily: {x}",
    "ct": "Confidence trying a new sport: {x}", "st": "Does sport: {x}",
    "dy": "Disability or long-term condition: {x}", "ly": "Learning difficulty: {x}",
    "mi": "Would do more sport if: {x}", "wd": "Wants more {x}", "li": "Ideas listened to: {x}",
    "im": "Values: {x}", "et": "Ethnicity: {x}", "wl": "Welsh language: {x}", "tp": "Takes part: {x}",
    "dl": "Disability and/or learning difficulty: {x}", "ed": "Ethnically diverse background: {x}",
    "ws": "Speaks Welsh (very well, a fair amount or a little): {x}",
    "ov": "Estimated times active through sport each week: {x}",
    "cb": "Estimated times active through club sport each week: {x}",
    "gd": "Disability and/or learning difficulty · sport {x}", "gy": "Disability or long-term condition · sport {x}",
    "gl": "Learning difficulty · sport {x}", "ge": "Ethnically diverse background · sport {x}",
    "gw": "Speaks Welsh · sport {x}", "eb": "Enjoys school sports clubs: {x}",
    "ec": "Enjoys clubs outside school: {x}", "eo": "Enjoys other settings: {x}",
    "cs": "Confidence learning a new skill: {x}", "cg": "Confidence trying again when sport is hard: {x}",
    "cn": "Confidence trying sport in a new place: {x}",
}
# the values that were in code (welsh_render.py, v2.5) — copied verbatim
PREFIX_CY = {
    "sp": "Dewiswyd {x}", "ep": "Mwynhau AG: {x}", "ji": "Ymuno’n hawdd: {x}",
    "ct": "Hyder i roi cynnig ar gamp newydd: {x}", "st": "Yn gwneud chwaraeon: {x}",
    "dy": "Anabledd neu gyflwr tymor hir: {x}", "ly": "Anhawster dysgu: {x}",
    "mi": "Byddai’n gwneud mwy o chwaraeon: {x}", "wd": "Eisiau mwy o {x}", "li": "Gwrando ar syniadau: {x}",
    "im": "Yn gwerthfawrogi: {x}", "et": "Ethnigrwydd: {x}", "wl": "Y Gymraeg: {x}", "tp": "Cymryd rhan: {x}",
    "dl": "Anabledd a/neu anhawster dysgu: {x}", "ed": "Cefndir ethnig amrywiol: {x}",
    "ws": "Yn siarad Cymraeg (yn dda iawn, cryn dipyn neu ychydig): {x}",
    "ov": "Amcangyfrif o weithiau’n actif drwy chwaraeon bob wythnos: {x}",
    "cb": "Amcangyfrif o weithiau’n actif drwy chwaraeon clwb bob wythnos: {x}",
    "gd": "Anabledd a/neu anhawster dysgu · chwaraeon {x}", "gy": "Anabledd neu gyflwr tymor hir · chwaraeon {x}",
    "gl": "Anhawster dysgu · chwaraeon {x}", "ge": "Cefndir ethnig amrywiol · chwaraeon {x}",
    "gw": "Yn siarad Cymraeg · chwaraeon {x}", "eb": "Mwynhau clybiau chwaraeon ysgol: {x}",
    "ec": "Mwynhau clybiau y tu allan i’r ysgol: {x}", "eo": "Mwynhau lleoliadau eraill: {x}",
    "cs": "Hyder i ddysgu sgil newydd: {x}", "cg": "Hyder i roi cynnig arall arni pan fydd camp yn anodd: {x}",
    "cn": "Hyder i roi cynnig ar chwaraeon mewn lle newydd: {x}",
}
SCOPES = [("whole", "Whole school", "Yr ysgol gyfan"), ("primary", "Primary phase", "Y cyfnod cynradd"),
          ("secondary", "Secondary phase", "Y cyfnod uwchradd")] + \
         [(f"y{n}", f"Year {n}", f"Blwyddyn {n}") for n in range(3, 12)]
GENDERS = [("all", "All respondents", "Pob disgybl"), ("boy", "Boys", "Bechgyn"), ("girl", "Girls", "Merched")]
# the "You are viewing" banner's audience part (narrative2.py short label
# "Whole school · All pupils"; welsh_render.scope_short_cy) — the English
# is "All pupils", distinct from the filter option "All respondents"
BANNER = [("all", "All pupils", "Pob disgybl"), ("boy", "Boys", "Bechgyn"), ("girl", "Girls", "Merched")]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "58 Chip prefixes" not in wb.sheetnames
    ws = wb.create_sheet("58 Chip prefixes")
    ws.append(["Chip prefixes and filter labels — the Welsh of the side panel's filter-group chips (the part before the answer), the scope options and the gender options. "
               "v2.6: moved here VERBATIM from pipeline/welsh_render.py (D50 'derived — listed for the linguist'); the build reads this sheet and fails on a missing row. "
               "{x} is the answer label from sheet 23 (or the D54 yes/no descriptor). Status DERIVED = written by Industryline, never checked by a Welsh speaker; the translator's decision arrives through the handover (sheet 2b, prefix column)."])
    ws.append(["Kind", "Key", "English", "Welsh", "Status", "Source / note"])
    for fam, en in PREFIX_EN.items():
        ws.append(["cohort prefix", fam, en, PREFIX_CY[fam], "DERIVED (D50) — awaiting the translator", "welsh_render.py COHORT_FRAME_CY (v2.5)"])
    for key, en, cy in SCOPES:
        ws.append(["scope label", key, en, cy, "DERIVED (D50) — awaiting the translator" if not key.startswith("y") else "sheet 23 (Blwyddyn N)", "welsh_render.py SCOPE_CY / staged_build (v2.5)"])
    for key, en, cy in GENDERS:
        ws.append(["gender label", key, en, cy, "DERIVED (D50) — awaiting the translator", "welsh_render.py SEX_CY (v2.5)"])
    for key, en, cy in BANNER:
        ws.append(["banner label", key, en, cy, "DERIVED (D50) — awaiting the translator", "welsh_render.py SEX_CY via scope_short_cy (v2.5): the banner's audience part"])
    ws59 = wb.create_sheet("59 v2.6 change log")
    ws59.append([f"Framework v2.6 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v26.py from v2.5."])
    ws59.append(["Sheet", "Key", "Change", "Before", "After", "Reason / source"])
    ws59.append(["58 Chip prefixes", "*", "NEW SHEET", "(values in code: welsh_render.py)", f"{len(PREFIX_EN)} cohort prefixes, {len(SCOPES)} scope labels, {len(GENDERS)} gender labels, {len(BANNER)} banner labels", "V4.14 fidelity audit §C: code-written Welsh made editable; output byte-identical"])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.6 (21 Sep 2026): sheet 58 Chip prefixes — the filter-chip prefixes and the scope/gender option labels, moved verbatim out of the renderer code so the translator's decisions apply as workbook edits; sheet 59 change log. No text changed.")
    wb.save(dst)
    print(f"written {dst}: sheet 58 with {len(PREFIX_EN)+len(SCOPES)+len(GENDERS)+len(BANNER)} rows")


if __name__ == "__main__":
    main()
