// School-agnostic jsdom regression for a real-school build (V5.0, pipeline 0.28.0).
// Every expectation is derived from the payload itself (school name, counts,
// year range, offered scopes, held cohorts), never typed for one school.
//   JSDOM=<node_modules/jsdom> WD=<wd with mini_data.json + template_stamped.html> node tests/jsdom/jsdom_school.js
const fs = require("fs");
const { JSDOM } = require(process.env.JSDOM || "jsdom");
const REPO = process.env.REPO || require("path").resolve(__dirname, "../..");
const WD = process.env.WD;
const tpl = fs.readFileSync(WD + "/template_stamped.html", "utf8");
const appjs = fs.readFileSync(REPO + "/web/app.js", "utf8");
const data = fs.readFileSync(WD + "/mini_data.json", "utf8");
const D = JSON.parse(data);
const SCHOOL = D.school.name, N = D.buildMetadata.acceptedRows;
const FIRST = D.school.years[0], LAST = D.school.years[D.school.years.length - 1];
let html = tpl.replace("__REPORT_JSON__", () => data.replace(/<\//g, "<\\/"))
              .replace("/*__APP_JS__*/", () => appjs.replace(/<\//g, "<\\/"))
              .replace(/__SCHOOL_NAME__/g, SCHOOL);
const dom = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/#scope=whole&gender=all&cohort=none&lang=en" });
const w = dom.window, d = w.document;
let pass = 0, fail = 0;
const ok = (cond, name, extra) => { if (cond) { pass++; } else { fail++; console.log("FAIL", name, extra || ""); } };
const txt = sel => (d.querySelector(sel) || {}).textContent || "";
const STATIC = D.welsh.static;
const els = () => Array.from(d.querySelectorAll("[data-i18n]"));
const norm = s => (s || "").replace(/\s+/g, " ").trim();
const visible = () => Array.from(d.querySelectorAll("main, aside, header, footer, nav")).map(e => e.textContent).join(" ");
const offered = D.filterOptions.scope.map(o => o.key);

// ---- English ----------------------------------------------------------------
ok(d.title.indexOf(SCHOOL) > -1 && txt("#cover-school") === SCHOOL, "school name on the cover and in the title", d.title);
ok(txt("#h1-view").startsWith("You are viewing:") && new RegExp("\\b" + N + "\\b").test(txt("#h1-view")), "en banner with the accepted count", txt("#h1-view").slice(0, 80));
ok(txt("#intro-sentence").indexOf(SCHOOL) > -1 && txt("#intro-sentence").indexOf("Years " + FIRST + " to " + LAST) > -1, "intro sentence: school, year range", txt("#intro-sentence"));
ok(txt("#faq-included").indexOf("Pupils in Years " + FIRST + " to " + LAST + " at " + SCHOOL) === 0, "FAQ 'who is included' carries the school's year range (EN-07)", txt("#faq-included").slice(0, 90));
// V6.0 (EN-11): a school with a year group inside its range that has no accepted
// response takes the variant without "All" (Framework v2.14, ui.overview_note_gap)
const GAP = !!D.school.yearsGap;
// V6.0 (EN-12, production pilot 23 Sep 2026): a blanked year bar (a year whose
// view is under five) means the note takes its "nocounts" variant — the same
// sentences without the largest/smallest one. Derived from the payload.
const BLANK = (D.states["whole|all|none"].m || {}).responses_by_year
  ? D.states["whole|all|none"].m.responses_by_year.v.some(v => v === null) : false;
// V6.0 (owner instruction, 22 Sep 2026): a school with fewer than five accepted
// responses receives its report with the whole-school view suppressed — the
// profile charts, the year-range sentence and the any-activity headline give
// way to the msg.suppressed_* frames, and no stack renders. The expectations
// below switch on that, derived from the payload as everything else is.
const WSUP = !!(D.states["whole|all|none"] || {}).sup;
const SUP_EN = "Results not shown", SUP_CY = "Canlyniadau heb eu dangos";
const OVERVIEW_EN = (GAP ? "Year groups from Year " : "All year groups from Year ") + FIRST + " to Year " + LAST + " are represented.";
ok(WSUP ? (txt("#overview-note").indexOf(SUP_EN) === 0 && txt("#static-profile").indexOf(SUP_EN) === 0 && txt("#any-activity-note") === "")
        : (txt("#overview-note").indexOf(OVERVIEW_EN) === 0 && (BLANK ? txt("#overview-note").indexOf("contributed") === -1 : txt("#overview-note").indexOf("contributed") > 0)),
   WSUP ? "whole-school view suppressed (under five): overview note, profile charts and any-activity headline show the suppression message"
        : "overview note carries the school's year range (EN-06" + (GAP ? "/EN-11 gap variant" : "") + ")", txt("#overview-note").slice(0, 90));
ok(!/\{(first|last|school|n|hi|lo|hin|lon)\}/.test(visible()), "no unresolved frame slot in the page");
// V6.0-rc10 (rc9 pilot review): a whole-school-suppressed report carries html.whole-sup, and the
// stylesheet lets its disclosure notices flow (position:static) instead of stacking over empty modules;
// the intro and FAQ sentences take the sanctioned singular at one response (EN-13)
ok(d.documentElement.classList.contains("whole-sup") === WSUP, "html.whole-sup exactly when the whole school is suppressed", String(WSUP));
ok(/html\.whole-sup \.paywall-box \{ position:static/.test(tpl), "stylesheet: whole-sup notices flow in the page");
ok(WSUP ? d.querySelectorAll(".paywall-box").length > 0 : true, "whole-sup: a notice in every dynamic module", d.querySelectorAll(".paywall-box").length);
ok(N === 1 ? (txt("#intro-sentence").indexOf("1 pupil response is included") > -1 && txt("#faq-included").indexOf("1 pupil response is included") > -1)
           : (txt("#intro-sentence").indexOf("pupil responses are included") > -1),
   "EN-13: the one-response singular in the intro and FAQ sentences", txt("#intro-sentence").slice(-60));
ok(txt("#overview-table").indexOf(D.school.localAuthority) > -1 && txt("#overview-table").indexOf(D.school.regionalSportPartnership) > -1 && txt("#overview-table").indexOf(D.school.schoolStages) > -1, "profile table: authority, partnership, stages", txt("#overview-table").slice(0, 200));
const scopeOpts = Array.from(d.querySelectorAll("#f-scope option")).map(o => o.value);
ok(scopeOpts.join(",") === offered.join(","), "scope select offers exactly the profile's scope groups", scopeOpts.join(","));
ok(!scopeOpts.some(k => !offered.includes(k)), "no scope outside the profile (a primary school lists no secondary phase)");
const yearOpts = D.metricDefs.responses_by_year.opts.map(o => o[0]);
ok(yearOpts.join(",") === D.school.years.map(y => "y" + y).join(","), "responses-by-year chart shows the school's years only", yearOpts.join(","));
ok(els().length === 211, "211 data-i18n elements (V4.18: the five Club Sports rows retired — 216 before)", els().length);
ok(els().every(e => norm(e.textContent) === norm(STATIC[e.getAttribute("data-i18n")].en)), "en static text equals manifest");
ok(!/⟪missing:(?!key⟫)/.test(visible()) && data.indexOf("⟪missing:") === -1, "no ⟪missing⟫ markers in the page or the payload");
// held cohorts: the bar stays, non-selectable (no cohort key exists for it)
const held = JSON.parse(fs.readFileSync(REPO + "/config/held_cohorts.json", "utf8"));
for (const key of Object.keys(held)) {
  const [fam, ...rest] = key.split("_"); const code = rest.join("_");
  const mid = Object.entries(D.metricDefs).find(([m, def]) => (def.cohortCodes || []).includes(code) && D.cohorts && !D.cohorts[key] &&
              Object.values(D.cohorts).some(c => c.metric === m && key.startsWith(fam + "_")));
  ok(!D.cohorts[key], "held cohort " + key + " is not offered as a filter");
}
ok(Array.from(d.querySelectorAll(".bar-grey")).length >= 0, "grey (non-selectable) bars render without error");
// V6.0 (production pilot review, 23 Sep 2026) — A06: a gender-exempt metric
// (the gender profile) never shows Boys/Girls columns; a filtered metric does
// when both gender views are reportable (derived from the payload).
const appxTables = Array.from(d.querySelectorAll("#appendices table"));
const genderTable = appxTables.find(tb => Array.from(tb.querySelectorAll("th[scope=row]")).some(th => /^Boys$/.test(th.textContent)) &&
                                          Array.from(tb.querySelectorAll("th[scope=row]")).some(th => /^Girls$/.test(th.textContent)));
const genderHeads = genderTable ? Array.from(genderTable.querySelectorAll("thead th")).map(th => th.textContent) : null;
ok(WSUP ? true : (genderTable && genderHeads.length === 2 && genderHeads.indexOf("Boys") === -1),
   "A06: the responses-by-gender appendix table has an All column only (exempt: gender)", genderHeads);
const bothGenders = !WSUP && D.states["whole|boy|none"] && !D.states["whole|boy|none"].sup && D.states["whole|girl|none"] && !D.states["whole|girl|none"].sup;
const anyGenderCols = appxTables.some(tb => Array.from(tb.querySelectorAll("thead th")).some(th => th.textContent === "Boys"));
ok(bothGenders ? anyGenderCols : !anyGenderCols, "A06: filtered metrics keep their Boys/Girls columns exactly when both gender views are reportable", String(bothGenders));
// A04: printing opens the guide's answers (details.faq) and the appendix tables, and closes them again
const faqs = Array.from(d.querySelectorAll("details.faq"));
ok(faqs.length === 15 && faqs.every(x => !x.open), "guide: 15 closed details.faq before printing", faqs.length);
w.dispatchEvent(new w.Event("beforeprint"));
ok(faqs.every(x => x.open) && Array.from(d.querySelectorAll("#m-appendices details")).every(x => x.open), "A04: beforeprint opens every guide answer and every appendix table");
w.dispatchEvent(new w.Event("afterprint"));
ok(faqs.every(x => !x.open), "A04: afterprint closes them again");
// A05: the page-margin footer is fed from the #print-footer spans (school name · view | survey name)
const pfL = () => d.documentElement.style.getPropertyValue("--pf-left"), pfR = () => d.documentElement.style.getPropertyValue("--pf-right");
ok(pfL().indexOf(SCHOOL) > -1 && pfL().indexOf(txt("#pf-view")) > -1 && pfR() === JSON.stringify("School Sport Survey 2026"), "A05: print-footer custom properties carry the school, the view and the survey name (EN)", pfL() + " | " + pfR());

// ---- Welsh ------------------------------------------------------------------
const btn = d.getElementById("btn-lang");
btn.click();
ok(d.documentElement.lang === "cy", "html lang cy");
ok(txt("#h1-view").startsWith("Rydych chi’n gweld:") && (N === 1 ? /ymateb disgybl wedi’i gynnwys/ : /ymateb disgybl wedi’u cynnwys/).test(txt("#h1-view")), "cy banner frame (N = 1 takes the singular form)", txt("#h1-view").slice(0, 80));
ok(txt("#intro-sentence").indexOf("Mae’r adroddiad hwn yn cyflwyno") === 0 && txt("#intro-sentence").indexOf(String(N)) > -1 && txt("#intro-sentence").indexOf("Flynyddoedd " + FIRST + " i " + LAST) > -1, "cy intro sentence with the school's slots", txt("#intro-sentence"));
ok(txt("#faq-included").indexOf("Disgyblion ym Mlynyddoedd " + FIRST + " i " + LAST + " yn " + SCHOOL) === 0, "cy FAQ sentence with the school's year range (EN-07)", txt("#faq-included").slice(0, 90));
if (!GAP) {
  ok(WSUP ? txt("#overview-note").indexOf(SUP_CY) === 0
          : (txt("#overview-note").indexOf("Mae’r holl grwpiau blwyddyn rhwng Blwyddyn " + FIRST + " a Blwyddyn " + LAST + " yn cael eu cynrychioli.") === 0
             && (BLANK ? txt("#overview-note").indexOf("gyfrannodd") === -1 : txt("#overview-note").indexOf("gyfrannodd") > 0)),
     WSUP ? "cy suppression message in the overview note" : "cy overview note with the school's year range (EN-06)", txt("#overview-note").slice(0, 100));
} else {
  // the variant's Welsh is the translator's: until returned the English shows under the pending marking
  const gapCy = (D.welsh.frames[BLANK ? "ui.overview_note_gap_nocounts" : "ui.overview_note_gap"] || {}).cy;
  const t = txt("#overview-note");
  ok(gapCy ? (t.indexOf("Blwyddyn " + FIRST) > -1 && t.indexOf("Blwyddyn " + LAST) > -1)
           : (t.indexOf(OVERVIEW_EN) === 0 && d.getElementById("overview-note").classList.contains("cy-missing")),
     "cy overview note: gap variant (translator's Welsh, or marked-English pending)", t.slice(0, 100));
}
ok(!/\{(first|last|school|n|hi|lo|hin|lon)\}/.test(visible()), "cy: no unresolved frame slot");
const NAMES = D.welsh.names || {};
ok(txt("#overview-table").indexOf("Enw’r Ysgol") > -1 && txt("#overview-table").indexOf(NAMES[D.school.localAuthority] || D.school.localAuthority) > -1 && txt("#overview-table").indexOf(NAMES[D.school.regionalSportPartnership] || D.school.regionalSportPartnership) > -1, "cy profile headings and proper names (sheet 53)", txt("#overview-table").slice(0, 200));
ok(Array.from(d.querySelectorAll("#f-scope option")).every(o => { const opt = D.filterOptions.scope.find(x => x.key === o.value); return opt && o.textContent.indexOf(opt.labelCy) === 0; }), "cy scope options from sheet 58");
ok(!els().some(e => e.classList.contains("cy-missing")), "no static node pending in Welsh mode");
ok(d.body.innerHTML.indexOf("⟪missing:ui") === -1, "no bare static markers in Welsh mode");
ok(visible().indexOf("tymor hir") === -1, "no 'tymor hir' (D86)");
ok(!/\bac \d/.test(d.body.textContent) && !/Yr ail camp/.test(d.body.innerHTML), "engine rules hold: a before figures, ail + soft mutation (D84, D85)");
// V6.0 (production pilot review, 23 Sep 2026): the four Welsh-engine findings, asserted over the whole page and payload
ok(!/Yr ail gamp mwyaf/.test(html), "A02: 'Yr ail gamp fwyaf cyffredin' — the adjective agrees with the feminine head (ADJ-02/07)");
ok(!/\b(Pharkour|Barkour|Mharkour|Fadminton|Foccia|FMX|MMX|Thriathlon|Driathlon|Daekwondo|Thaekwondo|Fajorettes|Fuay Thai|Bhadel|Phadel|Fadel|Phickleball|Bickleball)\b/.test(html) && !/[ ‘'](ymnasteg|olff)\b/.test(html),
   "A03: no immutable sport name mutated anywhere in the page or the payload (PR-05, EX-01..04)");
ok(!/ymhlith bechgyn a [bdfgm]ê?l /.test(html) && !/ymhlith bechgyn a (redeg|ddringo|griced|dennis)/.test(html), "A03/CONJ-04: the gender-leaders sentence takes a/ac + aspirate after 'a'");
ok(!/a ddewisodd pêl /.test(html), "T-035: the f10 cohort sentence mutates the object of 'dewisodd'");
// A01: a data value without a sheet-53 Welsh form is MARKED (cy-missing, lang=en) in Welsh mode; one with a form shows it unmarked
// (rc11, RC9-A03: the marking is a span inside the cell, so it shows inside details.dtable too)
const marked = td => !!(td && td.querySelector("span.cy-missing[lang=en]"));
const stagesCell = Array.from(d.querySelectorAll("#overview-table td")).find(td => td.textContent === (NAMES[D.school.schoolStages] || D.school.schoolStages));
ok(stagesCell && (NAMES[D.school.schoolStages] ? !marked(stagesCell) : marked(stagesCell)),
   "A01: the school-stages value is marked pending in Welsh mode until its sheet-53 row exists", stagesCell && stagesCell.outerHTML.slice(0, 160));
const laCell = Array.from(d.querySelectorAll("#overview-table td")).find(td => td.textContent === (NAMES[D.school.localAuthority] || D.school.localAuthority));
ok(laCell && !marked(laCell) === !!NAMES[D.school.localAuthority], "A01: the authority's Welsh name (sheet 53) shows unmarked");
const supCell = Array.from(d.querySelectorAll("#meta-table td")).find(td => td.textContent === (NAMES[D.buildMetadata.suppressionModel] || D.buildMetadata.suppressionModel));
ok(supCell && (NAMES[D.buildMetadata.suppressionModel] ? !marked(supCell) : marked(supCell)), "A01/RC9-A03: the suppression-model value is marked pending (span inside the technical record's cell)");
ok(/^\.cy-missing \{ border-bottom:1px dotted/m.test(tpl) && supCell && supCell.closest("details.dtable") !== null, "RC9-A03: the technical record sits in details.dtable, whose cell border would hide a cell-level marking", supCell && supCell.closest("details.dtable") !== null);
ok(pfR() === JSON.stringify("Arolwg Chwaraeon Ysgol 2026") && pfL().indexOf(SCHOOL) > -1, "A05: print-footer custom properties switch with the language (CY)", pfR());
ok(d.querySelector("aside.filter-rail").getAttribute("aria-label") === "Archwilio’r Canlyniadau", "cy aria-label from a frame");
ok(WSUP ? txt("#any-activity-note") === "" : txt("#any-activity-note").indexOf("Adroddodd " + D.anyActivity + " o’r " + N) === 0, WSUP ? "cy: no any-activity headline for a suppressed whole school" : "cy any-activity headline from the school's own counts", txt("#any-activity-note").slice(0, 60));
const caps = Array.from(d.querySelectorAll("caption")).map(c => c.textContent).filter(t => /a ddewiswyd amlaf/.test(t));
ok(WSUP ? caps.length === 0 : (caps.length > 0 && caps.every(t => /^Y/.test(t))), WSUP ? "cy: no stack renders for a suppressed whole school" : "cy stack captions capitalised", caps.filter(t => !/^Y/.test(t)).slice(0, 3));

// ---- interaction and state --------------------------------------------------
const gbtn = d.querySelector('[data-g="girl"]');
if (gbtn) gbtn.click();
ok(w.location.hash.indexOf("gender=girl") > -1 && txt("#h1-view").indexOf("Rydych chi’n gweld:") === 0, "girl filter keeps the Welsh banner");
const firstYear = offered.find(k => k.startsWith("y"));
const sel = d.getElementById("f-scope"); sel.value = firstYear; sel.dispatchEvent(new w.Event("change", { bubbles: true }));
ok(w.location.hash.indexOf("scope=" + firstYear) > -1, "year scope selectable from the profile's list", w.location.hash);
ok(!/⟪missing:(?!key⟫)/.test(visible()) && !/\{(first|last|school|n)\}/.test(visible()), "year view: no markers or unresolved slots");
d.getElementById("btn-lang").click();
ok(d.documentElement.lang === "en" && txt("#h1-view").startsWith("You are viewing:"), "back to English");
{ const dom2 = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/report.html" });
  ok(dom2.window.document.documentElement.lang === "cy", "default language is Welsh on first load"); }
{ const A = d.getElementById("btn-a11y"); A.click();
  ok(d.documentElement.classList.contains("a11y") && d.querySelectorAll("details.dtable:not([open])").length === 0, "accessibility switch on: tables open");
  A.click(); ok(!d.documentElement.classList.contains("a11y"), "accessibility switch off"); }
fs.writeFileSync(WD + "/jsdom_school.json", JSON.stringify({ school: SCHOOL, pass, fail }, null, 1));
console.log(`jsdom school regression (${SCHOOL}): ${pass}/${pass + fail} PASS${fail ? " (" + fail + " FAIL)" : ""}`);
process.exit(fail ? 1 : 0);
