const fs = require("fs");
const { JSDOM } = require(process.env.JSDOM || "jsdom");
const REPO = process.env.REPO || require("path").resolve(__dirname, "../..");
const WD = process.env.WD || "/tmp/v49wd";
const tpl = fs.readFileSync(WD + "/template_stamped.html", "utf8");
const appjs = fs.readFileSync(REPO + "/web/app.js", "utf8");
const data = fs.readFileSync(WD + "/mini_data.json", "utf8");
// IMPORTANT: replacer FUNCTIONS — a plain string replacement mangles "$$" in app.js
let html = tpl.replace("__REPORT_JSON__", () => data.replace(/<\//g, "<\\/"))
              .replace("/*__APP_JS__*/", () => appjs.replace(/<\//g, "<\\/"))
              .replace(/__SCHOOL_NAME__/g, "Ysgol Penrhyn Dewi");
const dom = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/#scope=whole&gender=all&cohort=none&lang=en" });
const w = dom.window, d = w.document;
let pass = 0, fail = 0;
const ok = (cond, name, extra) => { if (cond) { pass++; } else { fail++; console.log("FAIL", name, extra || ""); } };
const txt = sel => (d.querySelector(sel) || {}).textContent || "";
const btn0 = () => d.getElementById("btn-lang");
const STATIC = JSON.parse(data).welsh.static;

// EN state
ok(txt("#h1-view").startsWith("You are viewing:"), "en banner", txt("#h1-view").slice(0,60));
ok(/pupil responses included/.test(txt("#h1-view")), "en banner count");
ok(txt("#rail-toggle").indexOf("Explore results") === 0, "en rail toggle", txt("#rail-toggle"));
// V4.10 slider: both labels visible, switch state follows the language
ok(btn0().getAttribute("role") === "switch" && btn0().getAttribute("aria-checked") === "false", "slider role/state en");
ok(txt("#btn-lang .ls-en") === "English" && txt("#btn-lang .ls-cy") === "Cymraeg", "slider labels from the catalogue", txt("#btn-lang"));
ok(d.querySelector("#btn-lang .ls-en").classList.contains("on") && !d.querySelector("#btn-lang .ls-cy").classList.contains("on"), "slider highlights English");
ok(d.body.innerHTML.indexOf("View data table") > -1, "en table summary");
ok(d.body.innerHTML.indexOf("multiple answers permitted") > -1, "en multi seg");
ok(d.body.innerHTML.indexOf("3 or more times a week") > -1, "en legend");
// V4.9 D79: every static key rendered, English from the manifest
const els = () => Array.from(d.querySelectorAll("[data-i18n]"));
const norm = s => (s || "").replace(/\s+/g, " ").trim();
ok(els().length === 211, "211 data-i18n elements (V4.18: the Club Sports rows retired; V4.11: 12 slot-bearing fragments became sheet-43 frames)", els().length);
ok(Object.keys(STATIC).every(k => els().some(e => e.getAttribute("data-i18n") === k)), "every static key has an element");
ok(els().every(e => norm(e.textContent) === norm(STATIC[e.getAttribute("data-i18n")].en)), "en static text equals manifest");
ok(els().every(e => e.getAttribute("data-i18n-source") === "static:" + e.getAttribute("data-i18n")), "static provenance stamped");
// V4.9 D80: keyed attributes render their manifest string, no legacy attributes
ok(!d.querySelector("[data-ct],[data-nh],[data-also-h],[data-sh]"), "no legacy text-bearing attributes");
ok(Array.from(d.querySelectorAll("[data-ct-key]")).every(h => h.textContent.indexOf(STATIC[h.getAttribute("data-ct-key")].en) > -1), "data-ct-key hosts show the manifest heading");
ok(Array.from(d.querySelectorAll("[data-nh-key]")).every(h => h.textContent.indexOf(STATIC[h.getAttribute("data-nh-key")].en) > -1), "data-nh-key modules show the manifest heading");
ok(d.querySelector('[data-stack="overall"]').textContent.indexOf(STATIC.ui230.en) > -1, "data-sh-key note rendered");
ok(d.querySelector('[data-chart="pe_feel_healthy"] .chart-slot .chart-base'), "chart rendered into the slot beneath the static heading");

// toggle to Welsh
const btn = d.getElementById("btn-lang");
ok(!!btn, "lang button");
btn.click();
ok(d.documentElement.lang === "cy", "html lang cy");
ok(txt("#h1-view").startsWith("Rydych chi’n gweld:"), "cy banner frame (v2.3 prefix)", txt("#h1-view").slice(0,80));
ok(/ymateb disgybl wedi’u cynnwys/.test(txt("#h1-view")), "cy banner participle", txt("#h1-view"));
ok(txt("#rail-toggle").indexOf("Archwilio’r canlyniadau") === 0, "cy rail toggle", txt("#rail-toggle"));
ok(d.body.innerHTML.indexOf("Gweld Tabl Data") > -1, "cy table summary (translator's wording, V4.14)");
ok(d.body.innerHTML.indexOf("caniateir mwy nag un ateb") > -1, "cy multi seg");
ok(d.body.innerHTML.indexOf("Tair gwaith neu fwy yr wythnos") > -1, "cy legend 3+");
ok(d.body.innerHTML.indexOf("Dydw i ddim yn gwybod") > -1, "cy legend dk");
ok(d.body.innerHTML.indexOf("Cliciwch ar far i hidlo") > -1, "cy click note");
ok(d.body.innerHTML.indexOf("Dim un – dewiswch werth siart") > -1, "cy chip none (translator’s wording, V4.14)");
ok(btn.getAttribute("aria-checked") === "true" && d.querySelector("#btn-lang .ls-cy").classList.contains("on"), "slider state cy");
// V4.15: every catalogue key the page consumes now has a value — no marker anywhere
const visible = () => Array.from(d.querySelectorAll("main, aside, header, footer, nav")).map(e => e.textContent).join(" ");
ok(!/⟪missing:(?!key⟫)/.test(visible()) && data.indexOf("⟪missing:") === -1, "no ⟪missing⟫ markers in the page or the payload (V4.15; the guide's own sentence about the marker excepted)");
ok(d.body.innerHTML.indexOf("siart bar; ceir y ffigurau yn y tabl data isod") > -1, "cy chart aria");
// V4.10: static nodes with a translator value show it (block rows via sanitised markup),
// rows still pending show the English under the review marker with pending provenance
const STV = STATIC;
ok(els().every(e => { const k = e.getAttribute("data-i18n"), r = STV[k]; if (!r) return false;
  if (r.cy) return norm(e.textContent) === norm(r.cy.replace(/<[^>]+>/g, " ")) && !e.classList.contains("cy-missing") && e.getAttribute("data-i18n-source") === "static:" + k;
  return norm(e.textContent) === norm(r.en) && e.classList.contains("cy-missing") && e.getAttribute("data-i18n-source") === "handoff:pending:" + k; }),
  "cy static nodes: value when returned, English under the review marker when pending");
ok(Object.values(STV).filter(r => r.inline).length === 13 && els().filter(e => STV[e.getAttribute("data-i18n")].inline && STV[e.getAttribute("data-i18n")].cy).every(e => e.querySelector("strong,em") || !/<(strong|em)/.test(STV[e.getAttribute("data-i18n")].cy)), "block rows render the translator's emphasis as markup");
ok(!els().some(e => /<\/?(script|a|span|div|img)/i.test(e.innerHTML)), "no disallowed markup reaches a static node");
ok(Object.values(STV).filter(r => r.cy).length === 187 && Object.keys(STV).length === 187, "187 of 187 static rows carry a translator value (V4.18: five Club Sports rows retired; V4.15: all translated)", Object.values(STV).filter(r => r.cy).length);
ok(!els().some(e => e.classList.contains("cy-missing")), "no static node is pending in Welsh mode (V4.15)");
ok(d.body.innerHTML.indexOf("⟪missing:ui") === -1, "no bare static markers in Welsh mode");
ok(d.querySelector('[data-chart="pe_feel_healthy"] h4').textContent === STATIC.ui217.cy && !d.querySelector('[data-chart="pe_feel_healthy"] h4').classList.contains("cy-missing"), "cy keyed chart heading from the translator value", d.querySelector('[data-chart="pe_feel_healthy"] h4').textContent);
// V4.11: profile headings, navigation and slot sentences through sheet-43 frames
ok(txt("#overview-table").indexOf("Enw’r Ysgol") > -1 && txt("#overview-table").indexOf("Sir Benfro") > -1, "cy profile headings and LA name (sheet 53)", txt("#overview-table").slice(0,120));
ok(Array.from(d.querySelectorAll("nav.pagenav a")).some(a => a.textContent === "← Yn ôl") && Array.from(d.querySelectorAll("nav.pagenav a")).some(a => a.textContent === "Cynnwys"), "cy navigation labels from frames");
ok(txt("#intro-sentence").indexOf("Mae’r adroddiad hwn yn cyflwyno") === 0 && txt("#intro-sentence").indexOf("366") > -1, "cy intro sentence frame with slots", txt("#intro-sentence").slice(0,80));
ok(txt("#faq-included").indexOf("Ysgol Penrhyn Dewi") > -1 && txt("#faq-missing").indexOf("80%") > -1, "cy FAQ slot sentences");
ok(d.querySelector('[data-frame="ui.chart_sports_total_pe"]').textContent.indexOf("93") > -1 && !d.querySelector('[data-frame="ui.chart_sports_total_pe"]').classList.contains("cy-missing"), "cy PE chart note frame");
ok(!d.querySelector('[data-frame="ui.chart_sports_total_club"]').classList.contains("cy-missing") && d.querySelector('[data-frame="ui.chart_sports_total_club"]').textContent.indexOf("Mae’r siart bar hwn") === 0, "club chart note frame translated (V4.15)", d.querySelector('[data-frame="ui.chart_sports_total_club"]').textContent.slice(0,60));
ok(els().filter(e => e.classList.contains("cy-missing")).every(e => e.getAttribute("lang") === "en"), "every pending static node carries lang=en");
ok(d.querySelector("aside.filter-rail").getAttribute("aria-label") === "Archwilio’r Canlyniadau", "cy aria-label from a frame");
ok(txt("#any-activity-note").indexOf("Adroddodd 363 o’r 366") === 0, "cy any-activity headline frame", txt("#any-activity-note").slice(0,60));
ok(txt("#review-note-cy").indexOf("mae 187 o 187") > -1 && !d.getElementById("review-note-cy").classList.contains("cy-missing"), "review note generated from live counts, in Welsh (V4.15)", txt("#review-note-cy").slice(0,80));
ok(txt("#h1-view").indexOf("Rydych chi’n gweld:") === 0, "cy banner prefix from Framework v2.3", txt("#h1-view").slice(0,40));
ok(/rhywedd\./.test(d.body.innerHTML) && !/a rhyw\./.test(d.body.innerHTML), "stack caption uses rhywedd (v2.3)");
// V4.15: the translator confirmed the reviewer's suggestions on the handover (sheet 1) — applied as the exact substitutions
ok(/Yn ei dro/.test(d.body.innerHTML) && /Rhestrau cyflawn/.test(d.body.innerHTML) && /Defnyddiwch banel/.test(d.body.innerHTML) && !/Yn eich tro|Rhestri cyflawn|Defnyddio panel/.test(d.body.innerHTML), "translator-confirmed suggestions applied (V4.15)");
// V4.15: the translator's decisions on labels, chips and the profile table
ok(/Yn Mwynhau Addysg Gorfforol: Llawer/.test(d.body.innerHTML) && /Byddai’n gwneud mwy o chwaraeon os:/.test(d.body.innerHTML), "chip prefixes from Framework sheet 58 (translator's document)");
ok(Array.from(d.querySelectorAll("#f-gender option, [data-g]")).some(e => /Pob Ymatebwr/.test(e.textContent)) && /Yr ysgol gyfan · Pob disgybl/.test(txt("#h1-view")), "filter option ‘Pob Ymatebwr’, banner ‘Pob disgybl’ (2b rows 1–2)", txt("#h1-view").slice(0,80));
ok(visible().indexOf("Ddim yn hyderus o gwbl") > -1 && visible().indexOf("Gwyn Cymreig, Saesneg, Albanaidd, Gwyddel Gwyn o Ogledd Iwerddon, neu Wyn Brydeinig") > -1 && visible().indexOf("Du, Du Cymreig, Du Prydeinig, Caribïaidd, neu Affricanaidd") > -1 && visible().indexOf("White Welsh, English") === -1, "confidence ‘Ddim yn hyderus o gwbl’ and the ethnicity profile table in Welsh (V4.15)");
ok(visible().indexOf("tymor hir") === -1 && /hirdymor/.test(visible()), "one term: cyflwr hirdymor (AW-4)");
ok(!/\bac \d/.test(d.body.textContent) && /Yr ail gamp/.test(d.body.innerHTML) && !/Yr ail camp/.test(d.body.innerHTML), "engine rules: a before figures, ail + soft mutation (D84, D85)");
// V4.9 D75: captions capitalised at realisation from a LEXICAL table
const caps = Array.from(d.querySelectorAll("caption")).map(c => c.textContent).filter(t => /a ddewiswyd amlaf/.test(t));
ok(caps.length > 0 && caps.every(t => /^Y/.test(t)), "cy stack captions capitalised", caps.filter(t => !/^Y/.test(t)).slice(0,3));
ok(w.countNP(2, "camp, definite") === "y ddwy gamp" && w.countNP(2, "camp, definite, initial") === "Y ddwy gamp", "countNP role-only casing");
ok(w.eval("DATA").welsh.countNP["camp|definite"][0] === "yr un gamp", "table lexical at one");

// gender filter announce path (cy)
const gbtn = d.querySelector('[data-g="girl"]');
if (gbtn) gbtn.click();
ok(w.location.hash.indexOf("gender=girl") > -1, "hash gender");
ok(txt("#h1-view").indexOf("Rydych chi’n gweld:") === 0, "cy banner after filter");

// V4.11 (assessment §8.2): section navigation keeps language and filters in the hash
const contentsLink = Array.from(d.querySelectorAll("nav.pagenav a")).find(a => a.getAttribute("href") === "#m-contents");
contentsLink.click();
ok(/lang=cy/.test(w.location.hash) && /gender=girl/.test(w.location.hash) && /s=m-contents/.test(w.location.hash), "hash keeps state after Contents", w.location.hash);
ok(d.documentElement.lang === "cy", "still Welsh after section navigation");
// selected tick is a catalogue element, not CSS content
ok(!/content:" ✓ Selected"/.test(d.head.innerHTML + d.body.innerHTML), "no CSS-generated English");
// V4.7: stack rows resolve through the catalogue; caption counts
ok(/camp a ddewiswyd amlaf/.test(d.body.innerHTML) || /gamp a ddewiswyd amlaf/.test(d.body.innerHTML), "cy stack caption count-NP");
ok(d.body.innerHTML.indexOf("Cyfanswm y Disgyblion") > -1, "cy stack th total (translator's wording, V4.14)");
ok(d.body.innerHTML.indexOf("Grŵp Blwyddyn") > -1, "cy th year group (translator’s casing, V4.14)");
ok(d.body.innerHTML.indexOf("Bechgyn") > -1, "cy sex suffix");
ok(d.body.innerHTML.indexOf("data-i18n-source") > -1, "provenance stamped");
ok(d.body.innerHTML.indexOf("Canlyniadau llawn y campau presennol") > -1, "cy appendix group");
// V4.8: joiner spacing, caption casing, no-report marker, EN singular
ok(/Y[r]? [\wŵŷâêîôû’ ]*gamp a ddewiswyd amlaf|Y[r]? [\wŵŷ’ ]*camp a ddewiswyd amlaf/.test(d.body.innerHTML), "cy caption capitalised");
ok(d.body.innerHTML.indexOf(">n/r<") === -1, "no n/r markers");
ok(d.body.innerHTML.indexOf("Gwersi Addysg Gorfforol") > -1, "cy g4 heading");
ok(d.body.textContent.indexOf(" · ") > -1, "joined with spaced dot");
ok(!/\b1 pupils\b/.test(d.body.textContent), "no 1 pupils");

// V4.9 fixture toggle (browser gate v3 --fixture auto, in miniature): inject unique values at run time
for (const k of Object.keys(w.eval("DATA").welsh.static)) { w.eval("DATA").welsh.static[k].cy = "⟦CY:" + k + "⟧"; w.eval("DATA").welsh.handoff[k] = "⟦CY:" + k + "⟧"; }
w.applyLanguageState(); w.update();
ok(els().every(e => e.textContent === "⟦CY:" + e.getAttribute("data-i18n") + "⟧"), "fixture values rendered from the manifest at call time");
ok(Array.from(d.querySelectorAll("[data-ct-key]")).every(h => h.textContent.indexOf("⟦CY:" + h.getAttribute("data-ct-key") + "⟧") > -1), "fixture in keyed chart headings");

// back to EN — English restored FROM THE MANIFEST
d.getElementById("btn-lang").click();
ok(d.documentElement.lang === "en", "back to en");
ok(txt("#h1-view").startsWith("You are viewing:"), "en banner restored");
ok(els().every(e => norm(e.textContent) === norm(STATIC[e.getAttribute("data-i18n")].en)), "en static restored from the manifest");
// V4.12: a fresh load with no hash opens in Welsh; lang=en in a saved link selects English
{ const dom2 = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/report.html" });
  const d2 = dom2.window.document;
  ok(d2.documentElement.lang === "cy" && d2.getElementById("btn-lang").getAttribute("aria-checked") === "true" && /lang=cy/.test(dom2.window.location.hash), "default language is Welsh on first load", dom2.window.location.hash);
  ok((d2.getElementById("h1-view").textContent || "").indexOf("Rydych chi’n gweld:") === 0, "Welsh banner on first load");
  const dom3 = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/report.html#scope=whole&gender=all&cohort=none&lang=en" });
  ok(dom3.window.document.documentElement.lang === "en", "lang=en link still opens English"); }
// V4.13: the accessibility switch — off by default, on in both languages, nothing else changes
{ const A = d.getElementById("btn-a11y");
  ok(A && A.getAttribute("role") === "switch" && A.getAttribute("aria-checked") === "false", "a11y switch present, off by default");
  ok(!d.documentElement.classList.contains("a11y") && !/a11y=/.test(w.location.hash), "default hash carries no a11y flag", w.location.hash);
  ok(txt("#btn-a11y .a11y-lbl") === "Accessibility features", "a11y switch label from the ui.a11y_switch frame", txt("#btn-a11y"));
  ok(!d.querySelector("#btn-a11y .a11y-lbl").classList.contains("cy-missing"), "English mode: label not marked");
  // V4.17: the switch is described (aria-describedby → #a11y-desc, frame ui.a11y_switch_desc) and carries the symbol
  { const desc = d.getElementById("a11y-desc");
    ok(desc && A.getAttribute("aria-describedby") === "a11y-desc" && desc.getAttribute("data-frame") === "ui.a11y_switch_desc", "V4.17: switch described by #a11y-desc");
    ok(desc && /larger text/.test(desc.textContent) && desc.textContent === (JSON.parse(data).welsh.frames["ui.a11y_switch_desc"] || {}).en, "V4.17: description is the frame's English", desc && desc.textContent.slice(0, 40));
    ok(A.querySelector("svg.a11y-icon") && A.querySelector("svg.a11y-icon").getAttribute("aria-hidden") === "true", "V4.17: accessibility symbol present and hidden from AT");
    ok(A.closest(".a11y-ctl") !== null, "V4.17: switch sits in its own bordered panel"); }
  const dtBefore = d.querySelectorAll("details.dtable[open]").length;
  const mainBefore = d.querySelector("main.report").innerHTML;
  A.click();
  ok(d.documentElement.classList.contains("a11y") && A.getAttribute("aria-checked") === "true" && /a11y=1/.test(w.location.hash), "switch on: html.a11y + hash a11y=1", w.location.hash);
  ok(d.querySelectorAll("details.dtable:not([open])").length === 0 && d.querySelectorAll("details.dtable table:not([tabindex])").length === 0, "on: every data table open and focusable");
  ok(Array.from(d.querySelectorAll("img[data-frame-attr]")).every(i => i.nextElementSibling && i.nextElementSibling.classList.contains("a11y-cap") && i.nextElementSibling.textContent === i.getAttribute("alt")), "on: character images carry a caption equal to their alt frame");
  const gl = d.querySelectorAll("#a11y-glossary-list a");
  ok(gl.length === 9 && Array.from(gl).every(a => d.getElementById(a.getAttribute("href").slice(1)).tagName === "DETAILS"), "on: glossary lists 9 links to the guide's own FAQ entries", gl.length);
  ok(gl[0].textContent === d.querySelector("#faqd-base summary").textContent, "glossary term text is the FAQ question itself");
  gl[0].click();
  ok(d.getElementById("faqd-base").open && /s=faqd-base/.test(w.location.hash), "a glossary link opens its FAQ answer and records the section");
  ok(d.querySelector("main.report .reported p, main.report h2") && d.body.textContent.indexOf("Accessibility features") > -1, "content still present");
  // language change with the switch on keeps it on and follows the language
  btn.click();
  ok(d.documentElement.lang === "cy" && d.documentElement.classList.contains("a11y") && /a11y=1/.test(w.location.hash), "switch stays on across a language change");
  ok(txt("#btn-a11y .a11y-lbl") === "Nodweddion hygyrchedd" && !d.querySelector("#btn-a11y .a11y-lbl").classList.contains("cy-missing"), "Welsh mode: switch label translated (V4.15)", txt("#btn-a11y .a11y-lbl"));
  ok(d.getElementById("a11y-desc").classList.contains("cy-missing") && d.getElementById("a11y-desc").getAttribute("lang") === "en" && /larger text/.test(txt("#a11y-desc")), "V4.17 Welsh mode: the description stays marked pending English until the translator returns it");
  ok(d.getElementById("h-a11y-glossary").classList.contains("cy-missing") && d.getElementById("h-a11y-glossary").getAttribute("lang") === "en" && txt("#h-a11y-glossary") === "Glossary of terms used in this report", "Welsh mode: the glossary heading the translator returned in English stays marked pending (flag 15)", txt("#h-a11y-glossary"));
  ok(d.querySelector("#a11y-glossary-list a").textContent === d.querySelector("#faqd-base summary").textContent, "glossary follows the language");
  btn.click();
  A.click();
  ok(!d.documentElement.classList.contains("a11y") && A.getAttribute("aria-checked") === "false" && !/a11y=/.test(w.location.hash), "switch off: class and hash flag removed");
  ok(d.querySelectorAll("details.dtable[open]").length === dtBefore && !d.querySelector("details.dtable table[tabindex]"), "off: data tables restored to their earlier state", d.querySelectorAll("details.dtable[open]").length);
  // screen-reader structure present in both modes, invisible
  ok(Array.from(d.querySelectorAll(".chart-card h4[id^='ch-']")).length > 10 && Array.from(d.querySelectorAll(".chart-card[role='group']")).every(c => d.getElementById(c.getAttribute("aria-labelledby"))), "chart cards are groups labelled by their own heading");
  ok(d.querySelectorAll(".stackseg[data-seg]").length > 0 && d.querySelectorAll(".stackseg:not([data-seg])").length === 0, "stack segments carry their position");
  // V4.18 (EN-09): the Club Sports section is gone; under a setting selection the
// weekly-frequency chart keeps the wider picture, stays selectable, and its
// narrative leads with the selected-group definition
{ const D = JSON.parse(data);
  ok(!d.querySelector('[data-module="d2"]') && !d.querySelector('[data-chart="club_freq_estimate"]'), "V4.18: no Club Sports module or club chart on the page");
  ok(!Object.keys(D.cohorts).some(k => k.startsWith("cb_")), "V4.18: no club-estimate (cb_*) selected groups in the payload");
  ok(Object.values(D.states).every(s => !(s.mod && s.mod.d2)), "V4.18: no d2 narrative in any embedded state");
  const stKey = Object.keys(D.states).find(k => k.startsWith("whole|all|st_"));
  ok(!!stKey, "V4.18: a setting-selection state is embedded", stKey);
  if (stKey) {
    const dom5 = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/report.html#scope=whole&gender=all&cohort=" + stKey.split("|")[2] + "&lang=en" });
    const d5 = dom5.window.document;
    const host = d5.querySelector('[data-chart="freq_estimate"]');
    const bars = host ? Array.from(host.querySelectorAll("button.vcolbtn, button.hrowbtn")) : [];
    const whole = D.states["whole|all|none"].m.freq_estimate.v, own = D.states[stKey].m.freq_estimate.v;
    const shown = bars.map(b => parseInt((b.querySelector(".vval, .hval") || b).textContent.replace(/[^0-9]/g, ""), 10));
    const sel = shown.filter(n => !isNaN(n));   // the selectable (button) bars — the grey categorical columns are spans
    ok(sel.length > 0 && JSON.stringify(sel) === JSON.stringify(whole.slice(-sel.length)) && JSON.stringify(whole.slice(-sel.length)) !== JSON.stringify(own.slice(-sel.length)), "V4.18: under a setting selection the frequency chart shows the whole-view bars (not the group's)", JSON.stringify(sel) + " vs whole " + JSON.stringify(whole) + " own " + JSON.stringify(own));
    ok(bars.length > 0 && bars.every(b => !b.disabled), "V4.18: the frequency chart's bars stay selectable under a setting selection");
    const base = host && host.querySelector(".chart-base");
    ok(base && /Showing: Whole school · All pupils/.test(base.textContent) && !/defines the selected group/.test(base.textContent), "V4.18: the base line says the wider view is showing (not that this chart defines the group)", base && base.textContent.slice(0, 100));
    const d0 = d5.querySelector('[data-module="d0"] .mod-narrative');
    ok(d0 && /^This selected group contains .* The chart above keeps the wider picture for .* for context, with the selected answer highlighted\.$/.test((d0.querySelector("p") || {}).textContent || ""), "V4.18: d0 narrative leads with the selected-group definition sentence", d0 && (d0.querySelector("p") || {}).textContent);
  }
}
// a saved link with a11y=1 opens with the switch on
  const dom4 = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/report.html#scope=whole&gender=girl&cohort=none&lang=cy&a11y=1" });
  ok(dom4.window.document.documentElement.classList.contains("a11y") && dom4.window.document.getElementById("btn-a11y").getAttribute("aria-checked") === "true", "a11y=1 link opens with the switch on"); }
console.log(`jsdom regression: ${pass}/${pass+fail} PASS${fail?" ("+fail+" FAIL)":""}`);
process.exit(fail ? 1 : 0);
