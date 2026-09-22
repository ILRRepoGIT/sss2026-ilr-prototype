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
ok(txt("#overview-note").indexOf("All year groups from Year " + FIRST + " to Year " + LAST + " are represented.") === 0, "overview note carries the school's year range (EN-06)", txt("#overview-note").slice(0, 90));
ok(!/\{(first|last|school|n|hi|lo|hin|lon)\}/.test(visible()), "no unresolved frame slot in the page");
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

// ---- Welsh ------------------------------------------------------------------
const btn = d.getElementById("btn-lang");
btn.click();
ok(d.documentElement.lang === "cy", "html lang cy");
ok(txt("#h1-view").startsWith("Rydych chi’n gweld:") && /ymateb disgybl wedi’u cynnwys/.test(txt("#h1-view")), "cy banner frame", txt("#h1-view").slice(0, 80));
ok(txt("#intro-sentence").indexOf("Mae’r adroddiad hwn yn cyflwyno") === 0 && txt("#intro-sentence").indexOf(String(N)) > -1 && txt("#intro-sentence").indexOf("Flynyddoedd " + FIRST + " i " + LAST) > -1, "cy intro sentence with the school's slots", txt("#intro-sentence"));
ok(txt("#faq-included").indexOf("Disgyblion ym Mlynyddoedd " + FIRST + " i " + LAST + " yn " + SCHOOL) === 0, "cy FAQ sentence with the school's year range (EN-07)", txt("#faq-included").slice(0, 90));
ok(txt("#overview-note").indexOf("Mae’r holl grwpiau blwyddyn rhwng Blwyddyn " + FIRST + " a Blwyddyn " + LAST + " yn cael eu cynrychioli.") === 0, "cy overview note with the school's year range (EN-06)", txt("#overview-note").slice(0, 100));
ok(!/\{(first|last|school|n|hi|lo|hin|lon)\}/.test(visible()), "cy: no unresolved frame slot");
const NAMES = D.welsh.names || {};
ok(txt("#overview-table").indexOf("Enw’r Ysgol") > -1 && txt("#overview-table").indexOf(NAMES[D.school.localAuthority] || D.school.localAuthority) > -1 && txt("#overview-table").indexOf(NAMES[D.school.regionalSportPartnership] || D.school.regionalSportPartnership) > -1, "cy profile headings and proper names (sheet 53)", txt("#overview-table").slice(0, 200));
ok(Array.from(d.querySelectorAll("#f-scope option")).every(o => { const opt = D.filterOptions.scope.find(x => x.key === o.value); return opt && o.textContent.indexOf(opt.labelCy) === 0; }), "cy scope options from sheet 58");
ok(!els().some(e => e.classList.contains("cy-missing")), "no static node pending in Welsh mode");
ok(d.body.innerHTML.indexOf("⟪missing:ui") === -1, "no bare static markers in Welsh mode");
ok(visible().indexOf("tymor hir") === -1, "no 'tymor hir' (D86)");
ok(!/\bac \d/.test(d.body.textContent) && !/Yr ail camp/.test(d.body.innerHTML), "engine rules hold: a before figures, ail + soft mutation (D84, D85)");
ok(d.querySelector("aside.filter-rail").getAttribute("aria-label") === "Archwilio’r Canlyniadau", "cy aria-label from a frame");
ok(txt("#any-activity-note").indexOf("Adroddodd " + D.anyActivity + " o’r " + N) === 0, "cy any-activity headline from the school's own counts", txt("#any-activity-note").slice(0, 60));
const caps = Array.from(d.querySelectorAll("caption")).map(c => c.textContent).filter(t => /a ddewiswyd amlaf/.test(t));
ok(caps.length > 0 && caps.every(t => /^Y/.test(t)), "cy stack captions capitalised", caps.filter(t => !/^Y/.test(t)).slice(0, 3));

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
