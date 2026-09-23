# -*- coding: utf-8 -*-
"""Framework v2.16 — the overview sentence when a year-group bar is blanked (EN-12), and the EN-08 hold extended.

    python -m pipeline.make_framework_v216 config/01_Framework_v2.15.xlsx config/01_Framework_v2.16.xlsx

  Found by the production pilot of 23 Sep 2026 at the small and special schools
  (first at Crownbridge Special School, 7 responses over four year groups):

  sheet 43  TWO new frames. The profile chart "responses by year group" blanks a
            bar whose view is under the rule of five (engine suppression policy
            v2, exception 1). ui.overview_note / ui.overview_note_gap then have
            no count to cite for {hin} / {lon}, and at a school where every bar
            is blank no year to name either — the page showed the raw slots.
            226 of the 1,016 schools have at least one blanked year bar.
              ui.overview_note_nocounts      — ui.overview_note WITHOUT its second
                                               sentence (the largest / smallest year
                                               groups); English by deletion of that
                                               sentence, Welsh by deletion of the same
                                               sentence from the TRANSLATOR'S OWN row
                                               (nothing composed; translator to
                                               confirm, sheet 79).
              ui.overview_note_gap_nocounts  — the EN-11 gap variant likewise; Welsh
                                               EMPTY -> TRANSLATOR (as ui.overview_note_gap).
            The client selects the "nocounts" frame whenever any year bar is blank
            (a "smallest year group" named among the shown bars would be false, and
            the blanked count must not be printed); slots: first, last.
  sheet 49  EN-12: the sentence naming the largest and smallest year groups is
            omitted when any year-group bar is blanked; every other word of the
            note is unchanged. EN-08 extended: the one-pupil hold now applies to
            every locked template (pipeline 0.31.1), not only f10's three; the
            templates the pilot held are listed for the owner's one-pupil forms.
  sheet 78  change log; sheet 79 flags. No narrative surface touched.
"""
from __future__ import annotations

import datetime
import re
import sys

import openpyxl

SRC_KEYS = ("ui.overview_note", "ui.overview_note_gap")
NEW_KEYS = ("ui.overview_note_nocounts", "ui.overview_note_gap_nocounts")


def drop_second_sentence(text: str) -> str:
    """Remove the second sentence (the {hi}/{hin}/{lo}/{lon} one) from a
    four-sentence frame; the remaining sentences are untouched."""
    if not text:
        return text
    parts = re.split(r"(?<=\.)\s+", text.strip())
    assert len(parts) == 4, parts
    assert "{hin}" in parts[1] and "{lon}" in parts[1], parts[1]
    return " ".join([parts[0], parts[2], parts[3]])


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "78 v2.16 change log" not in wb.sheetnames
    ws43 = wb["43 Interface frames"]
    rows = {str(r[0].value): r for r in ws43.iter_rows(min_row=4) if r[0].value}
    for k in NEW_KEYS:
        assert k not in rows, k
    log = []
    for src_key, new_key in zip(SRC_KEYS, NEW_KEYS):
        r = rows[src_key]
        en = drop_second_sentence(str(r[3].value))
        cy_src = r[4].value
        cy = drop_second_sentence(str(cy_src)) if cy_src and str(cy_src).strip() else None
        status = ("DERIVED — Welsh is the translator's own ui.overview_note row minus its second sentence (nothing composed); translator to confirm (sheet 79)"
                  if cy else "TRANSLATOR")
        ws43.append([new_key, "V6.0 EN-12",
                     f"#overview-note — used instead of {src_key} when any bar of the 'responses by year group' profile chart is blanked (its view is under the rule of five): the sentence naming the largest and smallest year groups is omitted",
                     en, cy, "first, last",
                     "V6.0 (pilot, 23 Sep 2026 — first seen at Crownbridge Special School, every year bar blanked): the second sentence has no count to cite. "
                     "English = the source frame minus that sentence; Welsh = the translator's row minus the same sentence"
                     + ("" if cy else " (source Welsh pending, so this is pending too)") + ".",
                     status])
        log.append(("43 Interface frames", new_key, "NEW ROW", "", en, f"EN-12 — derived from {src_key} by deleting its second sentence; pilot finding, 23 Sep 2026"))
    h = ws43.cell(row=1, column=1)
    h.value = str(h.value) + " · v2.16: +ui.overview_note_nocounts, +ui.overview_note_gap_nocounts (EN-12) — see sheet 78."

    ws49 = wb["49 English client edits"]
    ws49.append(["EN-12", "ui.overview_note / ui.overview_note_gap when any 'responses by year group' bar is blanked (its view under the rule of five)",
                 "{hi} contributed the largest number of responses ({hin}) and {lo} the smallest ({lon}). — rendered with the raw slots when a bar is blank (no count to cite)",
                 "That sentence is omitted (frames ui.overview_note_nocounts / ui.overview_note_gap_nocounts); every other sentence of the note is unchanged.",
                 "Production pilot, 23 Sep 2026: a blanked bar carries no count, and a 'smallest year group' named among the shown bars would be false. 226 of the 1,016 schools have at least one blanked year bar; 33 have every bar blanked. "
                 "No narrative state changes; the frame is client-realised.",
                 "SANCTIONED v2.16 (owner, 23 Sep 2026 — 'change nothing else')"])
    ws49.append(["EN-08 (extended)", "every locked template with no one-pupil form (pipeline 0.31.1) — previously f10's three only",
                 "The build's English gate refused the whole report when a selected group of ONE pupil met a plural template ('None of the 1 pupil …'): six of the twenty pilot schools.",
                 "The sentence is HELD in every module — not rendered in either language, not audited, logged in the validation summary — exactly as f10's have been since V5.0; every sentence the gate accepts is unchanged.",
                 "Production pilot, 23 Sep 2026. Templates held in the pilot: li_join_cross_v3 (g5), leader_multi_v2 (f10), and the d7 / h1 sentences the six schools reached. The owner's one-pupil forms lift each hold.",
                 "SANCTIONED v2.16 (owner, 23 Sep 2026)"])
    log.append(("49 English client edits", "EN-12", "NEW ROW", "", "largest/smallest sentence omitted when a year bar is blanked", "pilot finding, 23 Sep 2026"))
    log.append(("49 English client edits", "EN-08 (extended)", "NEW ROW", "", "one-pupil hold applies to every template", "pilot finding, 23 Sep 2026"))

    ws78 = wb.create_sheet("78 v2.16 change log")
    ws78.append([f"Framework v2.16 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v216.py from v2.15. "
                 "Sheet 43 +2 frames (EN-12, derived by deletion); sheet 49 EN-12 and EN-08 extended. No narrative surface touched; no translator wording changed — "
                 "the derived Welsh row is the translator's sentences 1, 3 and 4 verbatim."])
    ws78.append(["Sheet", "Key", "Change", "Before", "After", "Reason / source"])
    for row in log:
        ws78.append(list(row))

    ws79 = wb.create_sheet("79 V6.0 flags (4)")
    ws79.append(["Flags raised by the production pilot of 23 Sep 2026 — questions for the translator and the report owner; nothing here is decided by Industryline beyond what sheet 49 records."])
    ws79.append(["Where", "What", "Detail", "Action needed"])
    ws79.append(["43 Interface frames — ui.overview_note_nocounts", "Confirm the derived Welsh",
                 "The Welsh is the translator's ui.overview_note row with its second sentence deleted (sentences 1, 3, 4 verbatim). Shown at every school with a blanked year bar (226 schools).",
                 "Translator: confirm, or supply the row."])
    ws79.append(["43 Interface frames — ui.overview_note_gap_nocounts", "Welsh pending",
                 "Pending with ui.overview_note_gap (EN-11).",
                 "Translator: two rows in the next handoff (the gap variant with and without the second sentence)."])
    ws79.append(["49 English client edits — EN-08", "One-pupil forms for the held templates",
                 "li_join_cross_v3 (g5: 'None of the {base} pupils … who said their ideas … are not often listened to …'), leader_multi_v2 (f10), and the d7 / h1 sentences held at St Chad's, Portfield, Ysgol Nantgwyn, Greenfield, Idris Davies and Crownbridge (validation summaries list each view). Until the owner sanctions one-pupil forms, the module is listed under 'Data available in this view' in those views.",
                 "Report owner: sanction one-pupil forms (English), then translator (Welsh); a new tag lifts the holds."])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.16 (V6.0 pilot, 23 Sep 2026): sheet 43 +ui.overview_note_nocounts / +ui.overview_note_gap_nocounts (EN-12 — the largest/smallest "
                                       "year-group sentence omitted when a year bar is blanked; Welsh derived by deleting that sentence from the translator's row, to confirm); "
                                       "sheet 49 EN-12 and EN-08 extended to every template; sheet 78 change log; sheet 79 flags. No translator wording changed.")
    wb.save(dst)
    print(f"written {dst}")


if __name__ == "__main__":
    main()
