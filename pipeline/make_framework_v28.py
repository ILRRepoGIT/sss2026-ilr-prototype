# -*- coding: utf-8 -*-
"""Framework v2.8 — the workbook edit that lets the V4.15 prototype build be
run on any school in the cleansed 2026 dataset (the V5.0 real-school round).

    python -m pipeline.make_framework_v28 config/01_Framework_v2.7.xlsx \
        config/S16_Translations_MASTER_v6_English_import.xlsx config/01_Framework_v2.8.xlsx

Nothing here composes Welsh. Every Welsh string added is read programmatically
from S16 — the SmartSurvey master translation import (the strings as loaded
into the live instrument; sheet 01 Sources, class 0 GOVERNING) — for an
English option label that the live survey carries and the prototype school's
export happened not to contain. The grammatical features of those rows are
assigned by the rules the translator has already confirmed (PR-01: verb-nouns
masculine, unadapted loans masculine; PR-05 / EX-04: unadapted loans do not
mutate) and by the sheet's own sibling rows (pêl- compounds feminine, as
Pêl Droed / Pêl Rwyd / Pêl Fainc); they are PROVISIONAL (PR-20) until the
translator signs them.

Changes, all listed on the new sheet "62 v2.8 change log":
  sheet 23  twelve sport labels the live survey offers but the prototype's
            export did not contain (Baton Twirling … Softball), Welsh from
            S16, status ATTESTED-MASTER, features PROVISIONAL (PR-20).
  sheet 39  PR-20: the features of those twelve rows.
  sheet 43  ui.overview_note and ui.faq_included: the year range that was
            fixed in the text ("Year 3 to Year 11", "Years 3 to 11", and the
            Welsh "Blwyddyn 3 a Blwyddyn 11", "Blynyddoedd 3 i 11") becomes
            the {first}/{last} slots the intro sentence already carries.
            Digits only: no English or Welsh WORD changes; for a 3–11 school
            the realised text is byte-identical. The V4.11 grammar note on
            ui.overview_note had already RAISED this for sheet 49 "before
            other schools are built".
  sheet 49  EN-06 / EN-07: those two client-text edits, sanctioned as
            slot-only edits (D77).
  sheet 63  V5.0 flags — everything the translator or Sport Wales must
            confirm before a real-school report is published.
"""
from __future__ import annotations

import datetime
import html as _html
import re
import sys

import openpyxl

S16_NOTE = ("Approved SmartSurvey master import (S16) — the string as loaded into the live instrument "
            "(Translations_MASTER_v6, sheet Translations, Welsh column). v2.8 (V5.0 real-school round): the live "
            "survey offers this option and the prototype school's export did not contain it. Features PROVISIONAL (PR-20).")

# English label (exactly as S16 carries it) -> (gender, initial class, mutable?, rule applied)
# The Welsh itself is READ from S16 below, never typed here.
NEW_SPORTS = {
    "Baton Twirling":  ("g (m)",  "t", "YES",                      "verb-noun head (troelli) — PR-01 masculine; t- mutates (as Trampolinio)"),
    "Billiards":       ("plural", "b", "YES",                      "plural noun in -iaid (as Dartiaid) — plural; b- mutates"),
    "Floorball":       ("b (f)",  "p", "YES",                      "pêl- compound — feminine as Pêl Droed / Pêl Rwyd / Pêl Fainc; p- mutates"),
    "Gaelic Games":    ("plural", "g", "YES",                      "plural noun (gemau) — plural as Gweithgareddau Ffitrwydd; g- mutates"),
    "Gliding":         ("g (m)",  "g", "YES",                      "verb-noun (gleidio) — PR-01 masculine; g- mutates (as Gwyntsyrffio)"),
    "Handball":        ("b (f)",  "p", "YES",                      "pêl- compound — feminine as Pêl-droed Americanaidd; p- mutates"),
    "Jet Skiing":      ("g (m)",  "s", "NO — immutable initial",   "verb-noun (sgio) — PR-01 masculine; s- immutable (as Sgïo)"),
    "Krav Maga":       ("g (m)",  "k", "NO — unadapted (EX-04)",   "unadapted loan — PR-01/PR-05 masculine, no mutation (as Kung Fu)"),
    "Majorettes":      ("plural", "m", "NO — unadapted (EX-04)",   "unadapted loan, plural in form — no mutation (EX-04)"),
    "Morris Dancing":  ("b (f)",  "d", "YES",                      "sibling row Street Dance / Dawnsio Stryd carries b (f), d, YES — applied identically"),
    "Parachuting":     ("g (m)",  "p", "YES",                      "noun (parasiwt) — masculine default (PR-01); p- mutates"),
    "Softball":        ("b (f)",  "p", "YES",                      "pêl- compound — feminine as Pêl Fas (Baseball); p- mutates"),
}

# sheet 43: (key, en_before, en_after, cy_before, cy_after, slots_before, slots_after)
FRAME_EDITS = [
    ("ui.overview_note",
     "All year groups from Year 3 to Year 11 are represented.",
     "All year groups from Year {first} to Year {last} are represented.",
     "Mae’r holl grwpiau blwyddyn rhwng Blwyddyn 3 a Blwyddyn 11 yn cael eu cynrychioli.",
     "Mae’r holl grwpiau blwyddyn rhwng Blwyddyn {first} a Blwyddyn {last} yn cael eu cynrychioli.",
     "hi, hin, lo, lon", "hi, hin, lo, lon, first, last"),
    ("ui.faq_included",
     "Pupils in Years 3 to 11 at {school}",
     "Pupils in Years {first} to {last} at {school}",
     "Disgyblion ym Mlynyddoedd 3 i 11 yn {school}",
     "Disgyblion ym Mlynyddoedd {first} i {last} yn {school}",
     "school, n", "school, n, first, last"),
]

FLAGS = [
    ("23 Answer labels — 12 new sport rows (PR-20)",
     "Welsh from S16 (the live survey); grammatical features by the confirmed rules PR-01/PR-05 and sibling rows",
     "Baton Twirling, Billiards, Floorball, Gaelic Games, Gliding, Handball, Jet Skiing, Krav Maga, Majorettes, Morris Dancing, Parachuting, Softball. "
     "The running-prose form follows the sheet's mechanical convention (lower case for adapted forms, e.g. ‘pêl-droed americanaidd’; unadapted EX-04 forms keep their capitals) — "
     "‘dawnsio morris’ and ‘gemau gaileg’ therefore appear in lower case in prose; confirm whether the proper-name parts should keep a capital.",
     "confirm the twelve rows (Welsh form, gender, mutation); sign PR-20"),
    ("43 Interface frames — ui.overview_note, ui.faq_included (EN-06/EN-07)",
     "the fixed year range 3–11 became the {first}/{last} slots (digits only)",
     "English: ‘Year {first} to Year {last}’, ‘Years {first} to {last}’. Welsh: ‘rhwng Blwyddyn {first} a Blwyddyn {last}’, ‘ym Mlynyddoedd {first} i {last}’. "
     "For the prototype school (3–11) the realised sentences are unchanged. A school whose year range is not contiguous, or that has no responses in one of its years, "
     "would make ‘All year groups … are represented’ untrue: the build checks every profile year has at least one response and refuses otherwise.",
     "confirm the slotted Welsh reads correctly for ranges such as 3–6 and 7–11"),
    ("53 Proper names — local authorities",
     "four local-authority names in the cleansed dataset have no row",
     "The dataset writes ‘Carmarthenshire’, ‘Conwy’, ‘Rhondda Cynon Taf’ and ‘The Vale of Glamorgan’; sheet 53 carries ‘Conwy County’, ‘Rhondda Borough’, ‘Vale of Glamorgan’ and no Carmarthenshire row. "
     "A school in one of those authorities would show the English name in Welsh mode (data stays as data). None of the three V5.0 schools is affected.",
     "translator to supply ‘Sir Gaerfyrddin’ etc. against the dataset's English spellings before those authorities are built"),
    ("School profile — ‘School Stages Covered’ value",
     "the profile value (e.g. ‘Primary (Years 3–6)’) has no Welsh form in the workbook",
     "As in the V4.15 prototype (‘Primary and secondary (Years 3–11)’), the value is data and stays in English in Welsh mode. Three values are needed for the real-school round: "
     "‘Primary (Years 3–6)’, ‘Secondary (Years 7–11)’, ‘Primary and secondary (Years 3–11)’.",
     "translator to supply the three Welsh forms for sheet 53"),
    ("School profile — Regional Sport Partnership",
     "derived from the local authority by the Sport Wales partnership map, not present in the dataset",
     "Torfaen → Gwent Sport Partnership [GSP]; Flintshire → Actif North Wales; Ceredigion → Mid Wales Sport Partnership [MWSP]. FSM band and teacher-survey status stay ‘To be confirmed by Sport Wales’ as in the prototype.",
     "Sport Wales to confirm the partnership shown on each report"),
    ("22 Qualifier frames — four HELD cohorts (ov none_reported; et other_grouped; tp prefer_not_to_say, communication_aids)",
     "no Welsh relative clause for ‘reported no sport in any setting’, ‘identified with other ethnic groups’, ‘preferred not to say how they take part in sport’, ‘said they usually take part in sport with communication aids’",
     "The prototype school had fewer than five pupils in each of these answer groups, so the bars were never selectable filters and sheet 22 never needed the rows; a real school offers them "
     "(New Inn: ‘No sport reported’ 5 pupils; Castell Alun: ‘Other ethnic groups’ and ‘Prefer not to say’ how they take part). Welsh is never composed in code (D44), so each cohort is HELD (config/held_cohorts.json): "
     "the bar keeps its count and is shown as ‘This value cannot be selected as a filter’, and the validation summary names the hold. Sibling rows: cb ‘na nododd unrhyw chwaraeon clwb’ (PROPOSED); "
     "et ‘a ddewisodd ‘Grwpiau ethnig cymysg neu luosog’’; et ‘y byddai’n well ganddynt beidio â dweud eu hethnigrwydd’; tp ‘a ddywedodd eu bod fel arfer yn cymryd rhan mewn chwaraeon yn eistedd / yn sefyll’.",
     "translator to supply the four sheet-22 rows; each hold is then lifted by deleting its entry"),
    ("Welsh renderers — nil count on a one-pupil base (singleton antecedent)",
     "AGR-possessive at a real school: ‘Ni ddywedodd yr unig ferch … eu bod …’",
     "Six renderers wrote the plural complement (‘eu bod’, ‘nad ydynt’, ‘nad oeddent’, ‘ar eu syniadau’) after a singleton subject (‘yr unig ferch …’) when a group of ONE pupil had a nil count — a case the prototype's data never produced. "
     "They now use the same singular the one-pupil count already uses (D48 pronoun-free ‘y gall …’, ‘nad yw’n aml …’, ‘nad oedd …’, ‘ar ei syniadau’), and a sex-less view keeps PR-03's impersonal, negated (‘Ni nodwyd … gan yr unig ddisgybl …’). "
     "Only constructions the V4.15 corpus does not contain were changed; the prototype's corpus is unchanged (regression: 0 states moved). The PR-02 recast's topic (‘Ni ddewisodd yr un disgybl … ynghylch gwrando ar eu syniadau’) is attested in V4.15 and stands.",
     "translator to confirm the negated singular constructions (welsh_render: r_li_join_cross, r_combined, r_low_confidence, r_listened_always, r_h1_ev_join, r_h1_ev_listened)"),
    ("Narrative module f10 — one-pupil group views (HELD; sheet 49 EN-08)",
     "the locked English templates leader_multi_v2, group_codemand_top3_v12 and wd_current_check_v3 have no one-pupil form",
     "At Ysgol Bro Pedr three group views with exactly one pupil (a cohort of five or more school-wide, one of them in the primary phase) produced ‘selected by 1 of the 1 pupil in the primary phase who …’ and ‘None of the 1 pupil …’, "
     "which the build's own English gate rejects (‘plural template applied to a base of one’). Other modules carry a one-pupil template (unmet_base1_v12, important_base1_v5, barrier_base1_v5, combined_base1_v41); f10 does not, and the English narrative is locked (D01). "
     "A sentence those templates would produce that the build's own gate rejects (‘… of the 1 pupil …’, narrative2.BASE1_GATES) is HELD — not rendered, not audited, logged; every sentence the gate accepts is reproduced unchanged, "
     "including the forms the V4.15 corpus already contains (‘selected by 1 of the 1 boy in the primary phase who …’, ‘… the 1 Year 3 pupil …’), which the gate does not name; the owner's one-pupil forms should cover those too. The validation summary lists the held views.",
     "report owner to sanction one-pupil forms for the three f10 templates (EN-08); the hold is then lifted"),
    ("Welsh h1 summary — one-of-N count with the plural predicate",
     "‘Dywedodd un o’r 20 disgybl … nad ydynt yn aml …’ (V4.15 corpus, attested and locked)",
     "The V5.0 fix for a singleton antecedent (‘yr unig ferch … nad yw’n aml …’) leaves the one-of-N form untouched because the V4.15 corpus attests it and a change would move the locked Welsh without a ruling.",
     "translator to rule whether ‘un o’r N …’ takes ‘nad yw’ (singular) — if so, a ruling moves the corpus (D82)"),
    ("Data — partial responses",
     "the cleansed dataset's analytical set includes partial responses that reached page 48+",
     "The prototype export's partial rows carried no answers and were excluded; the cleansed Stage 2 file already applies the data owner's inclusion rule (completed OR partial with current_page_position ≥ 48), "
     "so a school build accepts every row of the analytical set (profile acceptedStatuses) and reports partial rows separately in its validation summary. "
     "The profile charts' base line (ui.base_line_complete) still reads ‘(complete survey response)’ — the locked interface text of the prototype.",
     "Sport Wales to confirm partial responses count as ‘pupil responses included’; if so, the translator/owner to re-word ui.base_line_complete (sheet 49) or the profile to accept ‘Complete’ only"),
]


def clean(s):
    s = re.sub(r"<[^>]+>", " ", str(s))
    s = _html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def s16_labels(path):
    """English option label -> the single Welsh string S16 carries for it."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    rows = list(wb["Translations"].iter_rows(values_only=True))
    hdr = [str(c or "") for c in rows[1]]
    assert hdr[2].startswith("English") and hdr[3].startswith("1. Welsh"), hdr[:4]
    out = {}
    for r in rows[3:]:
        key = str(r[0] or "")
        if key.startswith("o_") and r[2] is not None:
            en, cy = clean(r[2]), clean(r[3]) if r[3] is not None else ""
            out.setdefault(en, set()).add(cy)
    amb = {k: v for k, v in out.items() if len(v) != 1}
    return {k: next(iter(v)) for k, v in out.items()}, amb


def prose_form(cy, mutable):
    """The sheet's running-prose convention: adapted forms in lower case
    ('pêl-droed americanaidd', 'plymio scuba'); unadapted EX-04 forms keep
    their capitals ('Kung Fu', 'Lacros')."""
    if "unadapted" in mutable:
        return cy
    return cy.lower()


def main():
    src, s16, dst = sys.argv[1], sys.argv[2], sys.argv[3]
    wb = openpyxl.load_workbook(src)
    assert "62 v2.8 change log" not in wb.sheetnames
    log = []
    labels, amb = s16_labels(s16)
    for en in NEW_SPORTS:
        assert en in labels, f"S16 carries no option {en!r}"
        assert en not in amb, f"S16 carries more than one Welsh for {en!r}: {amb[en]}"
    # ---- 23 Answer labels ---------------------------------------------------
    ws = wb["23 Answer labels"]
    existing = {str(r[0].value).strip() for r in ws.iter_rows(min_row=4) if r[0].value}
    for en, (gender, initial, mutable, why) in NEW_SPORTS.items():
        assert en not in existing, en
        cy = labels[en]
        assert cy and cy != en or "unadapted" in mutable, (en, cy)
        assert cy[0].lower() == initial or initial == "vowel", (en, cy, initial)
        ws.append([en, cy, prose_form(cy, mutable), "Sport", gender, initial, mutable,
                   "ATTESTED-MASTER", S16_NOTE + " " + why])
        log.append(("23 Answer labels", en, "NEW ROW", "", cy, "S16 (live survey option); features PR-20 — " + why))
    h = ws.cell(row=1, column=1)
    h.value = str(h.value) + " · v2.8: +12 sport rows from S16 (PR-20), see sheet 62."
    # ---- 39 Provisional rulings -------------------------------------------
    ws39 = wb["39 Provisional rulings"]
    ws39.append(["PR-20",
                 "Sheet 23 — twelve sport labels the live survey offers (S16) that the prototype school's export did not contain: their gender, initial class and mutability.",
                 "FEATURES BY THE CONFIRMED RULES: verb-noun heads and unadapted loans masculine (PR-01), unadapted loans exempt from mutation (PR-05 / EX-04), pêl- compounds feminine and plural nouns ‘plural’ as the sheet's sibling rows; Street Dance's sibling Morris Dancing takes Street Dance's own features. The Welsh strings themselves are S16's, verbatim.",
                 "Leave the rows out and fail any school build in which a pupil reported one of the twelve sports (D44 fail-loud); or assign features by guesswork.",
                 "12 labels; 1,868 pupil mentions Wales-wide in the cleansed dataset",
                 "Industryline, by the translator-confirmed rules; the translator signs sheet 23",
                 "Sign-off of the twelve sheet-23 rows (V5.0 flags, sheet 63)"])
    log.append(("39 Provisional rulings", "PR-20", "NEW RULING", "", "features of the twelve v2.8 sport rows", "V5.0 real-school round"))
    # ---- 43 Interface frames ------------------------------------------------
    ws43 = wb["43 Interface frames"]
    rows43 = {str(r[0].value): r for r in ws43.iter_rows(min_row=4) if r[0].value}
    for key, en_b, en_a, cy_b, cy_a, sl_b, sl_a in FRAME_EDITS:
        r = rows43[key]
        en, cy, slots = str(r[3].value), str(r[4].value), str(r[5].value)
        assert en_b in en and cy_b in cy and slots == sl_b, (key, en[:60], cy[:60], slots)
        r[3].value = en.replace(en_b, en_a)
        r[4].value = cy.replace(cy_b, cy_a)
        r[5].value = sl_a
        r[6].value = ((r[6].value or "") + " · v2.8 (EN-06/EN-07): the fixed year range became the {first}/{last} slots "
                      "the intro sentence carries — digits only, no word changed; realised text unchanged for a 3–11 school.").strip(" ·")
        log.append(("43 Interface frames", key, "EDIT (slots)", en_b, en_a, "EN-06/EN-07 (sheet 49) — schools whose years are not 3–11"))
        log.append(("43 Interface frames", key, "EDIT (slots, Welsh)", cy_b, cy_a, "digits → slots; the translator's words unchanged"))
    # ---- 49 English client edits -------------------------------------------
    ws49 = wb["49 English client edits"]
    ws49.append(["EN-06", "ui.overview_note", "All year groups from Year 3 to Year 11 are represented.",
                 "All year groups from Year {first} to Year {last} are represented.",
                 "The V4.11 grammar note RAISED this for sheet 49 before other schools are built: the range is the school's, not the prototype's. Digits become slots; no word changes; the prototype's realised text is byte-identical.",
                 "SANCTIONED v2.8 (slot-only)"])
    ws49.append(["EN-07", "ui.faq_included", "Pupils in Years 3 to 11 at {school} …",
                 "Pupils in Years {first} to {last} at {school} …",
                 "As EN-06.", "SANCTIONED v2.8 (slot-only)"])
    ws49.append(["EN-08", "narrative module f10 (leader_multi_v2, group_codemand_top3_v12, wd_current_check_v3)",
                 "… selected by 1 of the 1 pupil in the primary phase who … / None of the 1 pupil … already reported …",
                 "(one-pupil forms to be sanctioned)",
                 "LOCKED NARRATIVE — the templates have no one-pupil form and the build's own gate rejects the plural form on a base of one (first produced by real-school data, V5.0). "
                 "Until sanctioned, a sentence the gate rejects is HELD (logged); the forms the gate accepts and the V4.15 corpus contains (‘1 of the 1 boy …’, ‘the 1 Year 3 pupil …’) stand under the lock. Requires the report owner's narrative-lock sign-off.",
                 "PENDING OWNER"])
    log.append(("49 English client edits", "EN-06, EN-07, EN-08", "NEW ROWS", "", "two slot-only edits sanctioned; EN-08 pending owner", "D77 / D01"))
    # ---- 62 change log ------------------------------------------------------
    ws62 = wb.create_sheet("62 v2.8 change log")
    ws62.append([f"Framework v2.8 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v28.py from v2.7. "
                 "Source of every Welsh string added: S16 (the SmartSurvey master translation import, the live instrument). No Welsh composed."])
    ws62.append(["Sheet", "Key", "Change", "Before", "After", "Reason / source"])
    for row in log:
        ws62.append(list(row))
    # ---- 63 V5.0 flags -------------------------------------------------------
    ws63 = wb.create_sheet("63 V5.0 flags")
    ws63.append(["Flags raised while preparing the V5.0 real-school round (three schools from the cleansed 2026 dataset) — each is a question for the translator or Sport Wales; nothing here is decided by Industryline."])
    ws63.append(["Where", "What", "Detail", "Action needed"])
    for f in FLAGS:
        ws63.append(list(f))
    # ---- README -------------------------------------------------------------
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.8 (V5.0 real-school round, 21 Sep 2026): sheet 23 +12 sport rows from S16 (features PROVISIONAL, PR-20); "
                                       "sheet 43 ui.overview_note / ui.faq_included year range as {first}/{last} slots (EN-06/EN-07, digits only); "
                                       "sheet 62 change log; sheet 63 V5.0 flags. No translator wording changed.")
    wb.save(dst)
    print(f"written {dst}: {len(NEW_SPORTS)} sheet-23 rows, {len(FRAME_EDITS)} frame edits, {len(FLAGS)} flags")


if __name__ == "__main__":
    main()
