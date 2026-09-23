# -*- coding: utf-8 -*-
"""Framework v2.17 — the production pilot's linguist/tester review (23 Sep 2026).

    python -m pipeline.make_framework_v217 config/01_Framework_v2.16.xlsx config/01_Framework_v2.17.xlsx

  The source-and-PDF review of the seven rc7 pilot reports (Llanfaes, Ysgol
  Eifionydd, Acton, Pontarddulais, Llanfairpwll, Birchgrove, St Teilo's)
  raised eight recurring class-A items, A01–A08. Four are rules of the Welsh
  engine that the pipeline (0.32.0) now applies as the framework already
  states them — no new ruling, no new wording, the Welsh corpus moves under
  the existing rulings (D82 re-emission, this sheet 80 cited as the ruling):

    A02  ADJ-02 / ADJ-07 (sheet 14): after the feminine singular head the
         superlative lenites — 'Yr ail gamp FWYAF cyffredin' (the sheet's own
         example is 'y gamp fwyaf poblogaidd'); masculine heads and, by PR-06,
         the coordinated 'camp neu weithgaredd' keep 'mwyaf'.
    A03  PR-05 / EX-04 and EX-01..03 (sheets 39, 25, 23 'Mutable? NO'): an
         unadapted loan or recent g- borrowing never mutates ON ANY PATH — the
         engine honoured the flag on the label service but lost it once a label
         had been joined into a list or a counted phrase ('a Pharkour', 'mwy o
         Barkour', 'am Fadminton', 'am ymnasteg', 'a Thriathlon', 'mwy o FMX',
         'am olff,'). The same review sentence (h1, gender leaders) applied the
         SOFT mutation after the conjunction 'a' ('a bêl droed', 'a redeg neu
         loncian'): it now takes the conjunction service, CONJ-01..05 ('a phêl
         droed', 'ac athletau', 'a rhedeg neu loncian').
    T-035 (sheet 26): the f10 cohort sentence 'Roedd y disgyblion a ddewisodd X'
         left the object of the inflected verb unmutated ('a ddewisodd pêl
         droed') while the same cohort's sheet-22 qualifier in the same report
         read 'a ddewisodd bêl droed'; it now takes the object mutation.

  Three are the client's, no wording involved: A04 the guide's answers are
  opened for printing; A05 the printed footer moves into the page margin
  (@page margin boxes) so it no longer covers the last line of a page; A06 the
  gender-exempt appendix table (the gender profile) shows the All column only.

  A01 (sheet 53, this version): two profile DATA values had no Welsh form and
  sat in Welsh mode as UNMARKED English — the school-stages phrase (28 distinct
  values across the 1,016-school register, e.g. 'Primary (Years 3–6)') and the
  suppression model of the technical record ('view-level rule of five
  (2026-07-20)'). The client now marks such a value pending (red dotted, lang
  en) exactly as an untranslated frame, and this version adds the 29 rows to
  sheet 53 with the Welsh EMPTY for the translator (V5.0 flag 4 asked for
  three stage values; the register shows 28).

  A07 (ui.base_line_complete — owner wording, V5.0 item 4), A08 ('un o'r N
  disgybl … nad ydynt' — translator ruling, V5.0 flag 9), C01 (ui189 'Diolch a
  cammau nesaf' — translator, sheet 61 row 8) and B01 (g4 'highest … and
  lowest …' in a cohort every year of which is 100% — owner) are decisions
  already on the flags sheets; they are restated on sheet 81 with the
  reviewer's evidence. Sheet 80 change log, sheet 81 flags. No translator
  wording changed; no narrative surface composed.
"""
from __future__ import annotations

import datetime
import sys

import openpyxl

# The 28 distinct 'School Stages Covered' values of the production register of
# 23 Sep 2026 (prod/register.py derives the phrase from the school's family
# and its PLASC year range; 1,016 schools). A phrase, never a school.
STAGE_VALUES = [
    "Primary (Years 3–6)", "Secondary (Years 7–11)", "Primary (Years 4–6)", "Secondary (Years 7–10)",
    "Primary (Years 3–5)", "Primary (Years 5–6)", "Primary and secondary (Years 3–11)", "Primary (Years 6–6)",
    "Primary (Years 3–4)", "Secondary (Years 7–9)", "Primary (Years 5–5)", "Primary (Years 3–3)",
    "Primary and secondary (Years 3–10)", "Primary (Years 4–5)", "Primary (Years 4–4)",
    "Primary and secondary (Years 4–10)", "Secondary (Years 7–8)", "Secondary (Years 9–11)", "Secondary (Years 8–11)",
    "Primary and secondary (Years 4–11)", "Primary and secondary (Years 3–9)", "Secondary (Years 8–9)",
    "Secondary (Years 8–10)", "Secondary (Years 8–8)", "Secondary (Years 9–10)", "Primary and secondary (Years 5–10)",
    "Primary and secondary (Years 5–11)", "Secondary (Years 11–11)",
]
SUPPRESSION_MODEL = "view-level rule of five (2026-07-20)"

RULING = ("Framework v2.17 sheet 80 — the Welsh engine (pipeline 0.32.0) applies PR-05 / EX-01..04 (immutable labels on every path), "
          "ADJ-02/ADJ-07 with PR-06 (the runner-up adjective agrees with its head), CONJ-01..05 (the h1 gender-leaders sentence after 'a') "
          "and T-035 (the object of 'dewisodd' in the f10 cohort sentence) as the framework states them; production pilot review, 23 Sep 2026")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "80 v2.17 change log" not in wb.sheetnames
    log = []

    ws53 = wb["53 Proper names"]
    existing = {str(r[1].value) for r in ws53.iter_rows(min_row=3) if r[1].value}
    for v in STAGE_VALUES:
        assert v not in existing, v
        ws53.append(["School stages", v, None,
                     "V6.0 pilot review, 23 Sep 2026 (A01) — the register's 'School Stages Covered' phrase (prod/register.py: family + PLASC year range)",
                     "TRANSLATOR — Welsh pending; the client shows the English MARKED (red dotted, lang en) until this row is filled"])
    ws53.append(["Suppression model", SUPPRESSION_MODEL, None,
                 "V6.0 pilot review, 23 Sep 2026 (A01) — the technical record's suppression-model value (buildMetadata.suppressionModel)",
                 "TRANSLATOR — Welsh pending; the client shows the English MARKED (red dotted, lang en) until this row is filled"])
    h = ws53.cell(row=1, column=1)
    h.value = str(h.value) + " · v2.17: +28 'School stages' values and the suppression-model value, Welsh pending (A01) — see sheet 80."
    log.append(("53 Proper names", "School stages ×28; Suppression model ×1", "NEW ROWS (Welsh empty)", "unmarked English in Welsh mode",
                "marked pending until the translator's Welsh arrives", "pilot review finding A01, 23 Sep 2026"))

    # engine alignments — no cell changes; the record of the ruled corpus move
    log.append(("14 Adjectives — ADJ-02/ADJ-07 (with 39 PR-06)", "runner-up sentence (welsh_render.r_runner)", "ENGINE ALIGNED",
                "Yr ail gamp mwyaf cyffredin", "Yr ail gamp fwyaf cyffredin (camp neu weithgaredd: mwyaf, PR-06; masculine heads: mwyaf)",
                "pilot review finding A02, 23 Sep 2026 — every report (216–1,443 states per report in the seven reviewed)"))
    log.append(("39 PR-05 / 25 EX-01..04 / 23 'Mutable? NO'", "every list-join and phrase path (welsh.immutable_heads)", "ENGINE ALIGNED",
                "a Pharkour; mwy o Barkour; am Fadminton; am ymnasteg; a Thriathlon; mwy o FMX; am olff,",
                "a Parkour; mwy o Parkour; am Badminton; am gymnasteg; a Triathlon; mwy o BMX; am golff,",
                "pilot review finding A03, 23 Sep 2026 — Parkour, Badminton, Boccia, BMX, Triathlon, Gymnasteg, golff (and Padel, Pickleball, Taekwondo, Muay Thai, Majorettes where they occur)"))
    log.append(("11 Conjunctions — CONJ-01..05", "h1 gender-leaders sentence (welsh_render.r_h1_an_gender_leaders)", "ENGINE ALIGNED",
                "ymhlith bechgyn a bêl droed / a redeg neu loncian / a Fadminton ymhlith merched",
                "ymhlith bechgyn a phêl droed / a rhedeg neu loncian / a Badminton / ac athletau ymhlith merched",
                "pilot review finding A03 (secondary schools), 23 Sep 2026 — the sentence applied the soft mutation after 'a'"))
    log.append(("26 Test matrix — T-035", "f10 cohort sentence (welsh_render.r_group_codemand_top3)", "ENGINE ALIGNED",
                "Roedd y disgyblion a ddewisodd pêl droed hefyd …", "Roedd y disgyblion a ddewisodd bêl droed hefyd … (unadapted names unchanged: a ddewisodd Badminton)",
                "found alongside A03, 23 Sep 2026 — the same cohort's sheet-22 qualifier already read 'a ddewisodd bêl droed'"))
    log.append(("client (web/app.js, web/template.html)", "print: guide answers; page-margin footer; gender-exempt appendix table; pending marking of data values", "CLIENT",
                "guide headings printed without answers; fixed footer over the last line; Boys/Girls columns on the gender profile; unmarked English data values",
                "details.faq opened for print; @page margin boxes with the page number; All column only for exempt=gender; cy-missing marking",
                "pilot review findings A04, A05, A06, A01, 23 Sep 2026"))

    ws80 = wb.create_sheet("80 v2.17 change log")
    ws80.append([f"Framework v2.17 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v217.py from v2.16. "
                 "Sheet 53 +29 rows (Welsh pending). ENGINE ALIGNED rows record where pipeline 0.32.0 now applies a rule this workbook already states; "
                 "the Welsh corpus of every school moves under those rules (D82 re-emission; ruling text below). No translator wording changed; nothing composed."])
    ws80.append(["D82 ruling text (lock re-emission):", RULING])
    ws80.append(["Sheet / rule", "Where", "Change", "Before", "After", "Reason / source"])
    for row in log:
        ws80.append(list(row))

    ws81 = wb.create_sheet("81 V6.0 flags (5)")
    ws81.append(["Flags from the production pilot review of 23 Sep 2026 (AI-assisted source/PDF review of seven rc7 reports; the designated Welsh linguist's sign-off is still required) — for the translator and the report owner."])
    ws81.append(["Where", "What", "Detail", "Action needed"])
    ws81.append(["53 Proper names — School stages (28), Suppression model (1)", "Welsh for two profile data values (A01)",
                 "Shown MARKED (red dotted, lang en) in Welsh mode until supplied. The stage values follow one pattern — '{Primary | Secondary | Primary and secondary} (Years {first}–{last})' — so three patterns cover all 28 if the translator prefers; the rows are then filled by substitution of the two figures only.",
                 "Translator: 29 rows (or the three patterns and the suppression-model line)."])
    ws81.append(["43 Interface frames — ui.base_line_complete", "'(complete survey response)' with partial responses included (A07; V5.0 item 4 restated)",
                 "The profile charts' base line reads 'Based on: N pupils (complete survey response)' / 'Yn seiliedig ar: N disgybl (ymatebion cyflawn i’r arolwg)' while accepted partial responses are counted (e.g. Llanfaes: 49 complete + 27 partial = 76). The wording is the owner's; ui.base_line ('Based on: N pupils') already exists in both languages if the owner prefers it with no new words.",
                 "Report owner (Sport Wales): the wording — reuse ui.base_line, or new words for both languages (translator)."])
    ws81.append(["h1 summary — one-of-N with the plural predicate", "'Dywedodd un o’r N disgybl … nad ydynt …' (A08; V5.0 flag 9 restated)",
                 "The reviewer expects singular agreement after 'un' ('nad yw’n …') or the PR-03 impersonal recast, as e2/h2 already use for a singleton subject. The form is attested in the V4.15 corpus and is left under the lock until ruled (D82).",
                 "Translator: rule; a ruling moves the corpus in the next tag (the singular predicate already exists in the renderer)."])
    ws81.append(["61 V4.15 flags row 8 — ui189", "'Diolch a cammau nesaf' (C01)", "Static page-furniture row; the reviewer suggests 'Diolch a chamau nesaf'.", "Translator: confirm or correct the handoff row."])
    ws81.append(["49 English client edits — candidate", "g4 'Enjoyment of PE was proportionally highest in Year X … and lowest in Year X …' (B01)",
                 "Within the cohort 'enjoys PE a lot' every reportable year is 100% by construction, and the extremes sentence names the same year twice. Locked English: an owner decision (omit the module for a cohort defined by its own metric, or a tie form).",
                 "Report owner: sanction a form, or leave as is."])
    ws81.append(["register — School Stages Covered", "single-year phrase 'Primary (Years 6–6)' (29 schools)",
                 "The phrase is derived from the PLASC year range; a one-year school reads 'Years 6–6'. English wording is the owner's (EN-13 candidate: 'Primary (Year 6)').",
                 "Report owner: confirm or sanction the single-year form; the translator's stage rows follow."])
    ws81.append(["print — page-margin footer", "page number added to the printed footer (A05 fix)",
                 "The footer now sits in the page margin (Chromium/Edge print) and carries '· <page>' after the survey name; browsers without margin boxes print no repeating footer rather than an overlapping one.",
                 "Report owner: note (revert on request)."])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.17 (V6.0 pilot review, 23 Sep 2026): sheet 53 +28 'School stages' values and the suppression-model value, Welsh pending (A01); "
                                       "sheet 80 change log — pipeline 0.32.0 applies PR-05/EX-01..04, ADJ-02/07 (PR-06), CONJ-01..05 and T-035 as already stated (ruled corpus move, D82); "
                                       "sheet 81 flags. No translator wording changed.")
    wb.save(dst)
    print(f"written {dst}")


if __name__ == "__main__":
    main()
