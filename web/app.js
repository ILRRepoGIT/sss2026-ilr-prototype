"use strict";
/* -------------------------------------------------------------------------
   School Sport Survey 2026 - Interactive Learning Report (client, v2)
   Displays pre-calculated, disclosure-checked aggregates and pre-generated
   deterministic narrative. Makes no calculations of findings, no ranking
   decisions, no suppression decisions, and no network or AI calls.
--------------------------------------------------------------------------*/
const DATA = JSON.parse(document.getElementById("report-data").textContent);
/* V6.0 (production, chunked delivery — deployment plan §2, review P0.7).
   The SERVED package carries only the first state ("whole|all|none") inline;
   every other state lives in a content-hashed chunk file per scope|gender
   group under the release tree, fetched on demand, verified and cached.
   DATA.chunked is the map of those files with each file's sha256, the
   identity envelope every chunk must carry, and the base URL. The
   monolithic assurance copy embeds every state and has no DATA.chunked, so
   on that file this block is inert and the report behaves exactly as before.
   Fail-closed: a view is never rendered from a chunk that failed to arrive,
   failed its sha256, or carries another report's identity; a late response
   from an earlier selection is discarded; while a view is loading the
   report content is masked and printing is unavailable. */
const CHUNKED = DATA.chunked || null;
const _chunkLoaded = new Set();
const _chunkPending = new Map();
let _viewSeq = 0;
const groupLoaded = g => !CHUNKED || _chunkLoaded.has(g) || !CHUNKED.map[g];
function _hex(buf) {
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2, "0")).join("");
}
async function fetchChunk(g, f) {
  const r = await fetch(CHUNKED.base + f.path, { credentials: "same-origin" });
  if (!r.ok) throw new Error("HTTP " + r.status + " " + f.path);
  const buf = await r.arrayBuffer();
  // fail closed: without SubtleCrypto (an insecure context) the file cannot be
  // verified, so it is not used — the reports are served over HTTPS only
  if (!(window.crypto && crypto.subtle)) throw new Error("integrity check unavailable (insecure context)");
  const d = await crypto.subtle.digest("SHA-256", buf);
  if (_hex(d) !== f.sha256) throw new Error("integrity " + f.path);
  const body = JSON.parse(new TextDecoder("utf-8").decode(buf));
  const env = body.env || {}, want = CHUNKED.envelope || {};
  for (const k of ["family", "recipient", "release", "schema", "binding"])
    if (env[k] !== want[k]) throw new Error("identity " + f.path + " " + k);
  if (body.group !== g) throw new Error("group " + f.path);
  const keys = Object.keys(body.states || {});
  if (keys.length !== f.n) throw new Error("count " + f.path);
  for (const k of keys) if (k.slice(0, g.length + 1) !== g + "|") throw new Error("key " + k);
  return body.states;
}
function loadGroup(g) {
  if (groupLoaded(g)) return Promise.resolve();
  if (_chunkPending.has(g)) return _chunkPending.get(g);
  const entry = CHUNKED.map[g];
  const p = Promise.all(entry.files.map(f => fetchChunk(g, f))).then(parts => {
    // commit only when EVERY part of the group verified
    for (const st of parts) for (const k in st) DATA.states[k] = st[k];
    _chunkLoaded.add(g); _chunkPending.delete(g);
  }).catch(e => { _chunkPending.delete(g); throw e; });
  _chunkPending.set(g, p);
  return p;
}
/* the states a view reads: its own state and its "none" sibling, the boys'
   and girls' states of the same scope and cohort (the appendix tables), and
   the whole-school state; a group is fetched only when one of those states
   is absent — the entry page inlines the three whole-school "none" states,
   so the default view renders with no fetch at all */
function neededKeys() {
  const sc = state.scope, co = state.cohort;
  return [sc + "|" + state.gender + "|" + co, sc + "|" + state.gender + "|none",
          sc + "|boy|" + co, sc + "|girl|" + co, "whole|all|none"];
}
const groupsFor = () => Array.from(new Set(
  neededKeys().filter(k => !DATA.states[k]).map(k => k.split("|").slice(0, 2).join("|"))
)).filter(g => !groupLoaded(g));
function setLoading(mode, retry) {
  const m = document.getElementById("load-mask");
  const main = document.getElementById("report");
  const pb = document.getElementById("btn-print");
  if (!m) return;
  if (!mode) {
    m.hidden = true; document.body.classList.remove("is-loading");
    if (main) main.removeAttribute("aria-busy");
    if (pb) pb.disabled = false;
    return;
  }
  m.hidden = false; document.body.classList.add("is-loading");
  if (main) main.setAttribute("aria-busy", "true");
  if (pb) pb.disabled = true;
  m.classList.toggle("load-error", mode === "error");
  const rb = document.getElementById("load-retry");
  if (rb) rb.onclick = retry || null;
}
/* Build configuration (Final Decision Approach D3):
   reviewMode        - review banner + provisional markers visible
   sensitiveFilters  - chart-derived filtering by disability / learning
                       difficulty; release default is FALSE until O09/O10
   showSummaries     - D22: chapter/final summaries visible               */
/* Build configuration (Final Decision Approach D3):
   reviewMode        - review banner + provisional markers visible
   sensitiveFilters  - chart-derived filtering by disability / learning
                       difficulty; release default is FALSE until O09/O10
   showSummaries     - D22: chapter/final summaries visible               */
const CONFIG = { reviewMode: true, sensitiveFilters: true, showSummaries: true };
// V4.12 (owner request, 16 Sep 2026): the report opens in WELSH; a saved
// link with lang=en, or the switch, selects English. Nothing else changed.
const state = { scope: "whole", gender: "all", cohort: "none", lang: "cy", a11y: false };
/* V4.2: bilingual toggle. Generated narrative and chart labels come from
   the Welsh Generation Framework; page furniture awaits the translator's
   handoff and falls back to English, visibly flagged in review mode. */
const CY = DATA.welsh || { ui: {}, handoff: {}, handoffMissing: 0 };
const isCy = () => state.lang === "cy";
const tr = (en, cyStr) => (isCy() && cyStr) ? cyStr : en;

/* D63/D64 (v1.9): the language layer. Every dynamic and assistive string
   is served by t(key, params) from the sheet-43 typed-frame catalogue
   embedded in the payload — both languages, one frame per string. No
   Welsh literal and no `|| "fallback"` lives in application code; a
   missing key renders the ⟪missing:key⟫ marker in this development build
   (a release build fails instead). {n:count NP} slots are filled from
   the numeral service's pre-realised forms (words 1–10, correct
   mutation, singular noun; figures above ten). */
const FRAMES = CY.frames || {};
const COUNT_NP = CY.countNP || {};
const MISS = k => "⟪missing:" + k + "⟫";
const uiStr = k => (CY.ui && CY.ui[k] != null) ? CY.ui[k] : MISS(k);
function countNP(n, noun) {
  // "camp, definite[, initial]" — 'definite' selects the DEFINITE table
  // (D71/PR-17); 'initial' capitalises the first cased character at
  // realisation (D75) and touches nothing else.
  const parts = String(noun).split(/\s*,\s*/);
  const key = parts.length > 1 ? parts[0] + "|" + parts[1] : noun;
  const arr = COUNT_NP[key];
  let out = (n >= 1 && n <= 10 && arr) ? arr[n - 1] : n + " " + parts[0];
  if (parts.indexOf("initial") > -1)
    out = out.replace(/[A-Za-zÀ-ÿŵŷ]/, ch => ch.toUpperCase());
  return out;
}
const SLOT_ALIAS = { labelCy: "label", answerCy: "answer",
                     baseNoteCy: "baseNote", optCy: "opt",
                     sportCy: "sport", segCy: "seg" };
/* D68/D72: a development build stamps data-i18n-source on every node the
   language layer writes; a release build strips it. The browser
   provenance gate (BROWSER-provenance) reads the attribute. */
const DEV = !(DATA.buildMetadata && DATA.buildMetadata.mode === "release");
const prov = k => DEV ? ' data-i18n-source="' + k + '"' : "";
function fmtFrame(s, p) {
  p = p || {};
  s = String(s).replace(/\[([^\][]*)\]/g, (m, seg) => {
    const slots = seg.match(/\{[^}]+\}/g);
    if (!slots) return p.multi ? seg : "";
    for (const sl of slots) {
      const name = sl.replace(/[{}]/g, "").split(":")[0];
      if (!p[SLOT_ALIAS[name] || name]) return "";
    }
    return seg;
  });
  s = s.replace(/\{(\w+):count ([^}]+)\}/g,
                (m, name, noun) => countNP(p[name], noun));
  s = s.replace(/\{(\w+)(?:\.\w+)?\}/g, (m, name) => {
    const k2 = SLOT_ALIAS[name] || name;
    return p[k2] != null ? p[k2] : m;
  });
  return s;
}
/* D77: the singular contract — the frame records WHICH count slot
   controls singular selection (sg_slot); t() tests exactly that slot. */
function sgSel(f, p) {
  if (!p) return false;
  const sl = f.sg_slot;
  if (sl === "base") return p.base === 1;
  if (sl === "b") return p.b === 1;
  if (sl === "k") return p.k === 1;
  if (sl === "n") return p.n === 1;
  return p.n === 1 || p.k === 1;
}
function t(k, p) {
  const f = FRAMES[k];
  if (!f) return MISS(k);
  const one = sgSel(f, p);
  let s;
  if (isCy()) s = (one && f.cy_sg) ? f.cy_sg : f.cy;
  else s = (one && f.en_sg) ? f.en_sg : f.en;
  if (s == null || s === "") {
    // V4.11: a declared frame whose Welsh has not been returned yet is
    // PENDING — the English is shown (the static-lane policy recorded in
    // V4.9), never a bare marker; framePending() lets the renderer mark
    // the node (review class, lang="en", provenance frame:pending:key).
    // A frame with no English at all is an error and shows the marker.
    const en = (one && f.en_sg) ? f.en_sg : f.en;
    if (en == null || en === "") return MISS(k);
    return fmtFrame(en, p);
  }
  return fmtFrame(s, p);
}
const framePending = k => { const f = FRAMES[k]; return !!f && isCy() && (f.cy == null || f.cy === ""); };
/* Write a frame into an element with the pending decoration (assessment
   §9.4: English fallback inside lang=cy carries lang="en"). */
function setFrame(el, k, p, asHtml) {
  if (!el) return;
  if (asHtml) el.innerHTML = t(k, p); else el.textContent = t(k, p);
  const pending = framePending(k);
  el.classList.toggle("cy-missing", pending);
  if (pending) { el.setAttribute("lang", "en"); el.setAttribute("title", "Heb ei gyfieithu eto — dangosir y Saesneg"); }
  else { el.removeAttribute("lang"); el.removeAttribute("title"); }
  if (DEV) el.setAttribute("data-i18n-source", (pending ? "frame:pending:" : "frame:") + k);
}
/* Attribute strings (aria-label, alt, title) from frames: the template's
   English literal is overwritten from the catalogue on every language
   change (assessment §9.3). */
/* The frame hosts and attribute frames the MARKUP declares (data-frame,
   data-frame-attr): the consumer set is written out here so the client
   states which frames it consumes (FRAME-dormant); a markup key outside
   this set renders the marker. */
const MARKUP_FRAMES = { "ui.a11y_switch": 1, "ui.a11y_switch_desc": 1, "ui.a11y_glossary_heading": 1, "ui.a11y_glossary_intro": 1,
  "ui.chart_sports_total_pe": 1, "ui.chart_sports_total_club": 1,
  "ui.chart_sports_total_community": 1, "ui.chart_sports_total_other": 1,
  "ui.aria_cover": 1, "ui.aria_rail": 1, "ui.aria_toc": 1,
  // V4.16: the Young Artists Competition artwork's alt frames (one per
  // image; the Brain Break frames ui.alt_brain_* are DEPRECATED on sheet 43)
  "ui.alt_yac_dragon_kit": 1, "ui.alt_yac_welsh_symbols": 1, "ui.alt_yac_balls": 1,
  "ui.alt_yac_footballer": 1, "ui.alt_yac_football_splash": 1, "ui.alt_yac_cyclist": 1,
  "ui.alt_yac_dragon_football": 1, "ui.alt_yac_heart": 1, "ui.alt_yac_horse": 1,
  "ui.alt_yac_tennis_football": 1, "ui.alt_yac_gymnastics": 1, "ui.alt_yac_cricket": 1,
  "ui.alt_yac_basketball": 1, "ui.alt_yac_dragon_wales": 1,
  // V6.0: the chunked-delivery loading mask (production serving)
  "ui.loading_view": 1, "ui.load_error": 1, "ui.retry": 1,
};
function applyFrameAttrs() {
  for (const el of document.querySelectorAll("[data-frame-attr]")) {
    for (const pair of el.getAttribute("data-frame-attr").split(",")) {
      const [attr, k] = pair.split(":").map(x => x.trim());
      if (attr && k) el.setAttribute(attr, MARKUP_FRAMES[k] ? t(k) : MISS(k));
    }
  }
  for (const el of document.querySelectorAll("[data-frame]")) {
    const k = el.getAttribute("data-frame");
    if (!MARKUP_FRAMES[k]) { el.textContent = MISS(k); continue; }
    setFrame(el, k, { n: DATA.buildMetadata.sportOptionCount || "" });
  }
}
/* V4.13 accessibility switch (#btn-a11y). The state lives in the hash
   (a11y=1) beside the language, so a saved or shared link keeps it. On:
   html.a11y scopes the accessibility presentation (template CSS), every
   chart's data table is opened and made focusable, the character images
   get a visible caption from their alt frame, and the guide's glossary
   panel lists links to the guide's own FAQ answers. Off: all of it is
   undone and the page is the default rendering. Content never changes. */
const GLOSSARY_FAQS = ["faqd-base", "faqd-numbers", "faqd-percentages", "faqd-colours", "faqd-grey",
                       "faqd-greyed", "faqd-hidden", "faqd-fsm", "faqd-banner"];
let _a11yOpened = [];
function applyA11yState() {
  const on = !!state.a11y;
  document.documentElement.classList.toggle("a11y", on);
  const b = document.getElementById("btn-a11y");
  if (b) b.setAttribute("aria-checked", on ? "true" : "false");
  // data tables: open while the switch is on, restored when it is turned off
  if (on) {
    for (const d of $$("details.dtable:not([open])")) { d.open = true; _a11yOpened.push(d); }
  } else {
    _a11yOpened.forEach(d => { if (d.isConnected) d.open = false; });
    _a11yOpened = [];
  }
  for (const tb of $$("details.dtable table")) {
    if (on) tb.setAttribute("tabindex", "0"); else tb.removeAttribute("tabindex");
  }
  // captions under the character images, from the image's own alt frame
  for (const img of $$("img[data-frame-attr]")) {
    let cap = img.nextElementSibling;
    if (!cap || !cap.classList.contains("a11y-cap")) {
      cap = document.createElement("span");
      cap.className = "a11y-only a11y-cap";
      img.insertAdjacentElement("afterend", cap);
    }
    cap.textContent = img.getAttribute("alt") || "";
    cap.setAttribute("aria-hidden", "true");       // the alt already names it
  }
  // glossary entries: the guide's own FAQ questions, in the active language
  const gl = document.getElementById("a11y-glossary-list");
  if (gl) gl.innerHTML = GLOSSARY_FAQS.map(id => {
    const d = document.getElementById(id), sm = d && d.querySelector("summary");
    return sm ? '<li><a href="#' + id + '">' + esc(sm.textContent) + "</a></li>" : "";
  }).join("");
}
/* D74: frames are clauses; the joiner is the ONLY place a separator
   exists, and the separators are CONTRACT data from sheet 43. */
const SEPS = CY.separators || {};
const sepDot = () => SEPS.dot != null ? SEPS.dot : MISS("ui.join_dot");
const sepDash = () => SEPS.dash != null ? SEPS.dash : MISS("ui.join_dash");
function joinClause(parts, sep) { return parts.filter(Boolean).join(sep); }
/* D79 (v2.2): the static translator lane is a BOUND row. Every
   translator-owned text node in the page carries data-i18n="<key>" (stamped
   at build time by the English); the payload manifest welsh.static holds
   {en, cy, consumer} per key. renderStatic() writes textContent from the
   manifest for the active language on load and on every language change,
   and restores English FROM THE MANIFEST, never from a cached DOM. The
   manifest is read at call time (the browser gate injects fixture values
   at run time). D80: the keyed fixed attributes (data-ct-key, data-nh-key,
   data-also-h-key, data-sh-key) resolve through the same staticStr(). */
const STATIC = () => (DATA.welsh && DATA.welsh.static) || {};
/* A static row whose Welsh value has not been returned yet is PENDING: in
   Welsh mode it shows the manifest ENGLISH under the review marker the
   translator lane has carried since V4.2 (dotted red, "Heb ei gyfieithu
   eto"), never a bare marker and never blank — the page stays readable
   while the translator's values are outstanding (V4.9 deviation from
   spec §14.1, recorded). A key with no manifest row at all is an error and
   shows the marker. Release mode fails on the empty value (CAT-values). */
const staticPending = k => { const e = STATIC()[k]; return !!e && isCy() && (e.cy == null || e.cy === ""); };
const staticStr = k => {
  const e = STATIC()[k];
  if (!e) return MISS(k);
  const v = isCy() ? e.cy : e.en;
  return (v == null || v === "") ? ((e.en == null || e.en === "") ? MISS(k) : e.en) : v;
};
/* V4.10 block rows (D79, V4.9 register item 6): a paragraph with inline
   emphasis is ONE row. Its English markup comes from the template
   (manifest `html`); its Welsh value carries the translator's own
   <strong>/<em> runs. Both pass through the same allow-list before they
   reach the DOM: strong / em / b / i / br only, one guarded colour style,
   everything else escaped. */
const INLINE_OK = { STRONG: 1, EM: 1, B: 1, I: 1, BR: 1 };
function sanitiseInline(src) {
  const tpl = document.createElement("template");
  tpl.innerHTML = String(src == null ? "" : src);
  const walk = node => {
    let out = "";
    for (const c of node.childNodes) {
      if (c.nodeType === 3) out += esc(c.nodeValue);
      else if (c.nodeType === 1 && INLINE_OK[c.tagName]) {
        const tag = c.tagName.toLowerCase();
        if (tag === "br") { out += "<br>"; continue; }
        const st = c.getAttribute("style") || "";
        const keep = /^color:\s*var\(--[a-z-]+\)$/.test(st.trim()) ? ' style="' + st.trim() + '"' : "";
        out += "<" + tag + keep + ">" + walk(c) + "</" + tag + ">";
      } else if (c.nodeType === 1) out += walk(c);
    }
    return out;
  };
  return walk(tpl.content);
}
const staticHtml = k => {
  const e = STATIC()[k];
  if (!e) return esc(MISS(k));
  const cy = isCy() ? e.cy : "";
  if (cy != null && cy !== "") return sanitiseInline(cy);
  if (e.html != null && e.html !== "") return sanitiseInline(e.html);
  return esc(staticStr(k));
};
function renderStatic() {
  for (const el of document.querySelectorAll("[data-i18n]")) {
    const k = el.getAttribute("data-i18n");
    const row = STATIC()[k];
    if (row && row.inline) el.innerHTML = staticHtml(k);
    else el.textContent = staticStr(k);
    const pending = staticPending(k);
    el.classList.toggle("cy-missing", pending);
    if (pending) { el.setAttribute("title", "Heb ei gyfieithu eto — dangosir y Saesneg"); el.setAttribute("lang", "en"); }
    else { el.removeAttribute("title"); el.removeAttribute("lang"); }
    if (DEV) el.setAttribute("data-i18n-source", (pending ? "handoff:pending:" : "static:") + k);
  }
}
/* PR-18/D76: the language-neutral no-report marker with its accessible
   name from ui.table_suppressed. */
const noRep = () => '<span title="' + esc(t("ui.table_suppressed")) +
  '" aria-label="' + esc(t("ui.table_suppressed")) + '"' +
  prov("catalogue:no_report") + '>' + esc(cat("no_report")) + "</span>";
/* The optional segments of a frame (e.g. the multiple-answers tag of
   ui.base_line), for consumers that need one segment on its own —
   sourced from the catalogue, never re-typed. */
const frameSegs = k => {
  const f = FRAMES[k];
  const s = f ? (isCy() ? f.cy : f.en) : "";
  const out = [];
  String(s || "").replace(/\[([^\][]*)\]/g, (m, seg) => { out.push(seg); return m; });
  return out;
};
const multiSeg = () => (frameSegs("ui.base_line").find(x => !/\{/.test(x)) || "");

const $ = (s, el) => (el || document).querySelector(s);
const $$ = (s, el) => Array.from((el || document).querySelectorAll(s));
const esc = s => String(s).replace(/[&<>"']/g, c =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const key = () => state.scope + "|" + state.gender + "|" + state.cohort;
const st = () => DATA.states[key()];
/* v5 (build 012): paywall suppression - a suppressed view keeps every
   section visible, rendered from WHOLE-SCHOOL data (never the protected
   small-group values), greyed with a message box on top. */
const viewSup = () => { const s = st(); return !s || !!s.sup; };
let FORCE_WHOLE = false;
/* V6.0 (owner instruction, 22 Sep 2026): a school with fewer than five
   accepted responses still receives its report. Its whole-school state is
   itself suppressed by the rule of five, so there is no whole-school content
   to grey underneath a message: every view has no display state, every chart
   and section shows the existing suppression message, and the school
   information, FAQ and metadata stay. */
const WHOLE_SUP = !!(DATA.states["whole|all|none"] || {}).sup;
const dst = () => WHOLE_SUP ? null : ((viewSup() || FORCE_WHOLE)
  ? DATA.states["whole|all|none"] : st());
const sib = () => DATA.states[state.scope + "|" + state.gender + "|none"];
const scopeOpt = k => DATA.filterOptions.scope.find(o => o.key === k);
const cohortDef = () => state.cohort !== "none" ? DATA.cohorts[state.cohort] : null;

/* ----------------------------------------------------------- hash + focus */
function readHash() {
  const h = new URLSearchParams(location.hash.replace(/^#(?=.*=)/, ""));
  const sc = h.get("scope"), g = h.get("gender"), co = h.get("cohort");
  const lg = h.get("lang");
  const sec = h.get("s");
  state.section = (sec && /^[\w-]+$/.test(sec) && document.getElementById(sec)) ? sec : null;
  if (lg === "cy" || lg === "en") state.lang = lg;
  state.a11y = h.get("a11y") === "1";           // V4.13: accessibility switch
  if (sc && scopeOpt(sc)) state.scope = sc;
  if (g && DATA.filterOptions.gender.some(o => o.key === g)) state.gender = g;
  if (co && (co === "none" || DATA.cohorts[co])) state.cohort = co;
}
function writeHash() {
  history.replaceState(null, "",
    "#scope=" + state.scope + "&gender=" + state.gender + "&cohort=" + state.cohort +
    "&lang=" + state.lang + (state.a11y ? "&a11y=1" : "") +
    (state.section ? "&s=" + state.section : ""));
}
/* V4.11 (assessment §8.2): in-page section links used to replace the
   state hash with a bare fragment, so a copied or reloaded link lost the
   language and filters. Every #section anchor now scrolls to its target
   and records the section in the state hash (…&s=<id>) instead. */
function gotoSection(id, focus) {
  const el = document.getElementById(id);
  if (!el) return false;
  state.section = id;
  writeHash();
  if (typeof el.scrollIntoView === "function") el.scrollIntoView({ block: "start" });
  if (focus && typeof el.focus === "function") { el.setAttribute("tabindex", "-1"); el.focus({ preventScroll: true }); }
  return true;
}
document.addEventListener("click", e => {
  const a = e.target.closest("a[href^='#']");
  if (!a) return;
  const id = a.getAttribute("href").slice(1);
  if (!id || id.includes("=")) return;
  const dt = document.getElementById(id);
  if (dt && dt.tagName === "DETAILS") dt.open = true;   // V4.13: a glossary link opens its FAQ answer
  if (gotoSection(id, true)) e.preventDefault();
});
let _lastLang = null;
function applyLanguageState() {
  // UI-001 / integration spec §5.4: the document language, the toggle
  // label (with its own lang attribute so its name is pronounced
  // correctly), the review note and the cached filter controls all
  // follow the language in the hash — from ANY entry point.
  document.documentElement.lang = state.lang;
  const b = document.getElementById("btn-lang");
  if (b) {
    // V4.10 slider: both labels always visible, from the catalogue; the
    // switch state and the highlighted label follow the language
    const en = b.querySelector(".ls-en"), cy = b.querySelector(".ls-cy");
    if (en) { en.textContent = uiStr("language_label_en"); en.classList.toggle("on", !isCy()); }
    if (cy) { cy.textContent = uiStr("language_label"); cy.classList.toggle("on", isCy()); }
    b.setAttribute("aria-checked", isCy() ? "true" : "false");
  }
  const rb = document.getElementById("review-note-cy");
  if (rb) {
    rb.style.display = (isCy() && CONFIG.reviewMode) ? "block" : "none";
    const rows = Object.values(STATIC());
    const done = rows.filter(r => r.cy).length;
    setFrame(rb, "ui.review_note", { done: done, total: rows.length, pending: rows.length - done });
  }
  document.title = t("ui.doc_title", { school: DATA.school.name });
  if (_lastLang !== state.lang) {
    // integration spec §5.1: the two cached filter controls are built
    // once; a language change must rebuild them
    const gsel = document.getElementById("f-group");
    const sel = document.getElementById("f-scope");
    if (gsel) gsel.innerHTML = "";
    if (sel) sel.innerHTML = "";
    _lastLang = state.lang;
    // V4.11: the school profile and the section navigation are language
    // aware (sheet-43 frames) — re-rendered on every language change
    if (document.getElementById("overview-table")) renderProfile();
    injectNav();
  }
  // D79: the static furniture follows the language from the manifest
  renderStatic();
  applyFrameAttrs();
  applyA11yState();      // V4.13: captions and glossary follow the language
}
let annT = null;
function announce(msg) {
  clearTimeout(annT);
  annT = setTimeout(() => { $("#live-region").textContent = msg; }, 250);
}

/* ------------------------------------------------------------- data views */
function metricFor(mid) {
  if (viewSup() || FORCE_WHOLE) {
    const w = DATA.states["whole|all|none"];
    return { res: w.m[mid], context: false };
  }
  const c = cohortDef();
  if (c && c.metric === mid) {
    const s = sib();
    return { res: s && !s.sup ? s.m[mid] : null, context: true };
  }
  /* V4.18 (owner instruction, 22 Sep 2026): the weekly-frequency chart
     ("On average, how often are our pupils engaging in sport each week?")
     keeps the wider picture under a SETTING selection ("Where are our
     pupils taking part in Sport?"), exactly as a chart does under its own
     selection — its bars stay selectable; the narrative carries the
     selected-group definition (EN-09). */
  if (c && mid === "freq_estimate" && c.metric === "participation_settings") {
    const s = sib();
    return { res: s && !s.sup ? s.m[mid] : null, context: true, wider: true };
  }
  const s = st();
  return { res: s && !s.sup ? s.m[mid] : null, context: false };
}
function cohortKeyFor(mid, code) {
  for (const [k, c] of Object.entries(DATA.cohorts))
    if (c.metric === mid && c.code === code) return k;
  return null;
}

/* ---------------------------------------------------------------- charts */
function stateMsg(kind) {
  // sheet 43: one typed frame pair per state message, both languages.
  // 'sup' consumes the msg.suppressed_* frames (D72): a metric held back
  // for disclosure control names the reason instead of vanishing.
  const keys = { nd: ["ui.state_nd_title", "ui.state_nd_body"],
                 na: ["msg.not_asked_title", "msg.not_asked_body"],
                 sup: ["msg.suppressed_title", "msg.suppressed_body"] }[kind];
  const title = keys ? t(keys[0]) : MISS("msg." + kind);
  const body = keys ? t(keys[1]) : "";
  const tail = kind === "sup"
    ? '<div class="b">' + esc(t("msg.suppressed_base")) + "</div>" : "";
  return '<div class="state-msg"' + prov("frame:" + (keys ? keys[0] : kind)) +
         '><div class="t">' + esc(title) +
         '</div><div class="b">' + esc(body) + "</div>" + tail + "</div>";
}

function barTitle(def, o, v, base, ctx) {
  // sheet 43 ui.bar_tooltip: one typed frame for the ordinary bar title;
  // both counts go through the numeral service in Welsh.
  return t("ui.bar_tooltip", { label: labelOf(def), opt: optLabel(o),
                               n: v, base: base, desc: viewDesc(ctx),
                               multi: def.type === "multi" });
}
/* D50: the view descriptor is a typed record realised per language —
   scope.shortCy is generated by the audience renderer at build time. */
const descOf = s => !s ? "" :
  (isCy() && s.scope.shortCy ? s.scope.shortCy : s.scope.short);
function viewDesc(contextOnly) {
  const base = descOf(st());
  if (contextOnly) {
    const parts = base.split(" · ");
    return parts.slice(0, 2).join(" · ");
  }
  return base;
}

function renderChart(host, mid) {
  const def = DATA.metricDefs[mid];
  const { res, context, wider } = metricFor(mid);
  /* D80: a chart-heading override is a static-manifest KEY (data-ct-key).
     Its heading is static furniture in the markup — bound by the static
     lane (data-i18n) and swapped by renderStatic() — and the chart renders
     into the slot beneath it; the renderer resolves the same key through
     the language layer so the heading is right even before the swap. */
  const ctKey = host.getAttribute("data-ct-key");
  const slot = ctKey ? $(".chart-slot", host) : null;
  const keyedH = ctKey ? $("[data-i18n]", host) : null;
  if (keyedH) keyedH.textContent = staticStr(ctKey);
  /* V4.13 (accessibility feedback: chart titles not announced): every chart
     card is a labelled group named by its own heading, so assistive
     technology announces the title on entering the chart. */
  const hid = "ch-" + mid;
  const sink = html => { if (slot) { slot.innerHTML = html;
      if (keyedH) { keyedH.id = hid; const cc = keyedH.closest(".chart-card");
        if (cc) { cc.setAttribute("role", "group"); cc.setAttribute("aria-labelledby", hid); } } }
    else { host.innerHTML = '<div class="chart-card"><h4' + prov("label:" + mid) +
      ">" + esc(labelOf(def)) + "</h4>" + html + "</div>";
      const cc = host.firstElementChild, h4 = cc && cc.querySelector("h4");
      if (h4) { h4.id = hid; cc.setAttribute("role", "group"); cc.setAttribute("aria-labelledby", hid); } } };
  let html = "";
  if (!res) { sink(stateMsg("sup")); return; }
  if (res.s !== "ok") { sink(stateMsg(res.s)); return; }
  const base = res.b;
  // sheet 43 ui.base_line: one typed frame, optional segments included by
  // role; the numeral slot is served by the numeral service.
  let baseTxt = t("ui.base_line", {
    n: base, multi: def.type === "multi",
    baseNote: (isCy() ? def.baseNoteCy : def.baseNote) || "" });
  // sheet 43: the three context suffixes are typed frames (UI-DYN-06);
  // D74: frames are clauses, joined by the one clause joiner.
  const ctxClause =
    // V4.18: the wider picture kept under a setting selection is announced
    // with the existing "Showing: {desc}" frame for the wider view — this
    // chart does not define the selected group, so ui.ctx_shown_for's
    // parenthesis would be untrue
    wider ? t("ui.ctx_showing", { desc: viewDesc(true) })
    : context ? t("ui.ctx_shown_for", { desc: viewDesc(true) })
    : (viewSup() || FORCE_WHOLE) ? t("ui.ctx_whole_school")
    : key() !== "whole|all|none" ? t("ui.ctx_showing", { desc: viewDesc(false) })
    : "";
  baseTxt = joinClause([baseTxt, ctxClause], sepDot());
  html += '<p class="chart-base"' + prov("frame:ui.base_line") + '>' +
          esc(baseTxt) + "</p>";
  let clickable = def.cf === "cohort";
  if (!CONFIG.sensitiveFilters &&
      (mid === "disability_condition" || mid === "learning_difficulty")) clickable = false;
  if (clickable) html += '<p class="chart-click-note"' +
    prov("frame:ui.click_note") + '>' + esc(t("ui.click_note")) + "</p>";

  /* v3 (build 010, owner decision): every chart alternates red and blue by
     canonical option index. Grey is reserved for (a) answers carrying no
     frequency value, (b) bars that are non-selectable on a selectable
     chart, and (c) suppressed values. Yellow marks the selected value. */
  const CYCLE = ["bar-red", "bar-blue"];
  const GREY_CODES = { less_weekly: 1, dont_know: 1,
                       less_weekly_only: 1, dont_know_only: 1 };
  let rows = def.opts.map((o, i) => ({ code: o[0],
                                       label: o[1], cy: def.optsCy && def.optsCy[i],
                                       v: res.v[i],
                                       cls: GREY_CODES[o[0]] ? "bar-grey"
                                            : CYCLE[i % 2] }));
  let note = "";
  const T2 = DATA.tier2Codes || [];
  const hasComposite = def.opts.some(o => o[0] === "other_sports");
  if (def.chart === "horizontal_ranked_bar") {
    rows = rows.filter(o => o.v !== 0 && o.v !== null);
    if (hasComposite) rows = rows.filter(o => T2.indexOf(o.code) === -1);
    rows.sort((a, b) => b.v - a.v);
    if (def.topN) {
      let cut = Math.min(def.topN, rows.length);
      while (cut < rows.length && rows[cut].v === rows[cut - 1].v) cut++;
      if (rows.length > cut)
        note = t("ui.ranking_note", { k: cut, n: rows.length });
      rows = rows.slice(0, cut);
    } else if (def.tail) {
      rows = rows.filter(o => !def.tail.includes(o.code))
                 .concat(rows.filter(o => def.tail.includes(o.code)));
    }
  }
  // v2 (Sport Wales feedback): on filtered views, keep the whole-school
  // outline so the filtered results visibly "fill up" the bars.
  let ghost = null;
  // V4.18: the frequency chart kept at the wider picture under a setting
  // selection is compared with the whole school only when that wider
  // picture is not the whole school itself (a source chart under its own
  // selection keeps its V4.17 outline)
  const wholeShown = wider && state.scope === "whole" && state.gender === "all";
  if (key() !== "whole|all|none" && !viewSup() && !FORCE_WHOLE && !wholeShown) {
    const w = DATA.states["whole|all|none"];
    const wres = w && !w.sup ? w.m[mid] : null;
    if (wres && wres.s === "ok") {
      ghost = { _b: wres.b };
      def.opts.forEach((o, i) => { ghost[o[0]] = wres.v[i]; });
    }
  }
  const gv = o => ghost && ghost[o.code] != null ? ghost[o.code] : 0;
  const max = Math.max(1, ...rows.map(o =>
    Math.max(o.v === null ? 0 : o.v, gv(o))));
  const selActive = clickable && state.cohort !== "none" &&
                    DATA.cohorts[state.cohort] &&
                    DATA.cohorts[state.cohort].metric === mid;
  const onlyCode = host.getAttribute("data-only");
  if (onlyCode) rows = rows.filter(o => o.code === onlyCode);
  const horizontal = def.chart.indexOf("horizontal") === 0;

  const bars = rows.map(o => {
    const blank = o.v === null;
    const sel = selActive && DATA.cohorts[state.cohort].code === o.code;
    const canClick = clickable && !blank && o.v > 0 &&
                     (def.cohortCodes || []).includes(o.code) &&
                     cohortKeyFor(mid, o.code) !== null;
    const tt = joinClause([
      blank ? t("ui.bar_tooltip_suppressed",
                { label: labelOf(def), opt: optLabel(o) })
            : barTitle(def, o, o.v, base, context),
      sel ? t("ui.bar_selected") : "",
      (clickable && !canClick && !blank) ? t("ui.bar_nonselectable") : "",
    ], sepDash());
    const barCls = blank ? " bar-dgrey" : " " +
      (clickable && !canClick ? "bar-grey" : o.cls);
    if (horizontal) {
      const w = blank ? 10 : Math.round(o.v / max * 100);
      const gw = !blank && ghost ? Math.round(gv(o) / max * 100) : 0;
      const tick = sel ? '<span class="sel-tick"' + prov("frame:ui.selected_tick") + '> ' + esc(t("ui.selected_tick")) + "</span>" : "";
      const inner = '<span class="hlab">' + esc(optLabel(o)) + tick + '</span>' +
        '<span class="htrack">' +
        (gw ? '<span class="hghost" style="width:' + gw + '%" title="' +
              esc(t("ui.ghost_title", { n: gv(o), base: ghost._b,
                pct: Math.round(100 * gv(o) / Math.max(1, ghost._b)) })) +
              '"></span>' : '') +
        '<span class="hbar' + barCls + '" style="width:' + w +
        '%"></span></span>' +
        '<span class="hval">' + (blank ? supMark() : o.v) + "</span>";
      return canClick
        ? '<button type="button" class="hrowbtn"' + prov("frame:ui.bar_tooltip") +
          ' data-cohort="' + cohortKeyFor(mid, o.code) +
          '" aria-pressed="' + sel + '" title="' + esc(tt) + '">' + inner + "</button>"
        : '<div class="hrow' + (blank ? " cell-blank" : "") + '"' +
          prov("frame:ui.bar_tooltip") + ' title="' + esc(tt) + '">' +
          inner + "</div>";
    }
    const hpx = blank ? 22 : Math.max(o.v === 0 ? 3 : 10, Math.round(o.v / max * 138));
    const gpx = !blank && ghost ? Math.round(gv(o) / max * 138) : 0;
    const inner = '<span class="vval">' + (blank ? supMark() : o.v) + '</span>' +
      '<span class="vtrack">' +
      (gpx ? '<span class="vghost" style="height:' + gpx + 'px" title="' +
             esc(t("ui.ghost_title", { n: gv(o), base: ghost._b,
               pct: Math.round(100 * gv(o) / Math.max(1, ghost._b)) })) +
             '"></span>' : '') +
      '<span class="vbar' + barCls + '" style="height:' + hpx + 'px"></span></span>' +
      '<span class="vlab">' + esc(optLabel(o)) + (sel ? '<span class="sel-tick"' + prov("frame:ui.selected_tick") + '> ' + esc(t("ui.selected_tick")) + "</span>" : "") + "</span>";
    return canClick
      ? '<button type="button" class="vcolbtn"' + prov("frame:ui.bar_tooltip") +
        ' data-cohort="' + cohortKeyFor(mid, o.code) +
        '" aria-pressed="' + sel + '" title="' + esc(tt) + '">' + inner + "</button>"
      : '<div class="vcol' + (blank ? " cell-blank" : "") + '"' +
        prov("frame:ui.bar_tooltip") + ' title="' + esc(tt) + '">' +
        inner + "</div>";
  }).join("");
  html += '<div class="' + (horizontal ? "hchart" : "vchart") + '"' +
          prov("frame:ui.chart_aria") + ' role="img" aria-label="' +
          esc(t("ui.chart_aria", { label: labelOf(def) })) + '">' + bars + "</div>";
  if (ghost) html += '<p class="chart-note"' + prov("frame:ui.note_ghost") +
    '>' + esc(t("ui.note_ghost")) + "</p>";
  if (hasComposite && rows.some(o => o.code === "other_sports"))
    html += '<p class="chart-note"' + prov("frame:ui.note_other_sports") +
      '>' + esc(t("ui.note_other_sports")) + "</p>";
  if (note) html += '<p class="chart-note"' + prov("frame:ui.ranking_note") +
    '>' + esc(note) + "</p>";
  html += dataTable(def, res, context);
  sink(html);
}

/* PR-18 / D76: the visible no-report marker is language-neutral; its
   accessible name is the ui.table_suppressed frame (V4.13: now also on
   chart values, as visually hidden text). */
const supMark = () => '<span aria-hidden="true">—</span><span class="visually-hidden">' + esc(t("ui.table_suppressed")) + "</span>";
function dataTable(def, res, context) {
  // sheet 43 ui.table_summary / ui.table_caption; the caption keeps the
  // view descriptor after the metric title, as before.
  let h = '<details class="dtable"' + prov("frame:ui.table_caption") +
    '><summary>' + esc(t("ui.table_summary")) +
    "</summary><table><caption>" +
    esc(t("ui.table_caption",
          { label: labelOf(def) + " — " + viewDesc(context), n: res.b,
            multi: def.type === "multi" })) + "</caption>" +
    "<thead><tr><th scope='col'>" + esc(t("ui.th_answer")) +
    "</th><th scope='col'>" + esc(t("ui.th_responses")) +
    "</th></tr></thead><tbody>";
  def.opts.forEach((o, i) => {
    const v = res.v[i];
    const lbl = (isCy() && def.optsCy) ? def.optsCy[i] : o[1];
    h += "<tr><th scope='row' class='rowh'>" + esc(lbl) + "</th><td class='num'>" +
         (v === null ? esc(t("ui.table_suppressed")) : v) + "</td></tr>";
  });
  return h + "</tbody></table></details>";
}

/* ------------------------- stacked sport-frequency charts (build 010) --- */
/* D66: the legend text is SOURCED FROM THE WORKBOOK through the payload
   catalogue (welsh.stackLegend) \u2014 never re-typed in code. Only the
   colours, which carry no language, live here. */
const STACK_COLOURS = ["#c7ced2", "#6FA0B6", "#094B68", "#FA2A3C", "#8f9ba1"];
const STACK_SEGS = (CY.stackLegend || []).map((r, i) => (
  { label: r.en, cy: r.cy, c: STACK_COLOURS[i] || "#c7ced2" }));
const segLabel = sg => (isCy() && sg.cy) ? sg.cy : sg.label;
/* D70 (sheet 46): a stack row carries the STABLE OPTION CODE of its sport
   (r[3]); the display label resolves through the optsCy catalogue of
   sports_participated in the active language. */
const SPORT_DEF = DATA.metricDefs && DATA.metricDefs.sports_participated;
function sportLabel(code, fallback) {
  const i = SPORT_DEF ? SPORT_DEF.opts.findIndex(o => o[0] === code) : -1;
  if (i < 0) return fallback || code;
  return optLabel({ label: SPORT_DEF.opts[i][1],
                    cy: SPORT_DEF.optsCy && SPORT_DEF.optsCy[i] });
}
function stackLegend() {
  return '<div class="stack-legend"' + prov("catalogue:stackLegend") +
    '>' + STACK_SEGS.map((sg, i) =>
    '<span><i data-seg="' + i + '" style="background:' + sg.c + '"></i>' + esc(segLabel(sg)) + "</span>"
  ).join("") + "</div>";
}
function renderStack(host) {
  const ctx = host.getAttribute("data-stack");
  const s = dst();
  const data = s && !s.sup && s.stk ? s.stk[ctx] : null;
  /* D80: the explanatory note (data-sh-key) is static furniture inside a
     static card — bound by the static lane and swapped by renderStatic();
     the chart renders into the slot above it and the table into the slot
     below. The renderer resolves the same key through the layer. */
  const shKey = host.getAttribute("data-sh-key");
  const slot = shKey ? $(".stack-slot", host) : null;
  const tslot = shKey ? $(".stack-table-slot", host) : null;
  const note = shKey ? $(".stack-note", host) : null;
  if (note) { const p = $("[data-i18n]", note); if (p) p.textContent = staticStr(shKey);
    const rh = $(".rep-h", note); if (rh) { rh.textContent = cat("what_showing");
      if (DEV) rh.setAttribute("data-i18n-source", "catalogue:what_showing"); } }
  if (!data || !data.length) {
    if (slot) { slot.innerHTML = stateMsg("nd"); tslot.innerHTML = ""; note.hidden = true; }
    else host.innerHTML = stateMsg("nd");
    return;
  }
  if (note) note.hidden = false;
  const max = Math.max(1, ...data.map(r => r[2]));
  const bars = data.map(r => {
    const segs = r[1], base = r[2];
    const lab = sportLabel(r[3], r[0]);   // D70: code -> catalogue label
    const w = Math.max(4, Math.round(base / max * 100));
    const inner = segs.map((v, i) => {
      if (!v) return "";
      const sw = (v / base * 100).toFixed(2);
      return '<div class="stackseg" data-seg="' + i + '"' + prov("frame:ui.stack_tooltip") +
        ' style="width:' + sw + '%;background:' +
        STACK_SEGS[i].c + '" title="' +
        esc(t("ui.stack_tooltip", { sport: lab,
                                    seg: segLabel(STACK_SEGS[i]), n: v })) +
        '"></div>';
    }).join("");
    return '<div class="stackrow"' + prov("opts:sports_participated") +
      '><span class="hlab">' + esc(lab) +
      '</span><div class="stacktrack"><div class="stackbar" style="width:' + w +
      '%">' + inner + '</div></div><span class="hval">' + base + "</span></div>";
  }).join("");
  const chart = stackLegend() +
    '<div role="img" aria-label="' + esc(t("ui.stack_aria")) + '">' +
    bars + "</div>";
  // D71/PR-17: the caption states the count it renders, through the
  // numeral service as a definite count-NP (Y deg camp / Y gamp at one).
  const table = '<details class="dtable"' + prov("frame:ui.stack_table_caption") +
    '><summary>' + esc(t("ui.table_summary")) +
    "</summary><table><caption>" +
    esc(t("ui.stack_table_caption", { k: data.length, desc: viewDesc(false) })) +
    ".</caption><thead><tr><th scope='col'>" + esc(t("ui.stack_th_sport")) +
    "</th>" +
    STACK_SEGS.map(sg => "<th scope='col'>" + esc(segLabel(sg)) + "</th>").join("") +
    "<th scope='col'>" + esc(t("ui.stack_th_total")) +
    "</th></tr></thead><tbody>" +
    data.map(r => "<tr><th scope='row' class='rowh'>" +
      esc(sportLabel(r[3], r[0])) + "</th>" +
      r[1].map(v => "<td class='num'>" + v + "</td>").join("") +
      "<td class='num'>" + r[2] + "</td></tr>").join("") +
    "</tbody></table></details>";
  if (slot) { slot.innerHTML = chart; tslot.innerHTML = table; }
  else host.innerHTML = '<div class="chart-card">' + chart + table + "</div>";
}

/* ------------------- multi-choice co-selection chart (build 012) -------- */
function renderCoSelection(host, mid) {
  const def = DATA.metricDefs[mid];
  const s = st();               // the selected group's own state
  const res = s && !s.sup ? s.m[mid] : null;
  const selCode = DATA.cohorts[state.cohort].code;
  if (!res || res.s !== "ok") { host.innerHTML = ""; return; }
  const rows = def.opts
    .map((o, i) => ({ code: o[0], label: o[1], cy: def.optsCy && def.optsCy[i], v: res.v[i] }))
    .filter(o => o.code !== selCode && o.v !== null && o.v > 0)
    .sort((a, b) => b.v - a.v);
  if (!rows.length) { host.innerHTML = ""; return; }
  const max = Math.max(...rows.map(o => o.v));
  const bars = rows.map((o, i) =>
    '<div class="hrow"' + prov("frame:ui.cosel_tooltip") + ' title="' +
    esc(t("ui.cosel_tooltip", { opt: optLabel(o), n: o.v })) +
    '"><span class="hlab">' + esc(optLabel(o)) +
    '</span><span class="htrack"><span class="hbar ' +
    (i % 2 === 0 ? "bar-red" : "bar-blue") + '" style="width:' +
    Math.round(o.v / max * 100) + '%"></span></span><span class="hval">' +
    o.v + "</span></div>").join("");
  const selIdx = def.opts.findIndex(o => o[0] === selCode);
  const selOpt = selIdx > -1 ? def.opts[selIdx] : null;
  const selLabel = DATA.cohorts[state.cohort].optionLabel ||
                   (selOpt ? selOpt[1] : DATA.cohorts[state.cohort].label);
  const selCy = (selIdx > -1 && def.optsCy && def.optsCy[selIdx]) || "";
  host.innerHTML = '<div class="chart-card"><h4>' + esc(t("ui.cosel_heading")) +
    "</h4>" + '<p class="chart-base">' +
    esc(t("ui.cosel_base", { n: res.b,
                             answer: (isCy() && selCy) ? selCy : selLabel })) +
    "</p>" + '<div class="hchart">' + bars + "</div></div>";
}

/* ---------------------------------------------------------- row tables */
function renderRows(hostId, rows, cols) {
  const host = $(hostId);
  if (!host) return;
  if (!rows) { host.innerHTML = ""; return; }
  let h = '<div class="chart-card"><table style="width:100%;border-collapse:collapse;font-size:13.5px">' +
    "<thead><tr>" + cols.map(c => "<th style='text-align:left;border-bottom:2px solid var(--blue);padding:5px 8px'>" +
    esc(c) + "</th>").join("") + "</tr></thead><tbody>";
  for (const r of rows) h += r;
  host.innerHTML = h + "</tbody></table></div>";
}

/* ------------------------------------------------------------ rendering */
const GROUP_COHORTS = ["dy_yes", "ly_yes", "dl_yes", "ed_yes", "ws_yes"];
/* D59: a control's text comes from the payload's Welsh fields via the
   language state — never a per-control English literal. */
const optLabel = o => (isCy() && (o.labelCy || o.cy)) ? (o.labelCy || o.cy) : o.label;
const optDesc = o => (isCy() && o.descCy) ? o.descCy : o.desc;
const cohortLabel = c => (isCy() && c.labelCy) ? c.labelCy : c.label;
/* CAT-schema (v1.9): every metric definition carries labelCy — fed from
   the translator catalogue; pending values show the dev marker. */
const labelOf = d => (isCy() && d.labelCy) ? d.labelCy : d.label;
function renderRail() {
  const gsel = $("#f-group");
  if (gsel && !gsel.options.length) {
    const allP = DATA.filterOptions.gender.find(o => o.key === "all");
    const opts = ['<option value="none">' + esc(optLabel(allP)) + "</option>"];
    for (const k of GROUP_COHORTS) {
      const c = DATA.cohorts[k];
      if (c) opts.push('<option value="' + k + '">' + esc(cohortLabel(c)) + "</option>");
    }
    gsel.innerHTML = opts.join("");
  }
  if (gsel) gsel.value = GROUP_COHORTS.indexOf(state.cohort) > -1 ? state.cohort : "none";
  const sel = $("#f-scope");
  if (!sel.options.length)
    sel.innerHTML = DATA.filterOptions.scope.map(o =>
      '<option value="' + o.key + '"' + (o.avail === false ? " disabled" : "") + ">" +
      esc(optLabel(o) + (optDesc(o) ? " — " + optDesc(o) : "") +
          (o.avail === false ? " " + cat("not_reportable") : "")) +
      "</option>").join("");
  sel.value = state.scope;
  $("#f-gender").innerHTML = DATA.filterOptions.gender.map(o =>
    '<button type="button" data-g="' + o.key + '" aria-pressed="' + (state.gender === o.key) +
    '">' + esc(optLabel(o)) + "</button>").join("");
  const c = cohortDef();
  $("#f-cohort").innerHTML = c
    ? '<span class="chip">' + esc(cohortLabel(c)) +
      '<button type="button" id="chip-x" aria-label="' +
      esc(t("ui.chip_remove")) + '">×</button></span>'
    : '<span class="chip-none">' + esc(t("ui.chip_none")) + "</span>";
  const s = st();
  // v2 (Sport Wales feedback): coverage badge removed; pupil-response wording
  $("#rail-base").innerHTML = s && !s.sup
    ? (isCy()
        ? "<strong>" + s.b + "</strong> " +
          esc(uiStr(s.b === 1 ? "response_included" : "responses_included"))
        : "<strong>" + s.b + "</strong> pupil " + (s.b === 1 ? "response" : "responses") +
          " included")
    : "<strong>—</strong> " + esc(cat("not_enough"));
}

function renderBanner() {
  const s = st();
  const desc = descOf(s);
  $("#vb-desc").textContent = desc;
  $("#vb-base").innerHTML = s && !s.sup
    ? (isCy()
        ? "<strong>" + s.b + "</strong> " +
          esc(uiStr(s.b === 1 ? "response_included" : "responses_included"))
        : "<strong>" + s.b + "</strong> pupil " + (s.b === 1 ? "response" : "responses") +
          " included")
    : esc(cat("not_enough"));
  // print footer (section 7.3 / 22.5)
  const pf = $("#pf-view");
  // D50: the print footer tests the typed record, never an English literal
  if (pf) pf.textContent = s ? " · " + descOf(s) : "";
  // collapsed mobile rail summary (§3.3: no duplicated respondent base —
  // the banner directly above already shows it)
  const rt = $("#rail-toggle");
  if (rt) rt.textContent = t("ui.rail_toggle", { desc: descOf(s) });
}

function paywallBox(bodyKey) {
  // D73: the disclosure-control bodies are catalogue records with
  // exception id Q17 (English in both languages until the legal
  // translation arrives) — never code literals.
  const d = document.createElement("div");
  d.className = "paywall-box";
  if (DEV) d.setAttribute("data-i18n-source", "frame:" + bodyKey);
  d.innerHTML = '<div class="t">' + esc(t("ui.suppressed_title")) + "</div>" +
    '<div class="b">' + esc(t(bodyKey)) + "</div>";
  return d;
}
function renderSuppressed() {
  const supp = viewSup();
  for (const el of $$(".module.dynamic")) {
    el.classList.remove("paywalled");
    const old = $(".paywall-box", el);
    if (old) old.remove();
    el.inert = false;
    if (supp) {
      el.classList.add("paywalled");
      el.inert = true;
      el.appendChild(paywallBox("ui.gdpr_body_full"));
    }
  }
}

const COSEL = { most_important: "f6", would_do_more_if: "f7" };
function renderModules() {
  const s = dst();
  if (!s) return;
  const paras = m => m && m.s === "ok" && m.p.length
    ? m.p.map(p => {
        if (isCy()) {
          if (p.c) return '<p class="k-' + esc(p.k) + '">' + esc(p.c) + "</p>";
          return '<p class="k-' + esc(p.k) + ' cy-missing" title="Heb ei ' +
            'gyfieithu eto — dangosir y Saesneg">' + esc(p.t) + "</p>";
        }
        return '<p class="k-' + esc(p.k) + '">' + esc(p.t) + "</p>";
      }).join("") : "";
  const availMap = {};
  (s.avail || []).forEach(a => { availMap[a[0]] = a[1]; });
  const supView = viewSup();
  /* v4 (build 011, owner decision): disability / learning difficulty
     three-tier display - the mode is pre-computed per view (s.dlm) */
  const dlEl = $('[data-module="n_dl"]');
  if (dlEl) {
    const dm = (availMap["n_dl"] === "insufficient" && !supView)
      ? DATA.states["whole|all|none"].dlm : s.dlm;
    const sep = $(".dl-sep", dlEl), comb = $(".dl-comb", dlEl);
    if (sep) sep.style.display = dm === "sep" ? "" : "none";
    if (comb) comb.style.display = dm === "comb" ? "" : "none";
  }
  for (const el of $$("[data-module]")) {
    const id = el.getAttribute("data-module");
    const alsoId = el.getAttribute("data-also");
    const m = s.mod[id];
    const also = alsoId ? s.mod[alsoId] : null;
    const nar = $(".mod-narrative", el);
    /* D80: a module with a keyed heading (data-nh-key) carries a STATIC
       reported block in the markup — heading (and the keyed also-heading,
       data-also-h-key) bound by the static lane and swapped by
       renderStatic(); narrative renders into its body slots. The renderer
       resolves the same keys through the layer. */
    const nhKey = el.getAttribute("data-nh-key");
    const alsoKey = el.getAttribute("data-also-h-key");
    const rep = nhKey && nar ? $(".reported", nar) : null;
    const body = rep ? $(".rep-body", rep) : null;
    const bodyAlso = rep ? $(".rep-body-also", rep) : null;
    const alsoH = rep ? $(".rep-also", rep) : null;
    if (rep) {
      const h = $(".rep-h", rep); if (h) h.textContent = staticStr(nhKey);
      if (alsoH && alsoKey) alsoH.textContent = staticStr(alsoKey);
    }
    const fill = (main, alsoHtml) => {
      if (!rep) return;
      body.innerHTML = main || "";
      if (bodyAlso) bodyAlso.innerHTML = alsoHtml || "";
      if (alsoH) alsoH.hidden = !alsoHtml;
      if (bodyAlso) bodyAlso.hidden = !alsoHtml;
      rep.hidden = !main && !alsoHtml;
    };
    let inner = paras(m);
    const alsoInner = paras(also);
    if (alsoInner && !rep)
      inner += "<h4 style='margin:10px 0 6px'" + prov("static:" + alsoKey) + ">" +
               esc(alsoKey ? staticStr(alsoKey) : "") + "</h4>" + alsoInner;
    if (!inner && !alsoInner) {
      /* v3 (build 010, owner decision): a section held back for disclosure
         control shows a suppression message instead of disappearing */
      if (availMap[id] === "insufficient" && !supView) {
        /* v5 (build 012): paywall the single module - whole-school content
           greyed underneath, message box on top, never the small group */
        el.classList.remove("omitted");
        el.classList.add("paywalled");
        el.inert = true;
        FORCE_WHOLE = true;
        const w = DATA.states["whole|all|none"];
        const wm = w.mod[id];
        if (rep) fill(wm && wm.s === "ok" && wm.p.length ? paras(wm) : "", "");
        else if (nar) nar.innerHTML = wm && wm.s === "ok" && wm.p.length
          ? '<div class="reported"><div class="rep-h"' +
            prov("catalogue:what_showing") + ">" + esc(cat("what_showing")) +
            "</div>" + paras(wm) + "</div>" : "";
        for (const ch of $$("[data-chart]", el)) renderChart(ch, ch.getAttribute("data-chart"));
        for (const sk of $$("[data-stack]", el)) renderStack(sk);
        FORCE_WHOLE = false;
        if (!$(".paywall-box", el)) el.appendChild(
          paywallBox("ui.gdpr_body_module"));
        continue;
      }
      el.classList.add("omitted");
      if (rep) fill("", ""); else if (nar) nar.innerHTML = "";
      continue;
    }
    if (!supView) { el.classList.remove("paywalled"); el.inert = false;
      const pb = $(".paywall-box", el); if (pb) pb.remove(); }
    el.classList.remove("omitted");
    if (rep) fill(paras(m), alsoInner);
    else if (nar) {
      nar.innerHTML = '<div class="reported"><div class="rep-h"' +
        prov("catalogue:what_showing") + ">" + esc(cat("what_showing")) +
        "</div>" + inner + "</div>";
    }
    for (const ch of $$("[data-chart]", el)) {
      const mid = ch.getAttribute("data-chart");
      /* v5 (build 012): multi-choice co-selection - the source chart keeps
         only the selected bar, and a second chart appears beneath showing
         what else those pupils selected */
      const co = COSEL[mid] === id && !supView && state.cohort !== "none" &&
                 DATA.cohorts[state.cohort] &&
                 DATA.cohorts[state.cohort].metric === mid;
      if (co) ch.setAttribute("data-only", DATA.cohorts[state.cohort].code);
      else ch.removeAttribute("data-only");
      renderChart(ch, mid);
      let cw = $(".cosel-wrap", el);
      if (co) {
        if (!cw) { cw = document.createElement("div");
          cw.className = "cosel-wrap"; ch.insertAdjacentElement("afterend", cw); }
        renderCoSelection(cw, mid);
      } else if (cw) cw.remove();
    }
    for (const sk of $$("[data-stack]", el)) renderStack(sk);
  }
  // v2 (Sport Wales feedback): dedicated boy/girl comparison charts removed
  const cols = c => c;
  /* v3 (build 010): year-group participation as stacked setting bars.
     D66/D70 (sheet 46): the segment labels are SOURCED from the optsCy
     catalogue of participation_settings — never re-typed; only the
     colours, which carry no language, live here. */
  const SETTING_COLOURS = ["#094B68", "#FA2A3C", "#6FA0B6", "#4A6472"];
  const PS_DEF = DATA.metricDefs.participation_settings;
  const SETTING_SEGS = (PS_DEF ? PS_DEF.opts : []).map((o, i) => (
    { code: o[0], label: o[1], cy: PS_DEF.optsCy && PS_DEF.optsCy[i],
      c: SETTING_COLOURS[i] || "#4A6472" }));
  /* D70: derived rows carry the stable scope key (yk); the display label
     resolves through filterOptions labelCy, sex through gender labelCy. */
  const rowYear = r => { const so = scopeOpt(r.yk); return so ? optLabel(so) : r.y; };
  const sexOpt = k => DATA.filterOptions.gender.find(o => o.key === k);
  const rowSex = (r, k) => rowYear(r) + " — " + optLabel(sexOpt(k));
  const settingLegend = () => '<div class="stack-legend">' + SETTING_SEGS.map((sg, i) =>
    '<span><i data-seg="s' + i + '" style="background:' + sg.c + '"></i>' + esc(segLabel(sg)) + "</span>"
  ).join("") + "</div>";
  const settingBar = (lab, c, b, sup, max) => {
    if (sup) return '<div class="stackrow"' + prov("catalogue:filterOptions") +
      '><span class="hlab">' + lab +
      '</span><div class="stacktrack"><div class="stackbar" style="width:12%">' +
      '<div class="stackseg" style="width:100%;background:#c7ced2"' +
      prov("frame:ui.table_suppressed") + ' title="' +
      esc(t("ui.table_suppressed")) + '">' +
      '</div></div></div><span class="hval">' + noRep() + "</span></div>";
    if (!c) return "";
    const tot = c.reduce((a, v) => a + v, 0);
    if (!tot) return '<div class="stackrow"><span class="hlab">' + lab +
      '</span><div class="stacktrack"></div><span class="hval">' + b + "</span></div>";
    const w = Math.max(4, Math.round(tot / max * 100));
    const inner = c.map((v, i) => v ? '<div class="stackseg" data-seg="s' + i + '"' +
      prov("frame:ui.stack_tooltip") + ' style="width:' +
      (v / tot * 100).toFixed(2) + '%;background:' + SETTING_SEGS[i].c + '" title="' +
      esc(t("ui.stack_tooltip", { sport: lab.replace(/<[^>]*>/g, ""),
                                  seg: segLabel(SETTING_SEGS[i]), n: v })) +
      '"></div>' : "").join("");
    return '<div class="stackrow"' + prov("catalogue:filterOptions") +
      '><span class="hlab">' + lab +
      '</span><div class="stacktrack"><div class="stackbar" style="width:' + w +
      '%">' + inner + '</div></div><span class="hval">' + b + "</span></div>";
  };
  const f2host = $("#rows-f2");
  if (f2host) {
    if (!s.rows.f2) { f2host.innerHTML = ""; } else {
      const max = Math.max(1, ...s.rows.f2.map(r =>
        r.c ? r.c.reduce((a, v) => a + v, 0) : 0));
      const bars = s.rows.f2.map(r =>
        settingBar(esc(rowYear(r)), r.c, r.b, r.sup, max)).join("");
      const f2table = '<details class="dtable"' +
        prov("frame:ui.stack_caption_year") + '><summary>' +
        esc(t("ui.table_summary")) + "</summary><table>" +
        "<caption>" + esc(t("ui.stack_caption_year")) +
        "</caption><thead><tr><th scope='col'>" +
        esc(t("ui.th_year_group")) + "</th>" +
        SETTING_SEGS.map(sg => "<th scope='col'>" + esc(segLabel(sg)) + "</th>").join("") +
        "<th scope='col'>" + esc(t("ui.th_base")) +
        "</th></tr></thead><tbody>" +
        s.rows.f2.map(r => {
          if (r.sup) return "<tr><th scope='row' class='rowh'>" + esc(rowYear(r)) +
            "</th><td class='num' colspan='5'>" + noRep() + "</td></tr>";
          const c = r.c || [null, null, null, null];
          return "<tr><th scope='row' class='rowh'>" + esc(rowYear(r)) + "</th>" +
            c.map(v => "<td class='num'>" + (v == null ? "\u2014" : v) + "</td>").join("") +
            "<td class='num'>" + (r.b || "\u2014") + "</td></tr>";
        }).join("") + "</tbody></table></details>";
      f2host.innerHTML = '<div class="chart-card"><h4>' +
        esc(t("ui.stack_caption_year").split(". ")[0]) + "</h4>" +
        '<p class="chart-base">' + esc(t("ui.stack_note")) + "</p>" +
        settingLegend() + bars + f2table + "</div>";
    }
  }
  const e4host = $("#rows-e4");
  if (e4host) {
    if (!s.rows.e4) { e4host.innerHTML = ""; } else {
      let max = 1;
      for (const r of s.rows.e4)
        for (const c of [r.bc, r.gc])
          if (c) max = Math.max(max, c.reduce((a, v) => a + v, 0));
      const bars = s.rows.e4.map(r =>
        settingBar(esc(rowSex(r, "boy")), r.bc, r.bcb, r.bsup, max) +
        settingBar(esc(rowSex(r, "girl")), r.gc, r.gcb, r.gsup, max)).join("");
      const e4row = (lab, c, b, sup) => {
        if (sup) return "<tr><th scope='row' class='rowh'>" + lab +
          "</th><td class='num' colspan='5'>" + noRep() + "</td></tr>";
        if (!c) return "";
        return "<tr><th scope='row' class='rowh'>" + lab + "</th>" +
          c.map(v => "<td class='num'>" + (v == null ? "\u2014" : v) + "</td>").join("") +
          "<td class='num'>" + (b || "\u2014") + "</td></tr>";
      };
      const e4table = '<details class="dtable"' +
        prov("frame:ui.stack_caption_sex") + '><summary>' +
        esc(t("ui.table_summary")) + "</summary><table>" +
        "<caption>" + esc(t("ui.stack_caption_sex")) +
        "</caption><thead><tr><th scope='col'>" + esc(t("ui.th_group")) +
        "</th>" +
        SETTING_SEGS.map(sg => "<th scope='col'>" + esc(segLabel(sg)) + "</th>").join("") +
        "<th scope='col'>" + esc(t("ui.th_base")) +
        "</th></tr></thead><tbody>" +
        s.rows.e4.map(r =>
          e4row(esc(rowSex(r, "boy")), r.bc, r.bcb, r.bsup) +
          e4row(esc(rowSex(r, "girl")), r.gc, r.gcb, r.gsup)).join("") +
        "</tbody></table></details>";
      e4host.innerHTML = '<div class="chart-card"><h4>' +
        esc(t("ui.stack_caption_sex").split(". ")[0]) + "</h4>" +
        '<p class="chart-base">' + esc(t("ui.stack_note")) + "</p>" +
        settingLegend() + bars + e4table + "</div>";
    }
  }
  renderRows("#rows-g4", s.rows.g4 && s.rows.g4.map(r => {
    const cell = c => c == null ? "<td style='padding:5px 8px'>—</td>"
      : "<td style='padding:5px 8px'>" + t("ui.of", { n: c[0], b: c[1] }) + "</td>";
    if (r.sup) return "<tr><td style='padding:5px 8px;font-weight:600'>" + esc(rowYear(r)) +
      "</td><td colspan='4' style='padding:5px 8px;color:#5F6E76'>" +
      esc(t("ui.table_suppressed")) + "</td></tr>";
    const cs = r.all || [null, null, null, null];
    return "<tr><td style='padding:5px 8px;font-weight:600'>" + esc(rowYear(r)) + "</td>" +
      cs.map(cell).join("") + "</tr>";
  }), [t("ui.th_year_group"), t("ui.g4_th_pe"), t("ui.g4_th_school_clubs"),
       t("ui.g4_th_community"), t("ui.g4_th_other")]);

  // f14 mini comparison
  const f14 = $("#f14-table");
  if (f14) {
    const cur = s.m.sports_participated, un = s.m.unmet_demand;
    if (cur && cur.s === "ok" && un && un.s === "ok") {
      const defC = DATA.metricDefs.sports_participated, defU = DATA.metricDefs.unmet_demand;
      const top5 = (def, res) => def.opts.map((o, i) => (
          { c: o[0], label: o[1], cy: def.optsCy && def.optsCy[i], v: res.v[i] }))
        .filter(o => o.v > 0 && o.c !== "other_sports" &&
                (DATA.tier2Codes || []).indexOf(o.c) === -1)
        .sort((a, b) => b.v - a.v).slice(0, 5);
      const rowsC = top5(defC, cur), rowsU = top5(defU, un);
      f14.innerHTML = '<div class="chart-card"><div class="pairwrap"><div><h5' +
        prov("frame:ui.f14_most") + '>' + esc(t("ui.f14_most")) + "</h5>" +
        '<div class="hchart"' + prov("opts:sports_participated") + '>' +
        rowsC.map(o => '<div class="hrow"><span class="hlab">' + esc(optLabel(o)) +
        '</span><span class="htrack"><span class="hbar" style="width:' +
        Math.round(o.v / rowsC[0].v * 100) + '%"></span></span><span class="hval">' + o.v +
        "</span></div>").join("") + '</div></div><div><h5' +
        prov("frame:ui.f14_unmet") + '>' + esc(t("ui.f14_unmet")) + "</h5>" +
        '<div class="hchart"' + prov("opts:unmet_demand") + '>' +
        rowsU.map(o => '<div class="hrow"><span class="hlab">' + esc(optLabel(o)) +
        '</span><span class="htrack"><span class="hbar g" style="width:' +
        Math.round(o.v / rowsU[0].v * 100) + '%"></span></span><span class="hval">' + o.v +
        "</span></div>").join("") + "</div></div></div></div>";
    } else f14.innerHTML = "";
  }
}

function h1Para(e) {
  const en = typeof e === "string" ? e : e.t;
  if (isCy() && typeof e === "object" && e.c)
    return "<p" + prov("narrative:h1") + ">" + esc(e.c) + "</p>";
  if (isCy())
    return '<p class="cy-missing"' + prov("handoff:pending") +
           ' title="Heb ei gyfieithu eto — dangosir y ' +
           'Saesneg">' + esc(en) + "</p>";
  return "<p" + prov("narrative:h1") + ">" + esc(en) + "</p>";
}
function h2Item(e) {
  const t = typeof e === "string" ? e : e.t;
  let body = t, missing = false;
  if (isCy() && typeof e === "object") {
    if (e.c) body = e.c;                                  // generated
    else if (e.g && CY.handoff && CY.handoff[e.g]) body = CY.handoff[e.g];
    else missing = true;                                  // translator lane
  } else if (isCy()) missing = true;
  const cls = missing ? ' class="cy-missing"' + prov("handoff:pending") +
              ' title="Heb ei gyfieithu eto — ' +
              'dangosir y Saesneg"' : prov("narrative:h2");
  return "<li" + cls + " style='margin-bottom:8px'>" + esc(body) + "</li>";
}
const EN = (DATA.welsh && DATA.welsh.uiEn) || {};
const cat = k => (isCy() && (CY.handoff[k] || CY.ui[k]))
  ? (CY.handoff[k] || CY.ui[k]) : (EN[k] || k);
function renderClosing() {
  const s = dst();
  if (!s) {
    if (WHOLE_SUP) {
      $("#h1-view").textContent = t("ui.banner_showing",
                                    { desc: descOf(DATA.states["whole|all|none"]), n: DATA.buildMetadata.acceptedRows });
      for (const id of ["#h1-an", "#h1-ev", "#h1-ll", "#h1-en"]) $(id).innerHTML = "<p>" + esc(t("ui.closing_none")) + "</p>";
      $("#h2-list").innerHTML = "";
    }
    return;
  }
  // sheet 43 ui.banner_showing: one typed frame, numeral service on the
  // count slot, participle agreement handled by the frame's N = 1 form.
  $("#h1-view").textContent = t("ui.banner_showing",
                                { desc: descOf(s), n: s.b });
  for (const [k, id] of [["an", "#h1-an"], ["ev", "#h1-ev"], ["ll", "#h1-ll"], ["en", "#h1-en"]]) {
    $(id).innerHTML = (s.h1[k] && s.h1[k].length)
      ? s.h1[k].map(h1Para).join("")
      : "<p>" + esc(t("ui.closing_none")) + "</p>";
  }
  $("#h2-list").innerHTML = s.h2.map(h2Item).join("");
}

/* v2.3 sheet 53: a profile DATA value shown in Welsh when the workbook
   carries its Welsh form; otherwise the value is data and stays as is. */
const NAMES = () => (CY.names) || {};
const nameOf = v => (isCy() && NAMES()[v]) ? NAMES()[v] : v;
function renderProfile() {
  const b = DATA.buildMetadata, sc = DATA.school;
  setFrame($("#intro-sentence"), "ui.intro_sentence",
    { school: sc.name, n: b.acceptedRows, first: sc.years[0], last: sc.years[sc.years.length - 1] });
  // v6 (Framework v2.8, EN-07): the year range is the school's — the
  // {first}/{last} slots the intro sentence already carries
  setFrame($("#faq-included"), "ui.faq_included",
    { school: sc.name, n: b.acceptedRows, first: sc.years[0], last: sc.years[sc.years.length - 1] });
  setFrame($("#faq-missing"), "ui.faq_missing", { n: b.acceptedRows });
  $$(".dyn-count").forEach(el => { el.textContent = b.acceptedRows; });
  $$(".dyn-rows").forEach(el => { el.textContent = b.sourceRows; });
  // v2 (Sport Wales feedback): expanded school information section —
  // V4.11: every heading is a sheet-43 frame, every data value passes
  // through the proper-names table (assessment §8)
  const cell = (k, v, pendingKey) => {
    const pend = framePending(k);
    return "<tr><td" + (pend ? ' class="cy-missing" lang="en"' : "") + prov((pend ? "frame:pending:" : "frame:") + k) + ">" +
      esc(t(k)) + "</td><td>" + esc(String(v)) + "</td></tr>";
  };
  $("#overview-table").innerHTML =
    cell("ui.profile_school_name", sc.name) +
    cell("ui.profile_la", nameOf(sc.localAuthority)) +
    cell("ui.profile_rsp", nameOf(sc.regionalSportPartnership)) +
    cell("ui.profile_stages", sc.schoolStages) +
    cell("ui.appendix_total_responses", b.acceptedRows) +
    cell("ui.profile_fieldwork", nameOf(sc.fieldworkDates));
  // static whole-school profile (never changes with filters); single colour
  // per the Sport Wales feedback so colours are not read as meaningful
  const w = DATA.states["whole|all|none"];
  const host = $("#static-profile");
  /* v3 (build 010, owner decision): profile charts alternate red and blue
     like every other chart; they are simply not selectable */
  const mkChart = (mid, h) => {
    const def = DATA.metricDefs[mid], res = w.m[mid];
    const rows = def.opts.map((o, i) => ({ label: o[1], cy: def.optsCy && def.optsCy[i],
                                           v: res.v[i],
                                           cls: ["bar-red", "bar-blue"][i % 2] }));
    const mx = Math.max(1, ...rows.map(o => o.v || 0));
    return '<div class="chart-card"><h4' + prov("label:" + mid) + '>' + esc(labelOf(def)) +
      '</h4><p class="chart-base"' + prov("frame:ui.base_line_complete") + '>' +
      esc(t("ui.base_line_complete", { n: res.b })) +
      "</p><div class=\"vchart\">" +
      rows.map(o => '<div class="vcol"><span class="vval">' + (o.v === null ? "—" : o.v) +
        '</span><span class="vbar ' + o.cls + '" style="height:' +
        Math.max(3, Math.round((o.v || 0) / mx * 120)) + 'px"></span><span class="vlab">' +
        esc(optLabel(o)) + "</span></div>").join("") + "</div>" + (h || "") + "</div>";
  };
  if (w.sup) {
    // V6.0 (owner instruction, 22 Sep 2026): a school with fewer than five
    // accepted responses still receives its report. Its whole-school view is
    // suppressed by the rule of five, so the profile charts, the year-range
    // sentence and the any-activity headline give way to the existing
    // suppression message (msg.suppressed_* frames, both languages); the
    // school information table and the metadata table stay.
    host.innerHTML = stateMsg("sup");
    const note = $("#overview-note");
    if (note) { note.innerHTML = stateMsg("sup"); note.classList.remove("cy-missing"); note.removeAttribute("lang"); note.removeAttribute("title"); }
    const anyS = $("#any-activity-note");
    if (anyS) anyS.innerHTML = "";
    const extra = $("#profile-extra");
    if (extra) extra.innerHTML = "";
    $("#meta-table").innerHTML =
      cell("ui.meta_survey_year", sc.surveyYear) +
      cell("ui.meta_report_version", t("ui.meta_version_value", { report: DATA.reportVersion, schema: DATA.schemaVersion })) +
      cell("ui.meta_pipeline", b.pipelineVersion) +
      cell("ui.meta_suppression", b.suppressionModel) +
      cell("ui.meta_generated", b.generatedAt) +
      cell("ui.meta_checksum", b.sourceChecksum.slice(0, 16) + "…") +
      cell("ui.meta_weighting", t("ui.meta_weighting_value"));
    return;
  }
  host.innerHTML = mkChart("responses_by_year") + mkChart("responses_by_gender");
  const yr = w.m.responses_by_year;
  const yPairs = DATA.metricDefs.responses_by_year.opts.map((yo, i) => [yo[1], yr.v[i]]);
  const hi = yPairs.reduce((a, b) => (b[1] || 0) > (a[1] || 0) ? b : a);
  const lo = yPairs.reduce((a, b) => (b[1] || 0) < (a[1] || 0) ? b : a);
  const yLabel = en => { const o = DATA.filterOptions.scope.find(x => x.label === en); return (isCy() && o && o.labelCy) ? o.labelCy : en; };
  // V6.0 (EN-11, owner decision 22 Sep 2026): a school with a year group inside
  // its range that has no accepted response takes the variant frame (the same
  // sentence without "All"); the pipeline sets school.yearsGap from the profile
  setFrame($("#overview-note"), sc.yearsGap ? "ui.overview_note_gap" : "ui.overview_note",
    { hi: yLabel(hi[0]), hin: hi[1], lo: yLabel(lo[0]), lon: lo[1],
      first: sc.years[0], last: sc.years[sc.years.length - 1] });   // v6 (EN-06)
  renderProfileExtra(w);
  const anyN = $("#any-activity-note");
  if (anyN) {
    anyN.innerHTML = '<p class="any-activity-p"></p><p class="chart-note headline-note"></p>';
    const p1 = anyN.querySelector(".any-activity-p"), p2 = anyN.querySelector(".headline-note");
    setFrame(p1, "ui.any_activity", { n: DATA.anyActivity, base: b.acceptedRows,
      pct: Math.round(100 * DATA.anyActivity / b.acceptedRows) });
    p1.innerHTML = "<strong>" + p1.innerHTML + "</strong>";
    setFrame(p2, "ui.any_activity_note");
  }
  $("#meta-table").innerHTML =
    cell("ui.meta_survey_year", sc.surveyYear) +
    cell("ui.meta_report_version", t("ui.meta_version_value", { report: DATA.reportVersion, schema: DATA.schemaVersion })) +
    cell("ui.meta_pipeline", b.pipelineVersion) +
    cell("ui.meta_suppression", b.suppressionModel) +
    cell("ui.meta_generated", b.generatedAt) +
    cell("ui.meta_checksum", b.sourceChecksum.slice(0, 16) + "…") +
    cell("ui.meta_weighting", t("ui.meta_weighting_value"));
}

function renderAppendices() {
  const s = dst();
  const host = $("#appendices");
  if (!s) { host.innerHTML = ""; return; }
  // sheet 43: every appendix group heading is a typed frame (UI-DYN-18)
  const groups = [
    [t("ui.appendix_sports"), ["sports_participated"]],
    [t("ui.appx_settings_freq"), ["participation_settings", "sports_pe", "pe_freq",
      "sports_school_club", "school_club_freq", "sports_community_club",
      "community_club_freq", "sports_other_setting", "other_setting_freq"]],
    [t("ui.appx_latent"), ["sports_wanted"]],
    [t("ui.appx_unmet"), ["unmet_demand"]],
    [t("ui.appx_more_if"), ["would_do_more_if"]],
    [t("ui.appx_matters"), ["most_important"]],
    [t("ui.appx_voice"), ["join_in_easily", "enjoy_pe", "enjoy_school_clubs",
      "enjoy_community_clubs", "enjoy_other_settings", "ideas_listened",
      "confidence_try_new", "confidence_learn_skill", "confidence_try_again",
      "confidence_new_place", "pe_feel_healthy", "pe_feel_confident", "pe_feel_ready"]],
    [t("ui.appx_inclusion"), ["responses_by_year", "responses_by_gender",
      "disability_condition", "learning_difficulty", "take_part_method",
      "welsh_speaking", "welsh_when_playing_sport"]],
    // V4.18: the Club Sports section and its appendix table were removed
    // (owner instruction, 22 Sep 2026); its appendix heading frame is DEPRECATED on sheet 43
  ];
  const withGender = state.gender === "all";
  const bs = DATA.states[state.scope + "|boy|" + state.cohort];
  const gs = DATA.states[state.scope + "|girl|" + state.cohort];
  let h = "";
  for (const [gname, mids] of groups) {
    let inner = "";
    for (const mid of mids) {
      const def = DATA.metricDefs[mid];
      const { res, context } = metricFor(mid);
      if (!res) continue;
      if (res.s !== "ok") {
        inner += "<h4 style='margin:12px 0 4px'" + prov("label:" + mid) +
          ">" + esc(labelOf(def)) + "</h4>" + stateMsg(res.s);
        continue;
      }
      const gCols = withGender && bs && !bs.sup && gs && !gs.sup &&
                    bs.m[mid].s === "ok" && gs.m[mid].s === "ok";
      let tt = "<h4 style='margin:12px 0 4px'" + prov("label:" + mid) +
        ">" + esc(labelOf(def)) + "</h4>" +
        "<table><caption" + prov("frame:ui.appx_caption_base") + ">" +
        esc(t("ui.appx_caption_base", { b: res.b })) +
        (def.type === "multi" ? multiSeg() : "") +
        (gCols ? " · " + t("ui.th_boys") + ": " + bs.m[mid].b +
                 " · " + t("ui.th_girls") + ": " + gs.m[mid].b : "") +
        ".</caption><thead><tr><th scope='col'>" + esc(t("ui.th_answer")) +
        "</th><th scope='col'>" + esc(t("ui.th_all")) + "</th>" +
        (gCols ? "<th scope='col'>" + esc(t("ui.th_boys")) +
                 "</th><th scope='col'>" + esc(t("ui.th_girls")) + "</th>" : "") +
        "</tr></thead><tbody>";
      def.opts.forEach((o, i) => {
        const v = res.v[i];
        if (def.type === "multi" && (v === 0 || v === null) &&
            (!gCols || (!bs.m[mid].v[i] && !gs.m[mid].v[i]))) return;
        tt += "<tr><th scope='row' class='rowh'>" +
             esc(optLabel({ label: o[1], cy: def.optsCy && def.optsCy[i] })) +
             "</th><td class='num'>" +
             (v === null ? noRep() : v) + "</td>" +
             (gCols ? "<td class='num'>" +
                      (bs.m[mid].v[i] === null ? noRep() : bs.m[mid].v[i]) +
                      "</td><td class='num'>" +
                      (gs.m[mid].v[i] === null ? noRep() : gs.m[mid].v[i]) +
                      "</td>" : "") + "</tr>";
      });
      inner += tt + "</tbody></table>";
    }
    h += '<details class="dtable"' + prov("catalogue:appendix") +
      '><summary>' + esc(gname) + "</summary>" + inner + "</details>";
  }
  host.innerHTML = h;
}


/* ---------------------- v2 static profile, variation, completeness ------ */
function renderProfileExtra(w) {
  const host = $("#profile-extra");
  if (!host) return;
  const bar = mid => {
    const def = DATA.metricDefs[mid], res = w.m[mid];
    if (!res || res.s !== "ok") return "";
    const rows = def.opts.map((o, i) => ({ label: o[1], cy: def.optsCy && def.optsCy[i],
                                           v: res.v[i],
                                           cls: ["bar-red", "bar-blue"][i % 2] }));
    const mx = Math.max(1, ...rows.map(o => o.v || 0));
    return '<div class="chart-card"><h4' + prov("label:" + mid) + '>' + esc(labelOf(def)) +
      '</h4><p class="chart-base"' + prov("frame:ui.base_line") + '>' +
      esc(t("ui.base_line", { n: res.b })) + '</p><div class="vchart">' +
      rows.map(o => '<div class="vcol"><span class="vval">' + (o.v === null ? "—" : o.v) +
        '</span><span class="vbar ' + o.cls + '" style="height:' +
        Math.max(3, Math.round((o.v || 0) / mx * 110)) + 'px"></span><span class="vlab">' +
        esc(optLabel(o)) + "</span></div>").join("") + "</div></div>";
  };
  /* v3 (build 010, feedback row 6): disability and learning-difficulty
     charts kept; disability percentage table removed; Welsh language shown
     as a bar chart with the free-school-meals context beside it */
  const fp = k => (framePending(k) ? ' class="cy-missing" lang="en"' : "") + prov((framePending(k) ? "frame:pending:" : "frame:") + k);
  const fsmCard = '<div class="chart-card"><h4' + fp("ui.fsm_context_title") + '>' + esc(t("ui.fsm_context_title")) +
    "</h4><p" + fp("ui.fsm_context_body") + ">" +
    esc(t("ui.fsm_context_body", { value: t("ui.fsm_context_value") })) + "</p></div>";
  /* v5 (build 012, owner hard rule): every high-level ethnicity category
     from the survey, exact counts, zeros shown, nobody combined. This
     section is unfiltered and is not suppressed. */
  const ep = DATA.buildMetadata.ethnicityProfile || [];
  /* v2.7: the profile's long labels have their own Welsh (sheet 23,
     buildMetadata.ethnicityProfileCy, one entry per profile row, built
     fail-loud) — until V4.14 the client matched them against the chart's
     short options and showed English in Welsh mode for four rows */
  const epCy = DATA.buildMetadata.ethnicityProfileCy || [];
  const ethLabel = (en, i) => (isCy() && epCy[i]) ? epCy[i] : en;
  const ethTable = '<h4 style="margin:12px 0 4px"' + fp("ui.eth_heading") + '>' + esc(t("ui.eth_heading")) +
    '</h4><table class="var-table"' + prov("opts:ethnicity_group") +
    '><thead><tr>' +
    "<th" + fp("ui.eth_col_group") + ">" + esc(t("ui.eth_col_group")) + "</th><th style='text-align:right'" + fp("ui.eth_col_pupils") + ">" + esc(t("ui.eth_col_pupils")) + "</th>" +
    "</tr></thead><tbody>" +
    ep.map((r, i) => "<tr><td>" + esc(ethLabel(r[0], i)) + '</td><td class="num">' + r[1] +
      "</td></tr>").join("") +
    '</tbody></table><p class="chart-note"' + fp("ui.eth_note") + '>' + esc(t("ui.eth_note")) + "</p>";
  host.innerHTML = '<div class="grid2">' + bar("disability_condition") +
    bar("learning_difficulty") + "</div>" + ethTable +
    '<div class="grid2">' + bar("welsh_speaking") + fsmCard + "</div>";
}
/* --------------------- v2 navigation: Back / Next + contents links ------ */
function injectNav() {
  const stops = ["m-intro", "m-contents", "m-guide", "m-overview", "ch-anfe",
                 "ch-lifelong", "ch-sport", "m-summary", "m-thanks", "m-appendices"]
    .map(id => document.getElementById(id)).filter(Boolean);
  const link = (id, k) => { const p = framePending(k); return '<a href="#' + id + '"' + (p ? ' class="cy-missing" lang="en"' : "") + prov((p ? "frame:pending:" : "frame:") + k) + ">" + esc(t(k)) + "</a>"; };
  stops.forEach((sec, i) => {
    let nav = sec.nextElementSibling;
    if (!nav || !nav.classList.contains("pagenav")) {
      nav = document.createElement("nav");
      nav.className = "pagenav";
      sec.insertAdjacentElement("afterend", nav);
    }
    nav.setAttribute("aria-label", t("ui.nav_aria"));
    const prev = i > 0 ? stops[i - 1] : null;
    const next = i < stops.length - 1 ? stops[i + 1] : null;
    nav.innerHTML =
      (prev ? link(prev.id, "ui.nav_back") : "<span></span>") +
      link("m-contents", "ui.nav_contents") +
      (next ? link(next.id, "ui.nav_next") : "<span></span>");
  });
}

/* --------------------------------------------------------------- update */
function nearestHeading() {
  let best = null;
  for (const h of $$("main.report h2, main.report h3")) {
    if (h.getBoundingClientRect().top <= 70) best = h;
    else break;
  }
  return best;
}
function renderView(prefix) {
  /* v5 (build 012, owner request): stay at the nearest heading above the
     reader's position when filters re-render the page */
  const anchor = prefix && window.scrollY > 200 ? nearestHeading() : null;
  const ae = document.activeElement;
  const focusSel = ae && ae.dataset ? (
    ae.dataset.cohort ? '[data-cohort="' + ae.dataset.cohort + '"]' :
    ae.dataset.g ? '[data-g="' + ae.dataset.g + '"]' : (ae.id ? "#" + ae.id : null)) : null;
  writeHash();
  renderRail();
  renderBanner();
  renderSuppressed();
  renderModules();
  renderClosing();
  renderAppendices();
  applyA11yState();                            // V4.13: re-rendered tables follow the switch
  if (focusSel) { const el = $(focusSel); if (el) el.focus({ preventScroll: true }); }
  if (anchor && anchor.isConnected)
    anchor.scrollIntoView({ block: "start" });
  if (prefix) {
    const s = st();
    announce(isCy()
      ? prefix + " " + uiStr("showing") + " " + descOf(s) + ". " +
        (s && !s.sup
          ? s.b + " " + uiStr(s.b === 1 ? "response_included"
                                        : "responses_included") + "."
          : uiStr("not_enough") + ".")
      : prefix + " Showing " + descOf(s) + ". " +
        (s && !s.sup ? "There " + (s.b === 1 ? "is 1 pupil response" : "are " + s.b +
         " pupil responses") + " in this view."
         : "There were not enough responses to report these findings safely."));
  }
}

/* V6.0: every state change passes through here. On the monolithic copy
   (no DATA.chunked) it renders at once, as before. On the served package it
   first loads the chunks the view needs; the sequence number discards a
   late response from an earlier selection, and nothing is rendered — no
   label, no figure — until every needed chunk has verified. */
function update(prefix) {
  const need = CHUNKED ? groupsFor() : [];
  const seq = ++_viewSeq;                 // every change supersedes any load in flight
  if (!need.length) { if (CHUNKED) setLoading(null); renderView(prefix); return; }
  setLoading("loading");
  Promise.all(need.map(loadGroup)).then(() => {
    if (seq !== _viewSeq) return;
    setLoading(null);
    renderView(prefix);
  }).catch(err => {
    if (seq !== _viewSeq) return;
    if (window.console) console.error("ILR chunk load failed:", err && err.message);
    setLoading("error", () => update(prefix));
  });
}

const annFilter = () => cat("filter_applied");
function setScope(k) { state.scope = k; update(annFilter()); }
function setGender(k) { state.gender = k; update(annFilter()); }
function setCohort(k) {
  state.cohort = (state.cohort === k) ? "none" : k;
  update(cat(state.cohort === "none" ? "selection_cleared"
                                       : "selection_applied"));
}
function clearAll() {
  state.scope = "whole"; state.gender = "all"; state.cohort = "none";
  update(cat("all_cleared"));
}

document.addEventListener("click", e => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.cohort) setCohort(b.dataset.cohort);
  else if (b.dataset.g) setGender(b.dataset.g);
  else if (b.id === "chip-x" || b.id === "vb-clear" || b.id === "btn-reset") clearAll();
  else if (b.id === "btn-print") { if (!document.body.classList.contains("is-loading")) window.print(); }
  else if (b.id === "btn-lang") {
    state.lang = isCy() ? "en" : "cy";
    applyLanguageState();
    update();
  }
  else if (b.id === "btn-a11y") {              // V4.13 accessibility switch
    state.a11y = !state.a11y;
    applyA11yState();
    writeHash();
  }
  else if (b.id === "rail-toggle") {
    const r = $("#rail");
    r.classList.toggle("open");
    b.setAttribute("aria-expanded", r.classList.contains("open"));
  }
});
$("#f-scope").addEventListener("change", e => setScope(e.target.value));
const _fg = $("#f-group");
if (_fg) _fg.addEventListener("change", e => {
  state.cohort = e.target.value === "none" ? "none" : e.target.value;
  update(cat(e.target.value === "none" ? "group_cleared" : "group_applied"));
});
window.addEventListener("hashchange", () => {
  if (!location.hash.includes("scope=")) {          // a bare #section fragment
    const id = location.hash.slice(1);
    if (id && document.getElementById(id)) gotoSection(id, false);
    return;
  }
  readHash(); applyLanguageState(); update(cat("view_restored"));
});

/* Persistent-control layout (Prototype 4.1 §2.5): at narrow widths the
   banner and the filter control live inside ONE dedicated sticky stack, in
   the order banner -> filters -> content, matching DOM and keyboard order.
   The expanded filter drawer is absolutely positioned, so opening it never
   moves the reader's position. */
const NARROW = window.matchMedia ? window.matchMedia("(max-width: 1050px)")
  : { matches: false, addEventListener: function () {} };
function placeControls() {
  const banner = $("#view-banner");
  const rail = $(".filter-rail");
  const stack = $("#mobile-stack");
  const app = $(".app");
  const mainEl = $("main.report");
  if (NARROW.matches) {
    if (banner.parentElement !== stack) stack.appendChild(banner);
    if (rail.parentElement !== stack) stack.appendChild(rail);
  } else {
    if (banner.parentElement !== mainEl) mainEl.insertBefore(banner, mainEl.firstChild);
    if (rail.parentElement !== app) app.appendChild(rail);
  }
}
NARROW.addEventListener ? NARROW.addEventListener("change", placeControls)
                        : NARROW.addListener(placeControls);

// print behaviour (section 22): expand the appendix tables for printing
let _openedForPrint = [];
window.addEventListener("beforeprint", () => {
  _openedForPrint = $$("#m-appendices details:not([open])");
  _openedForPrint.forEach(d => { d.open = true; });
});
window.addEventListener("afterprint", () => {
  _openedForPrint.forEach(d => { d.open = false; });
  _openedForPrint = [];
});

if (!CONFIG.reviewMode) {
  const rb = $("#review-banner"); if (rb) rb.remove();
}
if (!CONFIG.showSummaries) document.body.classList.add("no-summaries");
readHash();
applyLanguageState();   // D79: also binds the static lane (renderStatic); sets the title
renderProfile();
injectNav();
placeControls();
update();
placeControls();
if (state.section) gotoSection(state.section, false);
