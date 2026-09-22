# -*- coding: utf-8 -*-
"""Framework v2.10 — the workbook edit for V4.17.

    python -m pipeline.make_framework_v210 config/01_Framework_v2.9.xlsx config/01_Framework_v2.10.xlsx

Sheet 43 only: ONE new frame, ``ui.a11y_switch_desc`` — the description a
screen reader announces with the accessibility switch (aria-describedby) and
sighted readers see under it. English written by Industryline (it states what
the switch does, nothing more); Welsh EMPTY → TRANSLATOR (pending: shown as
marked English in Welsh mode until returned). Change log sheet 66; V4.17
flags sheet 67. No Welsh composed; no translator wording changed.
"""
from __future__ import annotations

import datetime
import sys

import openpyxl

KEY = "ui.a11y_switch_desc"
EN = ("Turns on larger text in Aptos or Arial, higher-contrast colours, a colour-blind-safe chart palette, "
      "open data tables, a caption under every picture and a glossary of terms. The findings do not change.")


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "66 v2.10 change log" not in wb.sheetnames
    ws43 = wb["43 Interface frames"]
    keys = {str(r[0].value) for r in ws43.iter_rows(min_row=4) if r[0].value}
    assert KEY not in keys
    assert EN == EN.strip() and EN[0] not in "·—–:;," and EN[-1] not in "·—–:;,"
    ws43.append([KEY, "V4.17 accessibility",
                 "#a11y-desc — the paragraph under the accessibility switch, announced with it (aria-describedby)",
                 EN, None, "—",
                 "V4.17 (22 Sep 2026): the switch was made larger and more obvious and given a description so a screen "
                 "reader announces what it does (owner instruction). One sentence of plain description; the findings "
                 "are unchanged by the switch. Welsh pending the translator.", "TRANSLATOR"])
    h = ws43.cell(row=1, column=1)
    h.value = str(h.value) + " · v2.10: +ui.a11y_switch_desc (Welsh pending) — see sheet 66."
    ws66 = wb.create_sheet("66 v2.10 change log")
    ws66.append([f"Framework v2.10 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v210.py from v2.9. "
                 "Sheet 43 only: the accessibility switch's description frame. No Welsh composed; no translator wording changed; no narrative surface touched."])
    ws66.append(["Sheet", "Key", "Change", "Before", "After", "Reason / source"])
    ws66.append(["43 Interface frames", KEY, "NEW ROW", "", EN, "V4.17 — the accessibility switch's description (owner instruction, 22 Sep 2026)"])
    ws67 = wb.create_sheet("67 V4.17 flags")
    ws67.append(["Flags raised while preparing V4.17 — each is a question for the translator, Sport Wales or the owner; nothing here is decided by Industryline."])
    ws67.append(["Where", "What", "Detail", "Action needed"])
    ws67.append(["43 Interface frames — ui.a11y_switch_desc", "Welsh for the accessibility switch's description",
                 "New frame; English only. Shown as marked English in Welsh mode until returned.",
                 "Translator: one row in the next handoff (sheet 3 'Translate'), with the fourteen ui.alt_yac_* rows and ui.a11y_glossary_heading."])
    ws67.append(["Print / PDF", "Every report page now starts on a new printed page; headings never end a page",
                 "Print rules only (screen rendering unchanged): each section that is a page of the report opens on a new page; a heading is kept with what follows it.",
                 "Owner: confirm the page count is acceptable (the A4 PDF grows; see the compliance record)."])
    ws67.append(["Pipeline 0.29.1 — loader rule", "An off-route take-part answer is not carried",
                 "A respondent not routed to the take-part question (disability answer not Yes / Not sure / Prefer not to say) whose record still carries an answer: the answer is dropped by the loader, counted and reported. "
                 "Only Ysgol Bro Pedr is affected (one partial response); the prototype and the other two schools carry none.",
                 "Cleansing team: the 24 partial responses in the Stage 2 dataset that carry a take-part answer beside a 'No' (query sent with the round). Sport Wales: with the partial-response confirmation."])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.10 (V4.17, 22 Sep 2026): sheet 43 +ui.a11y_switch_desc (the accessibility switch's description; "
                                       "Welsh pending the translator); sheet 66 change log; sheet 67 V4.17 flags. No translator wording changed.")
    wb.save(dst)
    print(f"written {dst}: 1 sheet-43 row added")


if __name__ == "__main__":
    main()
