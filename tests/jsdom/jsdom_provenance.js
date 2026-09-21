/* Browser gate v3 (D72 / D79 / D80) executed under jsdom: the same collection and
   classification logic as 02_browser_gate_provenance.py v3 (COLLECT_JS + classify), the
   v2/v3 typography checks (join-space, n/r, "1 pupils", lower-case-initial on cased tags)
   and the v3 STATIC-FURNITURE TOGGLE with --fixture auto (unique values injected at run time
   into DATA.welsh.static / handoff; en → cy → en on every walked state, keyed-attribute
   consumers included), run over an 8-state reduced build because Chromium's system
   libraries are unavailable in the build environment. The stock playwright script is
   unmodified and ready for the operations run. */
const fs = require("fs");
const { JSDOM } = require(process.env.JSDOM || "jsdom");
const REPO = process.env.REPO || require("path").resolve(__dirname, "../..");
const WD = process.env.WD || "/tmp/v49wd";
const tpl = fs.readFileSync(WD + "/template_stamped.html", "utf8");
const appjs = fs.readFileSync(REPO + "/web/app.js", "utf8");
const data = fs.readFileSync(WD + "/mini_data.json", "utf8");
let html = tpl.replace("__REPORT_JSON__", () => data.replace(/<\//g, "<\\/"))
              .replace("/*__APP_JS__*/", () => appjs.replace(/<\//g, "<\\/"))
              .replace(/__SCHOOL_NAME__/g, "Ysgol Penrhyn Dewi");
const dom = new JSDOM(html, { runScripts: "dangerously", url: "https://x.test/#scope=whole&gender=all&cohort=none&lang=cy" });
const w = dom.window, d = w.document;
// regexes copied from the pack's browser gate v3
const ENW = /\b(the|this|these|for|in|of|to|by|a|an|and|or|not|no|selected|group|chart|table|data|view|pupils?|answers?|results?|school|year|boys|girls|based|show(?:ing|n)?|sport|sports|most|total|all|whole|club|clubs|answer)\b/gi;
const WELSHY = /[ŵŷ]|’n\b|’r\b|\b(yn|yr|ac|neu|mewn|disgybl|disgyblion|chwaraeon|ysgol|blwyddyn|bechgyn|merched|gyfan|ateb|pob|dim)\b/gi;
const ATTR_KEYS = ["data-ct-key", "data-nh-key", "data-also-h-key", "data-sh-key"];
const TYPO = [["join-space", /[\w\d][·—]|[·—](?=[\w])/], ["nr-literal", /(?<![\w\/])n\/r(?![\w\/])/], ["one-pupils", /\b1 pupils\b|\bun ddisgyblion\b/]];
const CASED = new Set(["caption", "h1", "h2", "h3", "h4", "h5", "summary", "th", "figcaption"]);
const classify = s => {
  const en = (s.match(ENW) || []).length, cy = (s.match(WELSHY) || []).length;
  if (en >= 2 && cy === 0) return "english";
  if (cy >= 1 && en <= 1) return "welsh";
  return (en && cy) ? "mixed" : "neutral";
};
const src = el => { let e = el; while (e && e.nodeType === 1) { if (e.hasAttribute && e.hasAttribute("data-i18n-source")) return e.getAttribute("data-i18n-source"); e = e.parentElement; } return null; };
const vis = el => { let e = el; while (e && e.nodeType === 1) { if (e.hidden || (e.getAttribute("style") || "").indexOf("display:none") > -1 || (e.getAttribute("style") || "").indexOf("display: none") > -1) return false; e = e.parentElement; } return true; };
const DATA = w.eval("DATA");
const states = Object.keys(DATA.states);
const seen = new Set(); const findings = []; const typos = [];
function goto(sk, lang) {
  const [scope, g, c] = sk.split("|");
  // the report's URL contract: gender= / cohort=
  w.location.hash = "scope=" + scope + "&gender=" + g + "&cohort=" + c + "&lang=" + lang;
  w.dispatchEvent(new w.Event("hashchange"));
  for (const det of d.querySelectorAll("details:not([open])")) det.open = true;
}
function collect(sk) {
  const walker = d.createTreeWalker(d.body, w.NodeFilter.SHOW_TEXT);
  let n;
  const push = (kind, el, text) => {
    const source = src(el); const key = kind + "|" + text + "|" + source;
    if (seen.has(key)) return; seen.add(key);
    const cls = classify(text);
    if (cls === "english" || cls === "mixed" || source === null)
      findings.push({ kind, tag: el.tagName.toLowerCase(), text: text.slice(0, 120), source, class: cls, state: sk });
    for (const [tid, rx] of TYPO) if (rx.test(text)) typos.push({ typo: tid, kind, tag: el.tagName.toLowerCase(), text: text.slice(0, 100), state: sk });
    if (kind === "text" && CASED.has(el.tagName.toLowerCase()) && /[A-Za-z]/.test(text[0]) && text[0] === text[0].toLowerCase())
      typos.push({ typo: "lower-case-initial", kind, tag: el.tagName.toLowerCase(), text: text.slice(0, 100), state: sk });
  };
  while ((n = walker.nextNode())) {
    const t = (n.nodeValue || "").replace(/\s+/g, " ").trim();
    if (t.length < 3) continue;
    const el = n.parentElement;
    if (!el || ["SCRIPT", "STYLE", "NOSCRIPT"].includes(el.tagName)) continue;
    if (!vis(el)) continue;
    push("text", el, t);
  }
  for (const el of d.querySelectorAll("[title],[aria-label]"))
    for (const a of ["title", "aria-label"]) { const v = el.getAttribute(a); if (v && v.trim().length >= 3) push(a, el, v.trim()); }
}
// ---- 1 + 2: provenance and typography over every state ----------------------------------
for (const sk of states) { goto(sk, "cy"); collect(sk); }
// ---- 3: the static-furniture toggle with --fixture auto -----------------------------------
const toggle = { static_keys: 0, attr_consumers: 0, en_ok: 0, cy_ok: 0, restored_ok: 0, failures: [] };
const stat = DATA.welsh && DATA.welsh.static;
if (!stat) toggle.failures.push({ key: "*", why: "DATA.welsh.static absent — nothing to toggle" });
else {
  const fix = {}; for (const k in stat) fix[k] = "⟦CY:" + k + "⟧";
  for (const k in fix) { DATA.welsh.static[k].cy = fix[k]; if (DATA.welsh.handoff) DATA.welsh.handoff[k] = fix[k]; }
  const norm = s => (s || "").replace(/\s+/g, " ").trim();
  const enExp = {}; for (const k in stat) enExp[k] = norm(stat[k].en);
  toggle.static_keys = Object.keys(stat).length;
  const grab = () => { const o = {}; for (const el of d.querySelectorAll("[data-i18n]")) o[el.getAttribute("data-i18n")] = norm(el.textContent); return o; };
  const grabAttrs = () => { const o = []; for (const ak of ATTR_KEYS) for (const el of d.querySelectorAll("[" + ak + "]")) o.push({ attr: ak, key: el.getAttribute(ak), text: norm(el.textContent).slice(0, 4000) }); return o; };
  for (const sk of states) {
    goto(sk, "en"); const before = grab(); const attrsEn = grabAttrs();
    goto(sk, "cy"); const during = grab(); const attrsCy = grabAttrs();
    goto(sk, "en"); const after = grab();
    for (const k in stat) {
      if (!(k in before)) { toggle.failures.push({ state: sk, key: k, why: "no [data-i18n] element rendered for this key" }); continue; }
      if (before[k] === enExp[k]) toggle.en_ok++; else toggle.failures.push({ state: sk, key: k, why: `en mode shows ${JSON.stringify(before[k].slice(0, 60))}, manifest en is ${JSON.stringify(enExp[k].slice(0, 60))}` });
      if (during[k] === norm(fix[k])) toggle.cy_ok++; else toggle.failures.push({ state: sk, key: k, why: `cy mode shows ${JSON.stringify((during[k] || "").slice(0, 60))}, fixture is ${JSON.stringify(fix[k])}` });
      if (after[k] === before[k]) toggle.restored_ok++; else toggle.failures.push({ state: sk, key: k, why: `after toggling back: ${JSON.stringify((after[k] || "").slice(0, 60))} ≠ ${JSON.stringify(before[k].slice(0, 60))}` });
    }
    toggle.attr_consumers = Math.max(toggle.attr_consumers, attrsEn.length);
    attrsEn.forEach((rEn, i) => {
      const rCy = attrsCy[i], k = rEn.key;
      if (k in fix && rCy.text.indexOf(fix[k]) === -1) toggle.failures.push({ state: sk, key: k, why: `${rEn.attr}="${k}": fixture value not rendered in Welsh mode` });
      if (k in enExp && enExp[k] && rEn.text.indexOf(enExp[k]) === -1) toggle.failures.push({ state: sk, key: k, why: `${rEn.attr}="${k}": manifest English not rendered in English mode` });
      if (!(k in stat)) toggle.failures.push({ state: sk, key: k, why: `${rEn.attr} names a key with no static manifest row` });
    });
  }
}
const bad = findings.filter(f => (f.class === "english" || f.class === "mixed") && !f.source);
const excepted = findings.filter(f => (f.class === "english" || f.class === "mixed") && f.source);
const warn = findings.filter(f => f.class === "welsh" && !f.source);
const bySource = {}; for (const f of excepted) bySource[f.source.split(":")[0]] = (bySource[f.source.split(":")[0]] || 0) + 1;
const byTypo = {}; for (const t of typos) byTypo[t.typo] = (byTypo[t.typo] || 0) + 1;
const summary = { document_lang: d.documentElement.lang, states_sampled: states.length, distinct_strings_seen: seen.size,
  english_without_provenance: bad.length, english_with_provenance: excepted.length, english_with_provenance_by_family: bySource,
  welsh_without_provenance: warn.length, typography_faults: typos.length, typography_by_kind: byTypo,
  toggle: { static_keys: toggle.static_keys, attr_consumers: toggle.attr_consumers, en_ok: toggle.en_ok, cy_ok: toggle.cy_ok, restored_ok: toggle.restored_ok, failures: toggle.failures.length } };
console.log(JSON.stringify(summary, null, 1));
for (const f of bad.slice(0, 20)) console.log("  BAD", f.kind, f.tag, JSON.stringify(f.text.slice(0, 90)), f.state);
for (const t of typos.slice(0, 20)) console.log("  TYPO", t.typo, t.tag, JSON.stringify(t.text), t.state);
for (const f of toggle.failures.slice(0, 20)) console.log("  TOGGLE", f.state || "", f.key, f.why);
fs.writeFileSync(WD + "/" + (process.env.OUT || "browser_gate_jsdom.json"), JSON.stringify({
  note: "browser gate v3 logic (COLLECT_JS + classify, v2/v3 typography incl. lower-case-initial, and the --fixture auto static-furniture toggle) executed under jsdom over an 8-state reduced build of the shipped head, payload and client; Chromium system libraries unavailable in the build environment; hash driven with gender=/cohort= per the URL contract",
  states: states, summary, english_without_provenance: bad, english_with_provenance: excepted, welsh_without_provenance: warn,
  typography: typos, toggle_failures: toggle.failures }, null, 1));
process.exit((bad.length || typos.length || toggle.failures.length) ? 1 : 0);
