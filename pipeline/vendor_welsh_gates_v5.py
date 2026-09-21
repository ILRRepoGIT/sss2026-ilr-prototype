#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSS2026 — Welsh acceptance gates, v5.

WHAT CHANGED FROM v4 (v5, for V4.7)
    V4.6 passed 47 of 48 v4 gates and the independent review still found nine
    partially routed renderer paths, six declared-but-dormant frames, five
    Welsh destinations with no catalogue row, 311,854 English stacked-chart row
    labels and 8,712 captions stating "10" over 1–9 rows. v5 therefore:
      - treats every stacked-chart ROW and every derived-table ROW as a surface
        (STK-*), and asserts captions state the rendered fact (STK-caption);
      - tests ROUTE COMPLETENESS per path: a path passes only when every child
        string it emits has a source (UI-path now lists children);
      - asserts declared frames are CONSUMED and heading frames match the
        rendered column count (FRAME-*);
      - scans the WHOLE payload for ⟪missing:*⟫ markers and requires every
        marker key to have a catalogue destination (CAT-marker, CAT-destination);
      - requires the build to embed its own gate results and, in release mode,
        to be a release configuration (GOV-results, GOV-mode);
      - writes a reproducibility BUNDLE (--bundle): runner hash, command line,
        framework hash, baseline hash, evidence hash, results;
      - ships a browser gate (browser_gate_provenance.py) for data-i18n-source
        provenance on rendered DOM, recorded as BROWSER-provenance.
    Seven new seeded faults; 48/48 on v5.0.0.

WHAT CHANGED FROM v3, AND WHY
    v3 ran over every generated surface and V4.5 passed all of its blocking gates.
    The independent V4.5 review then found 6,362 records in four deterministic
    defect families that v3 could not see, because v3 still looked for the
    SPELLING of a previously observed defect rather than for the FEATURE the
    output has to carry. v4 is rebuilt on the principles the review asked for:

    1.  ONE EXECUTABLE MANIFEST.  Every gate is declared in MANIFEST below with
        its family, surface, blocking status and the framework rule it enforces.
        The headline pass count is derived from that manifest at run time. A
        compliance record can no longer say "26 + 4" when the runner holds 25 + 5.

    2.  INSTANCE POPULATIONS.  Module paragraphs are loaded one row per paragraph
        instance (271,966 in V4.5), never de-duplicated. Every gate publishes both
        the occurrence count and the unique-record count.

    3.  REQUIRED-FEATURE ASSERTIONS, NOT PROHIBITED-TOKEN SEARCHES.
        - CONJ traces every coordination boundary, classifies the follower
          (vowel / h- / configured function word / consonant / figure read
          vigesimally) and compares the emitted a/ac with the configured form.
        - AGR carries the singleton antecedent through the whole clause and
          rejects ANY plural feature — arbitrary "eu + noun", plural pronouns,
          plural verb inflections — not a fixed marker list. It also asserts that
          a possession role present in the English is realised in the Welsh
          (ganddo / ganddi / gan …), so a deletion cannot satisfy the gate.
        - ROLE compares the qualifier roles the English carries with the roles
          the Welsh realises, from a role table read from the framework.
        - MUT checks numeral mutation after every soft-mutation trigger from
          the framework's own trigger list, not one memorised example.
        - UI is a static analysis of the client source: every render path,
          direct .label access where a Welsh helper exists, English literals
          reaching innerHTML / textContent / aria-label / title without the
          language layer, Welsh literals in code, and "|| fallback" strings that
          silently defeat fail-the-build.
        - CAT asserts key presence, value presence (release mode), a generic
          binder, and the metric schema (labelCy / baseNoteCy).
        - GOV asserts the build stamps the framework hash, gate manifest hash,
          surface counts and every active provisional ruling.

    4.  DEVELOPMENT vs RELEASE MODE (--mode).  Development may show an explicit
        missing-translation marker and empty catalogue values; release fails on
        every missing, fallback or unbound value.

    5.  MUTATION TESTING (--selftest).  One known fault per family is seeded into
        a synthetic record and the corresponding gate MUST fail. If it does not,
        the runner exits non-zero. A gate that cannot detect its own seeded fault
        is not a gate.

    6.  EVIDENCE (--evidence out.ndjson.gz).  One row per finding: gate id, state
        key, surface, module, paragraph index, matched fragment, locked English,
        Welsh output. This is the archive the reviewer asked for.

    The oracle re-derives configuration from the framework workbook
    (--framework <xlsx>) where it can, so that a coding error shared by the
    generator and this runner cannot make both agree. If openpyxl or the
    workbook is unavailable it falls back to the embedded defaults and says so
    in the GOV-config gate.

USAGE
    python welsh_acceptance_gates_v4.py report.html [--mode dev|release]
        [--framework fw.xlsx] [--json out.json] [--evidence out.ndjson.gz]
        [--baseline lock.json | --emit-lock lock.json]
    python welsh_acceptance_gates_v4.py --pairs pairs.jsonl --payload payload.json --js client.js ...
    python welsh_acceptance_gates_v4.py --selftest
"""
import sys, json, io, re, argparse, collections, hashlib, gzip, os

VERSION = '5.0.0'

# =============================================================================
# 1. THE MANIFEST — the single source of truth for what this runner asserts
# =============================================================================
# id, family, surface, blocking(True)/report(False)/manual(None), framework ref, title
MANIFEST = [
 # PUB — nothing internal may reach a reader
 ('PUB-placeholder', 'PUB',  'all',       True,  'D53',        'Internal placeholder, instruction or missing-translation marker in Welsh output'),
 ('PUB-empty',       'PUB',  'all',       True,  'D53',        'Welsh value empty where English is present'),
 ('PUB-copy',        'PUB',  'all',       True,  'PR-05/D36',  'Welsh identical to English and NOT on the signed loan/approved-string list'),
 ('PUB-copy-review', 'PUB',  'all',       False, 'sheet 23',   'Welsh identical to English and on the list but flagged for wording review'),
 ('PUB-leak',        'PUB',  'all',       True,  'D53',        'English function word inside a Welsh string'),
 # DIS — distinct English must give distinct Welsh
 ('DIS-module',      'DIS',  'module',    True,  'D57',        'Distinct English collapsing to one Welsh string'),
 ('DIS-h1',          'DIS',  'h1',        True,  'D57',        'Distinct English collapsing to one Welsh string'),
 ('DIS-h2',          'DIS',  'h2',        True,  'D57',        'Distinct English collapsing to one Welsh string'),
 ('DIS-scope',       'DIS',  'scope',     True,  'D50',        'Distinct English collapsing to one Welsh string'),
 # PAR — the same facts in both languages
 ('PAR-lost',        'PAR',  'module+h1', True,  'D57',        'A figure 11+ in the English has no counterpart in the Welsh'),
 ('PAR-added',       'PAR',  'module+h1', True,  'D57/PR-12',  'The Welsh states a figure 11+ the English does not'),
 ('PAR-follow',      'PAR',  'module',    True,  'D57',        'Follower list present in one language only (fact-flag test, not phrase test)'),
 ('PAR-generic',     'PAR',  'module',    True,  'D57',        '"Selected group" shorthand present in one language only'),
 # ROLE — semantic roles consumed identically
 ('ROLE-outer',      'ROLE', 'module',    True,  'D44/D57/D61','Outer cohort qualifier carried by the English is not realised in the Welsh'),
 ('ROLE-extra',      'ROLE', 'module',    True,  'D57/D61',    'Welsh realises a qualifier role the English does not carry'),
 ('ROLE-excepted',   'ROLE', 'module',    False, 'sheet 42',   'Welsh carries a role the locked English omits — signed parity exception in force'),
 # NUM — one realiser, every surface
 ('NUM-figword',     'NUM',  'prose',     True,  'D03',        'Small numeral as a figure before a written base (N o’r <word>)'),
 ('NUM-fignoun',     'NUM',  'prose',     True,  'D03',        'Small numeral as a figure before a countable noun in prose'),
 ('NUM-figcite',     'NUM',  'prose',     True,  'D03',        'Small numeral as a figure before a quoted citation (FT-16)'),
 ('NUM-zero',        'NUM',  'all',       True,  'D19',        'Digit zero in running prose instead of a negative branch'),
 ('NUM-opts-register','NUM', 'opts',      False, 'D36',        'Figure-led option labels reproduced verbatim from the approved survey (SURVEY register — expected)'),
 # MUT — mutation after configured triggers
 ('MUT-numeral',     'MUT',  'all',       True,  'sheet 07/08','Numeral unmutated after a soft-mutation trigger (gan dau → gan ddau)'),
 ('MUT-aspirate',    'MUT',  'all',       True,  'EX-23',      'Soft mutation where the trigger takes the aspirate (tua deirgwaith)'),
 # CONJ — a/ac decided by the follower's class, from the configured table
 ('CONJ-vowel',      'CONJ', 'all',       True,  'CONJ-01',    'a before a vowel-initial word'),
 ('CONJ-h',          'CONJ', 'all',       True,  'CONJ-02',    'ac before h-'),
 ('CONJ-fnword',     'CONJ', 'all',       True,  'CONJ-03/PR-13','a before a configured function word (mae, roedd, sydd, felly …)'),
 ('CONJ-neg',        'CONJ', 'all',       True,  'PR-04',      'a before ni / nid / na / nad (PR-04 configured value)'),
 ('CONJ-vig',        'CONJ', 'all',       True,  'CONJ-06',    'a/ac before a figure disagrees with its vigesimal reading'),
 ('CONJ-consonant',  'CONJ', 'all',       True,  'CONJ-04',    'ac before an ordinary consonant'),
 # AGR — singular antecedent, singular clause
 ('AGR-possessive',  'AGR',  'all',       True,  'D56',        'Plural possessive (eu + noun) inside the clause of a singleton antecedent'),
 ('AGR-pronoun',     'AGR',  'all',       True,  'D56',        'Plural pronoun or inflected preposition inside the clause of a singleton antecedent'),
 ('AGR-verb',        'AGR',  'all',       True,  'D56',        'Plural verb inflection inside the clause of a singleton antecedent'),
 ('AGR-partitive',   'AGR',  'all',       True,  'D56',        'Partitive taken over a singular set (un o’r unig …)'),
 ('AGR-possessor',   'AGR',  'all',       True,  'D56/D62/PR-14','Possession role carried by the English is missing from the Welsh (a oedd anabledd; well beidio)'),
 ('AGR-orphan-mut',  'AGR',  'all',       True,  'sheet 07',   'Mutation left standing after its trigger was deleted (well beidio) or removed with it (well peidio)'),
 # POL — polarity and the provisional recast
 ('POL-affirmative', 'POL',  'all',       True,  'PR-02',      'Nil count with a negative predicate and an AFFIRMATIVE cohort not recast (deterministic PR-02 class)'),
 ('POL-review',      'POL',  'all',       False, 'FT-11',      'Nil count whose defining cohort is itself negative — linguist review class (FT11-Q1…Q8)'),
 ('POL-uniform',     'POL',  'all',       True,  'D55',        'Same fact record realised with different PR-02 strategies on module and closing surfaces'),
 # STK — stacked and derived rows are surfaces too
 ('STK-label',       'STK',  'stack',     True,  'D70',        'Stacked-chart row label has no stable code / is rendered from the English row string'),
 ('STK-caption',     'STK',  'stack',     True,  'D71',        'Caption states a fixed count that differs from the rendered row count'),
 ('STK-code-map',    'STK',  'stack',     False, 'D70',        'Stack labels with an optsCy mapping available (coverage, for the record)'),
 # FRAME — declared frames must be consumed and match what is rendered
 ('FRAME-dormant',   'FRAME','client',    True,  'D72',        'Declared frame never consumed by the client (and not marked DEPRECATED)'),
 ('FRAME-shape',     'FRAME','client',    True,  'D72',        'Heading frame column count differs from the rendered table'),
 # UI — every emitted string comes from the language layer
 ('UI-path',         'UI',   'client',    True,  'D59/D63/D72','Renderer path with at least one child string still English-only in Welsh mode (route completeness)'),
 ('UI-literal',      'UI',   'client',    True,  'D59/D63',    'English sentence literal reaches the DOM outside the language layer'),
 ('UI-field',        'UI',   'client',    True,  'D59',        'Direct .label / .desc read where a Welsh field and helper exist'),
 ('UI-welsh-in-code','UI',   'client',    True,  'D64',        'Welsh text embedded in application code'),
 ('UI-fallback',     'UI',   'client',    True,  'D64',        '"|| literal" fallback after a catalogue lookup — defeats fail-the-build'),
 ('UI-lang',         'UI',   'client',    True,  'D59',        'No single applyLanguageState() synchroniser'),
 ('UI-legend-parity','UI',   'client',    True,  'sheet 28',   'Chart legend Welsh disagrees with the catalogue optsCy for the same English label'),
 # CAT — the static lane must be complete and bound
 ('CAT-keys',        'CAT',  'catalogue', True,  'D59',        'Declared static strings exceed the embedded catalogue keys'),
 ('CAT-values',      'CAT',  'catalogue', True,  'D64',        'Catalogue key with an empty value (release mode fails; dev mode reports)'),
 ('CAT-binder',      'CAT',  'catalogue', True,  'D59/D63',    'No generic binding mechanism (data-i18n or t()/cat() used across consumers)'),
 ('CAT-schema',      'CAT',  'catalogue', True,  'D63',        'Metric definition has no labelCy / baseNoteCy destination for Welsh'),
 ('CAT-marker',      'CAT',  'payload',   True,  'D64/D69',    '⟪missing:key⟫ marker anywhere in the payload (release fails; dev reports)'),
 ('CAT-destination', 'CAT',  'catalogue', True,  'D63/D72',    'Marker or consumer references a key that has no catalogue row (nowhere for the translation to arrive)'),
 # GOV — the build proves what it was built from
 ('GOV-config',      'GOV',  'runner',    False, 'D58',        'Configuration source for this run (workbook or embedded defaults)'),
 ('GOV-stamp',       'GOV',  'build',     True,  'D60',        'Build metadata lacks framework hash, gate-manifest hash or surface counts'),
 ('GOV-provisional', 'GOV',  'build',     True,  'D51/D60',    'Active provisional ruling not stamped into build metadata'),
 ('GOV-lock',        'GOV',  'build',     True,  'D01',        'English projection differs from the locked baseline (needs --baseline)'),
 ('GOV-results',     'GOV',  'build',     True,  'D68',        'Build does not embed its own gate results (runner hash, mode, pass/total, evidence hash)'),
 ('GOV-mode',        'GOV',  'build',     True,  'D69',        'Release configuration: buildMetadata.mode, CONFIG.reviewMode, CONFIG.sensitiveFilters against the signed value'),
 # MANUAL — cannot be evidenced by this runner; the manifest says so
 ('PERF-device',     'PERF', 'manual',    None,  'D65',        'Representative school-laptop load, toggle, filter, chart, table and print run'),
 ('A11Y-assist',     'A11Y', 'manual',    None,  'D65',        'Keyboard, focus, live-region, caption, title/ARIA language and document lang verified'),
 ('BROWSER-provenance','UI', 'browser',   None,  'D72',        'Every rendered visible/title/aria string in Welsh mode carries a data-i18n-source (browser_gate_provenance.py)'),
]
MANIFEST_HASH = hashlib.sha256(json.dumps([m[:4] for m in MANIFEST]).encode()).hexdigest()[:16]

# =============================================================================
# 2. CONFIGURATION — read from the framework when possible, defaults otherwise
# =============================================================================
CFG = {
  'source': 'embedded defaults',
  # CONJ-03 function words taking ac (sheet 11). v1.9 adds sydd / sy’n, maent, roeddent, mi, wedyn.
  'ac_fnwords': ['mae','maent','roedd','roeddent','sydd','sy’n',"sy'n",'meddai','megis','mor','mwy','mwyach',
                 'myn','fe','fel','felly','fry','mi','wedyn'],
  # PR-04: ac before the negative particles
  'ac_neg': ['ni','nid','na','nad'],
  # Soft-mutation triggers before a numeral (sheet 07/12)
  'soft_triggers': ['gan','o','i','am','ar','at','dan','dros','drwy','trwy','heb','hyd','wrth','neu','dy','ei'],
  # numerals that soft-mutate and their radical form
  'soft_numerals': {'dau':'ddau','dwy':'ddwy','tri':'dri','tair':'dair','pedwar':'bedwar','pedair':'bedair',
                    'pump':'bump','pum':'bum','deg':'ddeg','deng':'ddeng'},
  # aspirate triggers (EX-23 'tua'; a/â/gyda/tri/chwe handled elsewhere)
  'aspirate_triggers': ['tua','â','gyda','tri','chwe'],
  # signed loan / approved-string exception list (sheet 23, ATTESTED-* with identical Welsh)
  'copy_ok': ['bmx','badminton','boccia','parkour','tennis','triathlon','kung fu','muay thai','padel','pickleball','taekwondo'],
  # approved but FLAGGED for wording review (sheet 23)
  'copy_flagged': ['breakdancing','croquet','orienteering'],
  # role table: English qualifier phrase → Welsh realisations (sheet 22)
  'roles': [
    ('dl-outer', r'disability and/or learning difficulty',              [r'anabledd a/neu anhawster dysgu']),
    ('ed-outer', r'ethnically diverse background',                      [r'gefndir ethnig amrywiol']),
    ('wl-outer', r'\bspeak Welsh\b|Welsh[- ]speak',                     [r'siarad Cymraeg']),
  ],
  # generic shorthand pair (both or neither)
  'generic_pair': (r'selected group', r'grŵp a ddewiswyd|grŵp hwn|grŵp dan sylw'),
  # signed parity exceptions (framework sheet 42): (module, role) pairs where the locked English omits a role the
  # Welsh carries, accepted until the English is corrected. Consulted by ROLE-extra; excepted hits go to ROLE-excepted.
  'parity_exceptions': [('f2', 'dl-outer'), ('f2', 'ed-outer'), ('f2', 'wl-outer')],
  # provisional rulings expected in the build stamp
  'provisional_ids': ['PR-01','PR-02','PR-03','PR-04','PR-05','PR-06','PR-07','PR-08','PR-09','PR-10','PR-11','PR-12','PR-13','PR-14'],
  # UI-DYN path manifest: id, description, regex that betrays the English-only path
  'ui_paths': [
    # id, description, [child patterns that betray an English-only branch] — a path passes only when ALL are absent
    ('UI-DYN-01','renderBanner mobile rail toggle',          [r'"Explore results']),
    ('UI-DYN-02','renderClosing no-findings branch',         [r'No reportable findings for this theme']),
    ('UI-DYN-03','renderRail selected-group chip',           [r'esc\(c\.label\)']),
    ('UI-DYN-04','renderRail chip remove control',           [r'aria-label="Remove selected group"']),
    ('UI-DYN-05','renderRail no-selection state',            [r'None — select a highlighted chart value']),
    ('UI-DYN-06','renderChart base and context wording',     [r'" · multiple answers permitted"', r'" · shown for "', r'whole school shown for context', r'" · Showing: "']),
    ('UI-DYN-07','renderChart filter instruction',           [r'Click a bar to filter the report']),
    ('UI-DYN-08','barTitle / bar accessible text',           [r'Selected: this answer defines the selected group', r'\(v === 1 \? "pupil" : "pupils"\)', r'"Based on: " \+ base', r'"View: " \+', r'suppressed in this view', r'cannot be selected', r'"Multiple answers permitted"']),
    ('UI-DYN-09','renderChart ghost / comparison notes',     [r'title="Whole school: ', r'Dashed outline: the whole school', r'Other sports” refers|Other sports" refers']),
    ('UI-DYN-10','renderChart chart accessible name',        [r'bar chart; figures in the data table below\.']),
    ('UI-DYN-11','dataTable controls, caption, headings',    [r'<summary>View data table', r"<th scope='col'>Answer<\\?/th><th scope='col'>Pupil responses", r"scope='col'>Pupil responses"]),
    ('UI-DYN-12','renderChart ranking note',                 [r'"Showing the leading "']),
    ('UI-DYN-13','stateMsg no-data / applicability',         [r'nd: \["No responses recorded"']),
    ('UI-DYN-14','paywallBox / renderSuppressed bodies',     [r'Not enough data available for this selection', r'Fewer than five pupils match this selection', r'Fewer than five pupils are in this group']),
    ('UI-DYN-15','renderCoSelection heading, base, tooltips',[r'What else did these pupils select\?', r'\(o\.v === 1 \? " pupil" : " pupils"\)']),
    ('UI-DYN-16','renderStack legend, rows, table, tooltips',[r'Stacked bar chart; figures in the data table below', r"<th scope='col'>Sport<", r"<th scope='col'>Total pupils<", r'\(v === 1 \? " pupil" : " pupils"\)\) \+', r"esc\(r\[0\]\)"]),
    ('UI-DYN-17','renderModules derived row charts / tables',[r'"Pupils who did at least one sport', r"<th scope='col'>Year group<", r"<th scope='col'>Group<", r"<th scope='col'>Base<", r'" — Boys"|" \\u2014 Boys"', r'" of " \+', r'label: "In PE or lesson time"']),
    ('UI-DYN-18','renderAppendices groups, headings, labels',[r'"Full current-sport results"', r'"Sport settings and frequency"', r'"Full latent demand"', r'"Full unmet demand"', r'"Inclusion and demographics"', r"<th scope='col'>Answer<\\?/th><th scope='col'>All<", r"<th scope='col'>Boys<", r'"<table><caption>Base: "']),
  ],
  # frames deliberately withdrawn from the catalogue (sheet 43 status DEPRECATED) — not counted as dormant
  'deprecated_frames': ['msg.no_data_title', 'msg.no_data_body'],
  # heading frames → the renderer whose <th scope='col'> count they must match
  'heading_frames': {'ui.table_headings': 'dataTable'},
  # signed release configuration (sheet 02 D69). None = not yet signed → reported, not asserted.
  'sensitive_filters': None,
  # keys the payload may reference as destinations; every marker key must be one of these or a handoff key
  'stack_caption_key': 'stack_table_caption',

}

def load_framework(path):
    """Overwrite the embedded defaults from the governing workbook where the sheets exist."""
    try:
        from openpyxl import load_workbook
    except Exception:
        CFG['source'] = 'embedded defaults (openpyxl unavailable)'; return
    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception as e:
        CFG['source'] = f'embedded defaults (workbook unreadable: {e})'; return
    got = []
    if '11 Conjunctions' in wb.sheetnames:
        for row in wb['11 Conjunctions'].iter_rows(values_only=True):
            if row and row[0] == 'CONJ-03' and row[2]:
                m = re.search(r'one of:\s*(.+)$', str(row[2]))
                if m:
                    CFG['ac_fnwords'] = [w.strip() for w in re.split(r'[,;]', m.group(1)) if w.strip()]
                    got.append('CONJ-03')
    if '23 Answer labels' in wb.sheetnames:
        ok, flagged = [], []
        for row in wb['23 Answer labels'].iter_rows(min_row=4, values_only=True):
            if not row or not row[0] or not row[1]: continue
            en, cy, status = str(row[0]), str(row[1]), str(row[7] or '')
            if en.strip().lower() == cy.strip().lower():
                (flagged if 'FLAGGED' in status else ok).append(en.strip().lower())
        if ok: CFG['copy_ok'] = ok; CFG['copy_flagged'] = flagged; got.append('sheet 23 copy list')
    if '42 Signed parity exceptions' in wb.sheetnames:
        exc = []
        for row in wb['42 Signed parity exceptions'].iter_rows(min_row=4, values_only=True):
            if row and row[0] and row[1]: exc.append((str(row[0]).strip(), str(row[1]).strip()))
        CFG['parity_exceptions'] = exc; got.append('sheet 42 exceptions')
    if '23 Answer labels' in wb.sheetnames:
        lab = {}
        for row in wb['23 Answer labels'].iter_rows(min_row=4, values_only=True):
            if row and row[0] and row[1]: lab[str(row[0]).strip().replace('’', "'")] = str(row[1]).strip()
        CFG['labels'] = lab; got.append('sheet 23 labels')
    if '43 Interface frames' in wb.sheetnames:
        dep = []
        for row in wb['43 Interface frames'].iter_rows(min_row=4, values_only=True):
            if row and row[0] and str(row[7] or '').strip().upper() == 'DEPRECATED': dep.append(str(row[0]).strip())
        if dep: CFG['deprecated_frames'] = dep; got.append('sheet 43 deprecations')
    if '02 Project decisions' in wb.sheetnames:
        for row in wb['02 Project decisions'].iter_rows(min_row=4, values_only=True):
            if row and row[0] == 'D69' and row[4]:
                m = re.search(r'sensitiveFilters\s*[:=]\s*(true|false)', str(row[4]), re.I)
                if m: CFG['sensitive_filters'] = (m.group(1).lower() == 'true'); got.append('D69 release config')
    if '39 Provisional rulings' in wb.sheetnames:
        ids = []
        for row in wb['39 Provisional rulings'].iter_rows(min_row=4, values_only=True):
            if row and row[0] and re.match(r'PR-\d+$', str(row[0])): ids.append(str(row[0]))
        if ids: CFG['provisional_ids'] = ids; got.append('sheet 39 rulings')
    CFG['source'] = f'{os.path.basename(path)} — read: {", ".join(got) or "nothing usable; defaults kept"}'
    CFG['framework_sha256'] = hashlib.sha256(open(path, 'rb').read()).hexdigest()

# =============================================================================
# 3. LOADING — instance level, every surface
# =============================================================================
def rec(s, m, i, t, c, k=None):
    return {'s': s, 'm': m, 'i': i, 't': t or '', 'c': c or '', 'k': k}

def surfaces_from_states(states, metric_defs):
    S = {'module': [], 'h1': [], 'h2': [], 'scope': [], 'opts': [], 'stack': []}
    for sk, st in states.items():
        for mid, m in (st.get('mod') or {}).items():
            for i, p in enumerate(m.get('p') or []):
                S['module'].append(rec(sk, mid, i, p.get('t'), p.get('c'), p.get('k')))
        for k, v in (st.get('h1') or {}).items():
            for i, x in enumerate(v):
                if isinstance(x, dict): S['h1'].append(rec(sk, 'h1:' + k, i, x.get('t') or x.get('en'), x.get('c')))
        for i, x in enumerate(st.get('h2') or []):
            if isinstance(x, dict) and x.get('c'): S['h2'].append(rec(sk, 'h2', i, x.get('t') or x.get('en'), x.get('c')))
        sc = st.get('scope') or {}
        S['scope'].append(rec(sk, 'scope', 0, sc.get('short'), sc.get('shortCy')))
        for ctx, rows in (st.get('stk') or {}).items():
            S['stack'].append({'s': sk, 'm': 'stk:' + ctx, 'i': 0, 'n': len(rows), 't': '', 'c': '',
                               'labels': [r[0] if isinstance(r, list) else r for r in rows],
                               'coded': all(isinstance(r, list) and len(r) >= 4 and isinstance(r[3], str) for r in rows) if rows else True})
    for mid, md in (metric_defs or {}).items():
        cy = md.get('optsCy') or []
        for i, o in enumerate(md.get('opts') or []):
            en = o[1] if isinstance(o, (list, tuple)) else o
            w = cy[i] if i < len(cy) else None
            w = w[1] if isinstance(w, (list, tuple)) else w
            S['opts'].append(rec('*', 'opts:' + mid, i, en, w))
    return S

def load_report(path):
    raw, js, hit = None, [], False
    with io.open(path, encoding='utf-8') as fh:
        for line in fh:
            if raw is None and 'id="report-data"' in line:
                raw = line.split('>', 1)[1].rsplit('</script', 1)[0]; continue
            if hit: js.append(line)
            elif re.match(r'\s*<script>\s*$', line): hit = True
    if raw is None: sys.exit('no report-data block in ' + path)
    D = json.loads(raw)
    S = surfaces_from_states(D['states'], D.get('metricDefs'))
    return D, S, ''.join(js)

def load_parts(pairs, payload, jsp, stk=None):
    D = json.load(io.open(payload, encoding='utf-8'))
    S = {'module': [], 'h1': [], 'h2': [], 'scope': [], 'opts': [], 'stack': []}
    if stk:
        with io.open(stk, encoding='utf-8') as fh:
            for line in fh:
                r = json.loads(line)
                if r.get('ctx') == '__rows__': continue
                S['stack'].append({'s': r['s'], 'm': 'stk:' + r['ctx'], 'i': 0, 'n': r['n'], 't': '', 'c': '',
                                   'labels': r.get('labels', []), 'coded': bool(r.get('coded', False))})
    with io.open(pairs, encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            m = r['m']
            surf = 'h1' if m.startswith('h1:') else ('h2' if m == 'h2' else ('scope' if m == 'scope' else 'module'))
            S[surf].append(rec(r['s'], m, r.get('i', 0), r.get('t'), r.get('c'), r.get('k')))
    for mid, md in (D.get('metricDefs') or {}).items():
        cy = md.get('optsCy') or []
        for i, o in enumerate(md.get('opts') or []):
            en = o[1] if isinstance(o, (list, tuple)) else o
            w = cy[i] if i < len(cy) else None
            w = w[1] if isinstance(w, (list, tuple)) else w
            S['opts'].append(rec('*', 'opts:' + mid, i, en, w))
    js = io.open(jsp, encoding='utf-8').read() if jsp else ''
    return D, S, js

# =============================================================================
# 4. VOCABULARY
# =============================================================================
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
VOWELS = 'aeiouwyâêîôûŵŷáéíóú'
CY_NUM = {'un':1,'dau':2,'dwy':2,'ddau':2,'ddwy':2,'tri':3,'tair':3,'dair':3,'thri':3,'thair':3,
 'pedwar':4,'pedair':4,'bedwar':4,'bedair':4,'phedwar':4,'phedair':4,'pump':5,'pum':5,'bum':5,
 'bump':5,'phum':5,'chwech':6,'chwe':6,'saith':7,'wyth':8,'naw':9,'deg':10,'ddeg':10,'ddeng':10,
 'unwaith':1,'dwywaith':2,'ddwywaith':2,'deirgwaith':3,'theirgwaith':3}
EN_NUM = {'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,
          'ten':10,'once':1,'twice':2,'three times':3}
PLACEHOLDER = re.compile(r'\[[^\]]{4,}\]|question-dependent|see sheet|TODO|FIXME|⟪|\bTBC\b|\[\[missing|MISSING_TRANSLATION|\{\{')
ENGLISH_LEAK = re.compile(r'\b(the|of|and|who|were|said|most|pupils|school|among|across|selected)\b', re.I)
SINGLETON = re.compile(r"\b(?:[Uu]nig (?:ferch|fachgen|ddisgybl)|(?<!yr )(?<!Yr )un (?:disgybl|ddisgybl|ferch|fachgen))\b")
REL_VERB = re.compile(r"^(?:\w+(?:odd|wyd|ant|ent|asant|esant|ai|ir|on)|oedd|yw|ydynt|ydyw|oeddent|oes|fydd|fyddai|allai|allant|sydd)$")
PLURAL_PRON = re.compile(r"\b(ganddynt|ohonynt|iddynt|arnynt|amdanynt|hwy|hwythau|nhw|eu hunain)\b")
PLURAL_VERB = re.compile(r"\b(maent|ydynt|oeddent|oeddynt|byddent|baent|gallant|dywedasant|wnaethant|nododd\w*ant|\w{3,}(?:asant|esant))\b")
PLURAL_POSS = re.compile(r"\beu (\w+)")
# object-pronoun readings of 'eu' that refer to a plural NON-person noun (campau, geiriau, syniadau-as-object)
EU_OBJECT_OK = {'hoffi','dweud','gwneud','cael','dewis','gweld','mwynhau','chwarae','cynnwys','nodi','hadrodd','trin'}
FIG = r'(?<![\d,.])'
EVIDENCE = []   # global evidence rows

def numset(s, words, min_digit=0):
    o = {int(x) for x in re.findall(r'\d+', (s or '').replace(',', '')) if int(x) >= min_digit}
    for k, v in words.items():
        if v >= min_digit and re.search(r'\b' + k + r'\b', s or '', re.I): o.add(v)
    return o

def clause_of(cy):
    """The antecedent's bounded clause: from the singleton up to the main-clause comma or full stop."""
    m = SINGLETON.search(cy)
    if not m: return ''
    rest = cy[m.start():]
    cut = re.search(r',\s+(?:‘|\w+ oedd yr ateb|dewisodd|dywedodd|nid oedd|roedd|nododd|byddai)', rest)
    return rest[:cut.start()] if cut else rest

def js_strings(line):
    """String literals on one JS line, honouring quotes and escapes (regex cannot)."""
    out, i, n = [], 0, len(line)
    while i < n:
        ch = line[i]
        if ch in '"\'`':
            j = i + 1; buf = []
            while j < n and line[j] != ch:
                if line[j] == '\\' and j + 1 < n: buf.append(line[j + 1]); j += 2; continue
                buf.append(line[j]); j += 1
            out.append(''.join(buf)); i = j + 1
        else: i += 1
    return out

# =============================================================================
# 5. THE GATES
# =============================================================================
def run(D, S, js, mode='dev', baseline=None):
    R = {}          # id -> result
    def hit(gid, r, frag=''):
        R.setdefault(gid, []).append((r, frag))
        EVIDENCE.append({'gate': gid, 'state': r['s'], 'surface': r['m'].split(':')[0], 'module': r['m'],
                         'index': r['i'], 'kind': r.get('k'), 'matched': frag, 'en': r['t'], 'cy': r['c']})
    def client(gid, what, frag=''):
        hit(gid, rec('*', 'client', 0, what, ''), frag)
    ALL = S['module'] + S['h1'] + S['h2'] + S['scope'] + S['opts']
    PROSE = S['module'] + S['h1'] + S['h2'] + S['scope']
    for k in [m[0] for m in MANIFEST]: R.setdefault(k, [])

    # ---- PUB -----------------------------------------------------------------
    for r in ALL:
        cy, en = r['c'], r['t']
        if cy and PLACEHOLDER.search(cy): hit('PUB-placeholder', r, PLACEHOLDER.search(cy).group(0))
        if en.strip() and not cy.strip(): hit('PUB-empty', r)
        if cy and cy == en and re.search(r'[A-Za-zÀ-ÿ]{3}', cy):
            key = cy.strip().lower()
            if key in CFG['copy_flagged']: hit('PUB-copy-review', r, cy)
            elif key not in CFG['copy_ok'] and not re.fullmatch(r'[\d\W]+|\d+\+?|Blwyddyn \d+|Y\d+', cy.strip()):
                hit('PUB-copy', r, cy)
        if cy and ENGLISH_LEAK.search(cy): hit('PUB-leak', r, ENGLISH_LEAK.search(cy).group(0))

    # ---- DIS -----------------------------------------------------------------
    for name in ('module', 'h1', 'h2', 'scope'):
        by = collections.defaultdict(set)
        for r in S[name]:
            if r['c']: by[r['c']].add(r['t'])
        coll = {k for k, v in by.items() if len(v) > 1}
        for r in S[name]:
            if r['c'] in coll: hit('DIS-' + name, r, r['c'][:80])

    # ---- PAR -----------------------------------------------------------------
    for r in S['module'] + S['h1']:
        if not r['c']: continue
        en, cy = numset(r['t'], EN_NUM, 11), numset(r['c'], {}, 11)
        if en - cy: hit('PAR-lost', r, str(sorted(en - cy)))
        if cy - en: hit('PAR-added', r, str(sorted(cy - en)))
    for r in S['module']:
        en_f = bool(re.search(r'\bfollowed by\b', r['t'])); cy_f = bool(re.search(r'\bac yna\b', r['c']))
        if en_f != cy_f: hit('PAR-follow', r, 'EN follower=%s CY follower=%s' % (en_f, cy_f))
        gp = CFG['generic_pair']
        en_g = bool(re.search(gp[0], r['t'], re.I)); cy_g = bool(re.search(gp[1], r['c']))
        if en_g != cy_g: hit('PAR-generic', r, 'EN generic=%s CY generic=%s' % (en_g, cy_g))

    # ---- ROLE ----------------------------------------------------------------
    for r in S['module']:
        for rid, enp, cyps in CFG['roles']:
            en_has = bool(re.search(enp, r['t'], re.I)); cy_has = any(re.search(p, r['c']) for p in cyps)
            if en_has and not cy_has: hit('ROLE-outer', r, rid)
            if cy_has and not en_has:
                hit('ROLE-excepted' if (r['m'], rid) in CFG['parity_exceptions'] else 'ROLE-extra', r, rid)

    # ---- NUM -----------------------------------------------------------------
    CYW = r'(?:un|dau|dwy|tri|tair|pedwar|pedair|pum|pump|chwe|chwech|saith|wyth|naw|deg)'
    NOUN = r'(?:disgybl|ddisgybl|merch|ferch|bachgen|fachgen|camp|gamp|ateb|opsiwn|gwaith|waith|ymateb|lleoliad)'
    for r in PROSE:
        cy = r['c']
        if re.search(FIG + r'[1-9] o’r ' + CYW + r'\b', cy): hit('NUM-figword', r)
        m = re.search(FIG + r'(?:[1-9]|10) ' + NOUN + r'\b', cy)
        if m and not re.search(r'Blwyddyn \d', m.group(0)): hit('NUM-fignoun', r, m.group(0))
        if re.search(r'(?<!lwyddyn )' + FIG + r'(?:[1-9]|10) ‘', cy): hit('NUM-figcite', r)
    for r in ALL:
        if re.search(FIG + r'0 o’r', r['c']): hit('NUM-zero', r)
    for r in S['opts']:
        if re.search(r'^\d+ ' + NOUN, r['c']): hit('NUM-opts-register', r, r['c'])

    # ---- MUT -----------------------------------------------------------------
    trig = '|'.join(CFG['soft_triggers']); rad = '|'.join(CFG['soft_numerals'].keys())
    rx_soft = re.compile(r'\b(' + trig + r') (' + rad + r')\b')
    rx_asp = re.compile(r'\btua (deirgwaith|ddwywaith|bedair|bum|ddeg)\b')
    for r in ALL:
        m = rx_soft.search(r['c'])
        if m:
            # 'o dau' etc. never legitimately occur; 'ei' masculine soft-mutates, feminine does not: skip 'ei'
            if m.group(1) != 'ei': hit('MUT-numeral', r, m.group(0) + ' → ' + m.group(1) + ' ' + CFG['soft_numerals'][m.group(2)])
        m = rx_asp.search(r['c'])
        if m: hit('MUT-aspirate', r, m.group(0))

    # ---- CONJ : classify every coordination follower -------------------------
    fn = set(w.lower() for w in CFG['ac_fnwords']); neg = set(CFG['ac_neg'])
    rx = re.compile(r'(^|[\s(‘“])(a|ac) ([\w’\'\d][\w’\'\d,]*)', re.U)
    for r in ALL:
        cy = r['c']
        for m in rx.finditer(cy):
            form, foll = m.group(2), m.group(3)
            fl = foll.lower().rstrip(',')
            if form == 'a' and REL_VERB.match(fl): continue   # relative particle, not the conjunction
            if fl[0].isdigit():
                lead = vig_lead(fl.replace(',', '').rstrip('+') or '0')
                want, gid = ('ac' if lead[0] in VOWELS else 'a'), 'CONJ-vig'
            elif fl in neg:                       want, gid = 'ac', 'CONJ-neg'
            elif fl in fn or fl.split('’')[0] in fn or fl.split("'")[0] in fn:
                                                  want, gid = 'ac', 'CONJ-fnword'
            elif fl[0] in VOWELS:                 want, gid = 'ac', 'CONJ-vowel'
            elif fl[0] == 'h':                    want, gid = 'a', 'CONJ-h'
            else:                                 want, gid = 'a', 'CONJ-consonant'
            if form != want: hit(gid, r, f'{form} {foll} → {want} {foll}')

    # ---- AGR : singleton antecedent, singular clause -------------------------
    for r in ALL:
        cy = r['c']
        if not SINGLETON.search(cy): continue
        cl = clause_of(cy) or cy
        for m in PLURAL_POSS.finditer(cl):
            if m.group(1).lower() not in EU_OBJECT_OK: hit('AGR-possessive', r, m.group(0))
        for m in PLURAL_PRON.finditer(cl): hit('AGR-pronoun', r, m.group(0))
        for m in PLURAL_VERB.finditer(cl):
            if m.group(1) not in ('cant', 'pedwarant'): hit('AGR-verb', r, m.group(0))
        if re.search(r'\bo’r unig\b', cy): hit('AGR-partitive', r, 'o’r unig')
        # required possession role
        en = r['t']
        if re.search(r'whether they have a disability', en, re.I) and re.search(r'a oedd anabledd', cy) \
           and not re.search(r'a oedd gandd\w+ anabledd', cy):
            hit('AGR-possessor', r, 'a oedd anabledd (possessor deleted)')
        if re.search(r'preferred not to say', en, re.I) and re.search(r"well (?:b|p)eidio", cy):
            hit('AGR-possessor', r, re.search(r"well (?:b|p)eidio", cy).group(0) + ' (gan X deleted)')
        if re.search(r'\bwell beidio\b', cy): hit('AGR-orphan-mut', r, 'well beidio — mutation with no trigger')
        if re.search(r'\bwell peidio\b', cy): hit('AGR-orphan-mut', r, 'well peidio — trigger and mutation both gone')

    # ---- POL -----------------------------------------------------------------
    # Three things are distinguished per fact record, from the LOCKED ENGLISH (the fact) not the Welsh (the output):
    #   cohort polarity   — is the defining cohort's relative clause negative?  (FT-11 review class when yes)
    #   predicate polarity— is the reported predicate negative?               (PR-02 applies when yes)
    #   strategy          — did the Welsh recast (Ni ddewisodd … ‘label’) or keep a negative predicate (stacked)?
    NEG = re.compile(r"\b(not|never|no|don’t|didn’t|don't|didn't|prefer(?:red)? not|unsure)\b", re.I)
    strat = collections.defaultdict(lambda: collections.defaultdict(lambda: collections.defaultdict(set)))
    for r in ALL:
        cy, en = r['c'], r['t']
        if not re.match(r'^(?:None of the|No pupil)', en): continue
        surf = 'h1' if r['m'].startswith('h1') else 'module'
        en = re.sub(r'‘[^’]*’|\([^)]*\)', '‘…’', en)   # answer labels and parentheticals carry no polarity
        verbs = list(re.finditer(r'\b(said|took part|selected|chose|answered|reported|did|found|were|enjoyed|spoke|feel|felt|think|thought|are|is|have|has)\b', en))
        who = en.find(' who ')
        pv = verbs[-1].start() if verbs else len(en)
        cohort = en[who:pv] if (who >= 0 and pv > who) else ''
        predicate = en[pv:]
        neg_coh, neg_pred = bool(NEG.search(cohort)), bool(NEG.search(predicate))
        recast = bool(re.match(r'^Ni ddewisodd', cy))
        inverse = bool(re.match(r'^(?:Roedd|Nid oedd) ', cy) and re.search(r'\bheb\b', cy))
        if neg_coh and re.search(r'\bnad\b|\bna\b|\bheb\b', cy):
            form = ('strict Ni…yr un…nad' if re.search(r'^N[ia]d? \w+ yr un[^.]*\bnad\b', cy)
                    else 'na-relative' if re.search(r'\bna\b', cy) else 'other negative cohort')
            hit('POL-review', r, f'{"recast" if recast else "inverse" if inverse else "faithful"}; {form}')
        if neg_pred:
            strategy = 'recast' if recast else 'inverse' if inverse else 'stacked'
            strat[r['s']]['neg-cohort' if neg_coh else 'aff-cohort'][surf].add(strategy)
            if strategy == 'stacked' and not neg_coh:
                hit('POL-affirmative', r, 'negative predicate under a negative matrix, affirmative cohort, not recast')
    for sk, byk in strat.items():
        for klass, d in byk.items():
            if 'module' in d and 'h1' in d and d['module'] != d['h1']:
                hit('POL-uniform', rec(sk, 'module+h1', 0, klass, ''), f'{klass}: module={sorted(d["module"])} h1={sorted(d["h1"])}')

    # ---- UI : static analysis of the client -----------------------------------
    if js:
        for pid, desc, pats in CFG['ui_paths']:
            hits = [pt for pt in pats if re.search(pt, js)]
            for pt in hits: client('UI-path', f'{pid} {desc} — child still English: {pt}', pt)
            R.setdefault('_paths', []).append({'id': pid, 'desc': desc, 'children': len(pats), 'english': len(hits),
                                               'status': 'complete' if not hits else ('partial' if len(hits) < len(pats) else 'english')})
        # direct .label where cohortLabel/optLabel exist
        has_helper = bool(re.search(r'const (cohortLabel|optLabel|labelOf)\s*=', js))
        for i, line in enumerate(js.split('\n'), 1):
            if not has_helper or 'isCy()' in line or 'optLabel(' in line or 'labelOf(' in line or 'cohortLabel(' in line: continue
            for m in re.finditer(r'esc\((c|o|coh|opt)\.(label|desc)\)|(?<![\w.])def\.label\b|(?<!\w)o\[1\](?!\s*,\s*cy)|esc\(r\[0\]\)|esc\(r\.y\)', line):
                if re.search(r'^\s*(//|\*)', line): continue
                client('UI-field', f'line {i}: {m.group(0)} read where a Welsh field / helper exists', m.group(0)); break
        # Welsh literals in code (outside the data payload)
        WELSH = re.compile(r'"([^"\n]*(?:ŵ|ŷ|’n |’r |yr wythnos|disgybl|Yn dangos|wedi’|Ddim yn|Cymraeg|ymateb)[^"\n]*)"')
        for m in WELSH.finditer(js):
            if 'language_label' in js[max(0, m.start() - 60):m.start()] and 'Cymraeg' in m.group(1) and len(m.group(1)) < 10: pass
            ln = js.count('\n', 0, m.start()) + 1
            client('UI-welsh-in-code', f'line {ln}: "{m.group(1)}"', m.group(1))
        for m in re.finditer(r'(CY\.(?:ui|handoff)\.[a-z_]+)\s*\|\|\s*"([^"]+)"', js):
            ln = js.count('\n', 0, m.start()) + 1
            client('UI-fallback', f'line {ln}: {m.group(1)} || "{m.group(2)}"', m.group(2))
        # English sentence literals reaching the DOM outside tr()/cat()/t()
        SINK = re.compile(r'(innerHTML|textContent|aria-label=|title=|<summary>|<caption>|<h4>|<p>|announce\()')
        ENW = re.compile(r'\b(the|this|these|for|in|of|to|by|a|an|and|or|not|no|selected|group|chart|table|data|view|pupils?|answers?|results?|school)\b', re.I)
        for i, line in enumerate(js.split('\n'), 1):
            if 'tr(' in line or 'cat(' in line or re.search(r'\bt\(', line) or 'isCy()' in line: continue
            if not SINK.search(line): continue
            for lit in js_strings(line):
                if len(lit) < 12: continue
                text = re.sub(r'<[^>]*>', ' ', lit).replace('\\/', '/')
                text = re.sub(r'\b(class|id|type|role|style|width|height|aria-\w+|data-\w+|title|button)=?\b', ' ', text)
                if len(ENW.findall(text)) >= 2 and re.search(r'[A-Za-z]{3}', text) and not re.fullmatch(r'[\s\W]*', text):
                    client('UI-literal', f'line {i}: "{text.strip()[:80]}"', text.strip()[:80]); break
        if 'applyLanguageState' not in js: client('UI-lang', 'applyLanguageState absent')
        # legend parity with optsCy
        legend = dict(re.findall(r'label:\s*"([^"]+)",\s*cy:\s*"([^"]+)"', js))
        opt_map = {}
        for r in S['opts']:
            opt_map.setdefault(r['t'].replace('’', "'"), set()).add(r['c'])
        labels = CFG.get('labels', {})
        for en, cy in legend.items():
            k = en.replace('’', "'")
            if k in opt_map and cy not in opt_map[k]:
                client('UI-legend-parity', f'legend "{en}" → "{cy}" but optsCy → {sorted(opt_map[k])}', cy)
            elif k in labels and labels[k] != cy:
                client('UI-legend-parity', f'legend "{en}" → "{cy}" but sheet 23 → "{labels[k]}"', cy)
            elif k not in opt_map and k not in labels:
                client('UI-legend-parity', f'legend "{en}" → "{cy}" has no catalogue source (re-typed in code)', cy)

    # ---- STK : stacked-chart rows are a surface -------------------------------
    w = D.get('welsh') or {}; ho = w.get('handoff') or {}
    opt_labels = {r['t'].replace('’', "'") for r in S['opts'] if r['c'] and '⟪' not in r['c']}
    raw_row_render = bool(js) and bool(re.search(r"esc\(label\)|esc\(r\[0\]\)", js[js.find('function renderStack'):js.find('function renderStack') + 2500])) if 'function renderStack' in js else False
    cap = (w.get('ui') or {}).get(CFG['stack_caption_key']) or (w.get('frames') or {}).get('ui.' + CFG['stack_caption_key'], {})
    cap_cy = cap.get('cy') if isinstance(cap, dict) else cap
    cap_en = (w.get('uiEn') or {}).get(CFG['stack_caption_key']) or (cap.get('en') if isinstance(cap, dict) else None)
    fixed = None
    for txt in (cap_cy, cap_en):
        m = re.search(r'(?<![{\w])(\d+)(?![}\w])', txt or '')
        if m and '{k' not in (txt or ''): fixed = int(m.group(1)); break
    mapped = set()
    for r in S['stack']:
        if r['n'] == 0: continue
        if not r['coded'] or raw_row_render:
            for _ in range(r['n']): pass
            R.setdefault('STK-label', []).extend([(dict(r, i=j, t=r['labels'][j] if j < len(r['labels']) else '', c=''), 'no stable code' if not r['coded'] else 'renderStack prints the English row label') for j in range(r['n'])])
        if fixed is not None and r['n'] != fixed:
            hit('STK-caption', dict(r, t=cap_en or '', c=cap_cy or ''), f'caption says {fixed}; rendered rows {r["n"]}')
        for l in r['labels']:
            if l.replace('’', "'") in opt_labels: mapped.add(l)
    all_labels = {l for r in S['stack'] for l in r['labels']}
    if S['stack']:
        R.setdefault('STK-code-map', []).append((rec('*', 'stk', 0, f'{len(mapped)}/{len(all_labels)} distinct stack labels have an optsCy value', ''), f'{len(mapped)}/{len(all_labels)}'))
    for r_, f_ in R.get('STK-label', [])[:0]: pass
    # evidence rows for STK-label are summarised (311k rows would swamp the archive): one row per state/context
    for r in S['stack']:
        if r['n'] and (not r['coded'] or raw_row_render):
            EVIDENCE.append({'gate': 'STK-label', 'state': r['s'], 'surface': 'stack', 'module': r['m'], 'index': 0, 'kind': None,
                             'matched': f'{r["n"]} rows rendered from the English label', 'en': '; '.join(r['labels'][:10]), 'cy': ''})

    # ---- FRAME : declared frames must be consumed and match what is rendered --
    frames = w.get('frames') or {}
    if js and frames:
        for k in frames:
            if k in CFG['deprecated_frames']: continue
            if k not in js: client('FRAME-dormant', f'{k} declared, never referenced by the client', k)
        for k, fn in CFG['heading_frames'].items():
            fr = frames.get(k)
            if not fr or fn not in js: continue
            body = js[js.find('function ' + fn):]
            body = body[:body.find('\n}') + 2] if '\n}' in body else body
            declared = len(str(fr.get('cy') or fr.get('en') or '').split('|'))
            rendered = len(re.findall(r"<th scope='col'>", body))
            if rendered and declared != rendered:
                client('FRAME-shape', f'{k} declares {declared} headings; {fn}() renders {rendered} columns', f'{declared} vs {rendered}')

    # ---- CAT -----------------------------------------------------------------
    missing = w.get('handoffMissing')
    if isinstance(missing, int) and missing > len(ho):
        client('CAT-keys', f'{missing} declared, {len(ho)} keys embedded')
    empty = [k for k, v in ho.items() if v in (None, '')]
    for k in empty: client('CAT-values', f'empty value: {k}', k)
    binder = bool(re.search(r'data-i18n', js)) or len(re.findall(r'\bcat\(|\btr\(|\bt\(', js)) >= 20
    n_calls = len(re.findall(r'\bcat\(|\btr\(', js)); n_ho = js.count('CY.handoff')
    if js and not binder: client('CAT-binder', f'no data-i18n; cat()/tr() used {n_calls} times; CY.handoff referenced {n_ho} times')
    md = D.get('metricDefs') or {}
    for k, d in md.items():
        if not d.get('labelCy'): client('CAT-schema', f'{k}: no labelCy', k)
        if d.get('baseNote') and not d.get('baseNoteCy'): client('CAT-schema', f'{k}: baseNote without baseNoteCy', k)
    def walk(o, path=''):
        if isinstance(o, dict):
            for kk, vv in o.items(): yield from walk(vv, path + '/' + str(kk))
        elif isinstance(o, list):
            for ii, vv in enumerate(o): yield from walk(vv, path + f'[{ii}]')
        elif isinstance(o, str) and '⟪missing' in o: yield path, o
    marker_keys = set()
    for path, val in walk({k: v for k, v in D.items() if k != 'states'}):
        client('CAT-marker', f'{path}: {val}', val)
        m = re.search(r'⟪missing:([^⟫]+)⟫', val)
        if m: marker_keys.add(m.group(1))
    for r in ALL:
        m = re.search(r'⟪missing:([^⟫]+)⟫', r['c'] or '')
        if m: marker_keys.add(m.group(1)); hit('CAT-marker', r, m.group(0))
    frame_keys = set((w.get('frames') or {}).keys()) | set((w.get('ui') or {}).keys())
    for mk in sorted(marker_keys):
        if mk not in ho and mk not in frame_keys and ('ui.' + mk) not in frame_keys:
            client('CAT-destination', f'{mk}: referenced by a ⟪missing⟫ marker but has no catalogue row', mk)

    # ---- GOV -----------------------------------------------------------------
    client('GOV-config', CFG['source'])
    bm = D.get('buildMetadata') or {}
    for f in ('welshFrameworkSha256', 'gateManifestHash', 'surfaceCounts'):
        if f not in bm: client('GOV-stamp', f'buildMetadata.{f} absent', f)
    stamped = {p.get('id') for p in (bm.get('provisionalRulings') or []) if isinstance(p, dict)}
    for pid in CFG['provisional_ids']:
        if pid not in stamped: client('GOV-provisional', f'{pid} not stamped', pid)
    gr = bm.get('gateResults') if isinstance(bm.get('gateResults'), dict) else None
    if not gr: client('GOV-results', 'buildMetadata.gateResults absent — the build does not carry its own gate evidence')
    else:
        for f in ('runnerSha256', 'mode', 'blockingPass', 'blockingTotal', 'evidenceSha256'):
            if f not in gr: client('GOV-results', f'buildMetadata.gateResults.{f} absent', f)
    if mode == 'release':
        if bm.get('mode') != 'release': client('GOV-mode', f'buildMetadata.mode = {bm.get("mode")!r}, expected "release"')
        if js:
            m = re.search(r'reviewMode:\s*(true|false)', js)
            if m and m.group(1) == 'true': client('GOV-mode', 'CONFIG.reviewMode is true in a release build')
            m2 = re.search(r'sensitiveFilters:\s*(true|false)', js)
            if m2 and CFG['sensitive_filters'] is not None and (m2.group(1) == 'true') != CFG['sensitive_filters']:
                client('GOV-mode', f'CONFIG.sensitiveFilters = {m2.group(1)}; signed D69 value is {str(CFG["sensitive_filters"]).lower()}')
            if m2 and CFG['sensitive_filters'] is None:
                R.setdefault('_notes', []).append(f'sensitiveFilters = {m2.group(1)} in the client; no signed D69 value to assert against')
    if baseline is not None:
        proj = english_projection(S)
        for k, v in baseline.items():
            if proj.get(k) != v: client('GOV-lock', f'state {k}: English projection changed', k)
        for k in proj:
            if k not in baseline: client('GOV-lock', f'state {k}: not in baseline', k)

    # ---- assemble ------------------------------------------------------------
    out = []
    dev_note = {'CAT-values': f'{len(empty)} empty values — expected until the translator returns; report-only in dev mode, BLOCKING in release mode' if mode == 'dev' else '',
                'CAT-marker': 'development markers are permitted in dev mode and BLOCKING in release mode' if mode == 'dev' else '',
                'GOV-mode': 'asserted in release mode only' if mode == 'dev' else '',
                'STK-label': 'occurrences = rendered rows; one evidence row per state/context',
                'STK-caption': f'fixed caption value {fixed}' if fixed is not None else 'caption has a count slot or no number'}
    R['_dev_note'] = dev_note
    for gid, fam, surf, blocking, ref, title in MANIFEST:
        rows = R.get(gid, [])
        uniq = {(r['s'], r['m'], r['i']) for r, _ in rows}
        if gid in ('CAT-values', 'CAT-marker') and mode == 'dev': blocking = False
        if gid == 'GOV-mode' and mode == 'dev': blocking = False
        status = ('MANUAL' if blocking is None else 'REPORT' if blocking is False
                  else ('PASS' if not rows else 'FAIL'))
        by_surface = collections.Counter(r['m'].split(':')[0] if r['m'] != 'client' else 'client' for r, _ in rows)
        out.append({'id': gid, 'family': fam, 'surface': surf, 'blocking': blocking, 'rule': ref, 'title': title,
                    'status': status, 'occurrences': len(rows), 'records': len(uniq),
                    'by_surface': dict(by_surface.most_common()),
                    'note': dev_note.get(gid, ''),
                    'examples': [{'where': f"{r['s']}|{r['m']}[{r['i']}]", 'matched': f, 'en': r['t'][:220], 'cy': r['c'][:260]}
                                 for r, f in rows[:3]]})
    out.append({'id': '_paths', 'paths': R.get('_paths', []), 'notes': R.get('_notes', [])})
    return out

def english_projection(S):
    """Per-state hash of every locked English value — the LOCK baseline."""
    by = collections.defaultdict(list)
    for name in ('module', 'h1', 'h2', 'scope'):
        for r in S[name]: by[r['s']].append((r['m'], r['i'], r['t']))
    return {k: hashlib.sha256(json.dumps(sorted(v), ensure_ascii=False).encode()).hexdigest()[:24] for k, v in by.items()}

# =============================================================================
# 6. SELF-TEST — every family must reject its own seeded fault
# =============================================================================
def selftest():
    def mk(cy, en='Of the 1 girl across the whole school who preferred not to say whether they have a disability or long-term condition, the largest group (1) said ‘4’.', m='d0'):
        return rec('whole|girl|dy_prefer_not_to_say', m, 0, en, cy)
    seeds = [
      ('CONJ-fnword',   mk('Ymhlith disgyblion, mae 175 o’r 366 yn mwynhau, a mae 288 yn hyderus.', 'Among pupils, 175 of 366 enjoy, and 288 are confident.', 'h1:an')),
      ('CONJ-vowel',    mk('Tennis a athletau.', 'Tennis and athletics.')),
      ('CONJ-h',        mk('cath ac heb.', 'x')),
      ('CONJ-neg',      mk('dywedodd un a nid oedd dau yn siŵr.', 'x')),
      ('CONJ-vig',      mk('rhwng Blynyddoedd 3 a 11.', 'between Years 3 and 11.')),
      ('CONJ-consonant',mk('Tennis ac criced.', 'x')),
      ('AGR-possessive',mk('O’r unig ferch yn yr ysgol gyfan y byddai’n well ganddi beidio â dweud eu hethnigrwydd, ‘4’ oedd yr ateb (1).')),
      ('AGR-pronoun',   mk('O’r unig fachgen a oedd ganddynt anabledd, ‘4’ oedd yr ateb (1).')),
      ('AGR-verb',      mk('O’r unig fachgen a ddywedodd y byddai yn gwneud mwy pe baent yn hyderus, ‘4’ oedd yr ateb (1).')),
      ('AGR-partitive', mk('Dewisodd un o’r unig ferch bêl droed.')),
      ('AGR-possessor', mk('O’r unig fachgen y byddai’n well ganddo beidio â dweud a oedd anabledd neu gyflwr tymor hir, ‘4’ oedd yr ateb (1).')),
      ('AGR-orphan-mut',mk('O’r unig ferch y byddai’n well beidio â dweud ei hethnigrwydd, ‘4’ oedd yr ateb (1).', 'Of the 1 girl who preferred not to say their ethnicity, the largest group (1) said ‘4’.')),
      ('ROLE-outer',    mk('Yn ystod AG oedd y lleoliad a ddewiswyd amlaf, gan 86 o’r 92 disgybl ymhlith disgyblion yn y grŵp a ddewiswyd.', 'PE was the most frequently selected setting, chosen by 86 of the 92 pupils among pupils who reported a disability and/or learning difficulty who answered.', 'n_dl')),
      ('PAR-generic',   mk('gan 86 o’r 92 disgybl yn y grŵp a ddewiswyd.', 'chosen by 86 of the 92 pupils who reported a disability and/or learning difficulty.', 'n_dl')),
      ('MUT-numeral',   mk('byddai’n well gan dau beidio â dweud.', 'x', 'e7')),
      ('MUT-aspirate',  mk('a oedd yn actif tua deirgwaith yr wythnos.', 'x')),
      ('NUM-fignoun',   mk('dewisodd 3 disgybl bêl droed.', 'x')),
      ('NUM-figcite',   mk('dewisodd 6 ‘Llawer’.', 'x')),
      ('NUM-zero',      mk('0 o’r 12 disgybl.', 'x')),
      ('PAR-lost',      mk('dewisodd 12 o’r disgyblion bêl droed.', '12 of the 366 pupils selected football.')),
      ('PAR-added',     mk('dewisodd 12 o’r 366 disgybl (45%) bêl droed.', '12 of the pupils selected football.')),
      ('PAR-follow',    mk('Pêl droed oedd y gamp, ac yna rygbi (4).', 'Football was the sport.')),
      ('PUB-placeholder',mk('[question-dependent] Ydw', 'Yes')),
      ('PUB-empty',     mk('', 'Yes')),
      ('PUB-copy',      mk('Volleyball', 'Volleyball', 'opts:x')),
      ('PUB-leak',      mk('Dewisodd the disgybl.', 'x')),
      ('POL-affirmative',mk('Ni ddywedodd yr un o’r chwe disgybl a ddewisodd ffensio nad ydynt yn mwynhau chwaraeon.', 'None of the 6 pupils who selected Fencing who answered said they do not enjoy sport.', 'g5')),
    ]
    S = {'module': [], 'h1': [], 'h2': [], 'scope': [], 'opts': []}
    for gid, r in seeds:
        S['h1' if r['m'].startswith('h1') else 'opts' if r['m'].startswith('opts') else 'module'].append(r)
    # DIS seed: two English → one Welsh
    S['scope'] += [rec('a', 'scope', 0, 'Boys · Year 3', 'Bechgyn'), rec('b', 'scope', 0, 'Girls · Year 3', 'Bechgyn')]
    js_seed = ('const CONFIG = { reviewMode: true, sensitiveFilters: true };\n'
               'function renderRail(){ $("#f").innerHTML = esc(c.label) + "<span>None — select a highlighted chart value to add one</span>"; }\n'
               'const cohortLabel = c => c.labelCy; const optLabel = o => o.labelCy; const labelOf = d => d.labelCy;\n'
               'x = CY.ui.showing || "Yn dangos";\n'
               'const STACK_SEGS=[{ label: "I don’t know", cy: "Ddim yn gwybod" }];\n'
               'function renderStack(host){ const [label, segs, base] = r; h += esc(label) + esc(r[0]) + "<th scope=\'col\'>Total pupils</th>"; }\n'
               'function dataTable(){ return "<th scope=\'col\'>Answer</th><th scope=\'col\'>Pupil responses</th>"; }\n'
               'function renderAppendices(){ x = "<h4>" + esc(def.label) + "</h4>" + esc(o[1]); }\n'
               'function barTitle(def,label,v){ return [def.label, label + ": " + v + " " + (v === 1 ? "pupil" : "pupils")].join(" — "); }\n'
               'p = "Fewer than five pupils match this selection, so their results are suppressed";\n')
    D = {'welsh': {'handoff': {'k1': None}, 'handoffMissing': 5,
                   'frames': {'ui.table_headings': {'en': 'Answer | Pupils | %', 'cy': 'Ateb | Disgyblion | %'}, 'msg.suppressed_body': {'en': 'x', 'cy': 'y'}},
                   'ui': {'stack_table_caption': 'Y 10 camp a ddewiswyd amlaf yn y golwg hwn —'}, 'uiEn': {'stack_table_caption': 'The 10 most selected sports in this view —'}},
         'metricDefs': {'m1': {'opts': [['a', 'I don’t know']], 'optsCy': ['Dydw i ddim yn gwybod'], 'baseNote': 'x', 'labelCy': '⟪missing:m1_label⟫', 'baseNoteCy': '⟪missing:m1_base_note⟫'}, 'm2': {'opts': [], 'baseNote': 'x'}},
         'buildMetadata': {'mode': 'dev'}}
    S['opts'].append(rec('*', 'opts:m1', 0, 'I don’t know', 'Dydw i ddim yn gwybod'))
    S['stack'] = [{'s': 'whole|all|sp_baseball', 'm': 'stk:community_club', 'i': 0, 'n': 8, 't': '', 'c': '', 'labels': ['Tennis'] * 8, 'coded': False}]
    res = {g['id']: g for g in run(D, S, js_seed, mode='release') if g['id'] != '_paths'}
    expect = [g for g, _ in seeds] + ['DIS-scope', 'UI-path', 'UI-field', 'UI-literal', 'UI-welsh-in-code', 'UI-fallback',
                                       'UI-lang', 'UI-legend-parity', 'CAT-keys', 'CAT-values', 'CAT-binder', 'CAT-schema',
                                       'GOV-stamp', 'GOV-provisional',
                                       # v5 seeds: English stack label · caption 10 over 8 rows · dormant frame · 3-vs-2 heading frame ·
                                       # missing base-note row · def.label / o[1] in appendices (UI-field) · English bar tooltip and
                                       # hard-coded GDPR body (UI-path children) · markers in payload · no embedded results · dev config in release
                                       'STK-label', 'STK-caption', 'FRAME-dormant', 'FRAME-shape', 'CAT-destination', 'CAT-marker',
                                       'GOV-results', 'GOV-mode']
    bad = [g for g in expect if res[g]['status'] != 'FAIL']
    print(f'self-test: {len(expect) - len(bad)}/{len(expect)} gates rejected their seeded fault')
    for g in bad: print('  NOT DETECTED:', g)
    return 0 if not bad else 2

# =============================================================================
# 7. REPORT
# =============================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('report', nargs='?')
    ap.add_argument('--pairs'); ap.add_argument('--payload'); ap.add_argument('--js')
    ap.add_argument('--framework'); ap.add_argument('--mode', choices=['dev', 'release'], default='dev')
    ap.add_argument('--json'); ap.add_argument('--evidence'); ap.add_argument('--baseline'); ap.add_argument('--emit-lock')
    ap.add_argument('--stk', help='stack rows jsonl (parts mode)'); ap.add_argument('--bundle', help='write the reproducibility bundle here')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args()
    if a.selftest: sys.exit(selftest())
    if a.framework: load_framework(a.framework)
    if a.report: D, S, js = load_report(a.report)
    elif a.pairs and a.payload: D, S, js = load_parts(a.pairs, a.payload, a.js, a.stk)
    else: ap.error('give report.html or --pairs/--payload/--js')
    if a.emit_lock:
        json.dump(english_projection(S), open(a.emit_lock, 'w')); print('lock written', a.emit_lock)
    baseline = json.load(open(a.baseline)) if a.baseline else None
    G = run(D, S, js, mode=a.mode, baseline=baseline)
    paths = next((g for g in G if g['id'] == '_paths'), {'paths': [], 'notes': []}); G = [g for g in G if g['id'] != '_paths']
    if baseline is None:
        for g in G:
            if g['id'] == 'GOV-lock': g['status'] = 'REPORT'; g['note'] = 'no --baseline supplied; lock not asserted this run'
    surfaces = {k: len(v) for k, v in S.items()}
    blocking = [g for g in G if g['blocking'] is True]
    failed = [g for g in blocking if g['status'] == 'FAIL']
    summary = {'runner': VERSION, 'manifest_hash': MANIFEST_HASH, 'mode': a.mode, 'config': CFG['source'],
               'framework_sha256': CFG.get('framework_sha256'),
               'surfaces': surfaces, 'surface_total': sum(surfaces.values()),
               'blocking_total': len(blocking), 'blocking_pass': len(blocking) - len(failed),
               'report_only': sum(1 for g in G if g['blocking'] is False), 'manual': sum(1 for g in G if g['blocking'] is None),
               'headline': f'{len(blocking) - len(failed)}/{len(blocking)} blocking gates pass; '
                           f'{sum(1 for g in G if g["blocking"] is False)} report-only; {sum(1 for g in G if g["blocking"] is None)} manual'}
    summary['paths'] = {'complete': sum(1 for p in paths['paths'] if p['status'] == 'complete'), 'total': len(paths['paths'])}
    summary['notes'] = paths['notes']
    if a.json:
        json.dump({'summary': summary, 'gates': G, 'paths': paths['paths']}, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if a.evidence:
        with gzip.open(a.evidence, 'wt', encoding='utf-8') as fh:
            fh.write(json.dumps({'record_type': 'metadata', 'runner': VERSION, 'manifest_hash': MANIFEST_HASH, 'summary': summary}, ensure_ascii=False) + '\n')
            for e in EVIDENCE: fh.write(json.dumps(e, ensure_ascii=False) + '\n')
    if a.bundle:
        def sha(pth):
            try: return hashlib.sha256(open(pth, 'rb').read()).hexdigest()
            except Exception: return None
        json.dump({'runner': VERSION, 'runnerSha256': sha(__file__), 'manifestHash': MANIFEST_HASH, 'commandLine': sys.argv,
                   'mode': a.mode, 'frameworkSha256': CFG.get('framework_sha256'), 'baselineSha256': sha(a.baseline) if a.baseline else None,
                   'evidenceSha256': sha(a.evidence) if a.evidence else None, 'resultsJsonSha256': sha(a.json) if a.json else None,
                   'reportSha256': sha(a.report) if a.report else None, 'summary': summary},
                  open(a.bundle, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'runner v{VERSION} · manifest {MANIFEST_HASH} · mode {a.mode} · config: {CFG["source"]}')
    print('surfaces: ' + ' · '.join(f'{k} {v:,}' for k, v in surfaces.items()) + f' · total {summary["surface_total"]:,}\n')
    print(f'{"gate":18} {"fam":5} {"status":7} {"occ":>8} {"records":>8}  title')
    for g in G:
        print(f'{g["id"]:18} {g["family"]:5} {g["status"]:7} {g["occurrences"]:8,} {g["records"]:8,}  {g["title"][:60]}')
    print('\n' + summary['headline'] + f' · renderer paths complete {summary["paths"]["complete"]}/{summary["paths"]["total"]}')
    for p in paths['paths']:
        if p['status'] != 'complete': print(f'  {p["id"]} {p["status"]:8} {p["english"]}/{p["children"]} child strings English — {p["desc"]}')
    for n in paths['notes']: print('  note:', n)
    for g in failed[:12]:
        if g['examples']:
            e = g['examples'][0]
            print(f'\n[{g["id"]}] {g["title"]} ({g["occurrences"]:,} occ, {g["records"]:,} records) {g["by_surface"]}\n  at {e["where"]}  «{e["matched"]}»')
            if e['en']: print(f'  EN: {e["en"]}\n  CY: {e["cy"]}')
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
