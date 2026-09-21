import json,re,openpyxl,sys
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.utils import get_column_letter
out=json.load(open("overlay_rows.json",encoding="utf-8"))
FW="/home/claude/work/sss2026-ilr-prototype/config/01_Framework_v2.4.xlsx"
wbf=openpyxl.load_workbook(FW,read_only=True)
smap={}
for r in wbf["30 Approved survey"].iter_rows(values_only=True):
    if not r or len(r)<4 or not r[2] or not r[3]: continue
    en=[x.strip() for x in str(r[2]).split("\n")]; cy=[x.strip() for x in str(r[3]).split("\n")]
    if len(en)!=len(cy): continue
    q=en[0]
    for e,c in zip(en,cy):
        e2=re.sub(r"[.\s]+$","",e).strip().lower()
        if e2 and c and e2 not in smap: smap[e2]=(re.sub(r"[.\s]+$","",e).strip(), c.strip(), q)
def norm(s): return re.sub(r"[’']","'",re.sub(r"\s+"," ",s or "")).strip()
def lookup(l):
    k=l.lower().strip()
    k2=re.sub(r"[\[\]()]","",k).replace("for example,","for example").strip()
    for cand in (k, k2, "if "+k, k.replace("per week","a week"), k.replace("3 or more","three or more")):
        if cand in smap: return smap[cand]
    # bracketed / "please specify" variants
    for sk,v in smap.items():
        sk2=re.sub(r"[\[\]()]","",sk).replace("for example,","for example").strip()
        if sk2==k2 or (k=="other" and sk.startswith("other, please specify")) or (k=="other" and sk.startswith("other [")):
            return v
    return None
rows=[]; seen=set()
for o in out:
    if (o["en"],o["tr"]) in seen or "Free School Meal" in o["en"]: continue   # the FSM row is an ingest artefact, not a label
    if o["where"].startswith("cohort et_") and ": " not in o["en"]: o["en"]="Ethnicity: "+o["en"]
    seen.add((o["en"],o["tr"]))
    is_cohort=o["where"].startswith("cohort")
    live=re.sub(r" \(English differs.*$","",o["live"])
    if is_cohort and ": " in o["en"]:
        pre_en, ans_en = o["en"].split(": ",1)
        pre_cy, ans_cy = (live.split(": ",1)+[""])[:2]
        tr_pre, tr_ans = (o["tr"].split(": ",1)+[""])[:2]
        pre_origin = "Written by Industryline in code when the filter chips were built (welsh_render.py COHORT_FRAME_CY, decision D50 “derived — listed for the linguist”). Not from the survey and not from the translator."
    else:
        pre_en=""; ans_en=o["en"]; pre_cy=""; ans_cy=live; tr_pre=""; tr_ans=o["tr"]; pre_origin="—"
    sv=lookup(ans_en)
    if ans_en in ("Yes","No"):
        sv=(("Yes","Oes","Do you have a disability or long-term condition that often makes things harder?") if ans_en=="Yes" else ("No","Nac oes","Do you have a disability or long-term condition that often makes things harder?")) if ("dy_yes" in o["where"] or "Disability" in o["en"]) else None
    if sv:
        s_en,s_cy,s_q=sv; ans_origin="The survey (Framework sheet 23, status ATTESTED-SURVEY)"
        if norm(s_cy)!=norm(ans_cy): ans_origin+=" — NOTE: today’s Welsh is not the survey option"
        g=f"“{s_en}” — an answer option to the question “{s_q}”"
    else:
        s_cy=None
        if "ed_combined" in o["where"] or "Ethnically" in o["en"]:
            ans_origin="Ruling PR-11: this group has no survey question, so it is named rather than answered"; g="— (built from the ethnicity question; there was no Yes/No question in the survey)"
        else:
            ans_origin="Report wording with no survey equivalent (our workbook, Framework sheet 23/28/43)"; g="— (not in the survey: report wording)"
    rows.append(dict(type=o["type"],pre_en=pre_en,pre_cy=pre_cy,pre_origin=pre_origin,tr_pre=tr_pre,ans_en=ans_en,s_en=g,s_cy=s_cy or "—",ans_cy=ans_cy,tr_ans=tr_ans,ans_origin=ans_origin,
        src=f"{o['doc_section']} — {o['doc_how']}"+(f"; the row reads “{o['doc_en']}” → “{o['doc_cy']}”" if o["doc_how"]=="a row of its own" else f"; the list begins “{o['doc_en'].splitlines()[0][:60]}…”"),
        quoted=o["quoted"]))
F="Arial"; BLUE="094B68"; thin=Side(style="thin",color="BFBFBF"); B=Border(left=thin,right=thin,top=thin,bottom=thin)
Y=PatternFill("solid",fgColor="FFF2CC"); WRAP=Alignment(wrap_text=True,vertical="top")
wb=openpyxl.Workbook(); ws=wb.active; ws.title="Survey vs translator"
hdr=["#","Type of label","PREFIX — English in the report","PREFIX — Welsh in the report today","PREFIX — where today’s Welsh came from","PREFIX — translator’s Welsh",
     "ANSWER — English in the report","ANSWER — English in the survey instrument (and the question it answers)","ANSWER — Welsh in the survey instrument (what pupils saw)","ANSWER — Welsh in the report today","ANSWER — where today’s Welsh came from","ANSWER — translator’s Welsh (document 15 Sep 2026)",
     "Where it came from in the translator’s document","Times the answer is quoted inside generated sentences (test school)","Decision — ANSWER wording (choose)","Decision — PREFIX wording (choose)","Comment"]
W=[5,26,26,30,34,30,28,40,30,30,34,32,44,12,24,24,30]
for i,w in enumerate(W,1): ws.column_dimensions[get_column_letter(i)].width=w
ws["A1"]=f"Answer labels — survey instrument, report today and translator’s document, side by side ({len(rows)} rows)"; ws["A1"].font=Font(name=F,bold=True,size=14,color=BLUE); ws.merge_cells("A1:Q1")
intro=["HOW TO READ THIS: many labels in the report are a filter-group chip made of two parts — a PREFIX that names the question (“Would do more sport if:”) and an ANSWER that is one of the survey’s answer options (“It felt more comfortable for me”). The survey only ever had the ANSWER; the PREFIX is report wording. The two parts are in separate columns so each can be compared with the right source. Rows that are a plain answer option or a legend item have no prefix.",
"WHERE TODAY’S WELSH CAME FROM: the ANSWER part was copied from the approved bilingual survey (Framework sheet 23, status ATTESTED-SURVEY) — column I equals column J on every row where the survey has the option. The PREFIX part was written by Industryline in code when the filter chips were built (welsh_render.py, decision D50 “derived — listed for the linguist”) and has never been checked by a Welsh speaker, so for prefixes the translator’s version is the first native-speaker wording we have and can simply be adopted.",
"THE QUESTION FOR THE TRANSLATOR: for the ANSWER part, should the report quote the survey’s wording (what pupils saw and chose — our recommendation, column I) or the document’s wording (column L)? For the PREFIX part, confirm the document’s wording or give a better one. Column N shows how many generated sentences quote the answer in the test school’s report; column M says exactly where in the translator’s document the wording came from (every one is a standalone label row or a line in a list of answer options — none is from inside a sentence)."]
r=2
for t in intro:
    c=ws.cell(row=r,column=1,value=t); c.font=Font(name=F,size=10); c.alignment=WRAP; c.fill=PatternFill("solid",fgColor="EAF1F5")
    ws.merge_cells(start_row=r,start_column=1,end_row=r,end_column=17); ws.row_dimensions[r].height=62; r+=1
r+=1
for i,h in enumerate(hdr,1):
    c=ws.cell(row=r,column=i,value=h); c.font=Font(name=F,bold=True,color="FFFFFF",size=10); c.fill=PatternFill("solid",fgColor=("4A6472" if i in (3,4,5,6,16) else BLUE)); c.alignment=Alignment(wrap_text=True,vertical="center"); c.border=B
ws.row_dimensions[r].height=58; ws.freeze_panes=ws.cell(row=r+1,column=3); r+=1; first=r
for i,o in enumerate(rows,1):
    vals=[i,o["type"],o["pre_en"] or "—",o["pre_cy"] or "—",o["pre_origin"],o["tr_pre"] or "—",o["ans_en"],o["s_en"],o["s_cy"],o["ans_cy"],o["ans_origin"],o["tr_ans"],o["src"],o["quoted"],"",("" if o["pre_en"] else "—"),""]
    for j,v in enumerate(vals,1):
        c=ws.cell(row=r,column=j,value=v); c.font=Font(name=F,size=10,bold=(j==9 and o["s_cy"]!="—")); c.alignment=WRAP; c.border=B
        if j in (15,17) or (j==16 and o["pre_en"]): c.fill=Y
        if j==11 and "NOTE" in str(v): c.font=Font(name=F,size=10,color="B3261E",bold=True)
    ws.row_dimensions[r].height=max(45, 13*max(len(o["src"])//48+1, len(o["s_en"])//42+1, len(o["pre_origin"])//36+1)+6)
    r+=1
last=r-1
dv=DataValidation(type="list",formula1='"Use the survey wording,Use the document wording,Other — see comment"',allow_blank=True); ws.add_data_validation(dv); dv.add(f"O{first}:O{last}")
dv2=DataValidation(type="list",formula1='"Use the document wording,Use my version in the comment,Keep today’s wording"',allow_blank=True); ws.add_data_validation(dv2); dv2.add(f"P{first}:P{last}")
n_s=sum(1 for o in rows if o["s_cy"]!="—"); n_mm=sum(1 for o in rows if "NOTE" in o["ans_origin"]); n_pre=sum(1 for o in rows if o["pre_en"])
ws.cell(row=r+1,column=2,value=f"Summary: {len(rows)} rows; {n_s} answers have a survey equivalent and on {n_s-n_mm} of them today’s Welsh is exactly the survey’s ({n_mm} differ — red in column K); {n_pre} rows carry a report-written prefix; {sum(1 for o in rows if o['quoted'])} answers are quoted inside generated sentences ({sum(o['quoted'] for o in rows):,} occurrences in the test school).").font=Font(name=F,italic=True,size=9)
ws.merge_cells(start_row=r+1,start_column=2,end_row=r+1,end_column=13)
ws.page_setup.orientation="landscape"; ws.page_setup.fitToWidth=1; ws.page_setup.fitToHeight=0; ws.sheet_properties.pageSetUpPr.fitToPage=True
wb.save("SSS2026_Answer_labels_survey_vs_translator_query.xlsx")
print(len(rows), n_s, n_mm, n_pre)
for o in rows:
    if "NOTE" in o["ans_origin"]: print("MISMATCH:", o["ans_en"], "| survey:", o["s_cy"], "| today:", o["ans_cy"])
    if o["s_cy"]=="—": print("NO SURVEY:", o["type"][:20], "|", o["pre_en"], "|", o["ans_en"][:50])
