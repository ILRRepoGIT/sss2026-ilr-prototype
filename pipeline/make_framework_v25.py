# -*- coding: utf-8 -*-
"""Framework v2.5 — the V4.14 fidelity round.

    python -m pipeline.make_framework_v25 config/01_Framework_v2.4.xlsx config/01_Framework_v2.5.xlsx

Nine sheet-43 frame edits, each carrying the TRANSLATOR's wording from the
document of 15 Sep 2026 (sha 15d726d0…) into an EXISTING frame that the V4.10
ingest had left on the workbook's earlier Welsh (fidelity audit sheet B,
verdict OVERSIGHT). Slots are kept where the frame has them; the translator's
words replace ours. No Welsh is composed. Every edit asserts the value it
replaces and is logged on sheet "57 v2.5 change log".
"""
from __future__ import annotations
import datetime, sys
import openpyxl

SRC = "translator's document 15 Sep 2026 (fidelity audit sheet B)"
# key: (old cy, new cy, note)
EDITS = {
    "ui.chip_none": ("Dim — dewiswch werth siart wedi’i amlygu i ychwanegu un", "Dim un – dewiswch werth siart wedi’i amlygu i ychwanegu un", "document row ‘None – select a highlighted chart value to add one’"),
    "ui.table_summary": ("Gweld y tabl data", "Gweld Tabl Data", "document row ‘View Data Table’"),
    "ui.stack_th_total": ("Cyfanswm disgyblion", "Cyfanswm y Disgyblion", "document table heading"),
    "ui.stack_caption_year": ("Disgyblion a wnaeth o leiaf un gamp ym mhob lleoliad, yn ôl grŵp blwyddyn.", "Disgyblion a wnaeth o leiaf un gamp ym mhob lleoliad, fesul grŵp blwyddyn.", "document caption (‘fesul’)"),
    "ui.stack_caption_sex": ("Disgyblion a wnaeth o leiaf un gamp ym mhob lleoliad, yn ôl grŵp blwyddyn a rhywedd.", "Disgyblion a wnaeth o leiaf un gamp ym mhob lleoliad, fesul grŵp blwyddyn a rhywedd.", "aligned with the translator's ‘fesul’ (v2.3 already took ‘rhywedd’)"),
    "ui.th_year_group": ("Grŵp blwyddyn", "Grŵp Blwyddyn", "document table heading"),
    "ui.th_base": ("Sail", "Sylfaen", "document table heading; matches the translator's FAQ (‘y rhif ‘sylfaen’’)"),
    "ui.f14_unmet": ("Y galw mwyaf heb ei ddiwallu", "Y galw mwyaf heb ei fodloni", "document summary heading; the engine's sentences already say ‘heb ei fodloni’"),
    "ui.ranking_note": ("Yn dangos y {k:count ateb} blaenaf o {n} — mae’r tabl data yn rhestru pob un.", "Dangosir y prif {k} ateb o blith {n} ateb – mae’r tabl data yn rhestru pob un ohonynt.", "document sentence ‘Dangosir y prif 11 ateb o blith 60 ateb – …’ with the figures returned to slots; the translator writes the count as a figure, so the count-word table is not used here"),
}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    ws = wb["43 Interface frames"]
    log = []
    rows = {str(r[0].value): r for r in ws.iter_rows(min_row=4) if r[0].value}
    for key, (old, new, why) in EDITS.items():
        row = rows[key]
        assert str(row[4].value) == old, (key, row[4].value)
        row[4].value = new
        row[6].value = ((row[6].value or "") + " · v2.5: " + SRC + " — " + why).strip(" ·")
        row[7].value = "TRANSLATED (document 15 Sep 2026)"
        log.append(("43 Interface frames", key, "EDIT", old, new, SRC + " — " + why))
    ws57 = wb.create_sheet("57 v2.5 change log")
    ws57.append([f"Framework v2.5 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v25.py from v2.4. Source: the translator's document (15 Sep 2026) via the V4.14 fidelity audit."])
    ws57.append(["Sheet", "Key", "Change", "Before", "After", "Reason / source"])
    for r in log:
        ws57.append(list(r))
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.5 (V4.14 fidelity round, 17 Sep 2026): nine sheet-43 frames take the translator's wording verbatim (existing frames the V4.10 ingest had left on earlier Welsh); sheet 57 change log. "
                                      "The handoff is reverted to the translator's text (V4.14). Nothing else changed.")
    wb.save(dst)
    print(f"written {dst}: {len(EDITS)} frame edits")


if __name__ == "__main__":
    main()
