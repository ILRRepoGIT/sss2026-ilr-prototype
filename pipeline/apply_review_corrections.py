# -*- coding: utf-8 -*-
"""Apply the reviewer's EXPLICIT Welsh corrections to the handoff (V4.11).

    python -m pipeline.apply_review_corrections <handoff_in.xlsx> <handoff_out.xlsx>

Source: "SSS2026_Welsh_Interactive_Text_V4.10_Assessment.docx" §7.1 (15 Sep
2026), an engineering and linguistic-screening review, "not native-speaker
certification". Only the items that name an exact replacement are applied,
each as a minimal substitution inside the translator's sentence; every
applied row gets the note "reviewer correction (assessment §7.1, 15 Sep
2026) — pending translator confirmation" in column G. Items whose required
action is a decision or an unspecified recast (ui023 voice, ui086 passive,
ui143 parallel clause, ui250 plural, ui255 agreement) are NOT applied and are
listed on the register's translator queue. Nothing else in the handoff is
touched; a substitution that does not match the current value is an error,
never silently skipped.
"""
from __future__ import annotations

import sys

import openpyxl

NOTE = "reviewer correction (assessment §7.1, 15 Sep 2026) — pending translator confirmation"

# key -> [(old, new)], applied in order, each must match exactly once
CORRECTIONS = {
    "ui029": [("ar y  canfyddiadau", "ar y canfyddiadau")],
    "ui034": [("Yn eich tro, gallwch", "Yn ei dro, gallwch")],
    "ui057": [("ac mae marciau llwyd tywyll yn dangos gwerthoedd cuddiedig",
               "ac mae barrau llwyd tywyll yn dynodi gwerthoedd cuddiedig")],
    "ui064": [("Pam mae rhai barrau yn llwyd, yn wag neu nid oes modd clicio arnyn nhw?",
               "Pam mae rhai barrau’n llwyd neu’n wag, neu pam na ellir clicio arnynt?")],
    "ui087": [("Pam mae rhai rhifau yn cuddio ar ôl cymhwyso hidlyddion?",
               "Pam mae rhai rhifau’n cael eu cuddio ar ôl cymhwyso hidlyddion?")],
    "ui095": [("o gylch hwn yr arolwg", "o gylch yr arolwg hwn")],
    "ui104": [("Cliciwch ar bob bar ac archwilio sut", "Cliciwch ar bob bar ac archwiliwch sut")],
    "ui143": [("gofynnwyd i disgyblion", "gofynnwyd i ddisgyblion")],
    "ui154": [("Sut mae AG neu Wersi Actif", "Sut mae AG a Gwersi Actif")],
    "ui157": [("os nad oedd yr un o’r opsiynau yn addas iddynt", "os nad oedd yr un o’r opsiynau yn addas iddynt.")],
    "ui190": [("Diolch i bob disgybl a rannodd eu barn", "Diolch i’r holl ddisgyblion a rannodd eu barn")],
    "ui197": [("Rhestri cyflawn", "Rhestrau cyflawn"), ("mae’r prif restri hefyd", "mae’r prif restrau hefyd")],
    "ui254": [("Defnyddio panel Archwilio’r canlyniadau", "Defnyddiwch banel Archwilio’r canlyniadau")],
    "ui255": [("Mae hwn yn cynnwys opsiynau ymateb", "Mae hyn yn cynnwys opsiynau ymateb")],
    "ui257": [("gwerth na ellir ei ddangos gan fod y grŵp", "gwerthoedd na ellir eu dangos gan fod y grŵp")],
    "community_club_freq": [("yn ystod Clwb y tu allan i’r ysgol bob wythnos", "mewn clwb y tu allan i’r ysgol bob wythnos")],
    "other_setting_freq": [("yn actif drwy chwaraeon Rhywle arall?", "yn actif drwy chwaraeon yn rhywle arall?")],
    "sports_other_setting": [("eu bod yn eu gwneud Rhywle arall?", "eu bod yn eu gwneud yn rhywle arall?")],
}


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    ws = wb["Strings"]
    if (ws.cell(row=1, column=7).value or "") != "Note":
        ws.cell(row=1, column=7).value = "Note"
    applied = []
    for r in ws.iter_rows(min_row=2):
        key = str(r[3].value or "")
        if key not in CORRECTIONS:
            continue
        val = r[5].value or ""
        for old, new in CORRECTIONS[key]:
            if val.count(old) != 1:
                raise SystemExit(f"{key}: expected exactly one occurrence of {old!r} in the current value; found {val.count(old)}")
            val = val.replace(old, new)
        r[5].value = val
        r[6].value = ((r[6].value or "") + " · " if r[6].value else "") + NOTE
        applied.append(key)
    missing = sorted(set(CORRECTIONS) - set(applied))
    if missing:
        raise SystemExit(f"rows not found in the handoff: {missing}")
    wb.save(dst)
    print(f"applied {len(applied)} corrections: {', '.join(applied)}")


if __name__ == "__main__":
    main()
