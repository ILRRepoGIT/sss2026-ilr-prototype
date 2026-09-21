import json,sys,openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
sys.path.insert(0,"/home/claude/work/tmp/v416")
from audit_content import FRAMES, CLIENT, GENERATED, V_OVERSIGHT, V_RULE, V_DECISION, V_ENGINE, V_OWNER, V_OK
A=json.load(open("audit_A.json",encoding="utf-8"))
F="Arial"; BLUE="094B68"; thin=Side(style="thin",color="BFBFBF"); B=Border(left=thin,right=thin,top=thin,bottom=thin); WRAP=Alignment(wrap_text=True,vertical="top")
RED=PatternFill("solid",fgColor="FADBD8"); AMB=PatternFill("solid",fgColor="FFF2CC"); GRN=PatternFill("solid",fgColor="E2F0D9"); GREY=PatternFill("solid",fgColor="EAF1F5")
def fill_for(v):
    return GRN if v.startswith("Already") or v=="Verbatim" else RED if v.startswith("Oversight") else AMB
wb=openpyxl.Workbook(); ws=wb.active; ws.title="Summary"
def sheet(name,title,intro,hdr,widths,rows,fillcol=None):
    w=wb.create_sheet(name)
    for i,x in enumerate(widths,1): w.column_dimensions[get_column_letter(i)].width=x
    w["A1"]=title; w["A1"].font=Font(name=F,bold=True,size=13,color=BLUE); w.merge_cells(start_row=1,start_column=1,end_row=1,end_column=len(hdr))
    r=2
    for t in intro:
        c=w.cell(row=r,column=1,value=t); c.font=Font(name=F,size=10); c.alignment=WRAP; c.fill=GREY
        w.merge_cells(start_row=r,start_column=1,end_row=r,end_column=len(hdr)); w.row_dimensions[r].height=48; r+=1
    r+=1
    for i,h in enumerate(hdr,1):
        c=w.cell(row=r,column=i,value=h); c.font=Font(name=F,bold=True,color="FFFFFF",size=10); c.fill=PatternFill("solid",fgColor=BLUE); c.alignment=Alignment(wrap_text=True,vertical="center"); c.border=B
    w.row_dimensions[r].height=36; w.freeze_panes=w.cell(row=r+1,column=1); r+=1
    for row in rows:
        for j,v in enumerate(row,1):
            c=w.cell(row=r,column=j,value=v); c.font=Font(name=F,size=10); c.alignment=WRAP; c.border=B
            if fillcol is not None and j==fillcol+1 and isinstance(v,str): c.fill=fill_for(v)
        w.row_dimensions[r].height=max(30, 13*max((len(str(x))//max(10,int(widths[j]*1.1))+1) for j,x in enumerate(row))+6)
        r+=1
    w.page_setup.orientation="landscape"; w.page_setup.fitToWidth=1; w.page_setup.fitToHeight=0; w.sheet_properties.pageSetUpPr.fitToPage=True
    return w
# A
rowsA=[]
for a in A:
    verdict="Verbatim" if a["verbatim"] else "Oversight — revert to the translator's text (V4.14)"
    rowsA.append([a["key"],a["kind"],a["src"],a["doc"],a["now"],"Yes" if a["verbatim"] else "No",a["cause"] or "—",verdict,a["rec"] or "—"])
sheet("A Static text",f"A — Page text the translator supplied ({len(A)} rows written in V4.10): is it in the report word for word?",
 ["Every row the V4.10 ingest wrote from the translator's document, compared with the Welsh in the V4.13 report. 199 of 216 are verbatim. The 17 that differ are ALL the V4.11 reviewer substitutions (assessment §7.1) — no framework rule touched a static row. V4.14 reverts them so the page text is the translator's exactly; the reviewer's points remain as questions on handover sheet 1."],
 ["Key","Kind","Source row in the translator's document","Translator's Welsh (document)","Welsh in the V4.13 report","Verbatim?","Why it differs","Verdict","Action"],[14,18,22,50,50,9,50,30,44],rowsA,fillcol=7)
# B
rowsB=[[k,doc,now,why,v,act] for k,doc,now,why,v,act in FRAMES]
sheet("B Frames",f"B — Sentences with a moving part (sheet-43 frames) that the translator's document also covered ({len(FRAMES)} frames)",
 ["The translator translated the report page with its sample numbers in place (“Based on: 22 pupils”). The report builds those strings from FRAMES with slots ({n}) so the number can change. The V4.10 ingest wrote the translator's text into NEW frames it created, but left EXISTING frames on the workbook's earlier Welsh — that is the oversight. Each row says which mechanism produced the difference and whether it is an oversight (apply the translator's wording), a rule question (the translator has, in effect, disagreed with a framework rule) or a decision that depends on a term."],
 ["Frame","Translator's Welsh (document)","Welsh in the report (frame text)","Why it differs — mechanism","Verdict","Action"],[24,44,44,60,40,50],rowsB,fillcol=4)
# E
rowsE=[[en,where,why,v,act] for en,where,why,v,act in CLIENT]
sheet("C Chips and options",f"C — Filter chips, options and other client-built labels ({len(CLIENT)} groups covering 52 document rows)",
 ["These rows are built by the page from parts: a PREFIX written by Industryline in code (decision D50, never checked by a Welsh speaker) plus an ANSWER from the survey (sheet 23). Nothing here is a grammar rule; the prefixes are simply ours. The query sheet (SSS2026_Answer_labels_survey_vs_translator_query.xlsx) carries the per-row decision; this sheet records the mechanism and verdict for each group."],
 ["Translator's row(s)","Where it is built in the report","Why it differs — mechanism","Verdict","Action"],[52,44,66,40,52],rowsE,fillcol=3)
# D
rowsD=[[i,doc,gen,why,v,act] for i,doc,gen,why,v,act in GENERATED]
sheet("D Generated sentences",f"D — The translator's versions of {len(GENERATED)} engine-generated sentences, against the engine's",
 ["The translator's document also translated sample sentences that the engine writes (they were on the English page). These are not translation slots — the engine composes them from rules — so nothing was applied. But they are the most useful thing in the document: every difference is the translator's implicit ruling on a framework rule. Each row names the rule(s) and where the question now sits (handover sheet 4 or 5). None of these is an oversight."],
 ["#","Translator's Welsh (document)","Engine's Welsh (V4.13)","Which rule(s) produced the difference","Verdict","Where the question goes"],[4,52,52,70,34,46],rowsD,fillcol=4)
# Summary
W=[36,90]
for i,x in enumerate(W,1): ws.column_dimensions[get_column_letter(i)].width=x
ws["A1"]="Translator fidelity audit — where the 15 September 2026 document is, and is not, in the V4.13 report, and why"; ws["A1"].font=Font(name=F,bold=True,size=14,color=BLUE); ws.merge_cells("A1:B1")
nA=len(A); nAv=sum(1 for a in A if a["verdict"] if False) if False else sum(1 for a in A if a["verbatim"])
lines=[
("The rule","The translator's document takes precedence: its text goes into the page text and labels word for word. This audit checks every row of that document against the V4.13 report and, where the report differs, names the mechanism and gives a verdict: OVERSIGHT (apply the translator's wording — an exception, or no rule was involved), RULE QUESTION (a framework rule produced the difference; the translator must confirm or correct the rule), DECISION (depends on a label or term decision already on the query sheet or handover), OWNER (the English is locked), or ENGINE SENTENCE (not a translation slot)."),
("A — Page text (216 rows)",f"{nAv} of {nA} rows are in the report exactly as the translator wrote them. The {nA-nAv} that differ are all the V4.11 reviewer substitutions (18 keys): the reviewer's assessment found grammatical points and we applied the smallest change with a “pending translator confirmation” note — the rule at the time (rulebook item 11), but not what you have now asked for. No framework rule changed a static row. ACTION (done in V4.14): every substitution reverted, so the page text is verbatim; the reviewer's points stay as questions on handover sheet 1."),
("B — Frames (18)",f"{sum(1 for f in FRAMES if f[4]==V_OK)} already match; {sum(1 for f in FRAMES if f[4]==V_OVERSIGHT)} are OVERSIGHTS (the V4.10 ingest wrote the translator's text only into frames it created, not into existing ones) — applied in V4.14 where no slot or term is involved (chip_none, table_summary, stack_th_total, stack_caption_year, th_year_group, th_base, f14_unmet, ranking_note); {sum(1 for f in FRAMES if f[4]==V_RULE)} are RULE QUESTIONS (count-noun table, mutation after 22, figure vs word, gwedd/golwg); {sum(1 for f in FRAMES if f[4]==V_DECISION)} depend on a term or label decision."),
("C — Chips and options (52 rows)","The chip prefixes were written by Industryline in code (D50) and are simply ours — the translator's are the first native-speaker versions and should be taken. But a prefix and its answer interact (“…os: Pe bai…” doubles the conditional; “Yn cymryd rhan: Yn sefyll” doubles ‘yn’), so they are decided together, per row, on the query sheet. Two defects found on the way: sheet 23 maps the English ‘Not at all’ to one generic Welsh label, so the confidence questions show “Dim o gwbl” where the survey said “Ddim yn hyderus o gwbl”; and the derived yes/no answers echo the survey's first-person “Ydw” where the translator wrote third-person “Ydy” — a register question for the translator."),
("D — Generated sentences (19)","Not translation slots, so nothing was applied — correctly. But they are the translator's implicit rulings on the engine's rules: the whole-school phrase (ar draws / yn), the cleft for ‘the largest group said’ (PR-08 — the translator uses the form PR-08 avoids), figure + singular noun vs partitive (12 camp / 12 o gampau), ‘fe’ before the verb, ordinals for ‘next most common’ (ADJ-11), sport-name casing (D21), ‘tra bo’ contrasts, mutation after chwe(ch) and adverbial ‘rywle arall’, ‘with a disability’ vs ‘who reported a disability’. Each is routed to handover sheet 4 or 5; none is applied until the translator answers, because each changes thousands of sentences."),
("What this means for the framework","Three concrete refinements follow from the audit: (1) the ingest must treat EXISTING frames' fixed wording as translator-owned, not framework-owned — a frame's slots are the framework's, its words are the translator's; (2) chip prefixes move out of code into a workbook sheet so they are translatable like everything else; (3) sheet 23 answer labels must be keyed by question + code, not by English text, so ‘Not at all’ and ‘Very’ can differ by question as the survey does. The rule questions in B and D are exactly what handover sheets 4 and 5 are for; nothing in the framework's grammar tables changes until the translator rules."),
]
r=3
for h,t in lines:
    c=ws.cell(row=r,column=1,value=h); c.font=Font(name=F,bold=True,size=10,color=BLUE); c.alignment=WRAP; c.border=B
    c=ws.cell(row=r,column=2,value=t); c.font=Font(name=F,size=10); c.alignment=WRAP; c.border=B
    ws.row_dimensions[r].height=max(40, 13*(len(t)//95+1)+6); r+=1
ws.page_setup.orientation="landscape"; ws.page_setup.fitToWidth=1; ws.page_setup.fitToHeight=0; ws.sheet_properties.pageSetUpPr.fitToPage=True
wb.save("SSS2026_V4.14_Translator_fidelity_audit.xlsx"); print("saved")
