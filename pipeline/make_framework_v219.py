# -*- coding: utf-8 -*-
"""Framework v2.19 — the reviewers' return on the rc9 pilot (23 Sep 2026).

    python -m pipeline.make_framework_v219 config/01_Framework_v2.18.xlsx config/01_Framework_v2.19.xlsx

  The linguist/tester review of the 21 rc9 pilot reports (all three packs,
  2,484 PDF pages, six Welsh samples of 1,101 paired records, two numerical
  cases) confirmed the six rc9 corrections and found no numerical
  inconsistency. It returned three class-A defect types (55 school rows) —
  two rules of the Welsh engine that the pipeline (0.32.2) now applies as the
  framework already states them, and one client repair that rc9 had made
  only on the profile page:

    RC9-A01  A numeral that counts the audience takes the audience's gender
             (sheet 04 row 4: the audience slot carries head noun + gender;
             sheet 08 rows 6–8: dwy / tair / pedair; sheet 20 row 6: merch is
             feminine; sheet 12 row 8: gan + soft mutation). The engine had the
             feminine forms and used them where the sentence names the girls
             as its subject ('Dywedodd pedair …') but sent a masculine numeral
             into the partitive counts ('gan bedwar o'r pum merch', 'dau o'r 21
             merch', 'tri o'r 14 merch'). Every numerator that counts the
             audience now carries the audience head's gender ('gan bedair o'r
             pum merch', 'dwy o'r 21 merch', 'tair o'r 14 merch'); a count of
             'disgybl' or 'bachgen' is unchanged, and a Girls view does not
             feminise a clause that counts pupils. 17 of the 21 reports.
    RC9-A02  A label the translator marked mutable on sheet 23 mutates on the
             prose paths even when its Welsh form is spelt as the English
             (sheet 23 row 154: Tennis, initial t, Mutable? YES; sheet 06 row
             5: t → d; sheet 12 row 4: soft mutation after 'o'; T-035: the
             object of 'dewisodd'). The rc7-era heuristic that read an
             identical form as an unadapted loan had overridden the sheet's
             flag on one service (welsh.label_after_soft) — 'a ddewisodd
             tennis', 'mwy o tennis' — while the same report's other paths
             mutated it ('a thennis', 'mwy o dennis bwrdd'). The sheet-23 flag
             governs; the identical-form reading is kept only for a label
             with no sheet-23 row. Badminton, BMX, Parkour and the other
             'Mutable? NO' labels are unchanged (the rc9 test cases stay in
             the suite alongside the new ones). 18 of the 21 reports.
    RC9-A03  The pending marker on the suppression-model value in the
             technical record was invisible: the cell's dotted red bottom
             border (.cy-missing) was overridden by the table's own cell
             border (details.dtable td). The marker now sits on a span inside
             the cell, in both the profile table and the technical record, in
             normal and accessibility modes and in print; the language tag
             and the pending tooltip move with it. 20 Welsh PDFs (residual of
             rc7 A01).

  Sheet 26 T-032 ('a ddewisodd Tennis') tests the verb's mutation (REL-01);
  its object is in the label form and predates D21 and T-035. A note is added
  to the row: in running prose the unquoted object reads 'a ddewisodd dennis'.
  No expected string on the sheet is changed.

  The Welsh corpus moves under RC9-A01 and RC9-A02 (D82 re-emission; the
  ruling text below is cited by the runner's --lock-ruling); the English is
  byte-identical. Sheet 84 change log, sheet 85 flags (the reviewers' class-B
  rows RC9-B01..B03 and the acceptance work they list as outstanding). No
  translator wording changed; no narrative surface composed.
"""
from __future__ import annotations

import datetime
import sys

import openpyxl

RULING = ("Framework v2.19 sheet 84 — the Welsh engine (pipeline 0.32.2) applies sheet 04 row 4 with sheet 08 rows 6–8 "
          "(a numeral that counts the audience takes the audience's gender: dwy / tair / pedair before 'merch') and sheet 23 row 154 "
          "with sheet 12 row 4 and T-035 (a label the translator marked mutable mutates on the prose paths: 'mwy o dennis', "
          "'a ddewisodd dennis') as the framework states them, in addition to the v2.17 sheet 80 rulings; the reviewers' return on "
          "the rc9 pilot, 23 Sep 2026")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "84 v2.19 change log" not in wb.sheetnames

    # sheet 26 T-032: annotate, do not change the expected string
    ws26 = wb["26 Test matrix"]
    t032 = None
    for row in ws26.iter_rows(min_row=4):
        if str(row[0].value) == "T-032":
            t032 = row
            break
    assert t032 is not None and str(t032[3].value) == "a ddewisodd Tennis"
    t032[6].value = ("v2.19 note (RC9-A02): this case exercises the verb's mutation (REL-01); its object is the label form and predates "
                     "D21 / T-035. In running prose the unquoted object of 'dewisodd' takes the soft mutation — 'a ddewisodd dennis' — "
                     "because sheet 23 row 154 marks Tennis mutable. tests/test_welsh.py::test_T032_subject_relative_sp checks both.")

    log = [
        ("04 Slot types row 4 / 08 Cardinals rows 6–8 / 20 Audience components row 6 / 12 Prepositions row 8",
         "every numerator that counts the audience (welsh_render: W.numerator / numz with the audience head's gender; 47 call sites)",
         "ENGINE ALIGNED",
         "gan bedwar o'r pum merch; dau o'r 21 merch; tri o'r 14 merch (a Girls view)",
         "gan bedair o'r pum merch; dwy o'r 21 merch; tair o'r 14 merch — 'disgybl' and 'bachgen' heads unchanged (gan bedwar o'r pum bachgen)",
         "rc9 review return RC9-A01, 23 Sep 2026 — 17 of the 21 pilot reports (Ysgol Bryn Collen mod.d3.p[0]; Ysgol Gynradd Llanfairpwll Year 5 girls mod.f13.p[0])"),
        ("23 Answer labels row 154 (Mutable? YES) / 06 Mutation map row 5 / 12 Prepositions row 4 / 26 T-035",
         "the prose-form label after a soft trigger (welsh.label_after_soft) — 'mwy o X', 'a ddewisodd X'",
         "ENGINE ALIGNED",
         "Roedd y disgyblion a ddewisodd tennis hefyd …; … mwy o tennis.",
         "Roedd y disgyblion a ddewisodd dennis hefyd …; … mwy o dennis. (Badminton, BMX, Parkour and every 'Mutable? NO' label unchanged)",
         "rc9 review return RC9-A02, 23 Sep 2026 — 18 of the 21 pilot reports (Ysgol Bryn Collen, Tennis cohort, mod.f10.p[1]); the sheet-23 flag governs, the identical-form reading only where no row exists"),
        ("26 Test matrix — T-032", "row note (column G)", "NOTE",
         "a ddewisodd Tennis (label form; the verb's mutation)", "unchanged; note: in running prose the object reads 'a ddewisodd dennis' (D21, T-035, sheet 23 row 154)",
         "rc9 review return RC9-A02 — the rc7-era test read the label form as an unadapted loan"),
        ("client (web/app.js)", "pending marking of data values in the profile table and the technical record", "CLIENT",
         "class cy-missing on the table cell — its dotted red border overridden by details.dtable td in the technical record (invisible)",
         "the marker on a span inside the cell (lang en, pending tooltip), visible in the profile, the technical record, accessibility mode and print",
         "rc9 review return RC9-A03, 23 Sep 2026 — 20 Welsh PDFs (residual of rc7 A01)"),
    ]
    ws84 = wb.create_sheet("84 v2.19 change log")
    ws84.append([f"Framework v2.19 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v219.py from v2.18. "
                 "ENGINE ALIGNED rows record where pipeline 0.32.2 now applies a rule this workbook already states; the Welsh corpus of the affected "
                 "schools moves under those rules (D82 re-emission; ruling text below). No sheet-23 or sheet-43 cell changed; no translator wording changed; nothing composed."])
    ws84.append(["D82 ruling text (lock re-emission):", RULING])
    ws84.append(["Sheet / rule", "Where", "Change", "Before", "After", "Reason / source"])
    for row in log:
        ws84.append(list(row))

    ws85 = wb.create_sheet("85 V6.0 flags (7)")
    ws85.append(["Flags from the reviewers' return on the rc9 pilot (23 Sep 2026; AI-assisted source/PDF review of the 21 reports — the designated Welsh linguist's and tester's sign-offs are still required) — for the report owner, Sport Wales and the tester."])
    ws85.append(["Where", "What", "Detail", "Action needed"])
    ws85.append(["print — pagination", "RC9-B01 sparse continuation and trailing pages (rc7 B02 carried forward)",
                 "Maes Ebbw EN p23: a faint continuation of the greyed prompt above the footer; Crownbridge EN p53: the final technical-table row alone on the last page; Llanfairpwll CY p63: a footer-only final page. No content is lost; the section starts the owner asked for and the page-margin footer are kept.",
                 "Client presentation, a later tag if the owner wants it tidied; not a regeneration trigger."])
    ws85.append(["print — whole-school-suppressed reports", "RC9-B02 Ysgol Beddgelert CY p9: overlapping suppression boxes; 23 pages per language",
                 "The overlap is the rc10 correction (html.whole-sup: the notices flow in the page, one per module; 29 pages at Beddgelert in the rc10 print). The reviewer also asks that the brief's shorter-print expectation be clarified: a fully suppressed report still prints every section heading with its notice.",
                 "Owner: confirm the rc10 presentation from the rc11 pack; decide whether the 23 under-five reports should print shorter (a client change, later tag)."])
    ws85.append(["49 English client edits — candidate", "RC9-B03 f2 'participation … was proportionally highest in Year 5 (14 of 14, or 100%) and lowest in Year 5 (14 of 14, or 100%)' in a DEFAULT view (St Chad's; Year 6 also 10 of 10)",
                 "The rc7 B01 tie item, now seen on the f2 path in a default view as well as g4 in a self-defined cohort. Locked English in both languages; the extremes sentence names the same year twice when every year ties.",
                 "Report owner: sanction a tie form covering f2 and g4 (translator for the Welsh), or leave as is."])
    ws85.append(["acceptance (reviewers' items 3 and 4)", "live tester's work and fresh prints",
                 "Outstanding, not gating Phase D: desktop Chrome/Edge on all reports, one Firefox and one phone/tablet case; language persistence, scope/year/gender controls, bar selection, cohort availability, clear/reset, banner counts, copied hashes, navigation, keyboard focus, accessibility mode, translated alt text; fresh A4 prints with background graphics (default, filtered, suppressed, greyscale), guide restoration after print, marker visibility, margin footers.",
                 "Designated tester, on the rc11 pack; sheet 39 by the designated linguist; O09/O10 and D69 by the owner/disclosure process."])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.19 (reviewers' return on the rc9 pilot, 23 Sep 2026): sheet 84 change log — pipeline 0.32.2 applies the audience's gender to every "
                                       "numeral that counts the audience (dwy / tair / pedair; RC9-A01) and the sheet-23 mutability flag on the prose paths (tennis; RC9-A02) "
                                       "as already stated (ruled corpus move, D82); the pending marker inside table cells (client; RC9-A03); sheet 26 T-032 annotated; "
                                       "sheet 85 flags (RC9-B01..B03, outstanding acceptance work). No sheet-23 or sheet-43 cell changed; no translator wording changed.")
    wb.save(dst)
    print(f"written {dst}")


if __name__ == "__main__":
    main()
