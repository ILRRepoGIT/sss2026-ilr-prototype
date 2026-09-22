# Prototype limitations log (Prototype v2 — 2026-prototype-005)

## Prototype v2 notes (Sport Wales feedback round)

- **7+ frequency scale.** The feedback asks for frequency "up to 7 or more
  times per week" to match CMO guidelines; the 2026 survey's frequency scale
  ends at "Three or more times a week", so the overall-frequency chart uses
  the survey's actual scale and the intro text says so. A 7+ scale needs a
  survey-item change (also listed as an outstanding decision in the Copilot
  summary). Tier 2 sports' contribution to frequency likewise awaits a Sport
  Wales decision.
- **Teacher Survey Completed and FSM band** are configurable school-profile
  fields shown as "To be confirmed": neither exists in the pupil response
  export. Wire to the production data source before the 900-school run.
- **Regional Sport Partnership** is set to "West Wales" for Pembrokeshire in
  config; confirm the canonical RSP naming with Sport Wales.
- **Chart-to-chart interactivity** was retained (the Notes' Top Tip relies on
  it and the selected-group filter model is built on it) with better
  signposting; the Copilot summary's "consider reducing / perhaps 2030"
  remains open for Sport Wales to confirm.
- **Bilingual splash page** (original notes query): open question; the
  architecture is translation-ready.
- **Cell-based suppression query** in the original notes conflicts with the
  agreed view-level policy (2026-07-20); unchanged, pending the statistical
  sign-off already flagged.
- **2022 comparison values** are not embedded (national benchmarks remain
  deferred); the report instead states which measures are 2022-comparable.
- **Pages 46/47/49/50** to be reviewed by Sport Wales on receipt of this
  version, per the Copilot summary.

## Prototype 4.1 notes (2026-prototype-004.1)

- **Brain Break characters.** Only three poses were supplied, and mirrored
  re-uses are ruled out. Assignments: introduction = javelin; Active
  Nation = footballer; Everyone = basketball. Lifelong and Enjoyment use
  two distinct brand-form SVG graphics (the sanctioned red/blue/yellow
  geometry) as deliberate placeholders — replace with two further Brain
  Break poses when supplied.
- **One-person selected groups** (permitted by the agreed §16 policy) use
  dedicated singular templates; cross-theme summaries are omitted for
  groups of one or two respondents, whose findings remain fully visible in
  the module charts.
- **Print page numbers** remain with the browser's print header/footer
  (Chromium lacks `@page` margin-box support); the repeating footer carries
  school, title and current view. To resolve before final delivery.
- **Production payload** (Prototype 4 review §11.4): ~26 MB per school ×
  900 schools requires the shared-asset / separate-JSON / lazy-state
  delivery workstream before generating final files; deterministic
  narrative is unaffected.
- **Young Artist artwork** was withheld from the generated report per the
  Corrective Brief §5 from Prototype 4.1 to V4.15; the owner's instruction of
  22 Sep 2026 reintroduced it (V4.16, fourteen entries, see below).
- **Print page numbers** still come from the browser's print header/footer
  (Chromium lacks `@page` margin-box support); the repeating footer carries
  school, title and current view.
- **Production delivery (§11.4).** The single-school file is ~27 MB with
  1,944 embedded states; 900 standalone copies would be roughly 24 GB before
  versioning. Deterministic narrative is unaffected by delivery choices —
  recommended hardening: shared fonts/JS/CSS assets, per-school compressed
  JSON fetched separately, lazy loading of selected-group states by chapter,
  serving states from the production Postgres service, and caching the
  whole-school and demographic states. To be assessed before generating the
  900 final files; does not block school-facing testing of this prototype.

## Prototype-3 policy notes

- **Disclosure model (§16, supersedes earlier policies).** The rule of five
  applies only to the phase/year × gender view; reportable views display
  exact counts of 1–4, small routed bases, and unrestricted chart-derived
  group sizes. Consequences accepted per instruction and flagged for
  statistical sign-off: a suppressed demographic view's size can be inferred
  by subtraction from visible parents (e.g. Year 11: 8 total and 5 girls
  visible → 3 boys inferable), and very small selected groups (1–4
  respondents) display their full response profiles.
- **Fourth Brain Break character.** Superseded in V4.16: the Brain Break
  characters were replaced by the Young Artists Competition artwork (see the
  V4.16 section below).
- **Print page numbers.** Chromium does not yet support CSS `@page` margin
  boxes, so the repeating yellow-rule footer carries the school name, title
  and current view, while page numbers come from the browser's print
  header/footer setting.
- **File sizes.** 2,088 pre-calculated states are embedded: report.html
  ≈ 27 MB, report JSON ≈ 26 MB, QA reconciliation CSV ≈ 57 MB. Fine locally;
  host with gzip/brotli (~8× text compression) or serve states via API for
  production. The QA CSV is an analyst artefact and need not be distributed
  with the report.
- **Percentage stability rule.** Approved percentages are additionally
  withheld where the relevant base is under 10 (spec §5.2 "small or unstable
  base"); the exact cut-off needs confirmation.

Distinguishing deliberately deferred production functionality from open
questions and known issues.

## Deliberately deferred (Revision Brief §28 / v1 carry-over)

- Postgres reporting database; production authentication and per-school
  tokens; LA/national user roles; SmartSurvey auto-extraction.
- Welsh narrative content (architecture is translation-ready; templates and
  labels are config/code constants keyed by stable codes; Welsh templates must
  be professionally written).
- National and local-authority benchmark values.
- Free-text analysis (free text never leaves the loader; only aggregate
  "Other" counts are kept).
- Server-side PDF generation (browser print stylesheet supplied).
- Usage analytics, CMS, email distribution.
- Sports-club **membership** and **volunteering** modules: no 2026 pupil-export
  source exists. Excluded rather than inferred (spec §1.2); no blank charts.

## Open data questions (need a Sport Wales / analyst decision)

1. **Screening question**: one completed respondent answered "No" to "Are you
   from [School Name]?" but completed the survey. Accepted (matches
   SmartSurvey's completed count of 366) and flagged in
   `generated/validation-summary.txt`.
2. **Partial records**: the 118 partials in this export contain no survey
   answers and are excluded. Confirm for other exports.
3. **Derived frequency**: per-setting frequency = highest reported across that
   setting's sports; **organised club participation** = highest across school
   club + community club (reproduces the specification's 106 / 29% headline).
   Confirm as the formal definitions.
4. **Unmet demand** = selected as "do more of" AND not reported as currently
   done this school year, with one label crosswalk (fitness activities ↔
   fitness classes). Reproduces the dodgeball-81 fixture. Confirm.
5. **"I don't know" frequency answers** remain visible and selectable.
6. **Coverage marks** (Broad/Partial/Limited) use a provisional heuristic
   against the 15/22 per-year-group response targets; needs sign-off.

## Disclosure model — for statistical sign-off

Agreed 2026-07-20: **view-level rule of five only.**

- Views (phase/year × gender × selected group) with <5 respondents are fully
  suppressed with a "broaden the view" route (e.g. Year 11 boys, 3
  respondents).
- Within reportable views, exact counts are shown, including cells and
  question bases below five (e.g. Year 6 boys who selected running — 9
  respondents — show all real figures).
- Exceptions protecting individuals: profile bars whose corresponding view is
  suppressed are withheld; ethnicity categories with <5 respondents
  school-wide are pre-aggregated into "Other ethnic groups".
- **Accepted residual risk**: cross-view complementary suppression is not
  applied, so a suppressed view's size can sometimes be inferred by
  subtraction from visible totals (e.g. Year 11: 8 total, 5 girls visible →
  3 boys inferable). Documented in the report's disclosure appendix; if
  unacceptable at national scale, serve single states from an API and/or
  reinstate family-wise complementary suppression (the v1 engine implemented
  it and the code remains in version history).

## Known visual / functional issues

- The report file is large (~15 MB) because 1,188 pre-calculated states with
  full narrative are embedded. Fine locally; for hosting, enable gzip/brotli
  (text compresses ~8×) or serve states in chunks / via API.
- The cover reproduces the supplied Word title page with extracted assets;
  print rendering of the angled panel depends on browser
  `print-color-adjust` support (works in Chromium/Edge).
- Boys/girls paired charts colour series blue/yellow for legibility with an
  explicit legend; branding guidance says colour should signal function, not
  identity — flag for design review.
- Playwright end-to-end automation is not bundled (headless verification was
  run during development); the automated suite covers calculations,
  suppression, narrative quality and the specification's numeric fixtures.
- Salesforce survey design references were not supplied; the visual system is
  derived from the mandatory title page and the established SSS branding.
  Swap in Salesforce-derived tokens when screens are provided.

## Provisional wording

All fixed editorial copy (module contexts, guide, thank-you) and all narrative
templates are provisional pending Sport Wales editorial review. Wording
changes are config/template edits followed by a rebuild; every sentence is
regenerated deterministically and re-audited
(`generated/ysgol-penrhyn-dewi.narrative-audit.csv`,
`generated/narrative-templates.md`).

## V5.0 real-school round (21 Sep 2026) — what the real data exposed, and what is held

The first three school reports built from the cleansed 2026 dataset (Industryline cleansing
handover v2.3, Stage 2 v2) run through the V4.15 prototype's pipeline unchanged except for the
per-school parameters (`config/schools/<slug>.json`), Framework v2.8 and pipeline 0.28.0. Everything
below is recorded on Framework sheet 63 (V5.0 flags) and in `config/held_cohorts.json`; nothing was
patched to pass a gate, and no Welsh was composed.

- **Held cohorts (four).** The Framework carries no Welsh relative clause for four qualifiers the
  prototype school never needed: `ov_none_reported` ("reported no sport in any setting"),
  `et_other_grouped` ("identified with other ethnic groups"), `tp_prefer_not_to_say` and
  `tp_communication_aids`. Those chart bars keep their counts but cannot be selected as a filter
  (the report's existing non-selectable-bar behaviour); the validation summary names each hold with
  the number of pupils affected. Lifted by the translator's sheet-22 rows.
- **Three f10 sentences held for one-pupil group views (EN-08).** The locked English templates
  leader_multi_v2 (a unique leader on a base of one), group_codemand_top3_v12 and
  wd_current_check_v3 have no one-pupil form and the build's own gate rejects "1 of the 1 pupil …".
  A sentence they would produce that the gate rejects is held (logged); every sentence the gate
  accepts — ties, definition sentences, and the forms the V4.15 corpus already contains ("1 of the 1
  boy …", "the 1 Year 3 pupil …") — renders as in V4.15, until the report owner sanctions one-pupil
  forms.
- **Partial responses.** The dataset's analytical set admits partial responses that reached page 48+;
  a school profile accepts them (`acceptedStatuses`) and the validation summary states the split.
  The profile charts' base line still reads "(complete survey response)" — Sport Wales to confirm.
- **Proper names.** `Carmarthenshire`, `Conwy`, `Rhondda Cynon Taf` and `The Vale of Glamorgan` have
  no sheet-53 row under the dataset's spelling; the "School Stages Covered" values have no Welsh
  form; the Regional Sport Partnership is derived from the local authority. None of the three V5.0
  schools is affected by the first point.
- **Sport labels.** Twelve live-survey sports absent from the prototype export are on sheet 23 with
  the survey's own Welsh (S16) and provisional grammatical features (PR-20).
- **Data adapter.** `pipeline/cleansed_to_export.py` writes one school's rows in the prototype's
  SmartSurvey layout. On the prototype school its 366 records match the original export's through
  the unchanged loader except for the cleansing team's documented corrections (R26-01 one setting
  cell; R26-02 seven "None of these" co-selections) — see the compliance record.
- **Review builds.** Like V4.15, the reports are dev-mode builds (review banner) until the translator's
  values above and the owner's D69 are signed.

## V4.16 — the Young Artists Competition artwork

- **Welsh alt text.** None of the fourteen alt frames (`ui.alt_yac_*`, Framework
  v2.9 sheet 43) has Welsh: the survey instrument describes six of the entries
  in English only. Until the translator returns the rows, the Welsh report shows
  the English alt text under the pending marking (`lang="en"`, "Heb ei gyfieithu
  eto — dangosir y Saesneg"), and the accessibility-mode caption under each image
  is that English. Sixteen frames are pending in all (with `ui.a11y_switch_desc`, V4.17, and
  `ui.a11y_glossary_heading`).
- **No release gate for an empty frame.** The gate pack tests the handoff
  catalogue (CAT-values) and the rendered narrative surfaces (PUB-empty) for
  empty Welsh, not the sheet-43 frames; a release run would not fail on the
  sixteen pending frames by itself. Raised with the pack owners; a release check
  is needed before the production round.
- **Publication approval.** The artwork is embedded as supplied; no pupil name or
  signature is visible in the files and none appears in the report. Sport Wales
  to confirm publication approval and any credit line before school-facing use
  (Framework sheet 65).
- **Cover.** Unchanged — the supplied title-page treatment only; the dragon in
  the Wales kit ("top of page — full width") opens the Contents page instead.
- **File size.** +1.3 MB against V4.15 (fourteen WebP images, 1.5 MB of data
  URIs). The production delivery note above (shared assets, per-school JSON)
  applies to the artwork too: fourteen images embedded in 900 files is 1.3 GB of
  repeated bytes that a shared asset bundle would carry once.

## V4.17 — accessibility switch, print page breaks, pipeline 0.29.1

- **Print page count.** Every page of the report now starts on a new printed page
  and no heading ends one (64 EN / 67 CY A4 pages; V4.16: 62 / 65). Long sections
  (who took part, the chapters) still flow over several pages; a page per module
  would double the count and was not asked for.
- **PDF tagging.** The "first line only" screen-reader symptom of the V4.13
  feedback (item 7) has no HTML cause; it depends on the browser's PDF export
  tagging. The page's paragraphs are plain `<p>` elements; the switch and its
  description are announced together (aria-describedby).
- **Off-route answers (0.29.1).** An answer to the take-part question from a
  respondent not routed to it is dropped by the loader and counted. The 24 such
  rows in the Stage 2 dataset (all partial responses) are with the cleansing team;
  if Stage 2 blanks them at source the rule becomes a no-op and can be retired.
  Other routed questions are already charted on their routed bases; their
  off-route answers are not yet dropped (raised in the query).

## V4.18 — the Club Sports section removed (EN-09)

- **The club-sport estimate is still cited in one place.** The section, its
  chart, its selected groups and its appendix table are gone, but the Summary
  page's chapter-summary sentence "… took part in club sport at least once a
  week" is computed from the same metric and was left exactly as it was: it
  is locked narrative, and the instruction named the section. Whether it
  follows the section is the owner's call (EN-10, flagged). (The "summary
  cards" named on Framework v2.11 sheet 69 are unreferenced generator code
  and have never rendered; the sentence is the only citation.)
- **The appendix table went with the section.** "Club sport (school or
  community)" was the section's table; its heading frame is DEPRECATED on
  sheet 43, not deleted, so it can be restored by one status change if wanted.
- **The corpus lock was re-based.** EN-09 is the first sanctioned change since
  V4.1 that moves the locked English, so the V4.15 lock could not be asserted;
  the V4.18 lock was emitted under the ruling and the exact difference proven
  and recorded (288 `cb_*` states removed, d2 removed everywhere, one
  definition paragraph added to d0 in 140 `st_*` states, nothing else). Every
  later build asserts against the V4.18 lock; the V4.15 lock stays in the
  repository as the record of the corpus before the ruling.
- **Only the named pairing is affected.** The weekly-frequency chart keeps the
  wider picture under a SETTING selection only; under every other selection
  (a year, a gender, a frequency band, an enjoyment answer …) it behaves as
  before, and no other chart changed.
- **The translator's five retired rows** (the "Club Sports" heading and its
  context paragraph) are kept verbatim on the V4.18 handoff's Retired sheet;
  they are no longer translator rows and would need re-adding if the section
  ever returned.
