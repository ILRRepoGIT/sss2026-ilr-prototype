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
- **Young Artist artwork** is temporarily withheld from the generated report
  per the Corrective Brief §5. All assets remain in the supplied ZIP for
  deliberate reintroduction; only the mandatory title-page treatment and
  Brain Break characters are embedded.
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
- **Fourth Brain Break character.** Only three Brain Break poses were
  supplied (javelin, football, basketball). Active Nation, Everyone and
  Lifelong each use one; the Enjoyment opener uses transparent Young Artist
  artwork until a fourth character is provided.
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
