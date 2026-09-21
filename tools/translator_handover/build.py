# -*- coding: utf-8 -*-
"""Build SSS2026_Welsh_Translator_Handover_V4.13.xlsx — the translator-facing
handover: overview, five task sheets, glossary. Every answer cell is yellow;
every decision is a dropdown; the overview counts what has been filled in."""
import json, math, sys
sys.path.insert(0, "/home/claude/work/tmp/v414")
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
from content_corrections import CORRECTIONS
from content_decisions import DECISIONS, ANSWER_WORDING
from content_translate_rules import TRANSLATE_WHERE, TRANSLATE_EXTRA_EN, TRANSLATE_ORDER, RULES, GLOSSARY

KEYS = json.load(open("/home/claude/work/tmp/v414/keys.json", encoding="utf-8"))
REP = json.load(open("/home/claude/work/sss2026-ilr-prototype/generated/ysgol-penrhyn-dewi.report.json", encoding="utf-8"))
STATIC = REP["welsh"]["static"]; FRAMES = REP["welsh"]["frames"]; MD = REP["metricDefs"]
SAMPLES = json.load(open("/home/claude/work/tmp/v414/samples.json", encoding="utf-8"))
QIN = openpyxl.load_workbook("/home/claude/work/tmp/v414/queue_in.xlsx", read_only=True)

F = "Arial"
BLUE = "094B68"; LIGHT = "EAF1F5"; YELLOW = "FFF2CC"; GREY = "F2F2F2"; RED = "B3261E"
thin = Side(style="thin", color="BFBFBF")
BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
H_FONT = Font(name=F, bold=True, color="FFFFFF", size=10)
H_FILL = PatternFill("solid", fgColor=BLUE)
IN_FILL = PatternFill("solid", fgColor=YELLOW)
BOX_FILL = PatternFill("solid", fgColor=LIGHT)
SEC_FILL = PatternFill("solid", fgColor="D9E2E8")
WRAP = Alignment(wrap_text=True, vertical="top")

wb = openpyxl.Workbook()
wb.remove(wb.active)


def est_height(texts_widths, base=15):
    """Rough row height for wrapped text: lines × 13pt, Arial 10."""
    lines = 1
    for text, width in texts_widths:
        if not text:
            continue
        chars = max(8, int(width * 1.15))
        n = 0
        for para in str(text).split("\n"):
            n += max(1, math.ceil(len(para) / chars))
        lines = max(lines, n)
    return min(400, base * lines + 4)


def title_block(ws, ncols, title, intro_lines, widths):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws["A1"] = title
    ws["A1"].font = Font(name=F, bold=True, size=14, color=BLUE)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=ncols)
    ws.row_dimensions[1].height = 24
    r = 2
    for line in intro_lines:
        c = ws.cell(row=r, column=1, value=line)
        c.font = Font(name=F, size=10, bold=line.startswith("WHAT TO DO") or line.startswith("HOW TO"))
        c.alignment = WRAP; c.fill = BOX_FILL
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=ncols)
        ws.row_dimensions[r].height = est_height([(line, sum(widths))], 14)
        r += 1
    return r + 1


def header(ws, row, labels):
    for i, lab in enumerate(labels, 1):
        c = ws.cell(row=row, column=i, value=lab)
        c.font = H_FONT; c.fill = H_FILL; c.alignment = Alignment(wrap_text=True, vertical="center"); c.border = BORDER
    ws.row_dimensions[row].height = 32
    ws.freeze_panes = ws.cell(row=row + 1, column=1)


def put(ws, row, col, value, inp=False, bold=False, fill=None, color=None):
    c = ws.cell(row=row, column=col, value=value)
    c.font = Font(name=F, size=10, bold=bold, color=color)
    c.alignment = WRAP; c.border = BORDER
    if inp:
        c.fill = IN_FILL
    elif fill:
        c.fill = fill
    return c


def dropdown(ws, col_letter, first, last, options):
    dv = DataValidation(type="list", formula1='"' + ",".join(options) + '"', allow_blank=True, showDropDown=False)
    dv.error = "Please choose one of the options in the list."; dv.errorTitle = "Choose from the list"
    ws.add_data_validation(dv)
    dv.add(f"{col_letter}{first}:{col_letter}{last}")


def section(ws, row, ncols, text):
    c = ws.cell(row=row, column=1, value=text)
    c.font = Font(name=F, bold=True, size=10, color=BLUE); c.fill = SEC_FILL; c.alignment = WRAP
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
    ws.row_dimensions[row].height = 18


# ============================================================ Start here
ws0 = wb.create_sheet("Start here")
W0 = [4, 44, 30, 30, 30]
for i, w in enumerate(W0, 1):
    ws0.column_dimensions[get_column_letter(i)].width = w
ws0["A1"] = "School Sport Survey 2026 — Welsh handover for the interactive school reports"
ws0["A1"].font = Font(name=F, bold=True, size=15, color=BLUE)
ws0.merge_cells("A1:E1"); ws0.row_dimensions[1].height = 26
ws0["A2"] = "Prepared by Industryline Research for the translator · 17 September 2026 (report V4.14) · please read this page first (about five minutes)"
ws0["A2"].font = Font(name=F, italic=True, size=10); ws0.merge_cells("A2:E2")

blocks = [
    ("What the survey is",
     "The School Sport Survey 2026 was completed by pupils in schools across Wales, in English or Welsh. It asks how often pupils take part in sport, where they do it, which sports they do and would like to do, how much they enjoy it, how confident they feel and what would help them do more. Sport Wales uses the results to inform funding and sport provision, and every school that took part receives its own report."),
    ("What is different about these reports",
     "Each school’s report is an INTERACTIVE web page. The reader can filter it — by year group, by gender, or by a group of pupils chosen from a chart (for example “pupils who chose Football”) — and every chart changes. Unusually, the written text changes too: the sentences that explain the findings are rewritten to describe exactly the pupils being viewed. For one school that adds up to about 300,000 possible sentences and paragraphs."),
    ("Why the Welsh is generated by software",
     "The reports must be in Welsh as well as English, and 300,000 sentences cannot be translated one by one. So the Welsh sentences are produced by a text-generation engine: it takes the facts the report is showing (a count, a comparison, a ranking), chooses a sentence pattern for each fact, and then applies a set of Welsh grammar rules — mutations, plural forms, the choice of a/ac, the definite article, agreement — step by step until a finished sentence comes out. The patterns and rules were collected from published Welsh-language Sport Wales and Welsh Government statistical reports and standard grammars. But the engine was built by people who do not speak Welsh, so nobody has yet checked that the rules, and the sentences they produce, are right. That is what we need you for."),
    ("What we need from you — five tasks, each on its own sheet",
     "1  Confirm corrections — 19 places where a reviewer queried the page text you translated (your text is in the report unchanged). Keep your wording, take the suggestion, or give a new version.\n"
     "2  Decide wording — 31 wording decisions on page text (register, capitalisation, one consistent term), plus 5 questions about the wording of the survey’s answer options.\n"
     "2b Answer labels — every answer label and filter chip where your document differs from the survey’s own Welsh, side by side, with the English the survey used; one decision per row.\n"
     "3  Translate — {N3} short pieces of page text that have no Welsh yet (headings, labels, notes, two data-protection messages and three new accessibility labels).\n"
     "4  Check the rules — the 43 grammar rules the engine applies, each with a real sentence from the report. Tell us if any rule is wrong.\n"
     "5  Check sentences — {N5} real generated sentences, English beside Welsh, then 19 sentences from your own document beside the software’s version of the same sentence. Mark each as correct or give the corrected Welsh.\n"
     "A glossary of the terms used in this workbook is on the last sheet."),
    ("How to fill it in",
     "• Every cell you need to fill in is YELLOW. Nothing else needs to be changed.\n"
     "• Cells with a small arrow have a list to choose from — please pick from the list.\n"
     "• Where we ask for a new sentence, write the WHOLE sentence or paragraph, ready to paste into the report, not just the changed words.\n"
     "• Keep anything in curly braces — {n}, {school}, {value} — exactly as it is; the software replaces it with a number or a name.\n"
     "• Please do not change the English or the reference codes in the first column (ui034, ui.doc_title …); we use them to put your Welsh in the right place.\n"
     "• If you are unsure, say so in the Comment column rather than leaving the row blank.\n"
     "• The same wording can appear thousands of times in the report, so one decision on sheet 2 or a rule change on sheet 4 corrects all of them at once."),
    ("Two things to know",
     "• Pupils answered a Welsh version of the survey. Where the report quotes an answer option (‘Llawer’, ‘Dim o gwbl’, ‘1 waith yr wythnos’), it quotes the survey’s own wording so that pupils and teachers see the words that were in the survey. Sheet 2 asks you to confirm this.\n"
     "• The report shows survey figures as numbers (12, 366, 16%), never as words. Only a few fixed phrases use number words (un disgybl, dau ddisgybl, y ddwy gamp)."),
    ("When you are done",
     "Save the file and return it to Alexander Howson at Industryline Research. If anything in this workbook is unclear, ask before guessing — a short question by email is much cheaper than a wrong decision applied to 300,000 sentences."),
]
r = 4
for head, body in blocks:
    ws0.cell(row=r, column=1, value=head).font = Font(name=F, bold=True, size=11, color=BLUE)
    ws0.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5); r += 1
    c = ws0.cell(row=r, column=1, value=body); c.font = Font(name=F, size=10); c.alignment = WRAP; c.fill = BOX_FILL
    ws0.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    ws0.row_dimensions[r].height = est_height([(body, sum(W0))], 14)
    r += 2
prog_row = r
ws0.cell(row=r, column=1, value="Your progress (updates as you fill in the sheets)").font = Font(name=F, bold=True, size=11, color=BLUE)
ws0.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5); r += 1
for i, lab in enumerate(["#", "Sheet", "Answered", "Of", "Status"], 1):
    c = ws0.cell(row=r, column=i, value=lab); c.font = H_FONT; c.fill = H_FILL; c.border = BORDER
PROG_HEADER = r
r += 1
PROG_FIRST = r   # rows filled after the sheets are built

# ============================================================ 1 Confirm corrections
ws1 = wb.create_sheet("1 Confirm corrections")
W1 = [16, 30, 44, 44, 40, 34, 22, 44, 30]
start = title_block(ws1, 9, "Sheet 1 — Reviewer queries on the page text (19 rows)", [
    "WHAT THIS IS: a reviewer checked the Welsh page text you supplied and queried 19 places. The report shows YOUR text exactly as you wrote it; nothing has been changed. For each row, the reviewer’s suggestion is in column E — keep your wording, take the suggestion, or give a new version. For six rows (marked “Rewrite” in column A) a new sentence is needed from you.",
    "WHAT TO DO: read columns C (English), D (the Welsh now in the report) and E (what was found). Then choose an answer from the list in column G. If you choose “Use my version below”, write the whole corrected sentence or paragraph in column H. Column I is for any comment.",
    "Note: column D is your text as it appears in the report today, so “Keep my wording” means leave it exactly as it is.",
], W1)
header(ws1, start, ["Reference", "Where it appears in the report", "English (locked — do not change)", "Welsh now in the report", "What was found", "What we need from you", "Your answer (choose)", "Your version (write the whole sentence / paragraph)", "Comment"])
r = start + 1
first1 = r
for key, where, found, need, kind in CORRECTIONS:
    k = KEYS[key]
    put(ws1, r, 1, key + ("\n(Rewrite)" if kind == "rewrite" else ""), bold=True, color=RED if kind == "rewrite" else None)
    put(ws1, r, 2, where); put(ws1, r, 3, k["en"]); put(ws1, r, 4, k["cy"]); put(ws1, r, 5, found); put(ws1, r, 6, need)
    put(ws1, r, 7, "", inp=True); put(ws1, r, 8, "", inp=True); put(ws1, r, 9, "", inp=True)
    ws1.row_dimensions[r].height = est_height([(k["en"], W1[2]), (k["cy"], W1[3]), (found, W1[4]), (need, W1[5])], 13)
    r += 1
last1 = r - 1
dropdown(ws1, "G", first1, last1, ["Keep my wording", "Use the reviewer’s suggestion", "Use my version below", "Not sure — see comment"])
# example row
put(ws1, r + 1, 1, "EXAMPLE", bold=True); put(ws1, r + 1, 7, "Use the reviewer’s suggestion", fill=PatternFill("solid", fgColor=GREY))
put(ws1, r + 1, 8, "(the whole corrected sentence, written here)", fill=PatternFill("solid", fgColor=GREY))
put(ws1, r + 1, 9, "(any note for us)", fill=PatternFill("solid", fgColor=GREY))
ws1.cell(row=r + 1, column=2, value="This is what a filled-in row looks like — it is not a real item.").font = Font(name=F, italic=True, size=9)

# ============================================================ 2 Decide wording
ws2 = wb.create_sheet("2 Decide wording")
W2 = [18, 30, 40, 44, 44, 34, 24, 44, 30]
start = title_block(ws2, 9, "Sheet 2 — Wording decisions on the page text (31 rows) and on the survey’s answer options (4 rows)", [
    "WHAT THIS IS: the reviewer also listed 31 places where the Welsh is probably fine but a choice is needed — register (formal “y mae” or not), capital letters inside headings, one consistent term where two are used, a natural way to write a chart question. None of these has been changed in the report yet. Several rows share one decision; the “What we need” column says which rows go together — answer the first and just write “same as …” for the others if you like.",
    "WHAT TO DO: read the English (C), the Welsh now in the report (D) and the question (E). Choose an answer in column G. If you choose “Use my version”, write the full text in column H.",
    "At the bottom of the sheet (rows marked AW-1 to AW-4) are four questions about the wording of the survey’s ANSWER OPTIONS, which the report quotes thousands of times. Please read those carefully — they affect more text than anything else in this workbook.",
], W2)
header(ws2, start, ["Reference", "Where it appears in the report", "English (locked)", "Welsh now in the report", "The question", "Our suggested wording (if any)", "Your answer (choose)", "Your version (write the whole text)", "Comment"])
r = start + 1
first2 = r
for key, where, question, suggestion, need in DECISIONS:
    k = KEYS[key]
    put(ws2, r, 1, key, bold=True); put(ws2, r, 2, where); put(ws2, r, 3, k["en"]); put(ws2, r, 4, k["cy"])
    put(ws2, r, 5, question + "\n\n" + need); put(ws2, r, 6, suggestion or "—")
    put(ws2, r, 7, "", inp=True); put(ws2, r, 8, "", inp=True); put(ws2, r, 9, "", inp=True)
    ws2.row_dimensions[r].height = est_height([(k["en"], W2[2]), (k["cy"], W2[3]), (question + " " + need, W2[4]), (suggestion, W2[5])], 13)
    r += 1
last2 = r - 1
dropdown(ws2, "G", first2, last2, ["Keep as it is", "Use the suggested wording", "Use my version below", "Not sure — see comment"])
r += 1
section(ws2, r, 9, "Answer options — how the report quotes what pupils answered (please read the Start here page, “Two things to know”)"); r += 1
first2b = r
for ref, where, question, rec, need in ANSWER_WORDING:
    put(ws2, r, 1, ref, bold=True); put(ws2, r, 2, where); put(ws2, r, 3, "—"); put(ws2, r, 4, "—")
    put(ws2, r, 5, question + "\n\n" + need); put(ws2, r, 6, rec or "—")
    put(ws2, r, 7, "", inp=True); put(ws2, r, 8, "", inp=True); put(ws2, r, 9, "", inp=True)
    ws2.row_dimensions[r].height = est_height([(question + " " + need, W2[4]), (rec, W2[5])], 13)
    r += 1
last2b = r - 1
dropdown(ws2, "G", first2b, last2b, ["Keep the survey wording", "Use my document’s wording", "See my answer in the next column", "Not sure — see comment"])

# ============================================================ 2b Answer labels (query sheet folded in)
ws2b = wb.create_sheet("2b Answer labels")
_q = openpyxl.load_workbook("/home/claude/work/tmp/v415/SSS2026_Answer_labels_survey_vs_translator_query.xlsx")["Survey vs translator"]
for col, dim in _q.column_dimensions.items():
    ws2b.column_dimensions[col].width = dim.width
for rng in _q.merged_cells.ranges:
    ws2b.merge_cells(str(rng))
for row in _q.iter_rows():
    for c in row:
        n = ws2b.cell(row=c.row, column=c.column, value=c.value)
        if c.has_style:
            n.font = c.font.copy(); n.fill = c.fill.copy(); n.alignment = c.alignment.copy(); n.border = c.border.copy()
for rr, dim in _q.row_dimensions.items():
    if dim.height: ws2b.row_dimensions[rr].height = dim.height
for dv in _q.data_validations.dataValidation:
    ndv = DataValidation(type="list", formula1=dv.formula1, allow_blank=True); ws2b.add_data_validation(ndv)
    for sq in str(dv.sqref).split(): ndv.add(sq)
ws2b.freeze_panes = _q.freeze_panes
_qrows = [r for r in _q.iter_rows(min_row=7, values_only=True) if isinstance(r[0], int)]
first2b_q, last2b_q = 7, 6 + len(_qrows)
ws2b["A1"] = "Sheet 2b — Answer labels: the survey’s Welsh, the report today and your document, side by side (" + str(len(_qrows)) + " rows)"

# ============================================================ 3 Translate
ws3 = wb.create_sheet("3 Translate")
W3 = [24, 44, 50, 34, 50, 28]
start = title_block(ws3, 6, "Sheet 3 — Translate the page text that has no Welsh yet ({N3} rows)", [
    "WHAT THIS IS: short pieces of the report that still show English in the Welsh version — headings, labels, notes, two data-protection messages and three labels for a new accessibility switch. Where the English contains a placeholder in curly braces, {n} or {school}, the software replaces it with a number or name; please keep the placeholder exactly as it is, in the place where Welsh word order needs it.",
    "WHAT TO DO: write the Welsh in column E (yellow). Column B says where the text appears and column D gives any notes (placeholders, length, a term to match). Use column F for comments.",
    "Three rows that were on the earlier list (the alternative text for the three ‘Brain Break’ character images) have been removed — the images are being changed.",
], W3)
header(ws3, start, ["Reference", "Where it appears in the report", "English", "Notes", "Your Welsh", "Comment"])
r = start + 1
first3 = r
n3 = 0
for group, keys in TRANSLATE_ORDER:
    section(ws3, r, 6, group); r += 1
    for key in keys:
        en = TRANSLATE_EXTRA_EN.get(key)
        if en is None:
            if key in STATIC: en = STATIC[key]["en"]
            elif key in FRAMES: en = FRAMES[key]["en"]
            elif key in MD: en = MD[key]["label"]
            else: raise SystemExit("no English for " + key)
        where, note = TRANSLATE_WHERE[key]
        put(ws3, r, 1, key, bold=True); put(ws3, r, 2, where); put(ws3, r, 3, en); put(ws3, r, 4, note or "—")
        put(ws3, r, 5, "", inp=True); put(ws3, r, 6, "", inp=True)
        ws3.row_dimensions[r].height = est_height([(where, W3[1]), (en, W3[2]), (note, W3[3])], 13)
        r += 1; n3 += 1
last3 = r - 1
ws3.cell(row=r + 1, column=1, value="EXAMPLE").font = Font(name=F, bold=True, size=10)
put(ws3, r + 1, 3, "Based on: {n} pupils", fill=PatternFill("solid", fgColor=GREY))
put(ws3, r + 1, 5, "Yn seiliedig ar: {n} disgybl", fill=PatternFill("solid", fgColor=GREY))
ws3.cell(row=r + 1, column=2, value="This is what a filled-in row looks like — the placeholder {n} is kept.").font = Font(name=F, italic=True, size=9)

# ============================================================ 4 Check the rules
ws4 = wb.create_sheet("4 Check the rules")
W4 = [5, 22, 62, 56, 14, 20, 50]
start = title_block(ws4, 7, "Sheet 4 — Check the grammar rules the engine applies (43 rules)", [
    "WHAT THIS IS: the Welsh sentences in the report are produced by software following the rules below. The rules were taken from published Welsh statistical reports and standard grammars, but they have never been checked by a Welsh speaker. Each row states one rule in plain English and shows a real sentence from the report that the rule produced.",
    "WHAT TO DO: for each rule choose “Correct”, “Wrong” or “Not sure” in column F. If a rule is wrong or incomplete, say in column G what the rule should be — with an example if you can. Two rows are marked PLEASE CHECK because we suspect a problem ourselves. Column E is our internal reference for the rule; you can ignore it.",
    "You are checking the RULE, not the whole sentence. If a sentence has a different problem, note it on sheet 5 (or in column G here).",
], W4)
header(ws4, start, ["#", "Area", "The rule, in plain English", "A real sentence from the report that uses it", "Our ref.", "Your verdict (choose)", "If wrong: what should the rule be?"])
r = start + 1
first4 = r
for i, (area, rule, example, ref) in enumerate(RULES, 1):
    flag = "PLEASE CHECK" in rule or "PLEASE CHECK" in example
    put(ws4, r, 1, i, bold=True); put(ws4, r, 2, area); put(ws4, r, 3, rule, color=RED if flag else None); put(ws4, r, 4, example); put(ws4, r, 5, ref)
    put(ws4, r, 6, "", inp=True); put(ws4, r, 7, "", inp=True)
    ws4.row_dimensions[r].height = est_height([(rule, W4[2]), (example, W4[3])], 13)
    r += 1
last4 = r - 1
dropdown(ws4, "F", first4, last4, ["Correct", "Wrong", "Not sure"])

# ============================================================ 5 Check sentences
ws5 = wb.create_sheet("5 Check sentences")
W5 = [5, 26, 52, 52, 30, 18, 52, 30]
start = title_block(ws5, 8, "Sheet 5 — Check real generated sentences ({N5} sentences)", [
    "WHAT THIS IS: {N5} sentences taken from the report exactly as the software wrote them (section A), followed by 19 sentences from YOUR document beside the software’s version of the same sentence (section B), with the English the software wrote for the same fact. They were chosen to cover the rules on sheet 4 and the situations that are hardest for the engine: nil counts, a single pupil, comparisons, rankings, filtered views. Column B says which view of the report the sentence comes from; column E lists the rules it uses.",
    "WHAT TO DO: read the Welsh against the English. Choose “Correct” or “Needs change” in column F. If it needs a change, write the corrected Welsh sentence in full in column G and, if you can, say WHY in column H (which word, which rule) — the same fix will then be applied to every sentence built the same way.",
    "The numbers are real data from a test school; do not change them. Answer options in single quotes (‘Llawer’) are the survey’s own wording (see sheet 2, AW-1).",
], W5)
header(ws5, start, ["#", "View of the report it comes from", "English (as generated)", "Welsh (as generated)", "Rules it uses", "Your verdict (choose)", "Corrected Welsh (whole sentence)", "Why / which word"])
r = start + 1
first5 = r
TAGDESC = {
 "NAS": "nasal mutation after yn", "SOFT-o": "soft mutation after o", "AC-FIG": "a/ac before a figure — PLEASE CHECK", "A-ASP": "aspirate after a (and)",
 "CLEFT": "cleft: ‘X’ oedd yr ateb a ddewiswyd amlaf", "NIL": "nil count: Ni ddewisodd yr un …", "SINGLETON": "one pupil: ganddo / ganddi / yr unig …",
 "COMPARE": "o gymharu â", "TRA": "tra bo", "YMHLITH": "ymhlith", "COUNTNP": "number words 1–10 from the fixed table", "RELLONG": "relative a ddywedodd / a nododd",
 "SYDD": "sy’n", "CYMRYD": "Cymerodd … ran", "DYWEDODD": "Dywedodd N o’r …", "NUMSG": "singular noun after y + numeral", "NUMPL": "N o + plural",
 "SPORT-LC": "sport names lower case + mutated", "SUPERL": "superlative / ar ei uchaf", "ORD": "ordinal (ail)", "HPROTH": "eu h-", "NEG": "negative relative nad",
 "PARENTH": "(ac eithrio …)", "AILCAMP": "‘Yr ail camp’ — PLEASE CHECK the mutation after ail",
}
chosen = []
seen_c = set()
order = ["DYWEDODD","CYMRYD","CLEFT","NUMPL","NUMSG","NAS","SOFT-o","A-ASP","AC-FIG","COMPARE","TRA","YMHLITH","RELLONG","SYDD","NEG","NIL","SINGLETON","COUNTNP","SPORT-LC","SUPERL","ORD","AILCAMP","HPROTH","PARENTH"]
per = {"AC-FIG": 1, "NIL": 1, "SINGLETON": 3, "AILCAMP": 1, "COUNTNP": 2, "DYWEDODD": 2, "NAS": 2, "TRA": 2, "SYDD": 2, "NEG": 2, "SUPERL": 2, "HPROTH": 2, "PARENTH": 2, "NUMSG": 2, "CYMRYD": 2}
for tag in order:
    n = per.get(tag, 2 if tag in ("CLEFT","COMPARE","RELLONG","SPORT-LC") else 1)
    for sk, mid, t, c in SAMPLES.get(tag, []):
        if len([x for x in chosen if x[0] == tag]) >= n: break
        if c in seen_c: continue
        if any(x[0] == tag and x[2] == mid for x in chosen): continue     # variety: one module per rule
        if any(c[:60] == x[4][:60] for x in chosen): continue              # no near-duplicates
        seen_c.add(c); chosen.append((tag, sk, mid, t, c))
# make sure the two PLEASE CHECK cases are present
def desc_view(sk):
    st = REP["states"].get(sk, {}); sc = st.get("scope", {})
    return (sc.get("short") or sk) + ("  ·  " + sc["shortCy"] if sc.get("shortCy") else "")
chosen = chosen[:40]
for i, (tag, sk, mid, t, c) in enumerate(chosen, 1):
    flag = tag in ("AC-FIG", "AILCAMP")
    put(ws5, r, 1, i, bold=True); put(ws5, r, 2, desc_view(sk)); put(ws5, r, 3, t); put(ws5, r, 4, c)
    tags = [TAGDESC[tag]] + [TAGDESC[x] for x in ("NAS","SOFT-o","CLEFT","NUMPL","YMHLITH","SYDD") if x != tag and any(c == y[3] for y in SAMPLES.get(x, []))]
    put(ws5, r, 5, "; ".join(tags), color=RED if flag else None)
    put(ws5, r, 6, "", inp=True); put(ws5, r, 7, "", inp=True); put(ws5, r, 8, "", inp=True)
    ws5.row_dimensions[r].height = est_height([(t, W5[2]), (c, W5[3]), ("; ".join(tags), W5[4])], 13)
    r += 1
last5 = r - 1
dropdown(ws5, "F", first5, last5, ["Correct", "Needs change", "Not sure"])
n5 = len(chosen)
# --- section B: the translator's own versions of 19 engine sentences, beside the engine's
sys.path.insert(0, "/home/claude/work/tmp/v416")
from audit_content import GENERATED
r += 1
section(ws5, r, 8, "Your sentences beside the engine’s — 19 sentences you translated in your document that the software writes itself. Column C is YOUR version, column D the engine’s, column E the rule(s) that make them differ. Please say which is right, or give a third version."); r += 1
first5b = r
for i, doc, gen, why, verdict, where in GENERATED:
    put(ws5, r, 1, "T" + str(i), bold=True); put(ws5, r, 2, "Whole school · All pupils (your document, section ‘An Active Nation’ / ‘A Lifelong Enjoyment’)")
    put(ws5, r, 3, doc); put(ws5, r, 4, gen); put(ws5, r, 5, why)
    put(ws5, r, 6, "", inp=True); put(ws5, r, 7, "", inp=True); put(ws5, r, 8, "", inp=True)
    ws5.row_dimensions[r].height = est_height([(doc, W5[2]), (gen, W5[3]), (why, W5[4])], 13)
    r += 1
last5b = r - 1
dropdown(ws5, "F", first5b, last5b, ["My version is right", "The engine’s version is right", "Neither — see my version", "Not sure"])
n5b = len(GENERATED)

# ============================================================ Glossary
wsg = wb.create_sheet("Glossary")
Wg = [34, 110]
start = title_block(wsg, 2, "Glossary — the terms used in this workbook", ["Plain-English meanings of the words we use on the other sheets. Nothing to fill in here."], Wg)
header(wsg, start, ["Term", "Meaning"])
r = start + 1
for term, meaning in GLOSSARY:
    put(wsg, r, 1, term, bold=True); put(wsg, r, 2, meaning)
    wsg.row_dimensions[r].height = est_height([(meaning, Wg[1])], 13); r += 1
wsg.freeze_panes = None

# ============================================================ progress rows on Start here
rows = [
    ("1", "1 Confirm corrections", f"=COUNTA('1 Confirm corrections'!G{first1}:G{last1})", last1 - first1 + 1),
    ("2", "2 Decide wording", f"=COUNTA('2 Decide wording'!G{first2}:G{last2})+COUNTA('2 Decide wording'!G{first2b}:G{last2b})", (last2 - first2 + 1) + (last2b - first2b + 1)),
    ("2b", "2b Answer labels", f"=COUNTA('2b Answer labels'!O{first2b_q}:O{last2b_q})", len(_qrows)),
    ("3", "3 Translate", f"=COUNTA('3 Translate'!E{first3}:E{last3})", n3),
    ("4", "4 Check the rules", f"=COUNTA('4 Check the rules'!F{first4}:F{last4})", last4 - first4 + 1),
    ("5", "5 Check sentences", f"=COUNTA('5 Check sentences'!F{first5}:F{last5})+COUNTA('5 Check sentences'!F{first5b}:F{last5b})", n5 + n5b),
]
r = PROG_FIRST
for num, name, formula, total in rows:
    put(ws0, r, 1, num); put(ws0, r, 2, name); put(ws0, r, 3, formula); put(ws0, r, 4, total)
    put(ws0, r, 5, f'=IF(C{r}>=D{r},"Complete",IF(C{r}=0,"Not started","In progress"))')
    r += 1
ws0.cell(row=r + 1, column=2, value="Counts are of the yellow ‘Your answer’ / ‘Your Welsh’ cells that have something in them.").font = Font(name=F, italic=True, size=9)

# sheet tab colours
for ws, col in ((ws0, BLUE), (ws1, "FA2A3C"), (ws2, "FA2A3C"), (ws2b, "FA2A3C"), (ws3, "FA2A3C"), (ws4, "FEBD06"), (ws5, "FEBD06"), (wsg, "B3B3B3")):
    ws.sheet_properties.tabColor = col
    ws.sheet_view.zoomScale = 90
    ws.page_setup.orientation = "landscape"; ws.page_setup.paperSize = ws.PAPERSIZE_A4
    ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True

for ws in (ws0, ws3, ws5):
    for row in ws.iter_rows():
        for c in row:
            if isinstance(c.value, str) and ("{N3}" in c.value or "{N5}" in c.value):
                c.value = c.value.replace("{N3}", str(n3)).replace("{N5}", str(n5))
out = "/home/claude/work/tmp/v414/SSS2026_Welsh_Translator_Handover_V4.13.xlsx"
wb.save(out)
print("saved", out, {"corrections": last1 - first1 + 1, "decisions": last2 - first2 + 1, "answer_wording": last2b - first2b + 1, "translate": n3, "rules": last4 - first4 + 1, "sentences": n5})
