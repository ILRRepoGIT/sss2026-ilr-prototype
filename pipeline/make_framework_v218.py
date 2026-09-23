# -*- coding: utf-8 -*-
"""Framework v2.18 — the rc9 pilot review (23 Sep 2026): the owner's decisions.

    python -m pipeline.make_framework_v218 config/01_Framework_v2.17.xlsx config/01_Framework_v2.18.xlsx

  The rc9 pilot (21 schools, every one built and verified) was read against
  the six items corrected at rc9 — all six hold in all 21 reports — and
  turned up what the 20-school sample had never exercised before Ysgol
  Beddgelert (one response) was added:

  sheet 49  EN-13 — the intro sentence and the FAQ sentence ('{n} pupil
            responses are included') read '1 pupil responses are included' at
            a one-response school (14 of the 1,016). The owner sanctioned the
            singular clause '1 pupil response is included' (23 Sep 2026); the
            lexicon derives it as it derives the other singular forms (the
            Welsh singular, 'wedi'i gynnwys', is the translator's, from sheet
            28). No cell of sheet 43 changes.
  client    A whole-school-suppressed report (23 schools under five responses)
            showed its disclosure notices stacked on top of one another on
            screen and in print — every module is empty there, and the notice
            was positioned over content that does not exist. It now flows in
            the page (web/template.html, web/app.js). No wording involved.
  sheet 83  flags: the single-year phrases ('Pupils in Years 6 to 6', 'All year
            groups from Year 6 to Year 6 … Year 6 contributed the largest number
            of responses (7) and Year 6 the smallest (7)'; 29 schools) — the owner
            chose to leave them for a later decision; the whole-school notice
            wording ('The greyed charts show the whole school for context.
            Broaden the selection …') at the 23 under-five schools, a Sport
            Wales / legal-review item since the GDPR frames are theirs; the
            rollup's 'corpus moves' line for first emissions (cosmetic, fixed).
  sheet 82  change log.
"""
from __future__ import annotations

import datetime
import sys

import openpyxl


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "82 v2.18 change log" not in wb.sheetnames
    ws49 = wb["49 English client edits"]
    ws49.append(["EN-13", "ui.intro_sentence, ui.faq_included at n = 1 (the 14 one-response schools)",
                 "{n} pupil responses are included — rendered '1 pupil responses are included'",
                 "{n} pupil response is included (the singular clause; every other word unchanged). Welsh: the translator's own singular ('wedi’i gynnwys', sheet 28), already in force.",
                 "rc9 pilot review, 23 Sep 2026 (Ysgol Beddgelert). Derived by the lexicon build as the other singular forms are (pipeline/build_welsh_lexicon.py); no sheet-43 cell changes.",
                 "SANCTIONED v2.18 (owner, 23 Sep 2026)"])
    ws82 = wb.create_sheet("82 v2.18 change log")
    ws82.append([f"Framework v2.18 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v218.py from v2.17. "
                 "Sheet 49 +EN-13 (the one-response singular). No sheet-43 cell changed; no translator wording changed; the Welsh corpus is unchanged "
                 "(Phase B at rc10 expects the rc9 counts against the V5.3 locks, or 0 against the rc9 locks)."])
    ws82.append(["Sheet / rule", "Where", "Change", "Before", "After", "Reason / source"])
    ws82.append(["49 English client edits", "EN-13", "NEW ROW", "1 pupil responses are included", "1 pupil response is included", "rc9 pilot review, 23 Sep 2026 — owner's sanction"])
    ws82.append(["client (web/template.html, web/app.js)", "whole-school-suppressed reports (23 schools)", "CLIENT",
                 "disclosure notices absolutely positioned over empty modules — stacked, overlapping, on screen and in print",
                 "html.whole-sup: the notice flows in the page, one per module, none overlapping; suppressed views at other schools unchanged",
                 "rc9 pilot review, 23 Sep 2026 (Ysgol Beddgelert, the added 21st school)"])
    ws82.append(["prod/runner.py, prod/checks.py", "rollup 'corpus moves'", "COSMETIC",
                 "a first emission (no previous lock) was listed as a move with 'supersedes None'",
                 "only builds asserted against a previous lock are listed", "operator's note, rc9 rollout progress"])
    ws83 = wb.create_sheet("83 V6.0 flags (6)")
    ws83.append(["Flags from the rc9 pilot review of 23 Sep 2026 — decisions left open by the owner, for the register."])
    ws83.append(["Where", "What", "Detail", "Action needed"])
    ws83.append(["43 Interface frames — ui.intro_sentence, ui.faq_included, ui.overview_note", "single-year schools (29 of the 1,016)",
                 "'across Years 6 to 6', 'Pupils in Years 6 to 6 at …', 'All year groups from Year 6 to Year 6 are represented. Year 6 contributed the largest number of responses (7) and Year 6 the smallest (7).' (and the Welsh equivalents). The largest/smallest sentence could take the existing EN-12 variant (both languages exist); a single-year form of the first sentence would be new wording in both languages.",
                 "Owner (English) and translator (Welsh), a later tag; the 29 schools rebuilt then. Left as is at rc10 (owner, 23 Sep 2026)."])
    ws83.append(["43 Interface frames — ui.gdpr_body_full (D73/Q17)", "whole-school-suppressed schools (23)",
                 "The notice reads 'Fewer than five pupils match this selection … The greyed charts show the whole school for context. Broaden the selection to see this group's findings.' At a school under five responses there is no whole-school context and nothing to broaden. The GDPR frames are Sport Wales's, under legal review.",
                 "Sport Wales: a whole-school variant, or accept."])
    ws83.append(["53 Proper names — School stages", "'Primary (Years 6–6)' (single-year phrase, 29 schools)",
                 "Shown marked pending in Welsh mode; the phrase itself is the register's (prod/register.py).", "Owner: with the single-year wording above."])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.18 (rc9 pilot review, 23 Sep 2026): sheet 49 EN-13 (the one-response singular 'pupil response is included'); "
                                       "sheet 82 change log (client: whole-school-suppressed notices flow in the page; rollup cosmetic); sheet 83 flags (single-year wording, the under-five notice wording). "
                                       "No sheet-43 cell or translator wording changed; the Welsh corpus is unchanged.")
    wb.save(dst)
    print(f"written {dst}")


if __name__ == "__main__":
    main()
