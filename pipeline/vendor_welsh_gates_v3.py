# -*- coding: utf-8 -*-
# VENDORED VERBATIM from the V4.5 handover pack (welsh_acceptance_gates_v3.py).
# Do not edit: the release contract is the stock script; welsh_gates3 wraps it.
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSS2026 — Welsh acceptance gates, v3.

WHAT CHANGED FROM v2, AND WHY IT MATTERS
    v2 tested the module paragraph array and nothing else. V4.4 scored 29/31 on
    it while carrying visible placeholders in 216 view descriptors, English-only
    interactive controls, and a closing branch that bypassed its own provisional
    ruling. A gate pack that only sees mod[*].p cannot certify a report.

    v3 therefore runs over EVERY generated Welsh surface:
        module paragraphs · closing h1 · closing h2 · scope descriptors ·
        chart/table option catalogues · the client source paths
    and adds three structural gate families that do not depend on knowing the
    defect's spelling in advance:
        PUB  publishable strings   — nothing internal may reach a reader
        DIS  distinctness          — distinct English must yield distinct Welsh
        PAR  cross-language parity — the same facts in both languages, or neither

    Structural gates survive a change in the generator. Pattern gates do not:
    the v1 numeral gate passed V4.3 while the defect was still present in a
    different shape, and the v2 agreement gate passed V4.4 for the same reason.

    python welsh_acceptance_gates_v3.py report.html [--json]
"""
import sys, json, io, re, argparse, collections

# ------------------------------------------------------------------ loading
def load(path):
    raw = None
    with io.open(path, encoding='utf-8') as fh:
        for line in fh:
            if 'id="report-data"' in line:
                raw = line.split('>', 1)[1].rsplit('</script', 1)[0]; break
    if raw is None: sys.exit('no report-data block in ' + path)
    D = json.loads(raw)
    js = ''
    with io.open(path, encoding='utf-8') as fh:
        hit = False
        for line in fh:
            if hit: js += line
            elif re.match(r'\s*<script>\s*$', line): hit = True
    S = {'module': [], 'h1': [], 'h2': [], 'scope': [], 'opts': []}
    seen = collections.Counter()
    for sk, st in D['states'].items():
        sex = sk.split('|')[1]
        for mid, m in (st.get('mod') or {}).items():
            for p in (m.get('p') or []):
                seen[(mid, sex, p.get('t') or '', p.get('c') or '')] += 1
        def pair(x):
            if isinstance(x, dict): return x.get('t') or x.get('en') or '', x.get('c') or ''
            return (x or ''), ''
        for k, v in (st.get('h1') or {}).items():
            for s in v:
                en, cy = pair(s); S['h1'].append({'s': sk, 'sex': sex, 't': en, 'c': cy, 'n': 1, 'm': 'h1'})
        for s in (st.get('h2') or []):
            en, cy = pair(s)
            if cy: S['h2'].append({'s': sk, 'sex': sex, 't': en, 'c': cy, 'n': 1, 'm': 'h2'})
        sc = st.get('scope') or {}
        S['scope'].append({'s': sk, 'sex': sex, 't': sc.get('short') or '',
                           'c': sc.get('shortCy') or '', 'n': 1, 'm': 'scope'})
    for k, v in seen.items():
        S['module'].append({'m': k[0], 'sex': k[1], 't': k[2], 'c': k[3], 'n': v})
    for mid, md in (D.get('metricDefs') or {}).items():
        cy = md.get('optsCy') or []
        for i, o in enumerate(md.get('opts') or []):
            en = o[1] if isinstance(o, (list, tuple)) else o
            w = cy[i] if i < len(cy) else None
            w = w[1] if isinstance(w, (list, tuple)) else w
            S['opts'].append({'m': mid, 'sex': 'all', 't': en or '', 'c': w or '', 'n': 1})
    return D, S, js

# ------------------------------------------------------------------ vocabulary
VIG = {0:"dim",1:"un",2:"dau",3:"tri",4:"pedwar",5:"pump",6:"chwech",7:"saith",8:"wyth",9:"naw",
       10:"deg",11:"un",12:"deuddeg",13:"tri",14:"pedwar",15:"pymtheg",16:"un",17:"dau",
       18:"deunaw",19:"pedwar",20:"ugain"}
def vig_lead(x):
    n = int(x)
    if n <= 20: return VIG.get(n, 'dim')
    if n < 40:  return vig_lead(n - 20)
    if n == 40: return 'deugain'
    if n < 60:  return vig_lead(n - 40)
    if n == 60: return 'trigain'
    if n < 80:  return vig_lead(n - 60)
    if n == 80: return 'pedwar'
    if n < 100: return vig_lead(n - 80)
    if n < 200: return 'cant'
    return vig_lead(n // 100)
VOWELS = 'aeiouwyâêîôûŵŷ'
CY_NUM = {'un':1,'dau':2,'dwy':2,'ddau':2,'ddwy':2,'tri':3,'tair':3,'dair':3,'thri':3,'thair':3,
 'pedwar':4,'pedair':4,'bedwar':4,'bedair':4,'phedwar':4,'phedair':4,'pump':5,'pum':5,'bum':5,
 'bump':5,'phum':5,'chwech':6,'chwe':6,'saith':7,'wyth':8,'naw':9,'deg':10,'ddeg':10,'ddeng':10,
 'unwaith':1,'dwywaith':2,'ddwywaith':2,'deirgwaith':3,'theirgwaith':3}
EN_NUM = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,
          'ten':10,'once':1,'twice':2,'three times':3}
PLACEHOLDER = re.compile(r'\[[^\]]{4,}\]|question-dependent|see sheet|TODO|FIXME|⟪|\bTBC\b')
ENGLISH_LEAK = re.compile(r'\b(the|of|and|who|were|said|most|pupils|school|among|across|selected)\b', re.I)
PLURAL_MARK = re.compile(r'\b(iddynt|y maent|eu bod|nad oeddent|nad ydynt|ganddynt|yr hoffent|ohonynt|oeddent)\b')

def numset(s, words, min_digit=0):
    o = {int(x) for x in re.findall(r'\d+', (s or '').replace(',', '')) if int(x) >= min_digit}
    for k, v in words.items():
        if v >= min_digit and re.search(r'\b' + k + r'\b', s or '', re.I): o.add(v)
    return o

# ------------------------------------------------------------------ the gates
def gates(D, S, js):
    G = []
    def gate(gid, surface, title, rows, limit=0, note=''):
        G.append({'id': gid, 'surface': surface, 'title': title,
                  'occurrences': sum(r.get('n', 1) for r in rows), 'records': len(rows),
                  'limit': limit,
                  'pass': True if limit is None else sum(r.get('n', 1) for r in rows) <= limit,
                  'note': note,
                  'examples': [{'en': (r.get('t') or '')[:200], 'cy': (r.get('c') or '')[:200],
                                'where': f"{r.get('s','')}|{r.get('m','')}"} for r in rows[:3]]})
    ALL = S['module'] + S['h1'] + S['h2'] + S['scope'] + S['opts']

    # ---- PUB : nothing internal may reach a reader -------------------------
    for name, rows in (('module', S['module']), ('h1', S['h1']), ('h2', S['h2']),
                       ('scope', S['scope']), ('opts', S['opts'])):
        gate('PUB-' + name, name, 'Internal placeholder or instruction exposed in Welsh output',
             [r for r in rows if r['c'] and PLACEHOLDER.search(r['c'])],
             note='non-empty is not the same as publishable')
    gate('PUB-empty', 'all', 'Welsh value empty where English is present',
         [r for r in ALL if (r.get('t') or '').strip() and not (r.get('c') or '').strip()])
    gate('PUB-copy', 'all', 'Welsh value identical to the English',
         [r for r in ALL if r.get('c') and r['c'] == r.get('t')
          and re.search(r'[A-Za-zÀ-ÿ]{3}', r['c'])],
         note='report-only: unadapted loans (BMX, Tennis, Boccia) are legitimately identical. '
              'Maintain a signed exception list; anything not on it is an untranslated label.',
         limit=None)
    gate('PUB-leak', 'all', 'English function word inside a Welsh string',
         [r for r in ALL if r.get('c') and ENGLISH_LEAK.search(r['c'])])

    # ---- DIS : distinct English must give distinct Welsh -------------------
    for name, rows in (('module', S['module']), ('h1', S['h1']), ('h2', S['h2']), ('scope', S['scope'])):
        by = collections.defaultdict(set)
        for r in rows:
            if r.get('c'): by[r['c']].add(r.get('t') or '')
        coll = {k for k, v in by.items() if len(v) > 1}
        gate('DIS-' + name, name, 'Distinct English collapsing to one Welsh string',
             [r for r in rows if r.get('c') and r['c'] in coll],
             note='the single strongest indicator of a dropped semantic role')

    # ---- PAR : the same facts in both languages ----------------------------
    def parity(rows, name):
        lost, added = [], []
        for r in rows:
            if not r.get('c'): continue
            en = numset(r['t'], EN_NUM, 11); cy = numset(r['c'], {}, 11)
            if en - cy: lost.append(r)
            if cy - en: added.append(r)
        gate('PAR-lost-' + name, name, 'A figure 11+ in the English has no counterpart in the Welsh', lost,
             note='small numerals are excluded because Welsh writes them as words (D03)')
        gate('PAR-added-' + name, name, 'The Welsh states a figure 11+ the English does not', added,
             note='usually a derived percentage; needs a bilingual presentation policy, not a code fix',
             limit=None)
    parity(S['module'], 'module'); parity(S['h1'], 'h1')
    gate('PAR-follow', 'module', 'Welsh adds a ranked follower list the English does not show',
         [r for r in S['module'] if r.get('c') and 'ac yna' in r['c'] and 'followed by' not in (r['t'] or '')],
         note='one shared presentation flag, or neither language shows it')

    # ---- NUM : one realiser, shape-independent -----------------------------
    CYW = r'(?:un|dau|dwy|tri|tair|pedwar|pedair|pum|pump|chwe|chwech|saith|wyth|naw|deg)'
    gate('NUM-figword', 'module', 'Small numeral as a figure before a written base (N o’r <word>)',
         [r for r in S['module'] if re.search(r'(?<!\d)[1-9] o’r ' + CYW + r'\b', r['c'] or '')])
    gate('NUM-fignoun', 'module', 'Small numeral as a figure before a countable noun',
         [r for r in S['module'] if re.search(r'(?<!\d)[1-9] (?:disgybl|merch|bachgen|ddisgybl|ferch|fachgen|gamp|camp|ateb|opsiwn)\b', r['c'] or '')])
    gate('NUM-figcite', 'module', 'Small numeral as a figure before a quoted citation (FT-16)',
         [r for r in S['module'] if re.search(r'(?<!\d)(?:[1-9]|10) ‘', r['c'] or '')],
         note='dewisodd 6 ‘…’ — the count must come from the numeral service')
    gate('NUM-zero', 'all', 'Digit zero in running prose instead of a negative branch',
         [r for r in ALL if re.search(r'(?<!\d)0 o’r', r.get('c') or '')])

    # ---- CONJ : a / ac decided from the spoken form ------------------------
    bad = []
    rx = re.compile(r'\b(a|ac) (\d[\d,]*)\b')
    for r in ALL:
        for m in rx.finditer(r.get('c') or ''):
            want = 'ac' if vig_lead(m.group(2).replace(',', ''))[0] in VOWELS else 'a'
            if m.group(1) != want: bad.append(r); break
    gate('CONJ-vig', 'all', 'a/ac before a figure disagrees with its vigesimal reading (CONJ-06)', bad)
    gate('CONJ-fnword', 'all', 'a before a consonant-initial function word (PR-04 configuration)',
         [r for r in ALL if re.search(r'\ba (roedd|mae|nid|ni)\b', r.get('c') or '')],
         note='report-only while PR-04 is provisional', limit=None)

    # ---- AGR : agreement follows the antecedent, not the string ------------
    gate('AGR-plural', 'all', 'Plural agreement after an explicitly singular antecedent',
         [r for r in ALL if re.search(r'\b(unig|un (?:ddisgybl|disgybl|ferch|fachgen|bachgen|merch))\b', r.get('c') or '')
          and PLURAL_MARK.search(r.get('c') or '')],
         note='includes "un ohonynt", which is a plural partitive over a singleton')
    gate('AGR-partitive', 'all', 'Partitive taken over a singular set (un o’r unig …)',
         [r for r in ALL if re.search(r'\bo’r unig\b', r.get('c') or '')])

    # ---- POL : polarity and the provisional recast -------------------------
    gate('POL-stacked', 'all', 'Negative matrix with a negative complement (FT-11 review class)',
         [r for r in ALL if re.search(r'N[ii]d? [^.]*\byr un\b[^.]*\bnad\b', r.get('c') or '')],
         note='report-only until the linguist rules on PR-02', limit=None)
    recast = [r for r in ALL if re.search(r'Ni ddewisodd yr un', r.get('c') or '')]
    stacked = [r for r in ALL if re.search(r'N[ii]d? [^.]*\byr un\b[^.]*\bnad\b', r.get('c') or '')]
    bysurf_r = collections.Counter(r['m'] for r in recast)
    bysurf_s = collections.Counter(r['m'] for r in stacked)
    miss = [r for r in stacked if r['m'] not in bysurf_r]
    gate('POL-uniform', 'all', 'A provisional ruling applied on one surface but not another',
         miss, note=f'PR-02 recast present on {sorted(bysurf_r)} but not on {sorted(set(bysurf_s)-set(bysurf_r))}')

    # ---- UI : the controls must select Welsh -------------------------------
    findings = []
    checks = [('scope filter options', r"esc\(o\.label"),
              ('pupil-group default option', r'<option value="none">All pupils'),
              ('banner English descriptor test', r'scope\.short !== "Whole school'),
              ('response-base wrapper', r'pupil responses? included'),
              ('live-region announcements', r'announce\("[A-Z]')]
    for name, pat in checks:
        if re.search(pat, js): findings.append({'t': name, 'c': '', 'm': 'client', 'n': 1})
    gate('UI-bind', 'client', 'Interactive control renders English text with no language branch', findings,
         note='shortCy/optsCy exist in the payload but the control renderers do not consult them')
    gate('UI-lang', 'client', 'No single applyLanguageState() synchroniser',
         [] if 'applyLanguageState' in js else [{'t': 'applyLanguageState absent', 'c': '', 'm': 'client', 'n': 1}])

    # ---- HANDOFF : the static lane must be bindable ------------------------
    w = D.get('welsh') or {}
    ho = w.get('handoff') or {}
    missing = w.get('handoffMissing')
    unbound = (isinstance(missing, int) and missing > len(ho))
    gate('CAT-bind', 'catalogue', 'Declared static strings exceed the embedded handoff keys',
         [{'t': f'{missing} declared, {len(ho)} keys embedded', 'c': '', 'm': 'welsh.handoff', 'n': 1}] if unbound else [],
         note='populating the keys alone will not translate every declared string')
    return G

# ------------------------------------------------------------------ report
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('report'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    D, S, js = load(a.report)
    G = gates(D, S, js)
    if a.json:
        print(json.dumps({'surfaces': {k: len(v) for k, v in S.items()}, 'gates': G},
                         ensure_ascii=False, indent=1))
        sys.exit(0 if all(g['pass'] for g in G if g['limit'] is not None) else 1)
    print('surfaces: ' + ' · '.join(f'{k} {len(v):,}' for k, v in S.items()) + '\n')
    print(f'{"gate":16} {"surface":9} {"result":8} {"occ":>9} {"records":>9}  title')
    for g in G:
        res = 'REPORT' if g['limit'] is None else ('PASS' if g['pass'] else 'FAIL')
        print(f'{g["id"]:16} {g["surface"]:9} {res:8} {g["occurrences"]:9,} {g["records"]:9,}  {g["title"][:52]}')
    hard = [g for g in G if g['limit'] is not None]
    bad = [g for g in hard if not g['pass']]
    print(f'\n{len(hard)-len(bad)}/{len(hard)} blocking gates pass '
          f'({sum(1 for g in G if g["limit"] is None)} report-only)')
    for g in bad[:8]:
        if g['examples']:
            e = g['examples'][0]
            print(f'\n[{g["id"]}] {g["title"]}\n  EN: {e["en"]}\n  CY: {e["cy"]}')
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
