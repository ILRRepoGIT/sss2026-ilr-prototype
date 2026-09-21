#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSS2026 — browser gate v3: rendered-DOM provenance, typography and the STATIC-FURNITURE TOGGLE (D72, D79, D80).

Static analysis of the client (welsh_acceptance_gates_v7.py) can prove a key exists and a binder exists. It cannot
prove what a reader sees. This gate opens the built report in a real browser and asks three things of the DOM:

  1. PROVENANCE  (v1) every rendered string in Welsh mode — visible text, title=, aria-label, <caption>, <summary>,
                 the live region — sits under an element carrying data-i18n-source="<frame|catalogue|label key>".
                 An English-looking string with no provenance is a defect.
  2. TYPOGRAPHY  (v2) no missing space around a clause joiner ("disgybl· Yn dangos"), no "n/r", no "1 pupils",
                 no lower-case sentence-initial caption / heading / summary.
  3. TOGGLE      (v3, BROWSER-toggle) with a FIXTURE of unique, unmistakable Welsh values for every static key
                 (welsh.static, the ui### rows) and every keyed fixed attribute (data-ct-key, data-nh-key,
                 data-also-h-key, data-sh-key):
                   en mode  → every [data-i18n] element shows the manifest English;
                   cy mode  → every [data-i18n] element shows its fixture value, and every keyed-attribute
                              consumer renders its fixture value;
                   en again → the English is restored FROM THE CATALOGUE (not from a cached DOM), byte-for-byte.
                 An accidental English fallback cannot pass by coincidence because every fixture value is unique.
                 The fixture is injected at runtime into DATA.welsh.static / CY.handoff when --fixture auto is
                 given (proving the MECHANISM in a dev build), or read from --fixture fixture.json (proving a
                 fixture BUILD, where the values were compiled in — the release-candidate form of the test).

    python browser_gate_provenance.py report.html [--states 60] [--fixture auto|fixture.json] [--toggle-states 8]
                                                  [--json out.json] [--seed 7]

Exit 1 if any English-looking string without provenance, any typography fault, or any toggle failure is found.
Requires: pip install playwright && playwright install chromium
"""
import argparse, json, random, re, sys, pathlib, collections

ENW = re.compile(r'\b(the|this|these|for|in|of|to|by|a|an|and|or|not|no|selected|group|chart|table|data|view|pupils?|answers?|results?|school|year|boys|girls|based|show(?:ing|n)?|sport|sports|most|total|all|whole|club|clubs|answer)\b', re.I)
WELSHY = re.compile(r'[ŵŷ]|’n\b|’r\b|\b(yn|yr|ac|neu|mewn|disgybl|disgyblion|chwaraeon|ysgol|blwyddyn|bechgyn|merched|gyfan|ateb|pob|dim)\b', re.I)
ATTR_KEYS = ['data-ct-key', 'data-nh-key', 'data-also-h-key', 'data-sh-key']

COLLECT_JS = r"""
() => {
  const out = [];
  const src = el => { let e = el; while (e && e.nodeType === 1) { if (e.hasAttribute && e.hasAttribute('data-i18n-source')) return e.getAttribute('data-i18n-source'); e = e.parentElement; } return null; };
  const vis = el => { const cs = getComputedStyle(el); if (cs.display === 'none' || cs.visibility === 'hidden') return false; return true; };
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = walker.nextNode())) {
    const t = (n.nodeValue || '').replace(/\s+/g, ' ').trim();
    if (t.length < 3) continue;
    const el = n.parentElement; if (!el || ['SCRIPT','STYLE','NOSCRIPT'].includes(el.tagName)) continue;
    if (!vis(el)) continue;
    out.push({kind: 'text', tag: el.tagName.toLowerCase(), text: t, source: src(el), path: el.closest('[id]') ? el.closest('[id]').id : ''});
  }
  for (const el of document.querySelectorAll('[title],[aria-label]')) {
    for (const a of ['title','aria-label']) { const v = el.getAttribute(a); if (v && v.trim().length >= 3) out.push({kind: a, tag: el.tagName.toLowerCase(), text: v.trim(), source: src(el), path: el.closest('[id]') ? el.closest('[id]').id : ''}); }
  }
  return out;
}
"""
STATIC_JS = r"""
() => {
  const out = [];
  for (const el of document.querySelectorAll('[data-i18n]'))
    out.push({key: el.getAttribute('data-i18n'), text: (el.textContent || '').replace(/\s+/g, ' ').trim()});
  return out;
}
"""
ATTR_JS = r"""
(keys) => {
  const out = [];
  for (const ak of keys) for (const el of document.querySelectorAll('[' + ak + ']'))
    out.push({attr: ak, key: el.getAttribute(ak), text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 4000)});
  return out;
}
"""
TYPO = [
  ('join-space',  re.compile(r'[\w\d][·—]|[·—](?=[\w])')),
  ('nr-literal',  re.compile(r'(?<![\w/])n/r(?![\w/])')),
  ('one-pupils',  re.compile(r'\b1 pupils\b|\bun ddisgyblion\b')),
]
CASED_TAGS = {'caption', 'h1', 'h2', 'h3', 'h4', 'h5', 'summary', 'th', 'figcaption'}

def classify(s):
    en = len(ENW.findall(s)); cy = len(WELSHY.findall(s))
    if en >= 2 and cy == 0: return 'english'
    if cy >= 1 and en <= 1: return 'welsh'
    return 'mixed' if en and cy else 'neutral'

def goto_state(pg, sk, lang):
    scope, sex, coh = sk.split('|')
    pg.evaluate(f"() => {{ location.hash = 'scope={scope}&gender={sex}&cohort={coh}&lang={lang}'; }}")
    pg.wait_for_timeout(700)
    for el in pg.query_selector_all('details:not([open]) > summary'):
        try: el.click(timeout=300)
        except Exception: pass

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('report'); ap.add_argument('--states', type=int, default=60); ap.add_argument('--json'); ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--timeout', type=int, default=180000)
    ap.add_argument('--fixture', help='"auto" (inject unique values at runtime) or a fixture.json {key: cy} compiled into the build')
    ap.add_argument('--toggle-states', type=int, default=8)
    a = ap.parse_args()
    from playwright.sync_api import sync_playwright
    url = pathlib.Path(a.report).resolve().as_uri()
    findings, typos, seen = [], [], set()
    toggle = {'static_keys': 0, 'attr_consumers': 0, 'en_ok': 0, 'cy_ok': 0, 'restored_ok': 0, 'failures': []}
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--js-flags=--max-old-space-size=4096'])
        pg = b.new_page(viewport={'width': 1280, 'height': 900})
        pg.set_default_timeout(a.timeout)
        pg.goto(url + '#lang=cy'); pg.wait_for_load_state('load'); pg.wait_for_timeout(3000)
        keys = pg.evaluate("() => Object.keys(DATA.states)")
        lang = pg.evaluate("() => document.documentElement.lang")
        random.seed(a.seed); sample = ['whole|all|none'] + random.sample(keys, min(a.states, len(keys)))
        # ---- 1 + 2: provenance and typography over the sample -------------------------------------
        for sk in sample:
            goto_state(pg, sk, 'cy')
            rows = pg.evaluate(COLLECT_JS)
            for r in rows:
                key = (r['kind'], r['text'], r['source'])
                if key in seen: continue
                seen.add(key)
                r['class'] = classify(r['text']); r['state'] = sk
                if r['class'] in ('english', 'mixed') or r['source'] is None: findings.append(r)
                for tid, rx in TYPO:
                    if rx.search(r['text']): typos.append(dict(r, typo=tid))
                if r['kind'] == 'text' and r['tag'] in CASED_TAGS and r['text'][0].isalpha() and r['text'][0].islower():
                    typos.append(dict(r, typo='lower-case-initial'))   # a string that opens with a figure or a marker is not a sentence start
        # ---- 3: the static-furniture toggle --------------------------------------------------------
        if a.fixture:
            static = pg.evaluate("() => (DATA.welsh && DATA.welsh.static) || null")
            if not static:
                toggle['failures'].append({'key': '*', 'why': 'DATA.welsh.static absent — nothing to toggle'})
            else:
                if a.fixture == 'auto':
                    fix = {k: f'⟦CY:{k}⟧' for k in static}
                    pg.evaluate("(fix) => { for (const k in fix) { DATA.welsh.static[k].cy = fix[k]; if (DATA.welsh.handoff) DATA.welsh.handoff[k] = fix[k]; } }", fix)
                else:
                    fix = json.load(open(a.fixture, encoding='utf-8'))
                en_expect = {k: re.sub(r'\s+', ' ', str(v.get('en') or '')).strip() for k, v in static.items()}
                toggle['static_keys'] = len(static)
                tsample = sample[:max(1, a.toggle_states)]
                for sk in tsample:
                    goto_state(pg, sk, 'en'); before = {r['key']: r['text'] for r in pg.evaluate(STATIC_JS)}
                    attrs_en = pg.evaluate(ATTR_JS, ATTR_KEYS)
                    goto_state(pg, sk, 'cy'); during = {r['key']: r['text'] for r in pg.evaluate(STATIC_JS)}
                    attrs_cy = pg.evaluate(ATTR_JS, ATTR_KEYS)
                    goto_state(pg, sk, 'en'); after = {r['key']: r['text'] for r in pg.evaluate(STATIC_JS)}
                    for k in static:
                        if k not in before: toggle['failures'].append({'state': sk, 'key': k, 'why': 'no [data-i18n] element rendered for this key'}); continue
                        if before[k] == en_expect.get(k): toggle['en_ok'] += 1
                        else: toggle['failures'].append({'state': sk, 'key': k, 'why': f'en mode shows {before[k][:60]!r}, manifest en is {en_expect.get(k, "")[:60]!r}'})
                        if k in fix and during.get(k) == re.sub(r'\s+', ' ', fix[k]).strip(): toggle['cy_ok'] += 1
                        elif k in fix: toggle['failures'].append({'state': sk, 'key': k, 'why': f'cy mode shows {during.get(k, "")[:60]!r}, fixture is {fix[k][:60]!r}'})
                        if after.get(k) == before[k]: toggle['restored_ok'] += 1
                        else: toggle['failures'].append({'state': sk, 'key': k, 'why': f'after toggling back: {after.get(k, "")[:60]!r} ≠ {before[k][:60]!r}'})
                    toggle['attr_consumers'] = max(toggle['attr_consumers'], len(attrs_en))
                    for r_en, r_cy in zip(attrs_en, attrs_cy):
                        k = r_en['key']
                        if k in fix and fix[k] not in r_cy['text']:
                            toggle['failures'].append({'state': sk, 'key': k, 'why': f'{r_en["attr"]}="{k}": fixture value not rendered in Welsh mode'})
                        if k in en_expect and en_expect[k] and en_expect[k] not in r_en['text']:
                            toggle['failures'].append({'state': sk, 'key': k, 'why': f'{r_en["attr"]}="{k}": manifest English not rendered in English mode'})
                        if k not in static: toggle['failures'].append({'state': sk, 'key': k, 'why': f'{r_en["attr"]} names a key with no static manifest row'})
        b.close()
    bad = [f for f in findings if f['class'] in ('english', 'mixed') and not f['source']]
    excepted = [f for f in findings if f['class'] in ('english', 'mixed') and f['source']]
    unaudited = [f for f in findings if f['class'] == 'welsh' and not f['source']]
    summary = {'document_lang': lang, 'states_sampled': len(sample), 'distinct_strings_seen': len(seen),
               'english_without_provenance': len(bad), 'english_with_provenance': len(excepted), 'welsh_without_provenance': len(unaudited),
               'typography_faults': len(typos), 'typography_by_kind': dict(collections.Counter(t['typo'] for t in typos)),
               'toggle': {k: v for k, v in toggle.items() if k != 'failures'} | {'failures': len(toggle['failures'])} if a.fixture else 'not run (--fixture)'}
    print(json.dumps(summary, indent=1, ensure_ascii=False))
    by = collections.Counter((f['kind'], f['path']) for f in bad)
    for k, v in by.most_common(20): print(f'{v:5}  {k[0]:10} #{k[1]}')
    for f in bad[:25]: print(f"  [{f['kind']}] #{f['path']} <{f['tag']}> {f['text'][:100]}")
    for t in typos[:25]: print(f"  [typo:{t['typo']}] #{t['path']} <{t['tag']}> {t['text'][:100]}")
    for f in toggle['failures'][:25]: print(f"  [toggle] {f.get('state', '')} {f['key']}: {f['why']}")
    if a.json: json.dump({'summary': summary, 'english_without_provenance': bad, 'english_with_provenance': excepted, 'welsh_without_provenance': unaudited,
                          'typography': typos, 'toggle_failures': toggle['failures']}, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    sys.exit(1 if (bad or typos or toggle['failures']) else 0)

if __name__ == '__main__':
    main()
