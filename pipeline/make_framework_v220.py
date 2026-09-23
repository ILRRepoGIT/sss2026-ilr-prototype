# -*- coding: utf-8 -*-
"""Framework v2.20 — the full production run (23 Sep 2026): 12 of 1,016 schools.

    python -m pipeline.make_framework_v220 config/01_Framework_v2.19.xlsx config/01_Framework_v2.20.xlsx

  The full run at v6.0-rc11 built 1,004 of the 1,016 schools; twelve failed
  their own gates twice, in two classes, both reproduced on Industryline's
  machine from the tagged code:

    FT-06   Six schools failed the Welsh gate AGR-partitive (D56: no partitive
            over a singular set). e2's comparison with the parent audience
            ('For comparison, among Year 5 pupils the figure was none of 1.')
            met a parent set of ONE pupil — one Year 5 pupil had answered the
            question — and the template's ZERO branch rendered it as 'nid oedd
            yr un o’r unig ddisgybl ym Mlwyddyn 5' (sheet 05 row 9 has no N = 1
            branch). The engine now takes the singleton form the framework
            already gives for every other frame (sheet 44; Ctx.neg_subject):
            'O gymharu, nid oedd yr unig ddisgybl ym Mlwyddyn 5.' and, for a
            count of one, 'O gymharu, yr unig ferch ym Mlwyddyn 5 oedd y
            ffigur.' Nothing composed: the template's own words with the
            prohibited partitive removed.
    FT-06   The same frame's numerator did not carry the parent audience's
            gender — 'O gymharu, dau o’r 16 merch ym Mlwyddyn 3 oedd y ffigur'
            in every girls' cohort view. This is RC9-A01 (v2.19) on the one
            site the rc11 sweep left out (the frame derives its gender from the
            parent, not from the view). Now 'dwy o’r 16 merch'. The rc11 pilot
            pack carried the form; the reviewers' sample did not reach it.
    names   Six schools failed the school regression's title check (58/59):
            their PLASC names carry a doubled space ('Brynteg  School', 'CWM
            IFOR  PRIMARY SCHOOL'), which the page and document.title collapse,
            so the title never matched the register's string. The register now
            collapses runs of whitespace in a name; the PLASC spelling is never
            changed ('Troedyrhiw Commmunity Primary School' stays as PLASC has
            it — flagged for the owner).

  The corrected engine is a new tag and, by rule 8, a full regeneration of
  the set under one tag (the rollup requires one release across the set). The
  Welsh corpus moves in the e2 comparison sentence of every girls' cohort
  view (D82 re-emission; ruling text below); the English is byte-identical.
  Sheet 86 change log, sheet 87 flags. No translator wording changed.
"""
from __future__ import annotations

import datetime
import sys

import openpyxl

RULING = ("Framework v2.20 sheet 86 — the Welsh engine (pipeline 0.32.3) applies D56 (no partitive over a singular set: "
          "'nid oedd yr unig ddisgybl ym Mlwyddyn 5', 'yr unig ferch … oedd y ffigur') and sheet 04 row 4 with sheet 08 rows 6–8 "
          "(the numerator agrees with the parent audience: 'dwy o’r 16 merch') to FT-06, the parent comparison of e2, as the "
          "framework states them, in addition to the v2.17 sheet 80 and v2.19 sheet 84 rulings; the full production run, 23 Sep 2026")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "86 v2.20 change log" not in wb.sheetnames

    # sheet 05 row 9 (FT-06): the singleton branch, as a note — the template cell is unchanged
    ws05 = wb["05 Welsh templates"]
    row = None
    for r in ws05.iter_rows(min_row=4):
        if str(r[0].value) == "FT-06":
            row = r
            break
    assert row is not None and str(row[1].value).startswith("O gymharu, ⟪N⟫ o’r ⟪BASE⟫")
    row[2].value = (str(row[2].value) + " v2.20 SINGLETON BRANCH (D56, sheet 44): when ⟪BASE⟫ = 1 the partitive is prohibited — "
                    "'O gymharu, nid oedd yr unig ⟪PARENT:HEAD_SG⟫ …' (zero) and 'O gymharu, yr unig ⟪PARENT:HEAD_SG⟫ … oedd y ffigur' (one); "
                    "⟪N⟫ takes the parent audience's gender (sheet 04 row 4; sheet 08 rows 6–8): 'dwy o’r 16 merch'. "
                    "Found by the full run of 23 Sep 2026 (six schools with a one-pupil parent base).")

    log = [
        ("05 Welsh templates row 9 — FT-06 / 02 D56 / 44 Singleton frames",
         "e2 parent comparison, parent base = 1 (welsh_render.r_parent_compare)", "ENGINE ALIGNED",
         "O gymharu, nid oedd yr un o’r unig ddisgybl ym Mlwyddyn 5. (gate AGR-partitive: build refused)",
         "O gymharu, nid oedd yr unig ddisgybl ym Mlwyddyn 5. / O gymharu, yr unig ferch ym Mlwyddyn 5 oedd y ffigur.",
         "full run, 23 Sep 2026 — Ysgol Y Waun, Brymbo Aided (St. Mary's), Birchgrove, Wick Marcross, Cwmclydach, St Julian's (6 of 1,016)"),
        ("05 Welsh templates row 9 — FT-06 / 04 Slot types row 4 / 08 Cardinals rows 6–8",
         "e2 parent comparison in a girls' cohort view — the numerator", "ENGINE ALIGNED",
         "O gymharu, dau o’r 16 merch ym Mlwyddyn 3 oedd y ffigur. (pedwar o’r 91 merch; tri o’r 25 merch)",
         "O gymharu, dwy o’r 16 merch ym Mlwyddyn 3 oedd y ffigur. (pedair; tair)",
         "full run, 23 Sep 2026 — RC9-A01 (v2.19) on the one site the rc11 sweep left out; every school with a girls' cohort view"),
        ("prod/register.py — name", "six PLASC names with a doubled space", "REGISTER RULE",
         "'Brynteg  School', 'CWM  IFOR  PRIMARY SCHOOL', 'Y G G  Y Castell', 'Ysgol Gymraeg  Lon Las', 'Monkton Priory Community Primary  School', 'Troedyrhiw  Commmunity Primary School'",
         "runs of whitespace collapsed to one space; spelling unchanged; name_dataset keeps the dataset's string",
         "full run, 23 Sep 2026 — the school regression's title check (document.title collapses whitespace) stopped six builds at 58/59"),
    ]
    ws86 = wb.create_sheet("86 v2.20 change log")
    ws86.append([f"Framework v2.20 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v220.py from v2.19. "
                 "ENGINE ALIGNED rows record where pipeline 0.32.3 now applies a rule this workbook already states; the Welsh corpus moves "
                 "in the e2 comparison sentence of every girls' cohort view and at the six one-pupil-parent schools (D82 re-emission; ruling text below). "
                 "No sheet-05 template cell changed (a note is appended to FT-06's divergence column); no translator wording changed; nothing composed."])
    ws86.append(["D82 ruling text (lock re-emission):", RULING])
    ws86.append(["Sheet / rule", "Where", "Change", "Before", "After", "Reason / source"])
    for r in log:
        ws86.append(list(r))

    ws87 = wb.create_sheet("87 V6.0 flags (8)")
    ws87.append(["Flags from the full production run of 23 Sep 2026 (v6.0-rc11 → v6.0-rc12) — for the translator, the report owner and the tester."])
    ws87.append(["Where", "What", "Detail", "Action needed"])
    ws87.append(["05 Welsh templates row 9 — FT-06 singleton branch", "'O gymharu, nid oedd yr unig ddisgybl ym Mlwyddyn 5.' / 'O gymharu, yr unig ferch ym Mlwyddyn 5 oedd y ffigur.'",
                 "The D56 realisation of the template's ZERO and one-count branches for a one-pupil parent set — the existing words with the prohibited partitive removed, as sheet 44 realises the other frames. Six schools carry the zero form; the one-count form is not attested in the set.",
                 "Translator: confirm (the designated linguist's sign-off)."])
    ws87.append(["49 English client edits — candidate", "e2 parent comparison at a one-pupil parent base: 'For comparison, among Year 5 pupils the figure was none of 1.' (and, were it to occur, '1 of 1')",
                 "Locked English; passes the English gate. Six schools carry it (the cohort views of a year in which one pupil answered the question). An EN-08 candidate: a one-pupil form ('… the one Year 5 pupil who answered did not') or a hold for a parent base of one.",
                 "Report owner: sanction a one-pupil form, hold the sentence, or leave as is (then the translator's Welsh)."])
    ws87.append(["register — school names from PLASC", "spelling as PLASC has it: 'Troedyrhiw Commmunity Primary School' (sic), 'CWM IFOR PRIMARY SCHOOL' (upper case), 'Y G G Y Castell'",
                 "The register takes the PLASC January 2026 name verbatim apart from whitespace (rc12). A misspelling or an all-capitals name in PLASC therefore appears on the school's cover, title and banner.",
                 "Report owner: accept, or supply a names overlay (an owner-signed list of corrected names by school id) for a later tag."])
    ws87.append(["review coverage", "the e2 comparison in girls' cohort views was outside the reviewers' rc11 sample",
                 "Every reviewed report carried the masculine numerator in that sentence; neither the sampled paragraphs nor Industryline's rc9→rc11 word-level diff (which checked changed words only) reached it. The rc12 proof scans every paragraph of the rebuilt reference schools for a masculine numeral before a feminine head (zero) and the reviewers' re-check should include an e2 girls' cohort view.",
                 "Tester/linguist: add one e2 girls' cohort view per sampled school to the re-check."])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.20 (the full production run, 23 Sep 2026): sheet 86 change log — pipeline 0.32.3 applies D56 to FT-06 (the singleton parent set: "
                                       "'nid oedd yr unig ddisgybl …'; six schools) and the parent audience's gender to FT-06's numerator ('dwy o’r 16 merch'; RC9-A01's last site), "
                                       "the register collapses whitespace in PLASC names (six schools); sheet 05 row 9 annotated; sheet 87 flags. "
                                       "No template or translator wording changed; the corpus moves in e2's comparison sentence (ruled, D82).")
    wb.save(dst)
    print(f"written {dst}")


if __name__ == "__main__":
    main()
