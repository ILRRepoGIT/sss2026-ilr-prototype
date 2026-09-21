# -*- coding: utf-8 -*-
"""Framework v2.3 — the workbook edit for the V4.11 round.

    python -m pipeline.make_framework_v23 config/01_Framework_v2.2.xlsx config/01_Framework_v2.3.xlsx

Every cell written here is either (a) the report's existing ENGLISH, moved
from application code into the workbook so the client can stop emitting
English outside the language layer (assessment §8, §9.3, §9.5), (b) the
TRANSLATOR's Welsh for exactly that English, carried verbatim from the
document "18117 Chwaraeon Cymru 2026 School Sport Survey - School
Reports.docx" (sha 15d726d0…), with slots put where the document's figures
and names stood, or (c) an inventory sheet. No Welsh word is composed here:
a row whose English the translator did not cover has an empty Welsh cell and
the status TRANSLATOR (the client shows English under the review marker in
a development build; release CAT-values refuses it).

Changes, all listed on the new sheet "55 v2.3 change log":
  sheet 43  new frames for the client's remaining English routes (navigation,
            school profile headings and technical record, ethnicity table,
            FSM card, cover/rail/contents ARIA names, image alt text, the
            document title, the selected tick, the review note) and for the
            slot-bearing sentences the static lane could not carry (intro
            sentence, two FAQ sentences, the four "This bar chart shows…"
            sentences, the any-activity headline and note, the overview note);
            two edits: ui.banner_showing prefix "Rydych chi’n gweld:" and
            ui.stack_caption_sex "rhywedd" (the translator's terms).
  sheet 53  Proper names: the 21 local authorities and 5 RSPs, English and
            Welsh, from the translator's document (data the profile reads).
  sheet 54  Translator label overlay — INACTIVE: the translator's Welsh for
            answer labels, cohort labels, the stacked-chart legend and two
            filter labels where it differs from sheets 23/28/43, with the
            workbook's current value beside it. Not applied to the live
            sheets: applying them changes the generated corpus and several
            need a per-question label structure (Very/Quite/Not very), so
            they wait for the linguist's ruling (assessment §12).
"""
from __future__ import annotations

import datetime
import sys

import openpyxl

TR = "TRANSLATED (document 15 Sep 2026)"
PEND = "TRANSLATOR"
DER = "DERIVED — confirm"

# (key, path, consumer, en, cy, slots, notes, status)
NEW_FRAMES = [
    # --- navigation (assessment §8: injectNav) ---
    ("ui.nav_back", "V4.11 §8", "injectNav link", "← Back", "← Yn ôl", "—", "Arrow is punctuation; the word is the document's 'Back' row.", TR),
    ("ui.nav_contents", "V4.11 §8", "injectNav link", "Contents", "Cynnwys", "—", "", TR),
    ("ui.nav_next", "V4.11 §8", "injectNav link", "Next →", "Nesaf →", "—", "", TR),
    ("ui.nav_aria", "V4.11 §8", "injectNav aria-label", "Section navigation", "", "—", "Not in the document.", PEND),
    # --- school profile (renderProfile) ---
    ("ui.profile_school_name", "V4.11 §8", "overview-table heading", "School Name", "Enw’r Ysgol", "—", "", TR),
    ("ui.profile_la", "V4.11 §8", "overview-table heading", "Local Authority", "Awdurdod Lleol", "—", "", TR),
    ("ui.profile_rsp", "V4.11 §8", "overview-table heading", "Regional Sport Partnership", "Partneriaeth Chwaraeon Ranbarthol", "—", "", TR),
    ("ui.profile_stages", "V4.11 §8", "overview-table heading", "School Stages Covered", "Cyfnodau Ysgol wedi’u Cynnwys", "—", "", TR),
    ("ui.appendix_total_responses", "V4.11 §8.1", "overview-table heading (was a code catalogue key)", "Total number of pupil responses included in this report", "Cyfanswm nifer yr ymatebion gan ddisgyblion sydd wedi’u cynnwys yn yr adroddiad hwn", "—", "Previously absent from the catalogue (assessment §8.1).", TR),
    ("ui.profile_fieldwork", "V4.11 §8", "overview-table heading", "Survey Fieldwork Dates", "Dyddiadau Gwaith Maes yr Arolwg", "—", "The date value itself is data (sheet 53 note).", TR),
    ("ui.base_line_complete", "V4.11 §8", "profile charts base line", "Based on: {n} pupils (complete survey response)", "Yn seiliedig ar: {n:count disgybl} (ymatebion cyflawn i’r arolwg)", "n", "Suffix moved into the frame (assessment §8). Document row 'Based on: 366 pupils (complete survey responses)'.", TR),
    ("ui.intro_sentence", "V4.11 §6.4", "#intro-sentence", "This report presents the responses given by pupils at {school}: {n} pupil responses are included, across Years {first} to {last}.", "Mae’r adroddiad hwn yn cyflwyno’r ymatebion a roddwyd gan disgyblion yn {school}: Mae {n} o ymatebion disgyblion wedi’u cynnwys, dros Flynyddoedd {first} i {last}.", "school, n, first, last", "Replaces static fragments ui017/ui018 (slot-bearing). 'gan disgyblion' is the translator's form — linguist to confirm the mutation.", TR),
    ("ui.any_activity", "V4.11 §8", "#any-activity-note headline", "{n} of the {base} pupils across the whole school ({pct}%) reported taking part in at least one sport or activity this school year, in at least one setting.", "Adroddodd {n} o’r {base} o ddisgyblion ar draws yr ysgol gyfan ({pct}%) eu bod wedi cymryd rhan mewn o leiaf un gamp neu weithgaredd yn y flwyddyn ysgol hon, mewn o leiaf un lleoliad.", "n, base, pct", "", TR),
    ("ui.any_activity_note", "V4.11 §8", "#any-activity-note note", "This statement always describes the whole school. The rest of this chapter shows where pupils take part, and how often.", "Mae’r datganiad hwn bob amser yn disgrifio’r ysgol gyfan. Mae gweddill y bennod hon yn dangos ymhle mae disgyblion yn cymryd rhan, a pha mor aml.", "—", "", TR),
    ("ui.overview_note", "V4.11 §8", "#overview-note", "All year groups from Year 3 to Year 11 are represented. {hi} contributed the largest number of responses ({hin}) and {lo} the smallest ({lon}). Every response option is shown, including those selected by no pupils. Unequal group sizes should be kept in mind when comparing raw counts.", "Mae’r holl grwpiau blwyddyn rhwng Blwyddyn 3 a Blwyddyn 11 yn cael eu cynrychioli. {hi} gyfrannodd y nifer fwyaf o ymatebion ({hin}) a {lo} y lleiaf ({lon}). Mae pob opsiwn ymateb yn cael ei ddangos, gan gynnwys yr opsiynau na wnaeth yr un disgybl eu dewis. Dylid cadw meintiau grwpiau anghyfartal mewn cof wrth gymharu niferoedd crai.", "hi, hin, lo, lon", "The year range 3–11 is fixed in the English (locked); RAISED for sheet 49 before other schools are built.", TR),
    ("ui.faq_included", "V4.11 §6.4", "FAQ 'Who is included'", "Pupils in Years 3 to 11 at {school} who completed the 2026 School Sport Survey: {n} pupil responses are included. The page “Which pupils in our school took part in 2026?” shows exactly who they are.", "Disgyblion ym Mlynyddoedd 3 i 11 yn {school} a atebodd Arolwg Chwaraeon Ysgol 2026: Mae {n} o ymatebion disgyblion wedi’u cynnwys. Mae’r dudalen “Pa ddisgyblion yn ein hysgol gymerodd ran yn 2026?” yn dangos pwy yn union ydyn nhw.", "school, n", "Replaces ui036–ui038.", TR),
    ("ui.faq_missing", "V4.11 §6.4", "FAQ 'Why are some responses missing'", "This report includes survey responses where pupils completed at least 80% of the survey. Responses with less information were not included, as there was not enough data to provide a meaningful picture of pupils’ views. As a result, more pupils from your school may have taken part in the survey than the total number shown here. The following sections therefore reflect the {n} responses that provided enough information to be included in the report.", "Mae’r adroddiad hwn yn cynnwys ymatebion i’r arolwg pan roedd disgyblion wedi cwblhau o leiaf 80% o’r arolwg. Nid oedd ymatebion gyda llai o wybodaeth wedi cael eu cynnwys, gan nad oedd digon o ddata i ddarparu darlun ystyrlon o safbwyntiau disgyblion. O ganlyniad, efallai y gwnaeth mwy o ddisgyblion yn eich ysgol gymryd rhan yn yr arolwg na chyfanswm y nifer sy’n cael ei ddangos isod. Felly, mae’r adrannau canlynol yn adlewyrchu’r {n} o ymatebion a ddarparodd ddigon o wybodaeth i gael ei chynnwys yn yr adroddiad hwn.", "n", "Replaces ui040/ui041.", TR),
    ("ui.chart_sports_total_pe", "V4.11 §6.4", "PE chart note", "This bar chart shows the most common 10 sports pupils said they did in PE and Lesson Time, and how often pupils said they usually do them. There were a total of {n} sports to choose from. Click on the ‘View Data Table’ to see the full results.", "Mae’r siart bar hwn yn dangos y 10 camp fwyaf cyffredin y dywedodd disgyblion eu bod yn eu gwneud mewn Addysg Gorfforol ac amser gwersi, a pha mor aml y dywedodd disgyblion eu bod yn eu gwneud nhw, fel arfer. Roedd cyfanswm o {n} o gampau i ddewis o’u plith. Cliciwch ar ‘Gweld y Tabl Data’ i weld y canlyniadau llawn.", "n", "Replaces ui116 + ui117.", TR),
    ("ui.chart_sports_total_club", "V4.11 §6.4", "school-club chart note", "This bar chart shows the most common 10 sports pupils said they did in a School Sports Club, and how often pupils said they usually do them. There were a total of {n} sports to choose from. Click on the ‘View Data Table’ to see the full results.", "", "n", "Replaces ui119 + ui117. Not in the document.", PEND),
    ("ui.chart_sports_total_community", "V4.11 §6.4", "community-club chart note", "This bar chart shows the most common 10 sports pupils said they did in a Club Outside of School, and how often pupils said they usually do them. There were a total of {n} sports to choose from. Click on the ‘View Data Table’ to see the full results.", "", "n", "Replaces ui127 + ui117. Not in the document.", PEND),
    ("ui.chart_sports_total_other", "V4.11 §6.4", "somewhere-else chart note", "This bar chart shows the most common 10 sports pupils said they did Somewhere Else, and how often pupils said they usually do them. There were a total of {n} sports to choose from. Click on the ‘View Data Table’ to see the full results.", "", "n", "Replaces ui129 + ui117. Not in the document.", PEND),
    # --- ethnicity table (renderProfileExtra) ---
    ("ui.eth_heading", "V4.11 §8", "profile ethnicity table heading", "What is the ethnicity of your pupils who took part?", "Beth yw ethnigrwydd eich disgyblion a gymerodd ran?", "—", "", TR),
    ("ui.eth_col_group", "V4.11 §8", "profile ethnicity table th", "High level ethnic group", "Grŵp ethnig lefel uchel", "—", "", TR),
    ("ui.eth_col_pupils", "V4.11 §8", "profile ethnicity table th", "Pupils", "Disgyblion", "—", "", TR),
    ("ui.eth_note", "V4.11 §8", "profile ethnicity table note", "All response categories are shown, including those selected by no pupils. This table always shows the whole school and is not affected by filters.", "Dangosir yr holl gategorïau ymateb, gan gynnwys y rhai na wnaeth yr un disgybl eu dewis. Mae’r tabl hwn bob amser yn dangos yr ysgol gyfan ac nid yw hidlyddion yn effeithio arno.", "—", "", TR),
    # --- FSM card ---
    ("ui.fsm_context_title", "V4.11 §8.1", "profile FSM card title (was a code catalogue key)", "Free school meals context", "", "—", "The document translates a DIFFERENT FSM card ('Free School Meal Quartile: / Your School is in Free School Meal Quartile 1 / See “What are…”'); the report's English is locked — RAISED for sheet 49.", PEND),
    ("ui.fsm_context_body", "V4.11 §8.1", "profile FSM card body", "Sport Wales uses the proportion of pupils eligible for Free School Meals as an indicator for deprivation. Your school’s figure (PLASC data): {value}", "", "value", "As above. The value is the ui.fsm_context_value frame (a frame may not end with a delimiter, FRAME-delimiter).", PEND),
    ("ui.fsm_context_value", "V4.11 §8", "profile FSM card value", "to be confirmed", "", "—", "Was a hard-coded suffix.", PEND),
    # --- technical record ---
    ("ui.meta_survey_year", "V4.11 §8", "meta-table", "Survey year", "", "—", "", PEND),
    ("ui.meta_report_version", "V4.11 §8", "meta-table", "Report version", "", "—", "", PEND),
    ("ui.meta_version_value", "V4.11 §8", "meta-table value", "{report} · schema {schema}", "", "report, schema", "", PEND),
    ("ui.meta_pipeline", "V4.11 §8", "meta-table", "Pipeline version", "", "—", "", PEND),
    ("ui.meta_suppression", "V4.11 §8", "meta-table", "Suppression model", "", "—", "", PEND),
    ("ui.meta_generated", "V4.11 §8", "meta-table", "Generated", "", "—", "", PEND),
    ("ui.meta_checksum", "V4.11 §8", "meta-table", "Source checksum", "", "—", "", PEND),
    ("ui.meta_weighting", "V4.11 §8", "meta-table", "Weighting", "", "—", "", PEND),
    ("ui.meta_weighting_value", "V4.11 §8", "meta-table value", "None — raw respondent counts", "", "—", "", PEND),
    # --- title / ARIA / alt / generated content (assessment §9.3) ---
    ("ui.doc_title", "V4.11 §8", "document.title", "Interactive Learning Report — {school}", "", "school", "The document's 'Interactive Report' is a different string (title page).", PEND),
    ("ui.aria_cover", "V4.11 §9.3", "section#m-cover aria-label", "Report cover", "", "—", "", PEND),
    ("ui.aria_rail", "V4.11 §9.3", "aside.filter-rail aria-label", "Explore results", "Archwilio’r Canlyniadau", "—", "Document row 'Explore Results'.", TR),
    ("ui.aria_toc", "V4.11 §9.3", "nav#rail-toc aria-label", "Report contents", "", "—", "", PEND),
    ("ui.alt_brain_javelin", "V4.11 §9.3", "img alt", "Brain Break character: a smiling brain wearing a Sport Wales headband, throwing a javelin from a wheelchair", "", "—", "", PEND),
    ("ui.alt_brain_football", "V4.11 §9.3", "img alt", "Brain Break character: a smiling brain in glasses kicking a football", "", "—", "", PEND),
    ("ui.alt_brain_basketball", "V4.11 §9.3", "img alt", "Brain Break character: a smiling brain in glasses dribbling a basketball", "", "—", "", PEND),
    ("ui.selected_tick", "V4.11 §9.3", "selected value marker (was CSS ::after content)", "✓ Selected", "✓ Dewiswyd", "—", "'Dewiswyd' is the workbook's own rendering of 'Selected' in the cohort label template (sp_*). Linguist to confirm in this position.", DER),
    ("ui.review_note", "V4.11 §9.5", "#review-note-cy (Welsh mode, review builds only)", "Review build: {done} of {total} page-text rows are in Welsh; {pending} still await translation and appear in marked English.", "", "done, total, pending", "Replaces the fixed Welsh note that said all page furniture was untranslated.", PEND),
]

EDITS = {
    # key: (column index in the row, old, new, reason)
    "ui.banner_showing": (4, "Yn dangos: {desc} · {n:count ymateb disgybl} wedi’u cynnwys",
                          "Rydych chi’n gweld: {desc} · {n:count ymateb disgybl} wedi’u cynnwys",
                          "Translator's banner label 'You are viewing' → 'Rydych chi’n gweld' (document rows 1, 184); the count phrase keeps the sheet-50 noun."),
    "ui.stack_caption_sex": (4, "Disgyblion a wnaeth o leiaf un gamp ym mhob lleoliad, yn ôl grŵp blwyddyn a rhyw.",
                             "Disgyblion a wnaeth o leiaf un gamp ym mhob lleoliad, yn ôl grŵp blwyddyn a rhywedd.",
                             "Translator's term for Gender is 'Rhywedd' throughout the document (rows 32, 152, 283); assessment §7.2 asked for one term."),
}

LA_NAMES = [
    ("Blaenau Gwent", "Blaenau Gwent"), ("Bridgend", "Pen-y-bont ar Ogwr"), ("Caerphilly", "Caerffili"),
    ("Cardiff", "Caerdydd"), ("Ceredigion", "Ceredigion"), ("Conwy County", "Sir Conwy"),
    ("Denbighshire", "Sir Ddinbych"), ("Flintshire", "Sir y Fflint"), ("Gwynedd", "Gwynedd"),
    ("Isle of Anglesey", "Ynys Môn"), ("Merthyr Tydfil", "Merthyr Tudful"), ("Monmouthshire", "Sir Fynwy"),
    ("Neath Port Talbot", "Castell-nedd Port Talbot"), ("Newport", "Casnewydd"), ("Pembrokeshire", "Sir Benfro"),
    ("Powys", "Powys"), ("Rhondda Borough", "Bwrdeistref y Rhondda"), ("Swansea", "Abertawe"),
    ("Torfaen", "Torfaen"), ("Vale of Glamorgan", "Bro Morgannwg"), ("Wrexham", "Wrecsam"),
]
RSP_NAMES = [
    ("Actif North Wales", "Gogledd Cymru Actif"),
    ("West Wales Sport Partnership [WWSP]", "Partneriaeth Chwaraeon Gorllewin Cymru [WWSP]"),
    ("Mid Wales Sport Partnership [MWSP]", "Partneriaeth Chwaraeon Canolbarth Cymru [MWSP]"),
    ("Central South Active Partnership [CSAP]", "Partneriaeth Actif Canolbarth y De [CSAP]"),
    ("Gwent Sport Partnership [GSP]", "Partneriaeth Chwaraeon Gwent [GSP]"),
]


def main():
    src, dst = sys.argv[1], sys.argv[2]
    overlay = sys.argv[3] if len(sys.argv) > 3 else None     # V4.10 register xlsx (sheet "2 framework-dynamic DIFFERS")
    wb = openpyxl.load_workbook(src)
    log = []
    ws = wb["43 Interface frames"]
    existing = {}
    for r in ws.iter_rows(min_row=4):
        if r[0].value:
            existing[str(r[0].value)] = r
    for key, (col, old, new, why) in EDITS.items():
        row = existing[key]
        assert str(row[col].value) == old, (key, row[col].value)
        row[col].value = new
        note = row[6].value or ""
        row[6].value = (note + " · v2.3: " + why).strip(" ·")
        log.append(("43 Interface frames", key, "EDIT", old, new, why))
    for f in NEW_FRAMES:
        assert f[0] not in existing, f[0]
        ws.append(list(f))
        log.append(("43 Interface frames", f[0], "NEW", "", f[4] or "(empty — translator)", f[6]))
    # ---- 53 Proper names --------------------------------------------------
    ws53 = wb.create_sheet("53 Proper names")
    ws53.append(["Proper names — the profile's data values in both languages (V4.11, assessment §8 renderProfile:overview-value). Source: the translator's document rows 200–201. The profile shows the Welsh form in Welsh mode when the English value matches a row here; a value with no row stays as data and is listed by the browser gate."])
    ws53.append(["Kind", "English", "Welsh", "Source", "Status"])
    for en, cy in LA_NAMES:
        ws53.append(["Local authority", en, cy, "document row 201", TR])
    for en, cy in RSP_NAMES:
        ws53.append(["Regional Sport Partnership", en, cy, "document row 200", TR])
    ws53.append(["Fieldwork dates", "13th April – 17th July 2026", "13 Ebrill – 17 Gorffennaf 2026", "document row 199", TR])
    log.append(("53 Proper names", "*", "NEW SHEET", "", f"{len(LA_NAMES)} LAs, {len(RSP_NAMES)} RSPs, fieldwork dates", "data for the profile"))
    # ---- 54 Translator label overlay (inactive) ---------------------------
    ws54 = wb.create_sheet("54 Translator label overlay")
    ws54.append(["INACTIVE OVERLAY — the translator's Welsh where it differs from the live sheets (23 Answer labels, 28/43 client strings, the stacked-chart legend). Nothing on this sheet is read by the build. Applying a row changes the generated corpus (answer labels are quoted in narrative) and the lock; several labels (Very / Quite / Not very / Not at all) need a per-question label structure the workbook does not have. Each row waits for the linguist's ruling (assessment §12) and is applied by moving the value to its live sheet."])
    ws54.append(["Where (live)", "English", "Workbook Welsh (live)", "Translator's Welsh (document)", "Apply?", "Ruling / note"])
    n54 = 0
    if overlay:
        ob = openpyxl.load_workbook(overlay, read_only=True)
        if "2 framework-dynamic DIFFERS" in ob.sheetnames:
            seen = set()
            for r in list(ob["2 framework-dynamic DIFFERS"].iter_rows(values_only=True))[1:]:
                where, en, rest = str(r[1]), str(r[2]), str(r[3])
                cy_doc, _, cy_live = rest.partition("  ‖ report: ")
                k = (where.split(" ")[0], en, cy_doc)
                if k in seen:
                    continue
                seen.add(k)
                ws54.append([where, en, cy_live.strip(), cy_doc.strip(), "NO", ""])
                n54 += 1
    log.append(("54 Translator label overlay", "*", "NEW SHEET (inactive)", "", f"{n54} rows", "awaiting the linguist"))
    # ---- 55 change log ----------------------------------------------------
    ws55 = wb.create_sheet("55 v2.3 change log")
    ws55.append([f"Framework v2.3 change log — generated {datetime.date.today().isoformat()} by pipeline/make_framework_v23.py from v2.2. Sources: the translator's document (15 Sep 2026) and the V4.10 independent assessment (15 Sep 2026)."])
    ws55.append(["Sheet", "Key", "Change", "Before", "After", "Reason / source"])
    for row in log:
        ws55.append(list(row))
    # README first line
    ws0 = wb["00 README"]
    ws0.insert_rows(1)
    ws0.cell(row=1, column=1).value = ("Version 2.3 (V4.11 round, 15 Sep 2026): sheet 43 frames for the client's remaining English routes and the slot-bearing sentences, two frame edits, "
                                      "sheet 53 Proper names, sheet 54 Translator label overlay (INACTIVE), sheet 55 change log. See sheet 55.")
    wb.save(dst)
    print(f"written {dst}: {len(NEW_FRAMES)} new frames, {len(EDITS)} edits, {len(LA_NAMES)+len(RSP_NAMES)+1} proper-name rows, {n54} overlay rows")


if __name__ == "__main__":
    main()
