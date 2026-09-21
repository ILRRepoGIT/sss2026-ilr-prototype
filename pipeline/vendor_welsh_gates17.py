#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSS2026 — Welsh acceptance gates.

Runs the corpus-level assertions from the V4.2 appraisal against a built
bilingual report and exits non-zero if any gate fails. Drop into CI between
the generator and release.

    python welsh_acceptance_gates.py SSS2026_ILR_Report_V4.2_Bilingual.html
    python welsh_acceptance_gates.py --json report.html > gates.json

Every gate is a corpus fact, not a style opinion: each one either matches a
defect pattern that must never appear, or checks a structural property that
must always hold. Thresholds are all zero except where noted.
"""
import sys, json, io, re, argparse, collections

# --------------------------------------------------------------- extraction
def load_pairs(path):
    """Yield {module, state, en, cy, n} from a built bilingual report."""
    raw = None
    with io.open(path, encoding='utf-8') as fh:
        for line in fh:
            if 'id="report-data"' in line:
                raw = line.split('>', 1)[1].rsplit('</script', 1)[0]
                break
    if raw is None:
        sys.exit('no <script id="report-data"> block found in ' + path)
    D = json.loads(raw)
    seen = collections.Counter()
    for sk, st in D['states'].items():
        for mid, m in (st.get('mod') or {}).items():
            for p in (m.get('p') or []):
                seen[(mid, sk.split('|')[1], p.get('t') or '', p.get('c') or '')] += 1
    return [{'m': k[0], 'gender': k[1], 't': k[2], 'c': k[3], 'n': v}
            for k, v in seen.items()]

# --------------------------------------------------------------- vocabulary
EN_SETTING = {'pe_lesson': r'in PE or lesson time',
              'school_club': r'in a school club',
              'outside_club': r'in a club outside of school',
              'elsewhere': r'somewhere else'}
CY_SETTING = {'pe_lesson': r'Addysg Gorfforol|Amser Gwersi|wersi AG',
              'school_club': r'clwb ysgol|glwb ysgol',
              'outside_club': r'tu allan i’r ysgol',
              'elsewhere': r'[Rr]hywle arall'}
EN_NUM = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,
          'nine':9,'ten':10,'once':1,'twice':2}
CY_NUM = {'un':1,'dau':2,'dwy':2,'ddau':2,'ddwy':2,'tri':3,'tair':3,'dair':3,'thri':3,
          'thair':3,'pedwar':4,'pedair':4,'bedwar':4,'bedair':4,'phedwar':4,'phedair':4,
          'pump':5,'pum':5,'bump':5,'bum':5,'phum':5,'chwech':6,'chwe':6,'saith':7,
          'wyth':8,'naw':9,'deg':10,'ddeg':10,'ddeng':10,'unwaith':1,'dwywaith':2,
          'ddwywaith':2,'deirgwaith':3,'theirgwaith':3}
LABEL_DIGIT = re.compile(r'\d+(?=-pin)|(?<=Bowls \(not )\d+')

def numset(s, words, strip_labels=False):
    if strip_labels: s = LABEL_DIGIT.sub(' ', s)
    out = {int(x) for x in re.findall(r'\d+', s.replace(',', ''))}
    for w, v in words.items():
        if re.search(r'\b' + w + r'\b', s, re.I): out.add(v)
    return out

# --------------------------------------------------------------- the gates
def gates(R):
    G = []
    def gate(gid, title, rows, limit=0, note=''):
        G.append({'id': gid, 'title': title, 'paragraphs': sum(r['n'] for r in rows),
                  'unique': len(rows), 'limit': limit,
                  'pass': sum(r['n'] for r in rows) <= limit, 'note': note,
                  'examples': [{'en': r['t'][:220], 'cy': r['c'][:220], 'module': r['m']}
                               for r in rows[:3]]})

    # --- G1  semantic role preservation ------------------------------------
    gate('G1a', 'Predicate substituted: Welsh asserts ease of joining in where English does not',
         [r for r in R if re.search(r'hawdd ymuno', r['c'])
          and not re.search(r'join(ing)? in', r['t'], re.I)])

    gate('G1b', 'Polarity inverted: "The one pupil said…" rendered as a negative',
         [r for r in R if re.match(r'\s*The (one|1)\b', r['t'])
          and re.match(r'\s*N[ii]d? ', r['c'])])

    gate('G1c', 'Respondent groups conflated: disability-only or LD-only rendered with the combined phrase',
         [r for r in R if 'a nododd anabledd a/neu anhawster dysgu' in r['c']
          and re.search(r'with a disability or long-term condition|with a learning difficulty', r['t'])])

    rows = []
    for r in R:
        for k, p in EN_SETTING.items():
            if re.search(p, r['t'], re.I) and not re.search(CY_SETTING[k], r['c']):
                rows.append(r); break
    gate('G1d', 'Setting present in English, absent from Welsh', rows)

    gate('G1e', 'Outer cohort qualifier dropped',
         [r for r in R if re.search(r'who selected [A-Z]|who would like to do more of', r['t'])
          and not re.search(r'a ddewisodd|hoffent wneud mwy', r['c'])])

    # --- G2  category / head-noun integrity --------------------------------
    gate('G2a', 'Non-sport answers described as campau (sports)',
         [r for r in R if r['m'] in ('f6', 'f7') and 'y campau a ddewiswyd amlaf' in r['c']])

    gate('G2b', 'English SETTING realised as camp (sport)',
         [r for r in R if re.search(r'y gamp flaenaf|y dwy gamp', r['c'])
          and re.search(r'setting', r['t'], re.I)])

    # --- G3  number, mutation, agreement -----------------------------------
    NOUN = r'(merch|bachgen|disgybl|ferch|fachgen|ddisgybl|gamp|camp|ateb|opsiwn)'
    small = re.compile(r'(?<!\d)([1-9]) ' + NOUN + r'\b')
    strict, mixed = [], []
    for r in R:
        if not small.search(r['c']): continue
        big = [int(x) for x in re.findall(r'\d+', r['c'].replace(',', '')) if int(x) > 10]
        (mixed if big else strict).append(r)
    gate('G3a', 'Figure used where D03 requires a Welsh word form (1–10 before a noun)', strict,
         note='excludes mixed-magnitude series, which D03 permits as digits')
    gate('G3a+', 'Same, in a mixed-magnitude series (arguable under the D03 exception)', mixed,
         limit=len(mixed) and sum(r['n'] for r in mixed),
         note='reported for the linguist to rule on; not counted as a failure')

    gate('G3b', 'Zero rendered as a positive count instead of a negative construction',
         [r for r in R if re.search(r'[Dd]ywedodd 0(?!\d)|atebodd 0(?!\d)', r['c'])])

    gate('G3c', 'Partitive not suppressed at n = 1 (D19 branch 1)',
         [r for r in R if re.search(r'(?<!\d)1 o ddisgyblion|gydag? 1 o ddewisiadau', r['c'])])

    gate('G3d', 'Masculine complement used for a girl-filtered audience',
         [r for r in R if r['gender'] == 'girl' and re.search(r'(?<!\d)dywedodd 1 ei fod', r['c'])])

    gate('G3e', 'Mutation missing after the definite article in a feminine dual NP (y dwy gamp)',
         [r for r in R if 'y dwy gamp' in r['c']])

    gate('G3f', 'First ordinal uses the general pre-nominal order (y gyntaf gamp)',
         [r for r in R if 'y gyntaf gamp' in r['c']])

    # --- G4  figure parity --------------------------------------------------
    NEGZERO = re.compile(r'\bN[ii]d?\b|\bni\b|yr un\b')
    g4 = []
    for r in R:
        missing = numset(r['t'], EN_NUM, True) - numset(r['c'], CY_NUM)
        if not missing: continue
        # a nil count correctly realised as a negative clause is not a lost figure
        if missing == {0} and NEGZERO.search(r['c']): continue
        g4.append(r)
    gate('G4', 'Figure in English with no counterpart in Welsh', g4,
         note='a zero realised as a negative clause is excluded — that is the correct branch')

    # --- G5  distinctness ---------------------------------------------------
    by = collections.defaultdict(set)
    for r in R: by[r['c']].add(r['t'])
    coll = {c for c, ts in by.items() if len(ts) > 1}
    gate('G5', 'Distinct English paragraphs collapsing to one Welsh paragraph',
         [r for r in R if r['c'] in coll],
         note='the strongest single indicator of dropped semantic roles')

    # --- G6  typography and framework templates -----------------------------
    gate('G6a', 'Quoted answer opened with U+2019 instead of ‘ (D27)',
         [r for r in R if re.search(r'’(iach|hyderus|barod|eithaf|Llawer)', r['c'])])

    gate('G6b', 'Plural tie rendered with singular wording (FT-18)',
         [r for r in R if 'Yr ail opsiwn' in r['c'] and 'yn ei ddewis' in r['c']])

    gate('G6c', 'Welsh paragraph more than 2.2× the English length (FT-24 list collapse)',
         [r for r in R if len(r['c']) > 2.2 * len(r['t'])])

    # --- G8  numeral realisation, shape-independent -------------------------
    CY_WORD = (r'(?:un|dau|dwy|ddau|ddwy|tri|tair|dair|thri|pedwar|pedair|bedwar|bedair'
               r'|pum|pump|bum|bump|phum|chwe|chwech|saith|wyth|naw|deg|ddeg)')
    gate('G8a', 'Small numeral written as a figure before a written base (N o’r <word>)',
         [r for r in R if re.search(r'(?<!\d)[1-9] o’r ' + CY_WORD + r'\b', r['c'])],
         note='D03/D19 — the numerator and the base must use the same regime')
    gate('G8b', 'Small numeral written as a figure before a partitive figure (N o’r N)',
         [r for r in R if re.search(r'(?<!\d)[1-9] o’r [1-9](?!\d)', r['c'])])
    gate('G8c', 'Small numeral written as a figure before a plural noun (N o <plural>)',
         [r for r in R if re.search(r'(?<!\d)[1-9] o [dgfbll]?\w+(?:ion|au|iau)\b', r['c'])])

    # --- G9  citation, agreement and article --------------------------------
    gate('G9a', 'Answer citation wrapped in two quote pairs',
         [r for r in R if re.search(r'‘‘|’’', r['c'])],
         note='D27 — exactly one opening and one closing mark per citation')
    gate('G9b', 'Plural agreement after an explicitly singular one-person base',
         [r for r in R if re.search(r'\bun (?:ddisgybl|disgybl|ferch|fachgen|bachgen|merch)\b', r['c'])
          and re.search(r'\b(iddynt|y maent|eu bod|nad oeddent|nad ydynt|ganddynt|yr hoffent)\b', r['c'])])
    gate('G9c', 'Article y used before the vowel-initial un (ART-02 requires yr)',
         [r for r in R if re.search(r'\by un\b', r['c'])])
    gate('G9d', 'Digit zero used in running prose instead of a zero branch',
         [r for r in R if re.search(r'(?<!\d)0 o’r', r['c'])])
    gate('G9e', 'Stacked negation: negative matrix plus negative complement',
         [r for r in R if re.search(r'N[ii]d? [^.]*\byr un\b[^.]*\bnad\b', r['c'])],
         note='FT-11 review population — the linguist rules on whether the positive-inverse branch is required')

    # --- G7  invariants that must hold --------------------------------------
    gate('G7a', 'Welsh paragraph empty', [r for r in R if not r['c'].strip()])
    gate('G7b', 'Welsh identical to English', [r for r in R if r['c'] == r['t']])
    gate('G7c', 'English function word leaking into Welsh',
         [r for r in R if re.search(r'\b(the|of|and|who|were|said|most|pupils|school|among|across)\b',
                                    r['c'], re.I)])
    gate('G7d', 'Welsh sentence opening with a figure (D04)',
         [r for r in R if re.match(r'^[\(‘’"]?\d', r['c'])])
    return G

# --------------------------------------------------------------- reporting
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('report'); ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    R = load_pairs(a.report)
    G = gates(R)
    occ = sum(r['n'] for r in R)
    if a.json:
        print(json.dumps({'occurrences': occ, 'unique': len(R), 'gates': G},
                         ensure_ascii=False, indent=1)); 
        sys.exit(0 if all(g['pass'] for g in G) else 1)
    print(f'corpus: {occ:,} paragraph occurrences, {len(R):,} unique\n')
    print(f'{"gate":6} {"result":8} {"paras":>9} {"unique":>8}  title')
    for g in G:
        print(f'{g["id"]:6} {"PASS" if g["pass"] else "FAIL":8} '
              f'{g["paragraphs"]:9,} {g["unique"]:8,}  {g["title"]}')
    bad = [g for g in G if not g['pass']]
    print(f'\n{len(G)-len(bad)}/{len(G)} gates pass')
    if bad:
        print('\nfirst failing example per gate:')
        for g in bad[:6]:
            if g['examples']:
                e = g['examples'][0]
                print(f'\n[{g["id"]}] {g["title"]}\n  EN: {e["en"]}\n  CY: {e["cy"]}')
    sys.exit(1 if bad else 0)

if __name__ == '__main__':
    main()
