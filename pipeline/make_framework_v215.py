# -*- coding: utf-8 -*-
"""Framework v2.15 — the four local-authority rows on sheet 53 (owner instruction, 22 Sep 2026).

    python -m pipeline.make_framework_v215 config/01_Framework_v2.14.xlsx config/01_Framework_v2.15.xlsx

  sheet 53  FOUR new "Local authority" rows, English spelt EXACTLY as the dataset
            spells the authority — `Carmarthenshire`, `Conwy`, `Rhondda Cynon Taf`,
            `The Vale of Glamorgan` — so that the profile's Welsh lookup (nameOf)
            finds every authority in the register and no school is held.
            Owner instruction of 22 Sep 2026: "add these to sheet 53, spell them
            exactly as the dataset spells them; all reports go out in the full run".
            Welsh: the authority's own official Welsh name (public record; the
            name a council uses of itself), NOT prose composed by Industryline —
            for The Vale of Glamorgan the translator's existing Welsh on the
            `Vale of Glamorgan` row (Bro Morgannwg) is reused verbatim; for
            Rhondda Cynon Taf the name is the same in both languages; Conwy the
            same; Carmarthenshire is Sir Gaerfyrddin. Status marks each row
            OWNER-INSTRUCTED with the translator asked to confirm in the next
            handoff (sheet 77); the existing translator rows (`Conwy County`,
            `Rhondda Borough`, `Vale of Glamorgan`) are left exactly as they are.
  sheet 76  change log; sheet 77 flags. No narrative surface touched; no
            interface frame changed.
"""
from __future__ import annotations

import datetime
import sys

import openpyxl

# (English exactly as the dataset spells it, Welsh, provenance of the Welsh)
ROWS = [
    ("Carmarthenshire", "Sir Gaerfyrddin", "official Welsh name of the authority (Cyngor Sir Gâr / Sir Gaerfyrddin)"),
    ("Conwy", "Conwy", "the authority's name is the same in both languages (the translator's `Conwy County` row gives `Sir Conwy` for the longer English form; the dataset's form has no 'County')"),
    ("Rhondda Cynon Taf", "Rhondda Cynon Taf", "the authority's name is the same in both languages"),
    ("The Vale of Glamorgan", "Bro Morgannwg", "the translator's Welsh on the existing `Vale of Glamorgan` row, reused verbatim"),
]
STATUS = "OWNER-INSTRUCTED (22 Sep 2026) — official name; translator to confirm (sheet 77)"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    assert "76 v2.15 change log" not in wb.sheetnames
    ws53 = wb["53 Proper names"]
    english = {str(r[1].value) for r in ws53.iter_rows(min_row=3) if r[1].value}
    for en, cy, _ in ROWS:
        assert en not in english, en
    log = []
    for en, cy, why in ROWS:
        ws53.append(["Local authority", en, cy, f"owner instruction 22 Sep 2026 — {why}", STATUS])
        log.append(("53 Proper names", en, "NEW ROW", "", cy, "owner instruction, 22 Sep 2026 — dataset spelling; " + why))
    h = ws53.cell(row=1, column=1)
    h.value = str(h.value) + " · v2.15: +4 local-authority rows in the dataset's spelling (owner, 22 Sep 2026) — see sheet 76."

    ws76 = wb.create_sheet("76 v2.15 change log")
    ws76.append([f"Framework v2.15 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v215.py from v2.14. "
                 "Sheet 53: four local-authority rows in the dataset's spelling (owner instruction). No interface frame or narrative surface touched; "
                 "no translator wording changed — the existing rows stay as they are."])
    ws76.append(["Sheet", "Key", "Change", "Before", "After", "Reason / source"])
    for row in log:
        ws76.append(list(row))

    ws77 = wb.create_sheet("77 V6.0 flags (3)")
    ws77.append(["Flags raised while applying the owner's instruction of 22 Sep 2026 on the local-authority names — for the translator; the rows are in force meanwhile."])
    ws77.append(["Where", "What", "Detail", "Action needed"])
    ws77.append(["53 Proper names — four new rows", "Confirm the Welsh of the four authority names",
                 "Sir Gaerfyrddin / Conwy / Rhondda Cynon Taf / Bro Morgannwg are the authorities' own Welsh names, entered on the owner's instruction so that the 207 schools in these authorities are built in the full run. "
                 "Not composed prose, but not yet the translator's rows either.",
                 "Translator: confirm or amend in the next handoff; an amendment is a new tag and a rebuild of the affected schools."])
    ws77.append(["53 Proper names — `Rhondda Borough`", "Existing row looks like a mis-entry",
                 "`Rhondda Borough` / `Bwrdeistref y Rhondda` matches no value in the dataset; it may have been meant as Rhondda Cynon Taf. Left as it is.",
                 "Translator: confirm or retire."])
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.15 (V6.0, 22 Sep 2026): sheet 53 +4 local-authority rows in the dataset's spelling — Carmarthenshire, Conwy, "
                                       "Rhondda Cynon Taf, The Vale of Glamorgan (owner instruction; translator to confirm, sheet 77); sheet 76 change log. "
                                       "No translator wording changed.")
    wb.save(dst)
    print(f"written {dst}")


if __name__ == "__main__":
    main()
