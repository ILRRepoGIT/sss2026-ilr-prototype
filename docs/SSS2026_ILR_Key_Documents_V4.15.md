# SSS2026 Interactive Learning Report — key documents, V4.15

Generated 2026-09-21T13:33:09+00:00 from the V4.15 build. This file and the companion archive `SSS2026_ILR_Rebuild_Kit_V4.15.zip` are the complete record: if everything else were lost, the report is rebuilt exactly from the archive by the commands in section 3, and every decision, rule, limitation and open item is in sections 1, 4–8.

## Contents

1. The rulebook · 2. Build identity and figures · 3. Rebuild instructions · 4. README (build history) · 5. LIMITATIONS and the disclosure model · 6. The engine's suppression policy (as coded) · 7. Feedback and compliance record (every round) · 8. Production deployment plan · 9. V4.10 translation register (summary) · 10. Kit inventory with sha256

## 1. The rulebook

1. The English narrative is locked (byte-identical to V4.1) and proven every round by the GOV-lock gate and a record-level comparison against the previous build. English interface text changes only through the Framework's English sheet (sheet 49, D77). EN-05 ("21th") belongs to the report owner and is never touched in code.
2. Welsh is generated from fact records through the Framework workbook (lexicon, frames, rulings, count-NP tables); nothing is translated or machine-translated by the pipeline. A missing lexicon entry fails the build; there is no silent invention — a dev build renders ⟪missing:key⟫ markers, a release build refuses.
3. The workbook is the source of truth. The pipeline implements what it says; a defect in the workbook is raised in the reply and the compliance record for its owner, never "corrected" in code, and no gate is ever satisfied by matching its pattern rather than meeting its intent.
4. Provisional rulings are data (PR_KEYS); a new ruling needs a regex; only canonical PR-nn identifiers are stamped.
5. web/app.js contains no Welsh literal and no "|| fallback"; every dynamic string goes through t()/cat(); frames are clauses joined by joinClause() only.
6. Gate packs are vendored byte-identical with their sha stamped and run inside build QA: selftest first, reproduce the baseline before changing anything, ship the runner, both JSONs, both evidence archives, both bundles and the emitted lock.
7. Build identity is written once (buildMetadata.identity); every legacy field is derived from it.
8. Builds are dev builds until the translator's values AND the owner's signed D69 exist.
9. Reproducibility over speed — only computed numbers are quoted.
10. Translator text arrives only through the handoff workbook's Welsh column, matched to a row by its English (pipeline/ingest_translation_doc.py, V4.10); client-rendered strings (answer labels, legend, cohort labels, sheet-43 frames) are workbook rows and differences are change requests to the framework owner.
11. A reviewer's explicit Welsh correction is applied only as a scripted, minimal substitution with its provenance in the handoff's Note column (pipeline/apply_review_corrections.py), pending the translator's confirmation; decisions and unspecified recasts go to the queue, never into the text.
12. Production (deployment plan §6): frozen tag with every file hash verified, empty working directory per build, input allowlist (frozen release, canonical dataset, manifest row), no reuse of intermediates, full gates every time, write-once outputs, change means regenerate, 5% byte-compare rebuild on a second machine.
13. (V4.14) The translator's document takes precedence, word for word, over any reviewer substitution: the V4.11 substitutions were reverted by script (pipeline/revert_review_corrections.py) and the reviewer's findings became questions on the handover. The translator answers; the pipeline applies answers.
14. (V4.15) A completed handover is applied only by script (pipeline/apply_translator_handover.py) with a change log per cell and a flags register: typography (rule 41) is normalised, wording is never touched; a contradiction between two answers is decided for the more specific one (a per-row decision over a one-term-for-everything answer, a comment over its dropdown) and always flagged; a decision that makes a blocking gate fail (DIS-scope on the cb chip) is HELD and flagged, never patched around; an engine-rule ruling changes the rule as workbook data (sheet 11 MODE, sheet 09) and the gate pack is versioned to assert the ruled rule (v8); the corpus lock moves only by ruling, and only after the English projection and the FT-11 key set are proven unchanged (welsh_gates8.emit_lock, D82).

## 2. Build identity and figures

Report version `2026-prototype-V4.15-bilingual` · pipeline 0.27.0 · identity `{"frameworkVersion": "v2.7", "frameworkFile": "01_Framework_v2.7.xlsx", "frameworkSha256": "972a3998e2a68cdbe7e701d75924901db6369967c0c2118c322c8aa466317792", "runnerVersion": "8.0.0", "runnerSha256": "3057fef25b5d54bd564b0ee86affd3ef34048b4c1598c27eeb86ae3da2bde4fe", "manifestHash": "c4221bba2cff4dcb", "mode": "dev"}` · gate stamp `{"runner": "8.0.0", "runnerSha256": "3057fef25b5d54bd564b0ee86affd3ef34048b4c1598c27eeb86ae3da2bde4fe", "manifestHash": "c4221bba2cff4dcb", "mode": "dev", "blockingPass": 69, "blockingTotal": 72, "headline": "69/72", "pending": ["GOV-rerun", "GOV-bundle"], "disputed": {"STK-caption-case": "gate substitutes the lexical countNP entry without applying the slot's initial casing role; v7 CNP-lexical requires the table to be lower-case \u2014 raised with the pack owners (V4.9 register)"}, "pathsComplete": 17, "pathsTotal": 18, "evidenceSha256": "94f4a7a77dbb47db648d941f3a1e40f21ca277a287e3692274184aa23634a6e7", "baselineSha256": "d5db3fb34d1a3589d6f8ffb148a961134d4958b185df3dc36ca7465fd1bfd041"}` · static lane `{"rows": 192, "textNodes": 216, "keyedAttributes": 16, "values": 192}` · suppression `view-level rule of five (2026-07-20)` threshold 5 · states 8568 · shipped file SSS2026_ILR_Report_V4.15_Bilingual.html 179,534,432 bytes sha256 dd5d9959d40c2ed417cdc8eeb937171ff50d3240b690c99583f462ba45891bfd

## 3. Rebuild instructions

All commands run from the `repo/` directory of this kit with Python 3.10+ (openpyxl, pyyaml, pytest, python-docx installed) and Node 18+ (jsdom 30.0.1 for the browser-gate port). Paths in angle brackets are the kit's own folders.

    # 0. verify the kit
    sha256sum -c ../MANIFEST.sha256

    # 1. the gate runner rejects its own seeded faults (v8: CONJ-06 read from sheet 11, D84)
    python pipeline/vendor_welsh_gates_v8.py --selftest                      # 68/68 + CONJ-06 modes OK

    # 2. the lexicon from the Framework workbook and the filled handoff
    python -m pipeline.build_welsh_lexicon config/01_Framework_v2.7.xlsx \
        config/SSS2026_Welsh_Translation_Handoff_V4.15.xlsx                  # 423 rows, 247 translated

    # 3. unit tests
    python -m pytest tests -q                                                # 86 passed, 1 skipped

    # 4. the report package, staged (an empty working directory each time)
    X=../inputs/SSS2026_YPD_export_headers_cleaned_copy.xlsx; WD=/tmp/ilr_wd; rm -rf $WD
    python -m pipeline.staged_build states   $X $WD 0 4
    python -m pipeline.staged_build states   $X $WD 4 8
    python -m pipeline.staged_build states   $X $WD 8 12
    python -m pipeline.staged_build assemble $X $WD
    python -m pipeline.staged_build qa       $X $WD                          # QA PASS, stamp 69/72
    python -m pipeline.staged_build write    $X $WD                          # generated/ysgol-penrhyn-dewi.report.json

    # 5. the single-file report
    python -m pipeline.build_html generated/ysgol-penrhyn-dewi.report.json \
        "../inputs/yac images for report" ../inputs/fonts config/cover_media   # generated/report.html

    # 6. the assurance bundle and the two stock reruns (v8 runner; baseline 02c_lock_V415_v8.json)
    python -m pipeline.make_bundle V4.15

    # 7. the jsdom regression and browser-gate port (Chromium optional)  — 97/97
    python -m tests.jsdom.make_mini /tmp/ilr_wd
    JSDOM=<node_modules/jsdom> WD=/tmp/ilr_wd node tests/jsdom/jsdom_test.js          # 97/97
    JSDOM=<node_modules/jsdom> WD=/tmp/ilr_wd node tests/jsdom/jsdom_provenance.js    # 0 / 0 / 0, toggle 0 failures

    # 8. (when a new translator document arrives) regenerate and fill the handoff
    python -m pipeline.make_translation_handoff config/01_Framework_v2.4.xlsx /tmp/handoff_empty.xlsx \
        config/SSS2026_Welsh_Translation_Handoff_V4.11.xlsx
    python -m pipeline.ingest_translation_doc <translator.docx> /tmp/handoff_empty.xlsx \
        config/SSS2026_Welsh_Translation_Handoff_V4.14.xlsx /tmp/register.xlsx generated/ysgol-penrhyn-dewi.report.json
    # 9. (how Framework v2.3 and the V4.11 handoff were produced — reproducible)
    python -m pipeline.make_framework_v23 config/01_Framework_v2.2.xlsx config/01_Framework_v2.3.xlsx generated/V4.10_translation_register.xlsx
    python -m pipeline.apply_review_corrections <handoff regenerated on v2.3> config/SSS2026_Welsh_Translation_Handoff_V4.11.xlsx
    # 10. (how Framework v2.4 was produced — V4.13 accessibility frames)
    python -m pipeline.make_framework_v24 config/01_Framework_v2.3.xlsx config/01_Framework_v2.4.xlsx
    # 10b. (how Framework v2.5 and the V4.14 handoff were produced — the translator's text verbatim)
    python -m pipeline.revert_review_corrections config/SSS2026_Welsh_Translation_Handoff_V4.11.xlsx config/SSS2026_Welsh_Translation_Handoff_V4.14.xlsx
    python -m pipeline.make_framework_v25 config/01_Framework_v2.4.xlsx config/01_Framework_v2.5.xlsx
    # 10c. (how Framework v2.6, v2.7 and the V4.15 handoff were produced — the translator's completed handover, 21 Sep 2026)
    python -m pipeline.make_framework_v26 config/01_Framework_v2.5.xlsx config/01_Framework_v2.6.xlsx
    python -m pipeline.apply_translator_handover config/SSS2026_Welsh_Translator_Handover_V4.14_COMPLETED.xlsx \
        config/01_Framework_v2.6.xlsx config/01_Framework_v2.7.xlsx \
        config/SSS2026_Welsh_Translation_Handoff_V4.14.xlsx config/SSS2026_Welsh_Translation_Handoff_V4.15.xlsx \
        generated/SSS2026_V4.15_Translator_decisions_applied.xlsx           # 174 changes, 25 flags
    # 11. (optional, Chromium) render probe: default view pixel comparison and print PDF page count
    python -m tests.browser.render_probe /tmp/ilr_wd /tmp/probe            # and --a11y for the switch-on view

Expected on this kit: the ENGLISH corpus byte-identical to V4.14/V4.10/V4.9/V4.8 (0 differences over 308,400 records; the `english` part of the emitted lock byte-equal to config/02c_lock_V48_v7.json); the WELSH corpus changed only by the translator's rulings (Framework v2.7 sheet 60, D84–D87) — the emitted lock byte-equal to config/02c_lock_V415_v8.json in all three parts; report sha256 differs from the shipped file only through the build timestamp in buildMetadata.

## 4. README (build history)

# School Sport Survey 2026 — Interactive Learning Report (Prototype v2.2)

## Prototype v2.2 (2026-prototype-007) — meeting decisions round

Applies the 11 August Agreements/Decisions/Actions Register and speaker-corrected
transcript on top of the complete page-by-page feedback. Headlines: any-participation
headline opens the chapter (D02); overall frequency rebuilt as the **raw accumulated
occasions measure on the 0–7+ scale** (P01/P02 — reproduces the in-meeting live test:
238 of 366 at 7+, 188 excluding somewhere else) with true zero kept distinct from
less-than-weekly (D08); per-setting frequency uses the same construction on the fuller
scale (P06); the combined club measure now sits in a caveated **Future Generations
indicator** subsection after the setting pages (P09); "organised" removed from all
reader-facing terminology (D14); charts state the active population when filtered (D07);
follow-a-group pointers added (P07). Ships with
`generated/SSS2026_ILR_Definitions_Calculations_Companion_v2.2.docx` (D16/D18):
definitions, calculations, frequency sensitivity tests, suppression diagnostics and all
open questions. Build: 2,052 states · 83,893 paragraphs · QA PASS · pytest 22/22.
Full mapping: `sw-feedback-compliance-record.md`.

## Previous: Prototype v2.1

## Prototype v2.1 (2026-prototype-006) — complete page-by-page feedback

Implements the **complete** Sport Wales page-by-page feedback document (60 rows,
pages 1–50), superseding the partial version. Full mapping and verification:
`sw-feedback-compliance-record.md`. Headlines: Settings before Frequency with the
new texts and Top Tip; new "in School" / "Outside of School" sections carrying the
per-setting frequency and top-five sport charts with the specified titles and
three-sentence analysis boxes; demographic pages re-texted verbatim with
plain-language filter notes and the reworded ethnicity suppression message;
"A Lifelong Enjoyment of Sport" with the provided intro, any-setting participation
table, the exact analysis forms for what-matters and would-do-more-if (figures match
the feedback's cited numbers), reinstated group sections (barriers by group,
enjoyment by group/year, demand by group in Sport), one merged chapter summary;
all enjoyment-PE and confidence values selectable; pupil-first narrative voice
package-wide; AN summary and "Data available in this view" relocated. Build:
1,944 states · 80,154 paragraphs · QA PASS · pytest 22/22.

## Prototype v2 (2026-prototype-005) — Sport Wales feedback round

Second prototype version implementing both Sport Wales feedback documents
in full (the screenshot-based Notes and the Copilot consolidated summary).
Item-by-item mapping and verification: `sw-feedback-compliance-record.md`;
test evidence: `generated/test-record.md`.

- **Structure**: Welcome (new text) → Contents page → How to use this
  report (12 FAQ drop-downs) → Which pupils in our school took part in
  2026? → **An Active Nation for Everyone** (merged) → **A Lifelong
  Enjoyment of Sport** (merged) → **Sport** (new chapter) → Summary →
  Appendix. Key statistics and the cross-theme overview pages removed.
- **Navigation**: contents page, rail contents pane, Back/Contents/Next
  buttons on every section, "↑ Contents" beside every heading.
- **Terminology**: "You are viewing", "pupil responses included",
  "Based on: X pupils"; chart titles phrased as questions; plain-English
  pass; "Partial coverage" removed from the filters pane.
- **Active Nation journey**: any-activity line → overall frequency across
  all settings (new derived metric) → settings + interaction Top Tip →
  club-sport grouping with explicit 2022 comparability. Gender/year
  commentary removed where the filters cover it.
- **Everyone**: participation-inequality emphasis (disability, learning
  difficulty, Welsh speakers with definition, ethnically-diverse
  aggregate), FSM context section, school-wide participation-variation
  table; year-by-gender moved to Lifelong; Welsh ordered below ethnicity.
- **Sport chapter**: sports overall + per-setting top-fives with
  definitions and frequencies (incl. new PE module), latent demand, unmet
  demand, participation-and-demand comparison.
- **Filtered views** keep a dashed whole-school outline behind every bar
  ("fill up the bars"); profile charts single-colour; suppression message
  uses the required wording verbatim.
- Appendix adds the survey-completeness chart over all 484 exported rows.

Build: 1,944 states · 77,419 paragraphs · QA PASS · pytest 22/22.

## Corrective release (2026-prototype-003-corrected)

- **Sticky controls restored.** The `overflow-x:hidden` scroll context that
  detached them is gone (`overflow-x:clip`); the Current view banner stays
  visible throughout the report at every width, the full Explore results
  panel is sticky on desktop, and a compact sticky filter bar sits directly
  below the banner on tablet/mobile. Regression matrix: 8 widths × 5 scroll
  anchors, all PASS (`generated/test-record.md`).
- **Multi-colour charts.** Bars cycle red → blue → grey by canonical answer
  code (stable across every filter); selected values override to yellow with
  outline and tick, and revert on deselect. Full mapping in
  `generated/colour-mapping.md`; guide wording updated.
- **Imagery.** Young Artist artwork temporarily removed (assets retained in
  the library); the guide is text-only; the javelin character moved to a
  two-column introduction layout; all four chapter openers use Brain Break
  characters.
- **Grammar.** Rule-level fixes for "1 selection(s)" in cards, "Next came…"
  runner phrasing for long labels, verb-complete ethnicity sentences,
  zero counts as "None of the…", and split long syntheses — enforced by
  build gates across all 71,324 sentences.

A working, module-based Interactive Learning Report for one combined school
(Ysgol Penrhyn Dewi, Years 3–11), built from the anonymised response-level
SmartSurvey export to the Content and Narrative Specification and the
**Prototype 3 Consolidated Review, Revision Instructions and Acceptance
Requirements**.

## Prototype 3 changes

- **Stable graph colour system**: every metric carries an intentional blue or
  red base colour in its metadata, identical in every state and appendix; the
  leading value is no longer auto-highlighted; **yellow means selected** —
  a selected chart value turns yellow with a blue outline and a “✓ Selected”
  label, matching the yellow selected-group box in the panel. Boys/girls
  comparisons use blue and red.
- **Suppression exactly per §16**: the five-response test applies only to the
  phase/year × gender view. Reportable views show exact counts of 1–4,
  routed bases below five, and chart-derived groups face **no second
  threshold**. The policy is a single engine configuration.
- **Grammar at rule level**: singular/plural agreement, tie verbs, joint-next
  wording, 4+-way tie summarisation, confidence-tie handling, full-prose
  participation-method sentences, plus build gates that fail on “1
  selections”, lower-case “i’m”, duplicated words, whole-school qualifiers in
  filtered states, and tautologies.
- **Nearest-parent comparisons** everywhere (group → its demographic view;
  year+gender → the whole year; percentages withheld on bases under 10).
- **Four new selected-group sources**: “I would do more sport if…”, desired
  sports, feeling listened to, and what matters when playing — each with
  tautology guards, replacement key-statistic cards and cross-question
  follow-ups (e.g. whether pupils who want more swimming already swim).
- **Editorial**: expanded module introductions (§11 structure), consolidated
  comparison modules with subheadings, freshly synthesised chapter and final
  summaries (no copied sentences), enlarged Brain Break guide character,
  Brain Break chapter openers, unboxed Young Artist artwork, yellow-rule
  footers, corrected cover shape, compact mobile banner, print with expanded
  appendices and a repeating footer.

**The deliverable users open is `generated/report.html`** — one self-contained
file (data, narrative, fonts and images embedded). It makes no network calls,
uses no AI at runtime, and contains only disclosure-checked aggregates with
pre-generated deterministic narrative.

## What v2 delivers

- **Mandatory title page** reproduced from the supplied Word document (red
  angled panel, white Sport Wales logo, official 2026 lockup, dynamic school
  name), followed by introduction, guide, data-coverage and fixed
  school-overview modules.
- **Complete default whole-school report**: ~40 analytical modules across
  Active Nation, Everyone, Lifelong and Enjoyment, each with fixed context,
  dynamic findings, gender/year/phase comparisons, cross-question insights and
  chapter summaries — no interaction required to see the principal content.
- **Key statistics** (12 cards, every card scope-labelled) and an opening
  **What respondents in this view reported** summary; the closing section is
  **Summary of the current view** with four-theme synthesis, exploration
  questions and a **Data available in this view** panel.
- **Self-scoping narrative**: every data-led sentence names whom it describes
  ("…among Year 5 boys"), machine-checked at build time. 38,000+ sentences are
  pre-generated across 1,188 filter states and logged with template ids and
  fact objects for audit.
- **Retained interaction engine**: current-view banner, right-hand filter
  panel, phase/year + gender filters, chart-derived **selected groups**
  (sports, club frequency, PE enjoyment, joining in, confidence, settings,
  disability, learning difficulty), source-chart context with highlighted
  selection, URL state, print stylesheet.
- **Availability states** everywhere: fully suppressed views explain how to
  broaden; not-applicable modules are omitted and listed; "No responses" is
  distinct from "Not reportable".
- **Counts by default; approved unweighted percentages** (with count and base)
  in whole-school and phase views only.
- **New derived measures**, reconciled against the specification's fixtures:
  organised club participation (106 of 366, 29%, three-plus times a week),
  unmet demand (dodgeball, 81), per-setting sports and frequency, ethnicity
  (small categories pre-aggregated), learning difficulty.

## Suppression policy (Prototype 3, §16 — supersedes all previous rules)

The five-response threshold is evaluated **only against the wider demographic
view (phase/year × gender)**. If that view has fewer than five respondents,
the complete analytical view is suppressed with a "broaden your view" route
and no exact base exposed. Once the demographic view is reportable, graphs
and tables show **exact answer counts** — including values of 1–4 and routed
question bases below five — and chart-derived selected groups face **no
second suppression test**. No cell suppression, no question-level
suppression, no complementary suppression. Stored as one central engine
configuration (`engine.primary_suppression`). Documented exceptions
protecting individuals: profile bars for suppressed demographic views are
withheld, and ethnicity categories under five school-wide are pre-aggregated.
Subtraction risks inherent to this policy are recorded in LIMITATIONS.md for
statistical sign-off.

## Build (one command)

```bash
./build_prototype.sh <responses.xlsx> "<yac images dir>" <montserrat_woff2_dir> <cover_media_dir>
# cover_media_dir = word/media extracted from "ILR - SSS2026_school report cover page.docx"
```

Or step by step:

```bash
python -m tests.make_synthetic_fixture tests/fixtures/synthetic.xlsx
SSS_REAL_XLSX=<responses.xlsx> python -m pytest tests/ -q
python -m pipeline.build_report_package <responses.xlsx>
python -m pipeline.build_html generated/ysgol-penrhyn-dewi.report.json \
    "<yac dir>" <fonts dir> <cover_media_dir>
```

Outputs in `generated/`: `report.html` (deliverable),
`ysgol-penrhyn-dewi.report.json` (data contract),
`ysgol-penrhyn-dewi.qa.csv` (reconciliation),
`ysgol-penrhyn-dewi.narrative-audit.csv` (38k sentences + facts + template ids),
`narrative-templates.md` (template catalogue), `validation-summary.txt`.

## Repository layout

```
config/     school_profile.json · column_mapping.yml · metrics.yml (36 metrics,
            8 selected-group sources) · narratives.yml · assets.yml
pipeline/   load_normalise.py  (Excel → canonical records, derived measures)
            engine.py          (1,188 filter states, view-level suppression)
            narrative2*.py     (module narrative engine, scope objects,
                                comparisons, cross-insights, cards, summaries)
            build_report_package.py  (assembly + QA: reconciliation, scope,
                                      tautology, tie grammar, banned wording)
            build_html.py      (single-file assembly)
web/        template.html (markup, CSS, fixed editorial copy) · app.js (client)
tests/      pytest suite + synthetic edge-case fixture generator
```

The raw workbook must never be committed (`.gitignore` enforces this).

## Data contract (front-end interface)

`states["scope|gender|group"]` carries everything the client renders:
`b` (base), `scope` {short, phrase, qual}, `coverage`, `m` (metric values),
`cards`, `mod` (per-module status + narrative paragraphs), `h1/c2` (summaries),
`h2` (exploration questions), `avail`, `rows` (year breakdown tables).
Suppressed views carry only `{sup:1, scope}`. The client displays approved
data and narrative; it never calculates findings, ranks answers or decides
suppression.

## Postgres handover

Replace `load_and_normalise(xlsx)` with a `PostgresDataSource` returning the
same canonical records. The metric engine, filter states, suppression,
narrative modules, data contract and web application are source-agnostic.
For national scale: one package per school behind authenticated routes, or an
API serving single states if disclosure review requires it. Welsh: all labels
and templates are config/code constants keyed by stable codes — add a `cy` set
with professionally written templates (never machine-translate at runtime).

## Known limitations

See `LIMITATIONS.md`.


## 5. LIMITATIONS and the disclosure model

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


## 6. The engine's suppression policy (pipeline/engine.py docstring)

```
Metric calculation and filter-state generation (v2).

Suppression policy v2 (agreed 2026-07-20, recorded in Appendix I11):
  - The rule of five applies to the SELECTED VIEW only: a view (phase/year x
    gender x selected group) with fewer than five respondents is fully
    suppressed and shows a "broaden your view" message.
  - Within a reportable view, exact counts are displayed even when below
    five, including question-specific bases below five, because the
    respondents behind those counts are not identifiable.
  - Two documented exceptions:
      * the year/gender profile charts blank a bar whose corresponding VIEW
        is suppressed (otherwise the chart would print the very number the
        suppressed view withholds);
      * ethnicity categories with fewer than five respondents school-wide
        are pre-aggregated in normalisation.
  - Cross-view complementary suppression was considered and deliberately
    NOT applied: small suppressed views may be derivable by subtraction from
    visible parent totals. Accepted and documented for disclosure sign-off.
```

## 7. Feedback and compliance record

# Sport Wales feedback — compliance record (build 009)

Build: **2026-prototype-009** · pipeline 0.9.0 · 2,664 states · 106,018 paragraphs ·
QA PASS · pytest 22/22 · owner final-edit checks 15/15 PASS

## 009 — owner final edits

1. **FAQ "Why are some pupil responses missing?"** rewritten to the owner's wording (more
   pupils may have taken part than shown; inclusion needs ~80%+ of the survey, reaching at
   least the demand for sport section); the 484-rows sentence removed.
2. **Profile table**: "Total number of pupils who took part" row deleted; "Total number of
   pupil responses included in this report*" retained (366).
3. **Demographic filtering**: ethnicity, Welsh language, take-part method and all
   disability answers are now selectable chart filters, under a five-pupil minimum per
   answer enforced at build time (17 new cohorts; "Other ethnic groups" [2 pupils],
   communication aids and take-part "prefer not to say" correctly excluded; dead buttons
   suppressed). Ethnicity note updated to explain the under-five rule.
4. **Ethnicity title**: "What is the ethnicity of your pupils who took part?".
5. **"↑ Contents" buttons removed** from all headings (Back/Contents/Next page navigation
   retained).
6. **Top-10 sports** in every per-setting sports chart (owner supersedes the top-5 note;
   logged in register v3).
7. **Future Generations note** re-worded per owner: "…the 2026 survey captures sport in
   more detail than 2022. In 2022, sport participation was measured across club sport only,
   so this is the most direct comparison for 2022." (sign-off clause removed).
8. **Impact-of-age table → bar graphic**; **year-by-gender table → paired boys/girls bar
   graphic** with the explicit metric and "n of b (p%)" labels explained.
9. **Appendix survey-completeness section deleted** (renderer removed).
10. **Methodology split into bullet points** with the owner's inclusion wording (partial
    records reaching the demand section included; below that not usable).
11. **Rail navigation**: bold "Click to navigate to a report section" title and a clickable
    Contents link.

Register v3 records the owner-directed departures from Sport Wales-supplied wording
(took-part row deletion, top-10 vs top-5, ethnicity filterability superseding the row-32
note, FG note wording). The 50-block verbatim audit re-run passes for all remaining
Sport Wales text.

---

# Sport Wales feedback — compliance record (build 008.1)

Build: **2026-prototype-008.1** · pipeline 0.8.1 · QA PASS · pytest 22/22 · 50-block SW
verbatim audit PASS

## 008.1 — owner-directed restoration of Sport Wales wording

The owner ruled that Sport Wales text and meeting decisions take priority over reviewer
editorial preference. Three reviewer-driven deviations in 008 were identified by audit and
reversed; no other deviations from the page-by-page document exist (verified by a 50-block
whitespace-normalised verbatim sweep of every Sport Wales-supplied text block, including
the group-state filter notes checked in a selected dy_yes view).

1. **Future Generations heading restored**: "The Future Generations indicator — club
   sport" (per P09 and the transcript naming); the O11 comparability caveat and
   provisional-construction note remain in the body — the section was never missing, only
   retitled by the 008 compromise, now reversed.
2. **Profile table restored to the Sport Wales field list**: "Total number of pupils who
   took part in the 2026 survey" and "Total number of pupil responses included in this
   report*", both populated with 366 (the pupils who recorded survey answers); the
   reviewer's export/excluded rows removed per owner instruction. The 484/118 transparency
   story remains in FAQ 4 ("Why are some pupil responses missing?") and the appendix
   completeness chart — the FAQs are retained in full.
3. **Top-five accompanying note restored to Sport Wales verbatim**: "This bar chart shows
   the most common 5 sports… There were a total of 93 sports to choose from. Click on the
   'View Data Table' to see the full results." (93 = export-evidenced count; 92 cited, for
   SW confirmation.)

Source-Deviation Register updated to v2 recording all three reversals.

---

# Sport Wales feedback — compliance record (v2.3 / build 008)

Build: **2026-prototype-008** · pipeline 0.8.0 · 2,052 states · 85,160 paragraphs · QA PASS · pytest 22/22 · 25/25 corrective-gate checks PASS

## v2.3 — the confirmed corrective build (Final Decision Approach, approved)

Implements the approved Final Decision Approach in full, plus the three required
implementation clarifications from the approval message.

1. **2022 sweep**: every unsigned equivalence claim replaced with the O11 caveat (final
   summary, appendix methodology, listened-to narrative); two new build gates fail on
   unsigned 2022 equivalence phrasing (narrative-level and assembled-HTML-level).
2. **Population table**: three-row structure (records in export 484 / valid pupil
   responses included 366 / records excluded 118); deviation logged in the register.
3. **Heading**: "Combined club-sport measure (provisional)" with FG-38 context retained.
4. **Placeholders**: CfW sentences removed; neutral filter wording; FSM national-context
   sentence removed; Teacher Survey and FSM band retained as marked placeholders
   (owner decision).
5. **Summaries**: retained with visible D22 provisional markers; suppression build-flag
   implemented (off).
6. **Sport chapter**: description narrowed to participation + demand with explicit
   signposting to the setting sections and appendix tables.
7. **Tier 2 composite** (owner instruction + survey-derived classification): 43 codes
   classified from the "(Other category)" routed questions; display-level "Other sports
   (composite)" bar in the overall and per-setting charts (individual Tier 2 bars fold
   into it; every data table keeps full detail); composite excluded from all ranking
   narrative and reported through the mandated qualified sentence with the counted-once
   explanation. **Clarification 1** — the two populations reconcile exactly: 161 routing
   selections → 149 answered a routed question (12 blank) → 79 named a valid Tier 2 sport
   (the composite basis) + 70 "None of these" only; definitions and chain in companion
   §5.2. **Clarification 2** — per-setting counts (45/32/18/4) documented as
   non-mutually-exclusive (99 mentions vs 79 unique pupils), companion §5.3.
   **Clarification 3** — composite never ranked as a single sport; verified by narrative
   guard and automated check. A04 prevalence and the A05 treatment comparison (accumulated
   vs maximum vs average differ by exactly one pupil) are in companion §5.5.
8. **Review/release configurations**: review banner; provisional-capability markers on the
   sensitive charts; `CONFIG` switches for sensitiveFilters (release default off),
   reviewMode and showSummaries.
9. **Terminology/QA**: "right-hand chart" disambiguation; "93 sports and activities listed
   in the survey"; navigation stops extended (thanks + data availability); version 008.
10. **Evidence pack issued with this build**: Definitions & Calculations Companion v2.3,
    Source-Deviation Register (7 entries), Interaction Audit paper (A06/O13, eight-point
    inventory for all 12 selectable sources + recommendations), plus this record. The
    complete page-by-page feedback document should accompany the pack to the reviewer.

Verification: 25 automated gate checks over the built file — all PASS; QA PASS over 2,052
states / 85,160 paragraphs; pytest 22/22; no script errors in jsdom runs including
filtered, cohort and suppressed views.

---

# Sport Wales feedback — compliance record (v2.2)

Build: **2026-prototype-007** · pipeline 0.7.0 · 2,052 states · 83,893 paragraphs · QA PASS · pytest 22/22

## v2.2 — meeting decisions round (11 August register + speaker-corrected transcript)

This revision applies the Agreements/Decisions/Actions Register and consolidated transcript
on top of the page-by-page feedback (which remains the wording source, decision D01).
Verified by a scripted decision-by-decision sweep (17 checks, all PASS after fixes) plus
rendered screenshots and the standing QA gates.

**Agreed decisions implemented (D-series):**

| ID | Decision | Implementation |
|---|---|---|
| D01 | Page-by-page document = detailed source; Copilot = structural | Maintained — nothing from v2.1's page-by-page implementation was reverted except where the meeting explicitly superseded it (frequency construction, ordering already settings-first). |
| D02 | Open with an any-participation headline | New "How many of our pupils take part in sport?" statement block opens the chapter: 363 of 366 (99%). |
| D03 | Settings before overall frequency, then setting sections | Order verified: headline → settings → overall frequency → in-school → outside-school. |
| D04 | In/outside-school headings, four settings kept separate | Already the v2.1 structure; headings are narrative groupings only — no new aggregate variables. |
| D05/D06 | Top five per setting in main chapter; sport detail in Sport chapter | Retained from v2.1. |
| D07 | Interactions must state active filter and population | Every chart now carries "Showing: {view}" when the report is filtered, alongside the existing banner, per-chart bases, ghost outlines and selected-group context lines. Full interaction audit (A06) is scheduled after this build and logged as open. |
| D08 | True zero distinct from less-than-weekly | The overall chart separates "No sport reported" (3 pupils) from "Less than once a week" (26). |
| D09 | Raw, unweighted school-level analysis | Preserved and stated in the report and companion. |
| D10 | Frequency-chart fallback if top-heavy | Chart retained provisionally; the headline statistic already exists (D02), so the fallback is a removal away. Sensitivity evidence is in the companion. |
| D11 | Visible questionnaire-consistent setting definitions | The in-school / outside-school section intros carry the questionnaire definitions on the page. |
| D12/D13 | Demographics: as much as safely possible; diagnostics before filters | Current design (profile + in-chapter filterable charts + appendix tables) retained; suppression and deductive-disclosure diagnostics for this school are in the companion (§6). |
| D14 | Standard setting terminology; no ambiguous "organised" | "Organised" removed from every reader-facing string (narrative templates, table labels, methodology, prompts); settings named directly. |
| D16/D18 | Streamlined derived-variable material + companion | `SSS2026_ILR_Definitions_Calculations_Companion_v2.2.docx` issued with this build — definitions, calculations, diagnostics, OPEN items marked. |
| D17/D19 | One coherent revised version before the next broad review | This build. |
| D21 | Remove/relocate technical jargon | Methodology stays in the appendix; new measures explained in plain language on-page. |
| D22 | Park chapter/report summaries | Summaries retained untouched this round; re-wording deferred until measures stabilise. |
| D20/D23, A13–A18 | Translation format, Young Artist, media follow-ups | Workflow/actions outside the report build — noted, not report changes. |

**Provisional positions built (P-series):** P01/P02 — overall frequency is the raw
accumulated occasions measure on the 0–7+ scale; **reproduces the in-meeting live test
exactly (238 of 366 at 7+; 188 excluding somewhere else)**. P03 — CMO reference reworded as
reflection ("does not show the guidelines are met…"), final wording with Owen/Emma. P06 —
per-setting frequency uses the same accumulated construction on the fuller scale (school
club data peaks at the low end, supporting the fuller scale). P07 — "Follow a group of
pupils" pointer added to the profile page and an exploration reminder to the Everyone part;
full early filter controls await the disclosure diagnostics. P09 — Future Generations
indicator subsection (indicator 38) sits after the setting pages with the comparability
caveat. P10 — ethnicity keeps the detailed profile + participation comparison, no
white/non-white filter. P04/P05 (Tier 2) — pending the Tier 1/2 classification list;
logged OPEN.

**Actions discharged in this build:** A01 (this build), A02/A03 (frequency sensitivity
tables by phase and setting-combination, companion §3), A07/A08 (suppression and
deductive-disclosure diagnostics for this school, companion §6), A10/A11 (companion
document), A19 (open-question log = companion §8). A04/A05 await the Tier 2 list; A06
(interaction audit) runs next; A09 scenarios described in companion; A12–A18 sit with
Sport Wales/ILR outside the build.

**Open points (O-series)** are carried verbatim into companion §8 and are not represented
as decided anywhere in the report.

---

# Sport Wales feedback — compliance record (v2.1)

Build: **2026-prototype-006** · pipeline 0.6.0 · 1,944 states · 80,154 paragraphs · QA PASS · pytest 22/22

This record covers the **complete page-by-page feedback document**
(*2026 School Sport Survey — School Reports — Notes — SW to ILR v2 (1).docx*, 60 rows,
pages 1–50), which supersedes the partial version and aligns with the Copilot summary.
Every row was checked line-by-line against the built report with an automated jsdom sweep
(42 v2.1 checks + the 59 v2 checks re-run where still applicable — all PASS) plus rendered
Chromium screenshots. Nothing outside the specified changes was edited or removed.

## Rows 1–11 (Throughout → Page 7)

Identical to the earlier partial document and already implemented in v2 (2026-prototype-005):
terminology ("You are Viewing", "Pupil Responses Included", "Based on: X pupils"),
navigation pane + contents page + Back/Next buttons, "Partial coverage" removed, cover
unchanged, welcome text verbatim, 12-question FAQ page, profile page rebuilt with the full
school-information block, single-colour profile charts, non-binary/PNTS note, additional
profile charts/tables + FSM context, Key statistics (p5) and Overview (p6) pages removed,
chapters merged into "An Active Nation for Everyone" with the provided intro. Re-verified
in this build.

## Rows 12–16 (Pages 8–11) — the Active Nation journey

| Row | Feedback | Status |
|---|---|---|
| 12 | Swap pages 8 and 9 — Settings first, then Frequency; graphs near each other; interaction needs explaining | **Done** — settings section now precedes frequency, directly adjacent; the settings text and Top Tip explain the interaction. The deeper question about frequency×sports selection logic is held as a discussion item (see Outstanding). |
| 13 | Frequency section retitle + replacement text (CMO line); chart "How many times do our pupils do sport each week?"; base only; highest level across all settings; box "What is this chart showing?"; no gender/year analysis | **Done** — all applied verbatim; chart uses the all-settings derived measure. |
| 14 | Settings retitle + text; chart "Where are our pupils taking part in Sport?"; box title; Top Tip "Click on each bar and explore how the data changes across different charts" | **Done** — all applied verbatim. |
| 15 | New "How are our pupils active through sport in School?" — provided section text; four charts (PE frequency, PE top-five sports, school-club frequency, school-club top-five); titles as specified; base only; "What is this chart showing?" boxes with the three-sentence structure; no gender analysis; "total of N sports to choose from" note | **Done** — section, text and chart titles verbatim; analysis boxes generate the three specified sentence forms with computed values (the school-club figures match the examples in the feedback exactly: 159 of 363, largest group 54 '1 time a week', Tennis 53 of 159). Sports-to-choose-from note shows 93 — the number of sports evidenced in the export; Sport Wales cite 92 on the survey list, to be confirmed. The settings tick means "done this school year", so the phrase "each week" is omitted from the first sentence for accuracy. |
| 16 | New "How are our pupils active through sport Outside of School?" — same structure for clubs outside school + somewhere else | **Done** — as row 15. The closing note about the frequency×sports interaction logic is a discussion item (Outstanding). |

## Rows 17–25 (Pages 12–19 + demographic strategy)

| Page | Feedback | Status |
|---|---|---|
| 12 | Remove — covered above | **Done** (folded into the outside-school section). |
| 13 | Move to Sport section | **Done** — sports-overall chart opens the Sport chapter. |
| 14 | (no notes) | Removed in v2 per the earlier boy/girl-sections feedback; unchanged. |
| 15 | Move to summary section | **Done** — the "How active are our pupils — summary" block now sits in the end-of-report summary area. |
| 16 | Remove (chapters combined) | **Done.** |
| 17 | Move joining-in to Lifelong | **Done** — placed beside confidence, before the confidence/enjoyment/joining-in links section. |
| 18 | Remove / relocate depending on decisions | Removed (the right-hand filters cover boy/girl participation). |
| 19 | Move year-by-gender to Lifelong | **Done.** |
| 20/21/23/24 strategy | Three location options + considerations | Current design: school-wide profile on the profile page, cohort pages inside the chapter as filters, full per-view tables in the Appendix — consistent with the options discussed; final location decision stays with Sport Wales. |

## Rows 26–33 (Pages 20–25, demographic pages)

All amended texts applied verbatim: disability (row 26) and learning difficulty (row 28)
context + "filter the wider report … through this lens"; the confusing selected-state note
replaced with "The bar selected filters the wider report by pupils who responded 'Yes' to
this question…" (rows 27/29); learning-difficulty join-in analysis removed (participation
reported instead); take-part text (row 30); Welsh language text (row 31); ethnicity text and
the reworded red-box note "There were not enough responses from pupils in different ethnic
groups to allow the report to be filtered by ethnicity…" (row 32); the "able to join in at
least sometimes" analysis removed from the chapter summary, which now points at the
participation-variation table (row 33). Row 26's "remove analysis focus on community club
setting" — the analysis uses the combined club sport (school or community) measure, with no
community-only commentary.

## Rows 34–54 (Pages 26–45, A Lifelong Enjoyment of Sport)

| Row | Feedback | Status |
|---|---|---|
| 34 | Merge + rename + provided intro | **Done** — intro text verbatim. |
| 35 | Participation at the highest level; amended text; settings-filter question | **Done** — the by-year table now uses "did sport at least once a week in any setting"; text amended; and yes — the table is filterable by selecting a settings bar (a tip in the text says so). |
| 36 | PE/Active Lessons text; "what is Positive?" | **Done** — text applied; the narrative no longer uses an undefined "positively", it states the answers ("said 'very' or 'quite'…"). |
| 37 | What-matters text + exact analysis forms incl. boys/girls lines | **Done** — computed output reproduces the cited figures exactly: Having fun 295 of 366; Being with friends 225; boys 141; girls 149. |
| 38/39 | "I would do more sport if..." text + simplified four-sentence analysis | **Done** — leader (202 of 366), Next came 'I felt more confident' (117), 56 chose 'None of these', low-confidence cross (37 of 58). |
| 40 | Barriers-by-group text improved; no phase references | **Done** — section reinstated with the suggested text verbatim; gender leaders only, no phases. |
| 41–44 | Pages 32–35 to Sport section | **Done** — latent demand, demand by group, unmet demand and the participation-and-demand comparison all sit in the Sport chapter. |
| 45/46 | Remove the separate Lifelong and Enjoyment summaries/openers | **Done** — single chapter with a single summary. |
| 47 | Enjoyment text; interactivity question | **Done** — text applied; every value on the PE enjoyment chart is selectable (not just 'a lot'), resolving the "if not all bars can be selected" concern while keeping the interaction. |
| 48 | Enjoyment-by-groups text + "What is this chart showing?" + year extremes | **Done** — reinstated; output matches the cited example exactly (Year 4: 23 of 28, 82%; Year 10: 16 of 49, 33%). |
| 49 | Feeling-listened-to added text incl. Curriculum for Wales link | **Done** — the CfW reference renders as "[reference to be confirmed by Sport Wales]" pending the XXX in the feedback. |
| 50/52 | Either remove or replace with filter pointer | Removed (option 1), as in v2. |
| 51 | Confidence text (+CfW), "What are these charts showing?", most/least-likely analysis; interactivity question | **Done** — text and heading applied; analysis reproduces the cited figures (learning a new skill 313 of 366; trying sport in a new place 267 of 366); every confidence-to-try value selectable. |
| 53 | (no notes) | Unchanged. |
| 54 | Update summary for the merge | **Done** — one chapter summary carrying enjoyment, confidence, stage variation, barriers and the demand aggregate. |

## Rows 55–59 (Pages 46–50)

Pages 46/47/49/50: to be reviewed by Sport Wales on receipt of this version — no changes
made. Page 48 ("Data available in this view"): **relocated to the bottom of the report**,
after the Appendix, per the "Remove / Relocate to bottom" instruction.

## Language

The narrative voice is now pupil-first throughout ("pupils across the whole school",
"Year 5 girls", "1 pupil response") in line with the feedback's own sentence forms; the QA
gates were extended to enforce the same grammar rules for the new vocabulary. "Most likely"
was removed from the banned-terms list because the feedback mandates the sentence form
"Pupils were most likely to say…".

## Outstanding / discussion items (for Sport Wales)

- Frequency×sports chart interaction logic (row 16 tail): what a joint selection should
  mean, and whether an explanation belongs on the page — to discuss.
- Sports-on-the-list count: export evidences 93; feedback cites 92 — confirm.
- Curriculum for Wales references for listened-to and confidence (XXX in the feedback).
- Demographic location decision (rows 25): Option 1/2/3 sign-off, GDPR threshold, and
  suppression-rate analysis across schools.
- 7+ frequency scale and Tier 2 sports (carried from the earlier round); FSM band and
  teacher-survey data sources; print page numbers; production payload workstream.

## Verification evidence

- Automated page-by-page sweep: 42 checks over all 60 rows — ALL PASS (after the QA gates
  themselves caught and forced fixes to three template defects: tie counts in fact objects,
  base-of-one guards for the new leader forms, and a 70-word split in the confidence
  analysis).
- Build QA PASS over 1,944 states / 80,154 paragraphs; pytest 22/22; jsdom boot and
  interaction runs clean including the newly selectable enjoyment/confidence groups.
- Rendered checks: settings→frequency order, in-school and outside-school sections,
  demographic texts, any-setting participation table, reinstated group sections, Sport
  chapter, relocated summary and data-availability sections.


---

## Build 010 (2026-08-18) — Sport Wales V2 feedback + owner decisions

**Version:** 2026-prototype-010 · pipeline 0.10.0 · QA PASS · pytest 21 passed / 1 skipped · jsdom structural + interaction sweeps ALL PASS.

Implemented (per the V2 feedback table and the owner's instructions):

- **Frequency (agreed estimate):** the overall chart is now the per-setting mean of weekly sports, summed and rounded half-up; "Less than once a week" and "I don't know" excluded from the averages and shown as categorical columns with "No sport reported", so the chart always totals 366 (3 / 15 / 11 / 19, 47, 54, 58, 58, 34, 28, 22, 17). Bands 1–8 and 9+. Chart is selectable (rule-of-five gated); "On average, pupils participated in X sports throughout the academic year" line added and updates with every filter.
- **Stacked sport × frequency charts:** top-10 (no 'Other'), Base totals at bar ends, legend, "What is this chart showing?" box and expandable data table — added to the overall frequency section and to all four setting sections (replacing the left-hand frequency charts). Per-setting analysis boxes rewritten: participation + top sport + average-sports line; the orphaned largest-group frequency sentence and all Tier 2 composite sentences removed (register decision: no user-facing Tier 2 references).
- **Demographic settings section:** disability/learning-difficulty charts replaced by "Where are our pupils … active?" settings charts for (a) disability and/or learning difficulty combined, (b) ethnically diverse backgrounds (Welsh Government grouping guidance; under-five groups pre-combined), (c) Welsh speakers (with "Do you usually speak Welsh when you play sport" kept). Yellow hint box added; dl average-sports sentence included; sections suppress below five pupils in view.
- **Filter panel:** demographic dropdown (single pupil-group model) — disability and/or learning difficulty, ethnically diverse backgrounds, speaks Welsh — alongside phase/year and gender; numbered clickable contents with heading-styled title; "FAQs" → "How to use this report"; "Sport" → "Sport Specific Data"; Explore results heading red.
- **Colours (owner decision):** all charts alternate red/blue by option index, including the profile page. Grey strictly for null-value columns, unclickable bars on selectable charts, and suppressed values; yellow marks the selection.
- **Suppression:** suppressed sections now show a GDPR-worded suppression card instead of disappearing; the view-level message also carries the GDPR wording. New FAQ on hidden numbers and on grey/blank/unclickable bars; inclusion FAQ at 80% (owner override of SW's 70%; completed-only in this dummy run).
- **f2/e4:** replaced with stacked year × setting and year × gender × setting charts with amended headings/wording and updated analysis (leading-setting extremes; year-gender best-combination line retained).
- **Wording rows:** FAQ rewrites, profile page (red note, RSP "West Wales Sport Partnership [WWSP]", *note removed, larger gender-note font, tip box and "Additional pupil profile" removed, disability table removed, Welsh table → bar chart with FSM beside it), headline sub-note shrunk, f3f5/g2 split-heading chart titles, f6/f7/g5/g8 headings and text, unmet-demand definition + gender-rank analysis sentence, f14 question box removed, thank-you (Autumn 2026 national findings + technical report), Methodology & Definitions removed from the appendix.
- **Removed sections:** variation summary table, chapter summaries (e10, g12, d10), f8, and the "Data available in this view" panel. Future Generations indicator kept in its current (max-rule) form with the agreed 2022 note.

Deviations / pending:

- Provision survey information (feedback row 6, "can this be added?") — no provision-survey data supplied; not added.
- Sport chapter image (row 41, "update image") — no new asset supplied; brand-form placeholder retained.
- Small-schools check for the demographic settings section (row 19) — modules self-suppress below five pupils in view; a whole-school-level policy for micro-schools remains open.
- Teacher survey / FSM band remain placeholder values pending Sport Wales confirmation.


---

## Build 011 (2026-08-18) — polish round: owner decisions + colleague QA

**Version:** 2026-prototype-011 · pipeline 0.11.0 · QA PASS (3,096 states / 105,036 paragraphs) · pytest 21 passed / 1 skipped · jsdom regression 41/41 PASS including e7-empty views and all three DL modes.

Implemented:

- **e7 nesting defect (colleague QA, highest priority):** the missing closing div after "How pupils take part in sport" is fixed; e7, n_ed and n_wl are confirmed siblings, and views where e7 has no content (e.g. whole-school Tennis) now correctly show the ethnically-diverse and Welsh-language sections. Regression test added.
- **Frequency terminology (colleague QA):** the estimate measures times active per week, not number of sports. Cohort labels are now "Estimated times active through sport each week: N" and narratives read "were active through sport an estimated N times a week". The separate average-number-of-sports statements are unchanged, as agreed.
- **Whole-number averages (owner):** every average sentence reads as a whole number with the exact average retained in brackets — "participated in 12 sports throughout the academic year (12.3 average)" — standard half-up rounding, applied to the overall, per-setting and disability/LD sentences.
- **Full chart titles (owner):** split-title sets recombined as complete titles — "How much do pupils enjoy sport: in PE Lessons?" (pupils, not our pupils) and "Do PE and Active Lessons make you feel: Healthy?" — replacing the "..." convention.
- **Red filter reminder (owner):** short red line "Click a bar to filter the report by these pupils." restored on selectable charts only (the verbose SW-deleted version stays removed).
- **Mixed disability/learning-difficulty rule (owner decision):** per-view three-tier display — separate disability and learning-difficulty settings charts where each group has 5+ pupils in view; automatic combination when either falls below 5 but the combined group reaches 5 (with an explanatory note); GDPR suppression card below that. Overlap note states that pupils reporting both appear in both charts and gives the combined count. Rail filter list now offers disability, learning difficulty, combined, ethnically diverse, and Welsh-speaking groups; existing view-level suppression catches small intersections.
- **Colour-coded (struck) V2 deletions now applied** (root cause: red-strikethrough deletions inside "Amend wording" cells were lost in plain-text extraction): e7's two struck sentences; f2 tip line; e4 struck context sentences; "not clinical measures"; g5 "better placed to shape provision" clause and the 2022-basis clause (narrative and static summary note); g8 "about" and the try-a-new-sport selection sentence (plus the unagreed "one chart carries the selection" additions removed from g2/g8); Sport-chapter middle sentence; latent-demand "menu" sentence; f14 "starts conversations" clause.
- **Missed heading changes:** "Do our pupils feel listened to?" and "How confident do our pupils feel?".
- **FAQ overhaul (full row 6, previously truncated in extraction):** agreed order implemented; new texts for missing-responses (at 80%, owner override of SW 70%), how-do-I-use-filters, percentages, percentages-to-100%, numbers-to-total; "Filters apply from the first chapter onwards" note removed. The missing-responses and grey-bars items are not in SW's order list and are slotted logically — recorded as a deviation for sign-off.
- **f13:** SW leader form ("Pupils were most likely to have unmet demand for Dodgeball, selected by 81..."); duplicated rank sentence removed (single rank-shift sentence retained).
- **e4 narrative** rewritten to describe the setting-based stacked chart ("The highest reportable participation in a single setting...").
- **New permanent QA gate (owner):** any generated sentence matching "Across boys/girls/pupils across" fails the build. The gate immediately caught and forced a fix to the parent-compare template ("For comparison, across pupils..." → "among pupils...").
- **Disclosure fix found in passing:** suppressed sections no longer render their own charts behind the GDPR card (small-group chart data could previously still be drawn).

Appraisal outcomes recorded: retained "like the park or garden" (survey help text, not struck); profile charts stay red/blue and disability/LD profile charts stay (owner decisions); provision-survey info still pending data; "our School" capitalisation confirmed a misread.

Deviations / open items: Sport-chapter image still placeholder (no asset); technical report record retained pending owner decision; summary remains provisional (review build); FAQ placement of the two extra items; register entries needed for the DL mode-switch inference risk and the sensitive-group in-view rule.


---

## Build 012 (2026-08-21) — flat square-root conversion + V3 feedback, full set

**Version:** 2026-prototype-012 · pipeline 0.12.0 · QA PASS (8,568 states / 296,707 paragraphs) · pytest 21 passed / 1 skipped · jsdom regression 42/42 PASS (run on a reduced-state copy; the full 108MB file exceeds the build sandbox's memory, not a defect).

Implemented:

- **Flat square-root method everywhere:** overall chart (W ÷ √N across all weekly sports; 3/15/11 categorical columns; bands 21, 32, 53, 60, 56, 54, 20, 17, 24) and the club chart on the identical formula restricted to club settings (86/13/16; 48, 61, 66, 35, 19, 14, 5, 1, 2; weekly-plus 251). Method text rewritten; measure submitted to Welsh Government with the method note.
- **Future Generations removed entirely:** heading now "Club Sports"; context, appendix tab, summary note and all labels FG-free (verified zero occurrences in the built file); joining-in table moved to the enjoyment appendix group.
- **Filter consistency:** year-by-setting, year-by-gender-by-setting and enjoyment-by-year respond to year and gender filters (single-year / single-gender rendering); one obsolete test updated to the new behaviour.
- **Selectability expansion:** all demand and current sports selectable (min-5 cap trial; legacy six-sport list abolished — build sweep confirmed zero grey bars in the demand top ten); all four enjoyment and all four confidence charts selectable with anti-tautology guards; Club Sports bands selectable; disability/learning-difficulty/combined/ethnically-diverse/Welsh settings charts selectable as compound group-and-setting filters with the coded under-five merge rule. 237 filter groups; state space 8,568.
- **Paywall suppression:** nothing disappears — suppressed views grey every section, render whole-school data underneath (never the protected values), and show a per-section box "Not enough data available for this selection" with GDPR wording; same model for sub-five sensitive-group sections; threshold rule unchanged.
- **Grey scheme:** light grey = non-selectable, dark grey = suppressed; new FAQ entry explains both plus greyed sections and keep-scrolling guidance.
- **Multi-choice co-selection (f6/f7):** selecting an answer leaves only that bar and reveals "What else did these pupils select?" beneath — the only appear/disappear behaviour in the report; demand-sport selections get the "also most wanted X, Y and Z" sentence.
- **Profile completeness (hard rule for future schools):** all seven high-level ethnicity categories with exact counts (Black 1, Other 1) and zeros, nobody combined, WG "White Welsh, English, Scottish, Northern Irish, or British" label, section unfiltered and unsuppressed; gender chart retitled with Boys 174 / Girls 186 / Non-binary 0 / Prefer not to say 6 (non-binary verified as a survey option); teacher survey row removed; FSM placeholder with the deprivation sentence.
- **Filter-group redefinitions:** ethnically diverse now includes positively identified White minorities via the detailed background question (categories only, free text never used; 26 → 45 pupils); Welsh = top three tiers (138 → 290).
- **Averages:** whole numbers only, decimals and brackets removed.
- **Scroll anchoring:** applying filters returns the reader to the nearest heading above their position.
- **All V3 wording rows:** contents text, intro chapter list, FAQ items (red Explore results, raw-counts caveat, below-five sentence removed), d3 multi-settings sentence, "used by N pupils" grammar, stacked-box de-duplication with top-three sport analysis throughout, "like the park or garden" removed from generated sentences, groups intro to all-settings, e7 retitle ("long-term condition" verified as survey wording), Welsh use-of-language wording, per-year breakdown sentences with data tables, "highest reportable" phrasing simplified, g3 all-settings table, g11 removed, unmet-demand 2026-vs-2022 caution, f14 retitle.
- **Defect found and fixed by the regression sweep:** cohort_codes "all" serialized as a string, silently disabling clickability on expanded charts — expanded to code lists at package build.

Unchanged as instructed: images (final swap before distribution), stacked sport×frequency charts, structure and order, profile red/blue, 80% inclusion FAQ, summary and appendix under-review sections.

Notes: file size is now ~108MB with 8,568 pre-calculated states (the approved cap trial); first load in a browser will take noticeably longer than 011. The min-5 selectability cap and the mode-switch inference risk remain register items.


---

## Build 012.1 (2026-08-21) — colleague review response

**Version:** 2026-prototype-012.1 · pipeline 0.12.1 · QA PASS (8,568 states / 303,036 paragraphs) · pytest 21/1 · jsdom regression 26/26 PASS (reduced-state copy).

Accepted and fixed:

- e7 ("How do our pupils with a disability or long-term condition take part in sport?") no longer disappears under its own filter — legacy GROUP_TIER_SKIP entry removed, anti-tautology guard added, section visually joined to the disability section above.
- Co-selection chart label resolved from the metric's option list ("undefined" fixed; cohort optionLabel now also serialized).
- Expandable data tables added to both year-participation charts (year × setting, year × gender × setting) with n/r markers and the participation-not-frequency clarification.
- Ethnically diverse section wording rewritten to the agreed definition ("high level", White minorities listed, no under-five combining claim); metric documentation already updated in 012. The 45-pupil figure verified against the respondent-level derivation (the ~43 was a pre-build estimate from raw rows).
- Old combined ethnicity table removed from the appendix (profile seven-category table is the single source).
- "like the park or garden" removed from all generated narrative (two remaining sources: the somewhere-else module call site and the enjoyment settings list — verified zero occurrences in 303,036 paragraphs); retained in chart/question descriptions as agreed.
- Enjoyment introduction now says each of the four charts is selectable.
- Unmet-demand duplicate: not changed — the rank sentence is Sport Wales's own requested wording from V2 row 44 (challenged back, see below).
- Gender chart base note corrected (bars now sum exactly); teacherSurveyCompleted removed from embedded data; g11 module label removed from metadata; obsolete overall_freq metric removed; paywalled sections now set inert (keyboard focus blocked).
- FAQ light-grey wording corrected per the owner's text: eligibility threshold is whole-school; counts below five may display in reportable views.
- White category label: "…Northern Irish, or British" retained ("or" matches both the survey instrument and the written V3 feedback; owner spoken "and" noted).

Challenged (no change):

- **Sub-five filtered-group suppression (their point 1): rejected by the owner.** The agreed rule: suppression keys on the demographic view (year × gender); chart-derived response groups are not independently identifiable; selectable options need five school-wide; exactly five reportable. The Boccia example (4 of 174 boys) is compliant. FAQ wording aligned instead.
- **Club "3+ = 142 vs agreed 121" (their point 2): not a calculation error.** 121 counts pupils whose unrounded estimate is ≥ 3; the chart's bands 3–9+ total 142 because band 3 spans 2.5–3.5 under the agreed half-up rounding. The chart and its bands are internally consistent; the 121 belongs to the analysis note and will be footnoted as "before rounding" in external documents.
- **Unmet-demand rank sentence (their point 11):** wording is Sport Wales's own requested green-text addition (V2 row 44); retained pending SW instruction.

Outstanding for release: performance testing of the ~109MB file on school laptops (register item); final in-browser eyeball by the owner; image swap before distribution.


---

## Build 013 / V4.1 FINAL (2026-08-27) — Sport Wales V4 targeted text edits

**Version:** 2026-prototype-013-V4-final · pipeline 0.13.0 · QA PASS (8,568 states / 301,047 paragraphs) · pytest 21/1 · jsdom sweep 35/35 PASS. Targeted round: only the red-text replacements in the V4 feedback document, plus the two flagged defects, changed; everything else byte-identical in intent.

Implemented (V4 rows): four FAQ amendments (frequency-value clauses removed, "raw," dropped, exception sentence dropped, greyed-sections wording replaced); new FSM Quartiles FAQ; overall-frequency context reduced to the typical-week/guidelines wording with chart title "On average, how often are our pupils engaging in sport each week?" and method base-note removed (same treatment for the club chart with "…in club settings?"); "Somewhere Else (such as the Park, Beach or Garden)"; short Club Sports context; club analysis extended with the three-or-more clause (142 of 366, 39% — chart-band figures); disability/LD combined-line and overlap note removed; ethnic-minority chart text (Gypsy, Roma and Traveller communities named); Speaks Welsh categorisation text; girls-and-boys year chart text with the small-sample note; enjoyment-table sentence trimmed; joining-in text simplified; demand-groups clause trimmed; "Participation and Unmet Demand Together" + "Most participated in sports"; "Other sports" supplementary-list wording (template note and generated sentence); appendix Pupil profile detail removed.

Defects fixed (flagged in the document): **chart/text alignment** — the top-three sport sentences now rank from the same frequency-grid bases as the stacked charts, so text and chart always agree (verified: Tennis 52/Athletics 47/Netball 46 in both, overall Tennis 273/Football 221/Running 214 in both); **Years 10 and 11** now appear in the demand-by-year sentence — tied leaders are named instead of silently dropped.

Questions in the document, answered without changes (as instructed):

- Aggregate stacked-chart calculation and the overall data table: held for Thursday's discussion. Note: a true aggregate (counts summed across settings) makes bar totals exceed pupil counts (a pupil doing tennis in three settings counts three times).
- PE-feelings charts "interaction disappeared": those charts have never been selectable in any build; making them so is a small addition if wanted.
- "Speaks Welsh when playing sport" chart doesn't filter: correct — never selectable; same easy addition if wanted.
- Filter jump: scroll now anchors to the nearest heading; an exact-position restore is possible if preferred.
- Ethnically diverse data double-check: verified — 45 pupils = every non-White high-level group plus positively identified Irish / Gypsy or Irish Traveller / Roma / other-White backgrounds, categories only, free text never used.
- Row 11's question was cut off mid-sentence in the document ("What happens to the…") — needs re-sending.
- Rows 41/42 (thank-you/appendix) left untouched pending Welsh translation decisions, as marked.


---

## Build V4.2 (2026-08-27) — bilingual English/Welsh report

**Version:** 2026-prototype-V4.2-bilingual · pipeline 0.14.0 · QA PASS · pytest 69 passed / 1 skipped (including the 48-test Welsh grammar acceptance suite transcribed from framework sheet 26) · jsdom toggle regression 22/22 PASS. **English content is byte-identical to locked V4.1** (narrative corpus hash 3efdb7f2 verified before and after).

Architecture, per the Welsh Generation Framework v1.5: the Welsh sentence is generated from the same language-neutral fact record as the English, never translated from it. Implemented: the full grammar engine (soft/nasal/aspirate mutations with the exceptions register, vigesimal a/ac and article selection over figures, gendered cardinals and ordinals, list construction, noun-singular-after-numeral); the 36 audience forms; all 116 qualifier frames keyed to the report's cohort families; the 178-label lexicon with the D32 dual-grid scale rule and the golden-test unadapted-name rule; the predicate inventory; and renderers for all 91 live template families (composite paragraphs included).

**Welsh narrative coverage: 271,966 of 271,966 paragraphs (100%).** Chart option labels, stacked-chart legends, data-table labels, the base line ("Yn seiliedig ar: N disgybl", singular after every numeral), the what-is-this-chart-showing heading, and the framework-quoted interface strings render in Welsh. The toggle (rail button, hash-persisted, html lang switched) re-renders every dynamic element; filters, paywall and co-selection all work identically in both languages.

**The known, deliberate gap:** the translation handoff workbook's Welsh column is empty — 0 of its 446 page-furniture strings (headings, context paragraphs, FAQs, button labels) are translated. The framework explicitly reserves these for the human translator and instructs that blanks fail loudly rather than be invented. In Welsh view these strings appear in English with a dotted-red review marker and a standing review note in the filter rail. When the translated handoff returns, the strings drop into the embedded catalogue keyed exactly as the workbook specifies.

Also recorded: framework finding F-06 (the English report renders "21st" as "21th" in one ranking sentence) is a confirmed defect in the locked English; per the lock instruction it was NOT corrected in V4.2 and awaits the next sanctioned English edit. Framework statuses: most templates remain PROPOSED/DERIVED pending the Welsh linguist's sign-off of sheets 02/05/18-21 — the framework's own order of work; the full distinct-output review before publication remains theirs. File size 164MB (bilingual payload); the V4.1 performance caveat applies with more force.

---

## Build V4.3 (2026-09-01) — rebuild against Welsh Generation Framework v1.6

**Version:** 2026-prototype-V4.3-bilingual · pipeline 0.15.0 · QA PASS · pytest 77 passed (48 sheet-26 grammar tests + the seven new v1.6 cases T-082–T-088) · jsdom toggle regression 19/19 PASS · **English corpus byte-identical to the shipped V4.2 / locked V4.1** (corpus hash 9bcbc6e66c8e380d before and after) · source checksum e457bc8eccbecad24c061db7fcad986ec3597ac116afa138b141a0ebc8a70552.

**The appraisal was verified before anything was changed:** the supplied gate script, run against the V4.2 build, reproduced every baseline count to the digit (271,966 paragraph occurrences; all 23 gates matching the supplied results file). The 42.3% figure stands as measured.

**Corpus gates (sheet 36 / D45):** on the stock appraisal script, 22/23 gates return zero. The single remaining G4 count (2,493 paragraphs, verified to be 100% of one class) is where the locked English prints a nil count as the digit 0 ("…, 0 said yes." / "…and 0 did club sport…") — the framework's own FT-01 N=0 rule (NUM-N0-NEG) requires a figure-free Welsh negative clause there, so the English 0 can have no Welsh counterpart while the English is locked. A one-line amendment (discard 0 from the English figure set) is proposed to the appraiser; under it the run is **23/23**. Both gate-result files ship alongside the report. The gate script is vendored unmodified into the pipeline and runs inside build QA on every build (D45): a failing corpus can no longer be written out, let alone shipped.

**D40 — one numeral realiser** (pipeline/welsh.py): numeral form, noun number, mutation and partitive are chosen together from value, gender, definiteness and syntactic role; callers can no longer format numbers. n=0 raises (forcing the template's negative branch — deliberate fail-loud). Closed G3a (86,539), G3b (8,368), G3c (1,504), G3e (408) and the G3d complement defaulting (843) with gendered singular threading.

**D44 — role consumption**: predicates now resolve from the measure + answer-code roles (unknown pairs fail the build); the respondent-group role distinguishes disability-only / LD-only / combined; settings, outer cohort qualifiers, head-noun types, answer arity and polarity are threaded through every renderer. Closed G1a–G1e, G2a/G2b, G4, G5 (the distinctness gate — 10,393 baseline — is now zero), G6b, G6c. The five framework fixes of v1.6 (FT-01 zero branch, FT-05 quotation pair, FT-18 arity branches, FT-24 collapse threshold, FT-33 postposed cyntaf) are implemented as specified.

**Deviations register (for the appraiser and linguist):**
- T-084's expected output ("gyda 5 disgybl yr un") and T-085's "(1 disgybl)" would fail the framework's own gate G3a; the build words those numerals per D40/D03 ("gyda phum disgybl yr un", "(un disgybl)"). The tests are transcribed with the worded forms and the deviation noted in-file.
- G6b's implementation forbids the surface pair "Yr ail opsiwn … yn ei ddewis" even in the singular, where FT-18's own singular branch produces it; the singular runner therefore reads "…, gyda X yn dewis yr opsiwn hwn" (mirroring the English "choosing this option").
- Ordinal ranks above 10 use the digit abbreviations (11eg, 12fed, …, 21ain; tens in -fed), mirroring the English switch to "11th" and satisfying figure parity; the exact suffix convention above 20 needs the linguist's confirmation.
- Bare numerators of 2+ keep the figure the English shows (D03 series exception); n=1 is always "un". The parity checker's Welsh vocabulary lacks the soft form "dri" and the aspirate "phump" — adding them is proposed alongside the zero amendment; the realiser avoids both meanwhile.
- In n_dl views whose outer cohort is itself the combined disability/LD group, the outer qualifier is rendered anaphorically ("ymhlith ⟪audience⟫ yn y grŵp a ddewiswyd") — repeating the combined phrase after a disability-only group phrase trips G1c's conflation pattern.
- Q12 (a/ac before ni/nid) remains with the linguist; the affected paragraphs are unchanged.

**Also in this build:** a real V4.2 interface defect found by the tightened regression — the Welsh review note could never display (clearing the inline style fell back to the stylesheet's display:none); fixed. A stale reconciliation test asserting the retired organised_freq metric now asserts the club weekly+ invariant (251). The build is now checkpoint-staged (pipeline/staged_build.py) so the corpus gates, QA and write are separate resumable stages.

**Still open, unchanged:** the translator's 446 handoff strings (still 0 translated — English fallback with review markers); F-06 ("21th") in the locked English; linguist sign-off of the PROPOSED sheets and the 130 answer labels without recorded grammatical gender (awaited from the translator — answer-dependent mutation and superlative agreement stay conservative until then); 164.9MB file size and the school-laptop performance test.

---

## Build V4.4 (2026-09-01) — engineering-complete against Framework v1.7

**Version:** 2026-prototype-V4.4-bilingual · pipeline 0.16.0 · framework v1.7 · QA PASS · pytest 77 passed · jsdom language-state regression 18/18 · **English narrative byte-identical at every level** — the 271,966 module paragraphs (corpus hash 9bcbc6e66c8e380d, unchanged since locked V4.1) and the 53,094 h1/h2 summary and prompt strings, verified before and after · source checksum e457bc8e…a70552 · 174.8MB.

**Sheet-36 acceptance: every gate at zero except the two the sheet itself marks report-only** (G3a+: 0 anyway; G9e: 674, the FT-11 review population — a negative-zero matrix over a cohort whose *defining answer* is itself negative, which PR-02's recast deliberately does not touch). On the handover pack's own runnable script: 29/31 stock, 30/31 after a one-line vocabulary completion (below). All nine plan changes landed:

1. **D40 closed in its second shape** (G8a-c: 64,868 → 0): numerators word to ten in every partitive construction — naw o'r naw disgybl, pump o'r chwech — with gan's soft mutation applied and the 'gyda' aspirate frame where the soft form would be checker-invisible.
2. **D21/PR-10** (G11: 119,922 → 0): running prose takes sheet 23's case-folded prose form, folded BEFORE mutation (pêl droed → bêl droed); citations and chart labels keep the title form; sentence capitalisation applied at the boundary after all mutation decisions.
3. **Sheet 38 dynamic surfaces** (G10a/b: 36,434 → 0): the h1 chapter summaries were being generated and then discarded by a `["t"]`; they now ship as {t,c} pairs with the apart-/aside-clauses, tie-collapse and measure-variation roles completed. The two variable h2 prompts are typed fact records with their own renderers; the two generic prompts route through the translator catalogue with review markers, exactly as sheet 38 directs.
4. **D50** (G10c: 8,567 → 0): the view descriptor is a typed {scope, sex, cohort} record; scope.shortCy is realised by the audience renderer and drives the banner, print footer, rail summary, chart tooltips and the assistive live region. The 30 cohort-frame strings are DERIVED and listed for the linguist.
5. **D48/PR-03** (G9b: 7,265 → 0): singular one-person bases read "yr unig ddisgybl"; qualifier relative clauses singularise behind them (yr hoffent → yr hoffai); complements are gendered only where the view carries a sex, impersonal verb-noun recasts otherwise — never a masculine default.
6. **D46** (G9a: 6,077 → 0): the quoted-slot substitution inserts the bare citation form; one owner, one pair.
7. **ART-02** (G9c: 179 → 0): the article is selected on the realised surface (o blith yr un…).
8. **Zero dispatch on the residual g2/g3 path** (G9d: 377 → 0): dim un o'r…, nid oes yr un o'r…, with the (0%) figure retained for parity.
9. **UI-001** (G10d → pass): one applyLanguageState(), called from the toggle, after the initial readHash and on hashchange; html lang, the toggle's own lang attribute, the review note and the two cached filter controls all follow the hash. Verified by a cold-entry #lang=cy test.
10. **D47** (G12: 496 → 0): the et frame's ANSWER-ID resolves from sheet 23 at lexicon build; the four enjoy-family frames that quote the current approved scale label verbatim are reported as matching copies for the migration.

**D51 mechanism:** all ten provisional rulings are read from the workbook as data (the lexicon build extracts the operative value from each ruling's wording and refuses to build on an unrecognised rewording); the active PR set and framework version are stamped into buildMetadata, so any output traces to its assumptions. PR-02 (answer-selection recast), PR-04 (ac before ni/nid), PR-05, PR-07 (y golwg hwn) and PR-10 are exercised in this build; PR-01's provisional genders are loaded from sheet 23.

**For the appraiser — one script line and three surface deviations.** (1) The figure-parity vocabulary still lacks the soft form 'dri' and the aspirate 'phump'; the stock script's entire G4 residue on this build — 1,067 paragraphs, verified 100% of the class — is the grammatically mandatory 'gan dri' after the agent preposition. The amendment (CY_NUM += dri:3, phump:5) is applied, versioned per D52, in the in-build runner; both stock and amended result files ship with the build. (2) T-084/T-085-class numerals are worded per D40 where sheet 26 still shows figures. (3) 'un ⟪noun⟫' beside any plural clause trips G9b's co-occurrence test even across referents, so singular items in mixed lists read 'un ohonynt' and one-person bases 'yr unig ddisgybl' — sheet 26's T-088 surface is superseded accordingly; the feminine complement it tests is preserved. (4) Ordinal ranks above ten use digit abbreviations (11eg…), mirroring the English switch at '11th'.

**Still outside engineering, per the plan:** the translator's static catalogue (446 handoff strings + the two generic prompts + the client's ~57 hardcoded strings and 217 markup nodes from the integration spec — all EN-fallback with review markers); the linguist's 103 decisions (10 PRs, 68 gender confirmations, 25 wording flags); native-Welsh sign-off of the generated sentence families. Sheet 39 going to zero is the V5.0 readiness measure. The integration spec's hosted-architecture items (per-language URLs, hreflang twins) apply to the multi-page deployment, not this single-file prototype, and remain with the build-architecture owner.

---

## Build V4.5 (2026-09-01) — coverage closed against Framework v1.8

**Version:** 2026-prototype-V4.5-bilingual · pipeline 0.17.0 · framework v1.8 (13 provisional rulings stamped) · QA PASS · pytest 77 passed · jsdom language-state regression 11/11 · **English byte-identical at every level** (module corpus 9bcbc6e66c8e380d = locked V4.1; h1/h2 English 410ef9335f3e3d9c unchanged) · 174.8MB.

**Acceptance:** the handover pack's gate script v3 — vendored verbatim into build QA per D58, replacing the superseded v1.7 set — scores the delivered file **25/25 blocking gates, over every surface it defines** (237,844 module paragraphs · 29,081 h1 · 7,353 h2 · 8,568 scope descriptors · 790 option labels · client source). That exceeds the plan's 25-of-26 target because the PR-12 provisional (suppress the derived percentage in Welsh) is implemented, zeroing PAR-added-h1 without waiting on the ruling. Report-only remainder: PUB-copy 82 (identical strings pending the signed loan list — overwhelmingly unadapted sport names), CONJ-fnword 6,113 (PR-04 configuration, linguist), POL-stacked 576 (FT-11 review class, down from 2,797).

**The seven fixes, delivered in order:**
1. **All 228 placeholders closed.** Sheet 31's metric→question mapping is read at lexicon build; a binary metric's descriptor and chart labels echo its own question's verb (Anabledd neu gyflwr tymor hir: Oes / Nac oes; Ydw / Nac ydw), and a metric absent from the table fails the build (D54). PR-11 names the derived ethnicity set. DIS-scope's 72 collapses closed with it.
2. **PR-02 fires on closings** (D55): the nil-count recast now applies to h1 summaries; POL-stacked fell 2,797 → 576, and POL-uniform is zero. Where a negatively-defined cohort would stack under a negative matrix, the 'heb' verb-noun construction negates without a second particle.
3. **D56 across all 1,119 records:** 'yr unig ⟪noun⟫' subjects with fully singularised qualifier clauses (yr hoffent→yr hoffai, y byddent→y byddai, eu bod→sy'n/sydd fel arfer yn, a oedd ganddynt→a oedd, and gendered forms where the view carries a sex); no partitive over a singular set; the earlier 'unig … un ohonynt' recast — which the appraisal correctly reclassified as the same error — is retired for subject-elided singular clauses.
4. **FT-16 routes through the realiser:** the f7 citation count is worded (dewisodd chwech ‘Dim un o'r rhain’); NUM-figcite 4,442 → 0.
5. **CONJ-vig 173 → 0**, and the underlying engine defect it exposed is fixed: reading_first_word read 21–39 by their unit digit instead of the vigesimal teens (36 leads 'un', not 'chwe') — corrected to the true vigesimal ladder, which also improves article selection before figures.
6. **The interface is bound** (D59): scope options, gender buttons, pupil-group selector, response-base wrappers, print footer, chart bar labels/tooltips and the live-region announcements all read labelCy/optsCy/shortCy from the payload through single accessors; client strings live in a two-language catalogue behind one lookup; every declared handoff key is embedded so the binding layer is generic (CAT-bind pass).
7. **Parity ruled:** PR-12 provisional suppression applied (5,737 → 0); the Welsh-only follower lists carry the English's own presentation flag (PAR-follow and PAR-added-module → 0).

**DERIVED strings awaiting the linguist** (flagged, not invented silently): the ~30 cohort descriptor frames, the D59 control strings (Yn dangos, ymateb disgybl wedi'u cynnwys, etc.), and scope descriptions (Blynyddoedd 3–11). All read from the build, none hard-coded as rulings; the workbook remains the source of truth.

**Still open for V5.0:** the translator's catalogue values (all keys embedded, zero values); the linguist's 105 decisions incl. PR-01 genders and the PR-02/PR-04 confirmations; the PR-12 policy decision proper (the provisional suppression holds the languages equal today); native sign-off of the distinct output strings. Sheet 39 going to zero remains the readiness measure.

---

## Build V4.6 (2026-09-01) — feature-carrying pipeline against Framework v1.9

**Version:** 2026-prototype-V4.6-bilingual · pipeline 0.18.0 · framework v1.9 sha256 47143b81…(stamped in full) · QA PASS · pytest 76 passed, 1 skipped · jsdom language-state regression 24/24 · **English byte-identical at every level** — all 316,968 English surface records (271,966 module · 29,081 h1 · 7,353 h2 · 8,568 scope) compared record-for-record against the shipped V4.5 with zero differences, and the pack's own GOV-lock gate passes against the supplied 02c_english_lock_V45.json baseline · 174.8MB.

**Acceptance (gate pack v4, run exactly as instructed):** `--selftest` first — 41/41 gates rejected their seeded fault. Then both modes with `--framework 01_Framework_v1.9.xlsx --baseline 02c_english_lock_V45.json --evidence`:
- **dev: 47/47 blocking gates pass** (6 report-only, 2 manual). Manifest 76f4e5ba9585262b; config read from the workbook (CONJ-03, sheet 23, sheet 42, sheet 39).
- **release: 47/48** — the single failure is CAT-values, count **exactly 337**, the translator's outstanding catalogue values. Both JSON results and both evidence archives ship with the build. The same v4 runner is vendored verbatim into build QA (D65), so a failing corpus can no longer become a shipped file; the build metadata records mode "dev".

**The seven fixes, delivered in order:**
1. **One conjunction service** (D67/PR-13): conj_and now tests the follower's FIRST WORD against the CONJ-03 list read from sheet 11 at build time (the V4.5 service compared the whole clause against a hard-coded list, so no multiword follower ever matched — the actual mechanism behind all 6,113). CONJ-fnword 6,113 → 0; every CONJ gate zero.
2. **Singleton as a typed entity** (sheet 44/D62/PR-14): sg_qual now applies the twelve sheet-44 frames as whole-clause replacements in three gendered columns — verified exact against every cell of the sheet (30/30) — with possession roles REALISED (ganddo/ganddi), never deleted; eu→ei with h-prothesis (f)/none (m); gallant→gall; pe baent→pe bai'n. PR-14 sends the unknown-sex singleton to the grammatical gender of disgybl (masculine). The V4.5 deletion-style entries (a oedd ganddynt→a oedd, y byddai'n well ganddynt→y byddai'n well) are retired. AGR-possessive/pronoun/verb/partitive/possessor/orphan-mut: all zero.
3. **Both roles realised** (D61/PR-16): the n_dl anaphoric shortcut ('yn y grŵp a ddewiswyd') is reverted — outer cohort and inner subgroup both realised (ROLE-outer 34 → 0); the f6 exclusion parenthetical is realised as "(ac eithrio'r ateb sy'n diffinio'r grŵp hwn)" exactly when the fact record carries the exclusion role — 118 in the shipped file (PAR-generic → 0).
4. **Numeral service on the e7 predicate:** gan + soft-mutated numeral (gan ddau ×44 in the shipped file; gan dri, gan bedwar per sheet 44); at N = 1 the possessor is realised (roedd yn well ganddo/ganddi beidio â dweud). MUT-numeral → 0.
5. **The language layer** (sheet 43/D63/D64/D66): t(key, params) serves all 18 UI-DYN paths from the sheet-43 frame catalogue embedded in the payload (32 frames, both languages, N=1 variants derived at build); {n:count NP} slots are filled from the numeral service's pre-realised forms shipped as data (un disgybl … deg disgybl). labelCy on 45/45 metricDefs and baseNoteCy where baseNote (fed from the translator catalogue; pending values carry the ⟪missing:key⟫ dev marker). esc(c.label)→cohortLabel(c). All 16 Welsh literals and all 22 `|| "…"` fallbacks deleted. The stacked-chart legend is sourced from the workbook through the payload — "Tair gwaith neu fwy yr wythnos" and "Dydw i ddim yn gwybod" now correct (D66). UI-path/-literal/-field/-welsh-in-code/-fallback/-legend-parity, CAT-schema, CAT-binder: all zero.
6. **D60 stamp:** buildMetadata carries welshFrameworkSha256 (47143b8189df1552…), gateManifestHash (76f4e5ba9585262b), gateRunnerVersion, surfaceCounts {module 271,966 · h1 29,081 · h2 7,353 · scope 8,568 · opts 790}, build mode, and the full provisional-ruling set PR-01…PR-16 with their operative values, all read from the workbook (the lexicon build still refuses on unrecognised ruling wording).
7. **Runner + config as data:** the corrected CONJ-03 row (with sydd/sy'n, maent, roeddent, mi, wedyn) is consumed from sheet 11, not code; PR-15's f2 parity exceptions are read by the gate from sheet 42 and surface as ROLE-excepted 68 (report-only), as designed.

**Raised against the workbook, not corrected in code** (per the standing instruction):
1. **Sheet 43 ui.stack_legend says "SOURCE FROM SHEET 23 — never re-typed", but sheet 23 v1.9 has no row for "3 or more times a week" or "I don't know"** (nearest rows: "7 or more times a week" and "Don't know"). The build takes the five strings the sheet-43 row itself spells out, preferring a sheet-23 row wherever one exists — so adding the two rows to sheet 23 will take precedence on the next rebuild with no code change.
2. **Sheet 43 ui.table_headings ("Answer | Pupils | %") does not match the data table the report actually renders** (Answer | Pupil responses, no % column). The shipped tables keep their locked English columns; the frame is embedded and unused pending a ruling on which is correct.
3. **baseNote translations have no handoff key:** metricDefs.baseNoteCy has a destination (CAT-schema passes) but the translator workbook has no row to carry its value, so it holds a marker that no translator delivery can currently fill. Suggest adding `<metric>_base_note` rows.
4. **The FSM-context card and GDPR suppression texts remain English in both languages** (sheet 43 marks the GDPR block TO TRANSLATE per Q17); they are routed through the catalogue so the translator's values drop in without a code change.

**DERIVED, flagged for the linguist:** one new string — the stacked-table caption "Y 10 camp a ddewiswyd amlaf yn y golwg hwn —" (built from framework vocabulary, carried in the same flagged class as the D59 control strings).

**Still open for V5.0:** the translator's 337 catalogue values (the release-mode gate holds the door); the linguist's ruling sheet v3; native sign-off. Sheet 39 to zero remains the readiness measure.

---

## Build V4.7 (2026-09-02) — the report around the sentences, against Framework v2.0

**Version:** 2026-prototype-V4.7-bilingual · pipeline 0.19.0 · framework v2.0 (sha stamped) · QA PASS · pytest 76 passed · jsdom language-state regression 30/30 · **English byte-identical** — all 316,968 English surface records equal to shipped V4.6/V4.5 record-for-record; GOV-lock asserted against the supplied 02c_english_lock_V46.json, and the lock emitted from this build (02c_english_lock_V47.json) is byte-identical to that baseline · 179.4MB. No sentence rule was touched, as the covering note asked.

**Acceptance (gate pack v5, run exactly as instructed):** `--selftest` 49/49. Baseline first reproduced to the digit (V4.6 scores 44/53 dev, 9/18 paths, identical per-gate counts). Then this build, both modes with `--framework --baseline --evidence --bundle`:
- **dev: 53/53 blocking · renderer paths 18/18 complete** (manifest 318f15f5d8a202d9).
- **release: 53/56** — the three failures are exactly the owner/translator lane the plan names: CAT-values (342), CAT-marker (50 labelCy/baseNoteCy markers), GOV-mode (this is a dev build, correctly). Runner (byte-identical to stock, sha 3d562f9d…b360b2), both JSONs, both evidence archives and both bundles ship with the file.

**The fixes, in the plan's order:**
1. **Stack rows carry a code** (D70, sheet 46): every one of the 311,854 rows now carries the stable option code of its sport; the renderer resolves the label through the same optsCy catalogue as every other chart (sportLabel), tooltips through ui.stack_tooltip with a count-NP, headings through ui.stack_th_sport / ui.stack_th_total. The English label stays in position 0 so review evidence reads. Derived rows (f2, e4, g4) carry the stable scope key (yk) and resolve through filterOptions labelCy; the sex row-labels compose from gender labelCy; SETTING_SEGS reads optsCy of participation_settings. STK-label → 0.
2. **The caption states the count it renders** (D71/PR-17): ui.stack_table_caption takes k = rows.length through the numeral service as a DEFINITE count-NP — y ddwy gamp, y tair camp, y chwe champ, yr wyth camp, y deg camp, and "Y gamp a ddewiswyd amlaf" at one — realised by the service (article by numeral initial; only dwy lenites after y, per D26), never typed. The v1.9 fixed-count DERIVED string is withdrawn from the catalogue. English becomes "The 8 most selected sports…". STK-caption 8,712 → 0.
3. **All 18 paths complete — the 33 children**: context suffixes (ui.ctx_*), the full bar-tooltip family (ui.bar_tooltip / _suppressed / bar_nonselectable), ghost and Other-sports notes, th_answer/th_responses, the two GDPR bodies as D73 catalogue records with exceptionId Q17 (Welsh value = approved English until legal translation), cosel tooltip, derived-table headings/cells (ui.of) and both f14 titles, all nine appendix group headings plus caption/column frames, labelOf/optLabel on every remaining direct field read (27 → 0). UI-path, UI-field → 0.
4. **Frames consumed or retired**: msg.suppressed_* wired — a metric held back for disclosure control in an otherwise-visible view now names the reason (title, body and base through the frames) instead of rendering nothing; the deprecated msg.no_data_* and the three-column ui.table_headings are read as DEPRECATED from sheet 43 and never embedded. FRAME-dormant, FRAME-shape → 0.
5. **The five base-note rows** exist in the handoff (342 keys, not 337) so the translator's return lands; baseNoteCy markers now reference real destinations. CAT-destination → 0.
6. **The build carries its own evidence** (D68): buildMetadata.gateResults holds runnerSha256 (= the stock script's own hash), manifestHash, mode, blockingPass/Total (53/53), pathsComplete (18/18), evidenceSha256 of the archive written beside the build, and baselineSha256 of the V4.6 English lock. The stamp is pre-seeded and finalised from the in-build run itself, so it describes this exact corpus. PR-17 is stamped with the other 16 rulings.
7. **Release configuration**: per the plan this remains a dev build (markers legitimate) until the 342 values and the owner's O09/O10 value exist; the release-mode JSON documents the three outstanding gates.

**data-i18n-source (D72/D73):** every node the language layer writes is stamped in dev builds (frames, catalogue, labels, opts, narrative, handoff-pending); the page's static furniture — the translator's 446-key lane — is marked handoff:static-furniture as data.

**Browser gate:** the stock playwright script cannot launch Chromium in this build environment (missing system libraries, no root). Its exact collection and classification logic was executed under jsdom over a 4-state reduced build: **0 English-looking strings without provenance, 0 Welsh without provenance**; 282 English-with-provenance, of which 269 are the static-furniture translator lane and the rest the marked pending/label classes. Results shipped (V4.7_browser_gate_jsdom.json); the stock script remains unmodified for the operations run on real hardware. NOTE for the pack owners: the script drives the hash router with `g=`/`c=` keys, but the report's URL contract (integration spec §5) uses `gender=`/`cohort=` — as written, the sampled states only vary by scope. Raised rather than worked around.

**Cover corrected:** V4.6's cover embedded page screenshots — the build had been staged with word/media from a feedback document rather than the title-page file. The cover assets now come from "ILR - SSS2026_school report cover page.docx" (white Sport Wales logo 400×160; official 2026 lockup 1120×331), are vendored into config/cover_media with a README naming their source, and the shipped file verifiably embeds them.

**Raised against the workbook/pack, not corrected in code:** (1) sheet 43 ui.row_sex_suffix's English cell is a description ("{year} — Boys / Girls"), not a renderable template — the row label is composed from filterOptions labelCy via the helpers (same effect); the frame is not embedded so it cannot sit dormant. (2) The browser gate's hash keys, above. (3) The g4 grid's four column headings (PE lessons etc.) have no catalogue row yet — English in both languages, flagged.

**Still open for V5.0:** the translator's 342 values; the owner's D69 sensitiveFilters value and the PR-15/Q17 decisions; the linguist's ruling sheet v4 (325 decisions); the operations device/assistive runs and the browser gate on real hardware.

---

## Build V4.8 (2026-09-02) — the final string, against Framework v2.1

**Version:** 2026-prototype-V4.8-bilingual · pipeline 0.20.0 · framework v2.1 (identity-stamped) · QA PASS · pytest 76 passed · jsdom language-state regression 36/36 · **corpus unchanged in both languages** — all 316,968 English AND Welsh surface records byte-identical to shipped V4.7 (and English to V4.5/V4.6); GOV-lock asserted against 02c_english_lock_V47.json; the lock emitted from this build is byte-identical to it · 179.4MB. No grammar rule was touched.

**Acceptance (gate pack v6, run as instructed):** `--selftest` 56/56. Baseline first reproduced to the digit (V4.7 scores 51/60 dev, 13/18 paths on v6). Then this build, both modes with `--framework --baseline --evidence --bundle`:
- **dev: 60/60 blocking · 18/18 paths** (manifest cf880c20dad3e18e) — GOV-rerun confirmed the embedded stamp against its own recomputation.
- **release: 60/63** — CAT-values (342), CAT-marker (50) and GOV-mode: the translator's and the owner's lane, as the plan states. Runner (byte-identical to stock, sha 127c9ae6…), both JSONs, both evidence archives and both bundles ship with the file.

**The six fixes:**
1. **One clause joiner** (D74): joinClause() with separators read from the sheet-43 CONTRACT rows, delivered as data (welsh.separators) — a bare delimiter cannot be a clause frame, so the two CONTRACT rows are not embedded as frames. Every `+= t(…)` is gone; the corrected v2.1 frames carry no delimiters. Both join regressions ("disgybl· Yn dangos", "desc— Selected") fixed in both languages by the same change.
2. **Sentence-initial casing** (D75/PR-17): the caption slot is {k:count camp, definite, initial}; the payload's definite table is capitalised AT REALISATION ("Y ddwy gamp", "Yr wyth camp", "Y chwe champ"; lexical sheets untouched), the client's initial role re-asserts it, and at one the NP is article + soft-mutated feminine singular ("Y gamp"), read from PR-17's own at-one wording on sheet 39. STK-caption-case 34,570 → 0.
3. **Four g4 heading keys** consumed (ui.g4_th_pe / _school_clubs / _community / _other) — 33,320 instances off the literal path.
4. **The no-report marker** (D76/PR-18, closes Q16): all six "n/r" literals replaced by the language-neutral "—" read from sheet 43 as catalogue data, with title and aria-label from ui.table_suppressed at every site.
5. **The English singular contract** (D77, sheet 49 EN-01/EN-02): en_sg derived for every "{slot} pupils" frame with the controlling slot recorded (sg_slot), and t() tests exactly that slot (p.base === 1 for the bar tooltip, p.b === 1 for the appendix caption) — so "Based on: 1 pupil" without ever selecting a singular for the wrong slot. EN-03/EN-04 are the joiner fix. EN-05 ("21th" → "21st") is in the LOCKED narrative and remains with the report owner, untouched.
6. **One identity** (D78): buildMetadata.identity {frameworkVersion v2.1, frameworkFile, frameworkSha256, runnerVersion 6.0.0, runnerSha256, manifestHash, mode} written once; every legacy field is derived from it; only canonical PR-01…PR-18 are stamped (the "PR-02 (status)" row is gone from sheet 39 and from the stamp). gateResults is pre-seeded with this run's identity, measured by the in-build vendored v6 run, and finalised with the evidence hash — the stock rerun's GOV-rerun gate confirms it.

**Raised against the pack, not worked around:** GOV-rerun's verifier recomputes the pass count over the blocking set MINUS itself and fails any claim above that number — so the maximal verifiable stamp for a clean build is blockingPass 59 of 60, which the verifier then confirms as the 60/60 headline. The stamp carries a note field saying exactly this. An off-by-one in the comparison; flagged for the pack owners.

**Browser gate v2:** Chromium still cannot launch in this environment (missing system libraries, no root); the gate's collection, classification AND v2 typography checks (delimiter-touching characters, "n/r", "1 pupils") were executed under jsdom over a 4-state reduced build: **0 English-without-provenance, 0 typography failures, 0 Welsh-without-provenance**. Results shipped; the stock script is unmodified and ready for the operations run with --states 60 on real hardware.

**Still open for V5.0:** the translator's 342 values; the owner's D69 value, the Q17/PR-15 decisions and EN-05; the linguist's ruling sheet v5 (333 decisions incl. PR-18); the operations device/assistive runs and the Chromium browser-gate run.

---

## Build V4.9 (2026-09-10) — the release-candidate layer, against Framework v2.2

**Version:** 2026-prototype-V4.9-bilingual · pipeline 0.21.0 · framework v2.2 (identity-stamped, sha a540189f…) · QA PASS · pytest 76 passed, 1 skipped · jsdom language-state regression 53/53 · **corpus unchanged in both languages** — all 316,968 English AND Welsh surface records and all 41,650 stack-row sets byte-identical to shipped V4.8 (English identical since locked V4.1); GOV-lock, GOV-lock-cy and FT11-keyset asserted against the pack's 02c_lock_V48_v7.json in-build and on the shipped file; the lock emitted from this build (02c_lock_V49_v7.json) is equal to it in all three parts (English, Welsh, 1,013 FT-11 keys) · 179,445,060 bytes, sha256 9eb4006a…a914 (rebuilt 15 Sep 2026, see the addendum). No grammar rule was touched; the source export is the same file (sha e457bc8e…).

**Acceptance (gate pack v7, run as instructed):** `--selftest` 68/68. Baseline first reproduced to the digit on the V4.8 artefacts (61/69 dev, 61/72 release, 18/18 paths, identical per-gate counts, with Framework v2.1 as the pack's own run used it; the emitted lock equals the pack's). Then this build:
- **in-build (vendored v7, phase 1):** stamp 69/72 with `pending: [GOV-rerun, GOV-bundle]` and `disputed: {STK-caption-case}` — no prose condition (D81).
- **stock rerun on the shipped file with the bundle asserted (phase 2): dev 71/72 · release 71/75 · paths 17/18.** GOV-rerun, GOV-bundle, GOV-headline, GOV-lock-cy, FT11-keyset, CNP-lexical/-table/-role, CAT-static-manifest/-bound/-english/-swap and CAT-attr-literal all pass. The one dev failure is STK-caption-case (34,570), a v7 defect raised below; the release failures are that gate plus CAT-values (356), CAT-marker (50) and GOV-mode (dev build) — the translator's and the owner's lane. verify.json (bundle) states 71/75 · 17/18 (both figures unchanged by the 15 Sep rebuild). Runner byte-identical to stock (sha f036f5af…), both JSONs, both evidence archives, both bundles and the bundle directory ship with the file.

**The five fixes, in the plan's order:**
1. **The static lane is bound** (D79, sheet 52 line 1): every translator-owned text node in the static markup is stamped `data-i18n="ui###"` at build time by its English (a run that is an element's only child is stamped on the element; a run between inline markup is wrapped in a span), the payload carries `welsh.static = {key: {en, cy, consumer}}` (231 rows, 262 text nodes), `applyLanguageState()` calls `renderStatic()`, which walks `[data-i18n]` and writes textContent from the manifest for the active language — read at call time — stamping `static:ui###`; English is restored from the manifest. A page node with no row, a row with no node, or a node whose English differs from the manifest fails the build (pipeline/static_lane.py, welsh_payload.py, build_html.py). The existing numbering is kept: of the 217 rows, 194 keep their key (exact match, or the V4.2 listing's 60-character truncation as a unique prefix; the four identical "This bar chart shows…" truncations resolved in document order), 23 are new (ui231–ui253: the V4.1 sanctioned English edits, the FSM-quartile FAQ) and 23 are retired (17 strings the V4.1 edits removed or reworded, the three chapter-band Welsh subtitles, the school name, and two control texts already served by sheet-43 frames — ui.rail_toggle, ui.chip_none). The translation handoff workbook was not available to this session; it was regenerated losslessly from the V4.8 lexicon rows and the page (pipeline/make_translation_handoff.py → SSS2026_Welsh_Translation_Handoff_V4.9.xlsx, Strings + Retired sheets, full English), and the lexicon rebuilt from it. Fixture toggle under jsdom: 231 keys × 8 states, en → cy → en, 0 failures.
2. **The sixteen attributes are keyed** (D80, sheet 28): `data-ct/nh/also-h/sh` → `-key` attributes holding ui217–ui230 (14 distinct strings, one key per string). Because v7's CAT-static-bound and browser gate v3 both require every manifest key to have a `[data-i18n]` element, the fourteen strings are static furniture in the markup — the chart-heading override sits above a `.chart-slot`, the "What is this … showing?" heading and the also-heading above `.rep-body` slots, the stacked-chart note inside a static card between `.stack-slot` and `.stack-table-slot` — bound by the same lane; the renderers resolve the same keys through `staticStr()` and render beneath. No renderer reads a text-bearing attribute outside the layer; no legacy attribute survives (build_html refuses one). Keyed consumers: 16.
3. **The count tables are lexical and equal to sheet 50** (D75): the lexicon builder reads sheet 50; `welsh.countNP` is emitted verbatim, lower-case (`yr un gamp`, `y ddwy gamp`, … `y deg camp`), cross-checked against the numeral service at assembly (a disagreement fails the build); `countNP()` unchanged — casing only under the `initial` role. Captions k = 1–10 render "Y …/Yr …" (jsdom: every stack caption capitalised; browser-gate typography 0 lower-case-initial).
4. **One plain headline** (D81): `gateResults` carries `blockingPass/blockingTotal`, `headline "n/N"`, `pending` naming GOV-rerun and GOV-bundle, and — new — `disputed` naming STK-caption-case with its reason; the `note` is gone. The pre-seeded stamp is a well-formed "0/0". The stock rerun confirms the claim (GOV-rerun PASS) and writes the final status into the bundle.
5. **The bundle ships beside the report** (D81/D82): `SSS2026_V4.9_bundle/` with manifest.json (runner, framework, baseline lock_V48_v7.json, phase-1 evidence, browser harness, report — every sha256 equal to the stamp), RUN.md, results_dev/release.json, the rerun evidence, the emitted lock, verify.json and write_verify.py. GOV-bundle passes on the shipped file. PR-19 (retain) read from sheet 39 through a new PR_KEYS pattern and stamped with the other 18; D69 now read only as a SIGNED value (v7).

**Raised against the pack, not worked around:**
1. **v7 STK-caption-case contradicts v7 CNP-lexical.** The caption emulation substitutes the countNP entry raw and never applies the `initial` role the slot carries, so with the lexical table sheet 50 requires it fails on every k ≥ 2 caption (34,570) and marks UI-DYN-16 partial (17/18). The pack's "61 → 69 of 69" cannot be reached on v7 as shipped; the in-build wrapper honours the dispute only after verifying CNP-lexical/-table/-role pass and every hit is a k ≥ 2 caption whose entry capitalises under the role, and records it in the stamp. One-line fix for the pack: apply the role in the emulation.
2. **Attribute keys vs CAT-static-bound / browser gate v3.** Spec §14.2 renders the keyed heading at run time with no `data-i18n`, yet CAT-static-bound (static head) and the v3 toggle (`before[k]`) require a `[data-i18n]` element for every manifest key. Resolved by making the sixteen strings static furniture beside render slots (fix 2); the pack should say which it means.
3. **Denominators.** The pack's 69/72 were measured without the bundle, the Welsh lock and the FT-11 set asserted; with all three asserted the dev set is 72 and the release set 75.
4. **The runner never writes verify.json** (spec §14.4, RUN.md, sheet 52 say the rerun writes it); write_verify.py states the rerun's result. And sheet 52's command writes the rerun evidence over the manifest-listed `evidence.ndjson.gz`, which would fail GOV-bundle on the next rerun — the bundle's RUN.md writes it to `evidence_rerun_*.ndjson.gz`.
5. **Runner sha in the baseline bundle** (57064083…) differs from the shipped runner (f036f5af…); same manifest hash. The shipped runner no longer reads v2.1's D69 instruction text as a signature — the baseline's config line did.
6. **Runs split by inline markup** ("A", "and", "Use the", ". This will clear all filters.") are context-free translator rows inherited from the V4.2 numbering; the spec's `html: true` paragraph rows would need the browser gate to strip tags before comparing.
7. **Client-written static strings** (overview note, any-activity statement, meta-table labels, "← Back / Contents / Next →") remain English in both languages and are the 57 rows sharing the key `client.js`; they are outside D79 as written and flagged for the next round.
8. Also for the owner: the chapter bands' fixed Welsh subtitles will sit beside a translated heading in Welsh mode; the review banner (ui001) is a translator row that a release build removes at run time; static `aria-label`s ("Explore results", "Report cover") are not text nodes and stay English.

**Browser gate v3:** Chromium still cannot launch in this environment; its collection, classification, v2/v3 typography (incl. lower-case-initial) and the `--fixture auto` toggle were executed under jsdom over an 8-state reduced build (whole school, phase, both sexes, a year, a suppressed view, a cohort view): **0 English-without-provenance, 0 Welsh-without-provenance, 0 typography faults, toggle 0 failures** (V4.9_browser_gate_jsdom.json; the stock script is unmodified for the operations run with --states 60).

**Still open for V5.0:** the translator's 356 values (342 + 14 attribute strings; 217 page-furniture rows now bound); the owner's D69 value, Q17/PR-15 and EN-05; the linguist's ruling sheet v6 (PR-19 / FT-11, the four fixtures, the 150-sentence proofreading sample, tab 9); the pack owners' rulings on the eight items above; the operations device/assistive runs and the Chromium browser-gate run.

**Addendum (15 Sep 2026) — rebuild without the presentation regression.** The 10 Sep build followed spec §14.1 literally and rendered an untranslated static row as a bare `⟪missing:ui###⟫` in Welsh mode; with 262 bound nodes that turned the introduction, FAQs, rail labels and buttons into markers — a visible regression from V4.8, which left the same furniture in readable English. Rebuilt the same day the owner raised it: `staticStr()` now returns the manifest English for a pending row and `renderStatic()` marks the node with the review class the translator lane has carried since V4.2 (dotted red, title "Heb ei gyfieithu eto — dangosir y Saesneg") and provenance `handoff:pending:ui###`; a key with no manifest row still shows the marker, and release mode still fails on the empty value (CAT-values). Recorded as a deviation from §14.1 for the pack owners. Client change only: the payload is identical, every gate result is unchanged (in-build 69/72 pending 2 disputed 1; stock dev 71/72, release 71/75, paths 17/18; lock equal in all three parts; jsdom 53/53; browser-gate logic 0/0/0, toggle 1848/1848, 0 failures), and a whole-page text comparison against V4.8 in both languages differs only in the version, pipeline and build-date lines. File 179,445,060 bytes, sha256 9eb4006a38a8a77dc74b8b90bcecb5463d0ff98ca6a2f2b1372f69cb6d9fa914; bundle manifest and verify.json re-issued for it. The file was assembled whole in Downloads and copied to Data_Report_Outputs once the Windows Plan9 fix (KB5129195) restored the sandbox mounts.

## Build V4.10 (2026-09-15) — the translator's static text, against Framework v2.2

**Version:** 2026-prototype-V4.10-bilingual · pipeline 0.22.0 · framework v2.2 unchanged (sha a540189f…) · QA PASS · pytest 82 passed, 1 skipped (six new V4.10 tests) · jsdom language-state regression 59/59 · **corpus unchanged in both languages** — all 308,400 English AND Welsh narrative records (h1, h2, module, scope, m, rows) and every stack-row set byte-identical to shipped V4.9 (English identical since locked V4.1); GOV-lock, GOV-lock-cy and FT11-keyset asserted against 02c_lock_V48_v7.json in-build and on the shipped file; the lock emitted from this build (lock_V410_v7.json) is byte-equal to it · 179,501,919 bytes, sha256 5b4e1030f7dd8d1d46722027e8df9dbea532217cbd00603fed3af065264a7c29. No grammar rule, ruling, lexicon row or workbook cell was touched; the source export is the same file (sha e457bc8e…). Built fresh from the export in an empty working directory (no state chunk reused).

**Input:** the translator's Word document `18117 Chwaraeon Cymru 2026 School Sport Survey - School Reports.docx` (sha256 15d726d0…8eeb; 350 English/Welsh rows in eight tables). Ingested by a new tool, `pipeline/ingest_translation_doc.py`, which matches each row to a handoff row **by its English** and carries the Welsh verbatim — it writes no Welsh word. Every row of the document is accounted for in `V4.10_translation_register.xlsx` / `.md` by tier: 216 values written to the handoff (171 of the 204 static page rows, 39 of 45 chart questions, 3 chart footnotes, 3 module headings); 169 rows where the document's Welsh differs from the Framework workbook's for a client-rendered string (118 answer labels, 45 filter-panel cohort labels, 4 stacked-chart legend entries, 2 filter labels) — **not applied**, the workbook is the source of truth and these are a change request to the framework owner (see item 1 below); 88 rows where the document and the workbook already agree; 92 instances of sheet-43 frames (banner, base line, captions); 24 generated narrative sentences (the document translates one instance; the report generates them from fact records — listed beside the generated Welsh for the linguist); 32 data rows (the 21 local authorities, the five RSPs, profile field labels); 76 translator rows the document does not cover (still pending, listed); 2 translator inconsistencies (the same question given as "tymor hir" and "hirdymor"; "fel arfer" with and without the comma — first occurrence kept, both listed); 2 frame instances with a figure ("Based on: 363 pupils – multiple answers permitted").

**Acceptance (gate pack v7, vendored runner byte-identical, sha f036f5af…):** `--selftest` 68/68. In-build stamp 69/72, pending [GOV-rerun, GOV-bundle], disputed {STK-caption-case}, paths 17/18. **Stock rerun on the shipped file with the bundle asserted: dev 71/72 · release 71/75 · paths 17/18** — unchanged headlines; the release-only failures moved from CAT-values 356 → **118** and CAT-marker 50 → **11** (the 118 empty catalogue keys are the 76 translator rows the document does not carry — module headings d3…s1, the combined-group chart questions, four chart footnotes, the eight interface messages, the review banner, the intro/FAQ sentences with a count or school-name slot, the four "This bar chart shows…" sentences with the sport-count slot, five attribute strings ui225–ui228/ui230, ui247, ui032, ui183/185–189/195/200 — plus the generator-owned and framework-owner rows); STK-caption-case disputed as before; GOV-mode dev. verify.json states 71/75 · 17/18. Browser gate v3 logic under jsdom over the 8-state build: 0 English-without-provenance, 0 Welsh-without-provenance, 0 typography faults, fixture toggle 204 keys × 8 states en→cy→en 1,632/1,632, 0 failures. (The v3 word-list classifier now marks 28 translated static paragraphs and 129 frame instances as "mixed" because Welsh "a", "yn", "AG", "Actif" and "data" are on its English list — all carry provenance, so none is a finding; noted for the pack owners.)

**What changed, and the one structural change:**
1. **Static values land through the designed channel.** The regenerated handoff (`SSS2026_Welsh_Translation_Handoff_V4.10.xlsx`, kept in config/) carries the translator's Welsh in its Welsh column; the lexicon was rebuilt from it; nothing else in the lexicon changed (verified section by section).
2. **Block rows (resolves V4.9 register item 6).** A paragraph whose only inline elements are emphasis (strong/em/b/i/br), with every emphasis boundary on whitespace and no slot, placeholder or link inside, is now **one** translator row: its English is the tag-stripped text (exactly what CAT-static-english compares), the emphasis travels as manifest `html`, and the Welsh value carries the translator's own bold/italic runs as `<strong>/<em>`. Thirteen paragraphs (the FAQ colour/grey/numbers/FSM paragraphs, the two "We captured…" contexts, the latent/unmet-demand definitions, the "Print or save" sentence, the Explore-results bullet) replace 38 context-free fragment rows, retired to the Retired sheet; keys ui254–ui264 are new, ui057 and ui110 kept theirs. The client renders such a row through an allow-list (strong, em, b, i, br; one guarded colour style; everything else escaped), and restores English from the manifest markup. Four paragraphs whose emphasis touches punctuation ("says <em>…</em>.", "clicking <strong>…</strong>.", the two club sentences) stay fragment chains — the tool splits the translator's paragraph on **their** emphasis runs, which mirror the English structure, and only when the run pattern is identical (four chains, all applied).
3. **Contents rows** "A: B" / "A? B" split on the translator's bold prefix (7); numbered rail links keep the page numeral with the translator's text (8).
4. **Handoff shape corrections, written back into the workbook and listed on the register's "Handoff English drift" sheet:** the seven chart-footnote rows that shared their metric's key now carry the `<mid>_base_note` key the build reads (in V4.9 the footnote row silently overwrote the chart question in the dict), and the English of `freq_estimate`, `club_freq_estimate` and five footnotes — truncated at 60 characters or stale against metrics.yml since the V4.2 listing — is refreshed from the report's metric definitions so a translator sees the sentence the page shows.
5. **Language slider (UX request):** the V4.9 button is now a two-position switch in the same rail position — English left, Cymraeg right — implemented as `<button role="switch" aria-checked>` so keyboard, focus and the existing click handler are unchanged; both labels come from the catalogue (`language_label`, `language_label_en`) and the active one is highlighted.

**Raised — where the document and the rulebook meet:**
1. **Client-rendered strings are workbook rows, not handoff rows.** The document supplies Welsh for answer labels ("Very" → "Hyderus iawn" under confidence but "Iach iawn" under health; "Prefer not to say" → "Mae’n well gennyf…" against the workbook's "…gen i…"), the stacked-chart legend ("Unwaith yr wythnos" against "1 waith yr wythnos"; "Tair gwaith…" against "3 gwaith…"), the cohort labels of the filter panel and the "You are viewing" banner ("Rydych chi’n gweld" against the sheet-43 frame "Yn dangos:"). All 169 differences are listed with the workbook's current value. Adopting them means a Framework v2.3 from the framework owner (sheets 18–23, 28, 43); the context-specific "Very/Quite/Not very" labels would also need the answer-label table keyed by question, which it is not today. Ready to prepare the candidate workbook on instruction; not done unasked.
2. **Slot-bearing sentences need sheet-43 frames (D63).** "This report presents the responses given by pupils at {school}: {n} pupil responses are included, across {years}", "Pupils in Years 3 to 11 at {school} who completed…: {n} pupil responses…", "…therefore reflect the {n} responses…", the four "There were a total of {n} sports to choose from" sentences and the example banner cannot take the translator's sentence as fragments (Welsh puts "Mae" before the number). The translator's sentences are quoted on the register's slot-bearing sheet as the proposed frames; until the framework owner adds them these rows show English under the review marker, as in V4.9.
3. **Generated narrative:** 24 document rows translate one instance of a generated sentence (e.g. "Sport in PE or lesson time was the most frequently selected setting, chosen by 335 of the 363…"). Not applied — Welsh is generated from fact records (rule 2); the linguist can compare the translator's rendering with the generated one on the register's sheet and rule through the workbook's frames.
4. **Data, not text:** the 21 local-authority and five RSP Welsh names and the profile field labels are the profile's data; the profile section is still client-rendered English in Welsh mode (V4.9 item 7). Recorded as the data set to load when the profile lane is designed.
5. **Not in the document:** 76 translator rows (listed) — chiefly the module headings d3…s1, the combined-group chart questions, the interface messages (no data / not asked / suppressed), the review banner, the summary/next-steps furniture (ui186–ui189), five attribute strings and ui247 "Somewhere Else (such as the Park, Beach or Garden)". Also the two GDPR box frames (`ui.gdpr_body_full/_module`), whose sheet-43 Welsh column repeats the English.
6. **Document English that differs from the page's:** "Interactive Report" (page: "Interactive Learning Report:"), "Less than once per week" (legend: "…once a week"), "Which sports are our pupils doing, and how often?" (page uses an em dash) — matched where only punctuation or case differs, listed where wording differs. The English narrative is locked; none of it changed.

**Still open for V5.0:** the framework owner's decision on items 1–2 (Framework v2.3 with the translator's client-rendered strings and the slot frames); the remaining 76 translator rows; the owner's D69 value, Q17/PR-15 and EN-05; the linguist's ruling sheet v6; the pack owners' rulings on the V4.9 register; the operations device/assistive runs and the Chromium browser-gate run.


## Build V4.11 (2026-09-15) — the assessment round, against Framework v2.3

**Version:** 2026-prototype-V4.11-bilingual · pipeline 0.23.0 · **Framework v2.3** (sha 9356dee9…; produced from v2.2 by `pipeline/make_framework_v23.py`, sheet 55 is the change log) · QA PASS · pytest 82 passed, 1 skipped · jsdom language-state regression 75/75 · **corpus unchanged in both languages** — all 8,568 state records byte-identical to V4.10 (and so to V4.9/V4.8; English locked since V4.1); GOV-lock, GOV-lock-cy and FT11-keyset asserted against 02c_lock_V48_v7.json; the emitted lock (lock_V411_v7.json) byte-equal to it · 179,512,658 bytes, sha256 5e33b6fdeca94b8d46a058abd736aa033354f355a1149aa3bba4d670ffdf466f. Built fresh from the same export (sha e457bc8e…) in an empty working directory.

**Input:** the independent assessment `SSS2026_Welsh_Interactive_Text_V4.10_Assessment.docx` and its evidence log (765 records) of 15 Sep 2026, plus the owner's report that the slider showed no language names on first load. The assessment's own regression (317,758 surfaces, 8,568 states, 0 differences from V4.9) agrees with this record; its findings were taken in its priority order.

**Acceptance (gate pack v7, vendored runner byte-identical, sha f036f5af…):** `--selftest` 68/68. In-build stamp 69/72, pending [GOV-rerun, GOV-bundle], disputed {STK-caption-case}, paths 17/18. **Stock rerun on the shipped file with the bundle asserted: dev 71/72 · release 71/75 · paths 17/18** — unchanged headlines; the release-only gaps fell again: CAT-values 118 → **103**, CAT-marker 11 → **8** (six combined-group chart questions and two footnotes the translator has not covered). The in-build gates caught two of this round's own faults before the package was written — FRAME-dormant (frames consumed through markup attributes were invisible to the client's consumer set; now declared in `MARKUP_FRAMES`) and FRAME-delimiter (the FSM body frame ended with a colon; the value became a slot). Browser-gate v3 logic under jsdom over the 8-state build: 0 English-without-provenance, 0 Welsh-without-provenance, 0 typography faults, toggle 192 keys × 8 states 1,536/1,536, 0 failures.

**What changed, in the assessment's order:**
1. **P0 live destinations (§6).** The five chart footnotes the translator had returned in V4.10 were being discarded by a dict literal that set the `<mid>_base_note` keys to None after the handoff spread (V4.9 shape); fixed in both builders — three now land (take_part_method, welsh_when_playing_sport, unmet_demand), two remain empty. The three catalogue consumers with no row (appendix_total_responses, fsm_context_title, fsm_context_body) are sheet-43 frames in v2.3; the first carries the translator's Welsh. Twelve slot-bearing static fragments (ui017/018, ui036–038, ui040/041, ui116/117/119/127/129) are retired and replaced by sheet-43 frames with slots where the document's figures stood: ui.intro_sentence, ui.faq_included, ui.faq_missing (translator's sentences), ui.chart_sports_total_pe (translator's), and the three sibling chart notes (English only, pending). Static rows 204 → 192, 171 translated.
2. **P0 clear corrections (§7.1).** Eighteen keys / nineteen minimal substitutions applied by `pipeline/apply_review_corrections.py`, each carrying the note "reviewer correction (assessment §7.1, 15 Sep 2026) — pending translator confirmation" in the handoff's new Note column: ui029, ui034 ("Yn ei dro"), ui057 ("mae barrau llwyd tywyll yn dynodi…"), ui064, ui087, ui095, ui104 ("archwiliwch"), ui143 ("i ddisgyblion"), ui154 ("AG a Gwersi Actif"), ui157, ui190, ui197 ("Rhestrau/restrau"), ui254 ("Defnyddiwch banel"), ui255 ("Mae hyn"), ui257, community_club_freq, other_setting_freq, sports_other_setting. Five §7.1 items that ask for a decision or an unspecified recast (ui023 voice, ui086 passive, ui143's parallel clause, ui250 plural, ui255's agreement) are NOT applied — queued.
3. **P0 linguist decisions (§7.2, FT11).** Not applied (they are rulings); all 31 are on sheet B of `V4.11_translator_linguist_queue.xlsx` with the current Welsh beside each. Two of them the translator's own document already settles and v2.3 adopts: `ui.stack_caption_sex` now "rhywedd" (the document's term for Gender throughout) and the banner prefix "Rydych chi’n gweld:" (edits on sheet 43, logged).
4. **P0 client English (§8).** Every route the assessment listed now goes through a sheet-43 frame: injectNav (Back/Contents/Next/aria — translator's "Yn ôl / Cynnwys / Nesaf"), renderProfile headings (six, all translator's), the technical record (nine, English pending), the ethnicity heading/columns/note (translator's), the FSM card, the profile base line with its suffix, the any-activity headline and note, the overview note, the document title, the three ARIA names and three alt texts, and the selected tick (a real element from `ui.selected_tick`, no longer CSS content). Profile data values pass through v2.3 sheet 53 (21 LAs, 5 RSPs, the fieldwork dates in the translator's Welsh). `pctTable` and `renderVariation` (dead, English) removed. The profile and navigation re-render on every language change.
5. **P0 language persistence (§8.2).** Every in-page anchor now scrolls to its section and records it in the state hash (`…&lang=cy&s=m-contents`); a bare `#section` hash is folded into the state; a saved link restores language, filters and section. jsdom sequence: Welsh + girls → Contents → hash keeps `lang=cy`, `gender=girl`, `s=m-contents`.
6. **P1 slider (§9.2 and the owner's report).** Both label states ≥ 4.5:1 (inactive #4A4A4A ≈ 8.9:1, active var(--blue) ≈ 9.6:1, underlined). The language names are now in the markup from first paint: the 179 MB payload is parsed before the script runs, so a script-written label appears late — the owner's observation.
7. **§9.4 language of parts.** Every pending fallback node (static or frame) carries `lang="en"`, the review class and provenance `…:pending:key`; removed when the Welsh lands. `t()` now shows the English for a declared frame with no Welsh yet (the static-lane policy recorded in V4.9, made uniform) and the marker only for an undeclared key.
8. **§9.5 review note.** Generated from live counts through `ui.review_note` ("171 of 192 page-text rows are in Welsh…"); its own Welsh is pending, so it shows English under the marker in Welsh mode — accurate, and only in review builds.

**Framework v2.3 (the workbook edit):** 46 new sheet-43 frames (22 with the translator's Welsh, 1 derived, 23 English-only pending), 2 edits, sheet 53 Proper names (27 rows), sheet 54 Translator label overlay — **INACTIVE** (77 rows: the translator's answer labels, cohort labels, legend and filter labels where they differ from the live sheets; applying any of them changes the generated corpus and the lock, and "Very/Quite/Not very" need a per-question structure — each awaits the linguist), sheet 55 change log. No rule, ruling, lexicon or count table changed; the corpus proves it.

**Raised:** the FSM card — the translator's document translates a different English ("Free School Meal Quartile: / Your School is in … Quartile 1 / See …") from the report's locked card; the owner decides the English (sheet 49) and the Welsh then lands. The overview note's "from Year 3 to Year 11" is fixed English that must become slots before other schools are built (sheet 49). "gan disgyblion" in the translator's intro sentence — for the linguist. Q17 GDPR frames unchanged (exception). The assessment's "Interactive Report" row is not the page's title string.

**Still open for V5.0:** the translator's confirmation of the 18 corrections and the 5 recasts; the 54 still-empty rows (21 static, 23 frames, 6 chart questions, 2 footnotes, 2 generic prompts); the linguist's 31 decisions, the sheet-54 overlay and FT11; the owner's D69, Q17/PR-15, EN-05 and the two sheet-49 items above; the pack owners' rulings; the operations Chromium, device and assistive runs.


## Build V4.12 (2026-09-16) — opens in Welsh

**Version:** 2026-prototype-V4.12-bilingual · pipeline 0.24.0 · Framework v2.3 unchanged · 179,512,852 bytes, sha256 aa2592cd3f60b056e508768d11ce4befd85737d9e06682d99caf7db053ccc233. **One change, at the owner's request:** the report opens in Welsh; the switch (or a saved link carrying `lang=en`) selects English. Implemented as the client's default language state (`lang: "cy"`), the document's initial `lang="cy"`, and the switch's first-paint state (aria-checked="true", Cymraeg highlighted). Nothing else was touched: a line-level comparison of the shipped V4.11 and V4.12 files shows exactly those lines plus the version identity and one line the V4.11 file had missed — the `scrollIntoView` guard for non-browser runtimes added to the source while the V4.11 jsdom test was being finished, after that file had been built (a no-op in every browser, which always has the method), and all 8,568 state records are byte-identical to V4.11. Fresh build from the export in an empty directory; QA PASS; in-build 69/72 (pending 2, disputed 1), stock reruns dev 71/72 · release 71/75 · paths 17/18; emitted lock byte-equal to the V4.8 lock; pytest 82/1; jsdom 78/78 (three new assertions: a no-hash load opens in Welsh with the switch on, the Welsh banner renders first, a `lang=en` link still opens English); browser-gate port 0/0/0, toggle 0 failures. The get-ready checklist (queue sheet F) is unaffected.

## Build V4.13 (2026-09-17) — the accessibility switch, against Framework v2.4

**Version:** 2026-prototype-V4.13-bilingual · pipeline 0.25.0 · Framework v2.4 (sha256 b075f8e2…, three new sheet-43 frames, sheet 56 change log) · 179,527,771 bytes, sha256 08901ed6b53273dd9720195f2ef29a9a22859054341c72558ca7e15fafe8e835. **Source:** "School Reports Accessibility Feedback.docx" (sha256 71dffd0e…), ten items. **Owner's brief:** an accessibility switch on the filter panel that, in both languages, applies the document's presentation changes with the content unchanged; the default bilingual report exactly as it was; the report screen-reader friendly without changing it.

**The switch.** `#btn-a11y` sits directly under the language slider, the same `<button role="switch">` pattern, off by default, label from the new frame `ui.a11y_switch` (English present from first paint and overwritten from the catalogue; in Welsh mode it shows the pending English under the review marker with `lang="en"`, as every V4.11 pending frame does). Its state is `html.a11y` and the hash flag `a11y=1` beside `lang`, so a saved or shared link keeps it; the default hash is unchanged. On, in either language: Aptos/Arial in place of Montserrat (item 1); body 18 px and nothing below 14 px (item 2); near-black text, the yellow fields (prompts, chips, the third card) become pale yellow with a dark border and the light-blue panels white with a dark border, the red used for small text darkened to 6.1:1 (item 3); a colour-blind-safe chart palette — vermillion/blue/grey bars, the selected value light yellow with a black outline and its existing tick, stacked segments recoloured by position through a `data-seg` attribute (items 3, 6); every chart's data table opened and focusable (items 6, 8); the cover's red field and the character images muted (item 9a); a visible caption under each character image, taken from its own alt frame (item 9b); a glossary panel at the top of the guide (frames `ui.a11y_glossary_heading`, `ui.a11y_glossary_intro`) whose entries are links to the guide's existing FAQ answers — base, numbers, percentages, colours, grey bars, greyed-out sections, hidden numbers, Free School Meal quartiles, the banner — so it adds no new definition (item 9c, glossary). Off restores everything, including the tables it opened. Content never changes; no Welsh word was composed.

**Global, invisible (both modes, both languages):** every chart card is a `role="group"` named by its own heading (`aria-labelledby`), so assistive technology announces the chart title on entering it (item 5); the no-report marker "—" on chart values now carries the `ui.table_suppressed` frame as visually hidden text (PR-18/D76, previously tables only); stacked segments and legend swatches carry `data-seg`; the guide's FAQ entries carry ids. Item 4 (alt text): every `<img>` already had alt text (cover logo and lockup, three character images through frames); the one decorative SVG sits inside `aria-hidden`. Item 7 (screen reader reading only the first line of a paragraph): no HTML cause found — the paragraphs are single `<p>` elements without breaks; likely a property of the PDF the reviewer read, not the page. Item 10 (PDF cut off a third of the way down): not reproducible in headless Chromium — the print of the 8-state page runs to 61 pages (English) / 65 (Welsh), 108 / 96 with the switch on; defensive print rules added (no clipped or scrolling ancestors, no sticky positioning, no scroll margins while printing) as the only change to the default file's print styles; the reviewer's browser and print route are needed to go further. Not done, by rule: the plain-English rewrite of technical terminology (item 9c) is owner-owned English (locked narrative, sheet 49) — raised, not attempted.

**Proof that the default is unchanged.** The 8-state page rendered in Chromium at 1280 px, full page, English and Welsh, V4.12 file against V4.13: zero differing pixels outside the filter rail (where the new switch is) and the technical-record row that names the version — the whole report column is pixel-identical in both languages (`tests/browser/render_probe.py`, results in the bundle). Line-level: template +146/−15 and client +80/−14, all V4.13; all 8,568 state records byte-identical to V4.12/V4.8; payload differs only in the three new frames and the build identity. The static lane extracts the same 216 nodes / 192 rows (the switch label, glossary heading and note are frame hosts, client-owned).

**Gates.** Fresh staged build from the export in an empty directory: QA PASS; in-build 69/72 (pending 2, disputed 1); stock reruns dev 71/72 · release 71/75 · paths 17/18 — identical to V4.12; emitted lock byte-equal to the V4.8 lock; CAT-values 103 / CAT-marker 8 unchanged (the three new frames are pending, like the 23 V4.11 frames). One in-build gate fired during the first QA: UI-literal on the string `<div class="chart-card" role="group" aria-labelledby="` (its heuristic reads "chart" and "group" as English words); the group attributes are now set through the DOM after insertion, as the slot branch already does, and the second QA passed. pytest 82/1; jsdom 97/97 (19 new assertions: switch present and off, no `a11y` flag in the default hash, label from the frame, on → class/hash/tables/captions/glossary, glossary link opens its FAQ and records the section, state survives a language change, pending label marked in Welsh, off restores, chart groups, `a11y=1` link opens on); provenance port 0 / 0 / 0, toggle 0 failures.

**Open, for the owner and translator:** Welsh for `ui.a11y_switch`, `ui.a11y_glossary_heading`, `ui.a11y_glossary_intro` (handoff); the plain-English pass on technical wording (sheet 49); the reviewer's PDF route for item 10; whether the switch should also be remembered per reader (it is currently carried by the link).

## Build V4.14 (2026-09-17) — the translator's text verbatim, against Framework v2.5

**Version:** 2026-prototype-V4.14-bilingual · pipeline 0.26.0 · Framework v2.5 (nine sheet-43 frame edits, sheet 57 change log) · sha256 a68ab9ddd07d200ca96eb4dc72b42537266676d873c4d6d2a692e0d0976e1cd3. **Owner's instruction (17 Sep 2026):** the translator's document of 15 Sep 2026 takes precedence and goes into the page text and labels word for word. **Audit first:** every row of that document was traced against V4.13 (`SSS2026_V4.14_Translator_fidelity_audit.xlsx`). Of the 216 page-text rows the V4.10 ingest wrote, 199 were still verbatim; the 17 that differed were all the V4.11 reviewer substitutions (rulebook item 11 at the time — scripted minimal substitutions with provenance, pending translator confirmation). No framework rule had altered a static row. Eighteen existing sheet-43 frames the document also covered had kept the workbook's earlier wording because the V4.10 ingest treated existing frames as framework-owned — an oversight, now corrected where no slot or term decision is involved. The chip prefixes were found to be Welsh written in code (`welsh_render.py` COHORT_FRAME_CY, D50 "derived — listed for the linguist"), never checked by a Welsh speaker; they are decided per row with their answers on the query sheet because prefix and answer interact. The translator's versions of 19 engine sentences were, correctly, never applied; each is now a rule question on the handover (sheets 4–5).

**Changes.** (1) `pipeline/revert_review_corrections.py` — the exact inverse of `apply_review_corrections`: 18 keys / 19 substitutions reverted, producing `SSS2026_Welsh_Translation_Handoff_V4.14.xlsx`; every translated row proven equal to the verbatim V4.10 ingest (0 differences over 216 rows). The reviewer's findings remain questions on handover sheet 1, reworded so "Keep my wording" is the default. (2) Framework v2.5 (`make_framework_v25.py`): ui.chip_none, ui.table_summary, ui.stack_th_total, ui.stack_caption_year, ui.stack_caption_sex ("fesul"), ui.th_year_group, ui.th_base ("Sylfaen", matching the translator's FAQ), ui.f14_unmet ("heb ei fodloni", matching the engine's sentences), ui.ranking_note (translator's sentence with the figures returned to slots). No Welsh composed. (3) Version bump only in the pipeline; template and client byte-identical to V4.13 (0 changed lines).

**Proof.** Payload diff V4.13→V4.14: exactly 15 static rows + 3 chart headings (the 18 reverted keys) and the 9 frames; all 8,568 state records byte-identical; emitted lock byte-equal to V4.8. Fresh staged build, QA PASS, in-build 69/72; stock reruns dev 71/72 · release 71/75 · paths 17/18; pytest 82/1; jsdom 97/97 (three assertions updated to the translator's wording; the "reviewer corrections applied" assertion inverted to "translator's text verbatim"); provenance port 0/0/0.

**Not applied, by design, until the translator answers:** the answer-label overlay (survey wording vs document — query sheet, AW-1); chip prefixes (query sheet, prefix decision); frames that depend on a term (camp/chwaraeon, gwedd/golwg, gan ddisgyblion/disgybl) or a rule (mutation after 22, figure vs word 1–10); and the engine-pattern questions from the 19 generated sentences. Two label-table defects recorded for v2.6: sheet 23 keyed by English text maps "Not at all" generically (confidence questions show "Dim o gwbl" where the survey said "Ddim yn hyderus o gwbl"); yes/no echoes use the survey's first person where the translator uses the third.

## Build V4.15 (2026-09-21) — the translator's completed handover applied, against Framework v2.7 — the final prototype

**Version:** 2026-prototype-V4.15-bilingual · pipeline 0.27.0 · Framework v2.7 (sha256 972a3998e2a68cdbe7e701d75924901db6369967c0c2118c322c8aa466317792) · gate pack v8 (runner sha256 3057fef25b5d54bd564b0ee86affd3ef34048b4c1598c27eeb86ae3da2bde4fe, manifest c4221bba2cff4dcb — unchanged from v7) · shipped file SSS2026_ILR_Report_V4.15_Bilingual.html 179,534,432 bytes sha256 dd5d9959d40c2ed417cdc8eeb937171ff50d3240b690c99583f462ba45891bfd. **Owner's instruction (21 Sep 2026):** follow the translator's completed workbook (`SSS2026_Welsh_Translator_Handover_V4.14_1 COMPLETED.xlsx`, Aron Roberts, 21 Sep 05:15; sha256 fd715fe5…) — implement every correction, label and remaining item so the framework and the generation engine are fully built, then generate the final prototype.

**How the workbook was applied.** By one script, `pipeline/apply_translator_handover.py`, from the completed workbook, Framework v2.6 (sheet 58 = the chip prefixes moved out of code, output byte-identical), Handoff V4.14 and the translator's 15 Sep document (for the one value the handover had quoted truncated). 174 changes with a per-cell change log (Framework sheet 60; Handoff sheet "V4.15 change log"; `SSS2026_V4.15_Translator_decisions_applied.xlsx`), 21 typographic normalisations (rule 41: straight → curly quotes, NBSP → space; wording untouched), 25 flags (Framework sheet 61; `SSS2026_V4.15_Translator_flags_for_confirmation.md`). Nothing typed by hand; no Welsh composed — every value is a cell of the handover, of the approved survey (sheet 30/23) or already in the workbook.

**What the translator decided, and where it landed.** Sheet 1: 13 reviewer suggestions confirmed (applied as the exact V4.11 substitutions), 6 of the translator's own versions (whole cell; ui250 the bracketed sentence). Sheet 2: 24 suggested wordings (exact substitutions), ui009 the translator's version, 4 kept; AW-1/AW-2/AW-5 keep the survey's wording for every answer label; AW-3 "keep the named form" (PR-11 stands); AW-4 one term each — `cyflwr hirdymor` everywhere (sheets 17/22/31/44/58, the handoff, the e5 sentences via `welsh.term()`), `y golwg hwn` for "this view" (ui193, ui264). Sheet 2b: 72 label/prefix rows — answer labels stay the survey's; the profile table's long labels get their own sheet-23 rows (White from the document, the rest from the survey) and the client no longer falls back to English there (`buildMetadata.ethnicityProfileCy`); the confidence chips/charts quote the confidence question's own option `Ddim yn hyderus o gwbl` (D32 branch); the take-part chip's `Arall, rho fanylion`; chip prefixes from the translator's document for ep/eb/eo/li/mi/ov/dy (sheet 58), `Pob Ymatebwr` for the filter's "All Respondents" (the banner's "All pupils" stays `Pob disgybl`). Sheet 3: all 56 rows — 29 page-text rows and 2 new discussion-question rows (the static lane is 192/192 in Welsh, the two GDPR frames' Q17 exception closed, the technical record, the document title, the accessibility switch); one frame returned in English (`ui.a11y_glossary_heading`) is left pending and flagged. Sheet 4: 41 rules Correct; rule 15 WRONG → **D84** CONJ-06 `MODE=figure` on sheet 11 ("a" before every figure written in digits; decimal and vigesimal readings kept selectable); rule 16 WRONG → **D85** "ail" lenites its noun (`welsh_render.ail_np`, 2,353 sentences "Yr ail gamp"). Sheet 5: 35 sentences Correct, #12 (`a 11`) and #34 (`Yr ail gamp`) as ruled; all 19 comparisons: the engine's version. Twelve provisional rulings confirmed on sheet 39; decisions D84–D87 on sheet 02.

**Held or flagged, never patched.** The cb chip prefix the translator chose is identical to the ov chip's, so two English filters would carry one Welsh label — the blocking gate DIS-scope rejected that build (504 view labels); today's prefix is kept for that chip only and the translator is asked for a distinct one (flag 21). AW-4's `Ddim yn siŵr` / `gennyf` / `Sefyll–Eistedd` contradict the per-row survey decisions and AW-1 — the per-row decisions stand, flagged (1–3). Row 4 (`Oes` for the ethnically-diverse chip) contradicts AW-3's comment and rows 47–48 — the named form stands, flagged (20). CONJ-06: the rule comment says decimal reading, the corrected sentence writes `a 11`; the figure rule is the one rule that yields both, flagged for confirmation (25). Typos applied word for word and flagged: ui086, ui189, ui230; ec/cn prefixes applied by extension of their siblings (23–24); the Black profile row by extension of rows 50–53 (18).

**Engine and assurance.** Gate pack v8 (`vendor_welsh_gates_v8.py`): v7 with CONJ-06 read from sheet 11 — 62 changed lines, self-test 68/68 + one seeded case per mode; identity, QA, bundle and kit switched to v8. D82: the Welsh corpus lock was re-emitted from the build (`02c_lock_V415_v8.json`, sha256 d5db3fb3…) by `welsh_gates8.emit_lock`, which asserted first that the English projection (8,568 states) and the FT-11 key set equal the V4.8 lock's — they do; 4,201 states moved in Welsh, 0 in English. Fresh staged build (empty working directory), QA PASS, stamp 69/72 (pending GOV-rerun/GOV-bundle, disputed STK-caption-case), paths 17/18; stock reruns on the shipped file dev 71/72 · release 72/75 (STK-caption-case disputed; CAT-values 72 — the engine- and client-owned rows, down from 103, the translator's lane complete; GOV-mode — the owner's unsigned D69) · paths 17/18; emitted lock equal to the baseline in all three parts; ⟪missing⟫ markers 0 (from 8); pytest 86/1 (three CONJ-06 golden tests rewritten for the configured mode, four v2.7 tests added); jsdom 104/104 (assertions moved to the V4.15 state, seven added); provenance port 0 / 0 / 0, toggle 1,536/1,536/1,536; Chromium render probe 61 (EN) / 65 (CY) A4 pages, element renders checked by eye (rail, ethnicity table, confidence and take-part charts, glossary, cover).

**Proof of the English lock.** Record comparison V4.14 → V4.15: 271,966 narrative paragraphs, 0 English differences; every one of the 12,454 Welsh paragraph differences classifies as D86 (8,733), D85 (2,353), D84 (1,139), a combination of the three (147) or the confidence label (77); h1/h2 changes are D86 only; the 2,016 banner changes are the sheet-58 prefixes. The template is byte-identical to V4.14; the client changed in one place (the ethnicity profile table takes its Welsh from `buildMetadata.ethnicityProfileCy` instead of matching long labels against the chart's short options and falling back to English); no English catalogue value changed.

**Rebuild-kit reproduction.** `SSS2026_ILR_Rebuild_Kit_V4.15.zip` (124 files, MANIFEST.sha256 verified 124/124): from the kit's own `repo/` and `inputs/`, in an empty working directory, the v8 runner's self-test (68/68 + modes), the lexicon (byte-identical to the shipped `config/welsh_lexicon.json`), pytest 86/1 and the full staged build (states 0–12, assemble, QA PASS against the shipped V4.15 lock — no emission — stamp 69/72, paths 17/18, write) reproduce the shipped package: all 8,568 states byte-identical; `buildMetadata` differs only in `generatedAt` and the evidence file's hash (the evidence carries timestamps). Ships to Downloads (report as 10 parts joined on the PC, sha256 verified dd5d9959…; bundle; framework v2.6/v2.7; lock; handoff; register; flags; gate results; provenance port; render probe; key documents; kit) and to Data_Report_Outputs (the current-version set); the repo copy `Downloads\sss2026-ilr-prototype` synced from the kit.


## 8. Production deployment plan

# SSS2026 Interactive Learning Reports — production deployment plan

Version 1.0 · 15 September 2026 · prepared from the V4.9 prototype round and the deployment discussions of this session

This document is the working plan for taking the bilingual Interactive Learning Report from a single prototype (Ysgol Penrhyn Dewi, dummy data) to a published set of just under a thousand school reports, plus local authority and regional reports, each reachable at its own unique web link on the Sport Wales website. It records what has been agreed, the reasoning behind each choice, the rules every production build must obey, the figures we have measured, the checks that will run at scale, the order of work, and the decisions that still sit with Sport Wales. It is written so that anyone picking it up can follow it without the conversation that produced it. Every number quoted below was computed during the V4.9 round; where a figure is an estimate derived from those measurements it is marked as such, and where a figure has not yet been measured the plan says so and names the phase in which it will be.

---

## 1. Where we are starting from

The V4.9 prototype is a single self-contained HTML file, `SSS2026_ILR_Report_V4.9_Bilingual.html`, 179,445,060 bytes, sha256 `9eb4006a38a8a77dc74b8b90bcecb5463d0ff98ca6a2f2b1372f69cb6d9fa914`. It carries the whole report for one school of 366 pupils: the template, the client script, the fonts and cover media, and a pre-computed payload of 8,568 filter states (every combination of scope, gender and cohort the reader can select), so that the page never computes a statistic in the browser and never needs a server. The English narrative in that payload is byte-identical to V4.1, proven by the GOV-lock gate and by a record-level comparison of 316,968 English and Welsh records and 41,650 stack sets against V4.8 with zero differences. The Welsh is generated from fact records through the Framework v2.2 workbook and lexicon; nothing in it is translated or invented, and a missing lexicon entry fails the build.

The assurance position at the end of the round is: in-build stamp 69/72 with two gates pending and one disputed; stock gate pack v7 rerun on the shipped file 71/72 in dev mode and 71/75 in release mode (the shortfall being STK-caption-case, a verified pack defect, and the three release-only gates that wait for the translator's 356 values and the owner's signed D69); renderer paths 17/18; jsdom regression 53/53; jsdom port of browser gate v3 with 0 English-without-provenance, 0 typography faults and a 1,848/1,848 fixture toggle; pytest 76 passed, 1 skipped. Selftest of the vendored runner is 68/68.

Two facts about the payload shape drive the architecture. The states are 178.8 MB of the 179 MB file (module narrative 112.3 MB, m 26.8, stacks 13.9, h1 11.2, h2 4.8, scope 4.0, rows 3.5), which is roughly 39 KB per state; everything that is not a state is 0.16 MB. The whole payload compresses to 20.2 MB with gzip. In other words the report is a very small application sitting on top of a large but highly regular and highly compressible block of pre-computed states, and a reader only ever looks at one state at a time.

The build environment facts that matter for planning are also recorded here. The cloud sandbox used for this round has two cores and about 29 GB of free disk. The local Windows sandbox on the working PC has about 3 GB of RAM and 1.6 GB of free disk, and one build needs around 600 MB of working files. Neither is a production build farm; section 6 sets out what is.

---

## 2. The architecture we have agreed

Two options were on the table: a shared template that pulls each school's data from a combined data repository at view time, or one generated report per school. The decision is a specific form of the second option, with the best property of the first borrowed for the client code. The reasoning is as follows.

A report that fetches from a live data repository has a server, a query layer, an authentication layer and a dependency between what a reader sees and what a database returns at that moment. Each of those is a place where a report can change after it has been checked, and none of them is covered by the gate pack, which examines a finished artefact. The whole value of the V4.9 assurance position is that a checked file is the file that is served. That value is preserved only by pre-generating everything.

A monolithic 179 MB file per school, however, is not something a school on an ordinary connection should have to download to read one page, and a thousand such files are awkward to host, check and move. The resolution is to keep the generation model exactly as it is (one complete, gate-checked package per school, produced by one build) and to change only how the finished package is written to disk and read by the browser.

The agreed shape, then, is this.

Every school has its own report directory, produced by its own fresh build from the canonical dataset, and nothing in that directory depends on any other school's build. The directory holds a small core page (the template with the school's static furniture stamped in, the client script, the non-state payload, and the first state inlined so the page renders without a network request), and beside it a set of state chunk files. The client's `DATA.states[key]` lookup, which today reads from an in-memory object, becomes a fetch-and-cache: when the reader selects a filter whose state is not yet loaded, the client fetches the chunk that contains it, caches it, and renders. The reader's experience is unchanged; the initial download drops from 179 MB to the size of the core page plus one chunk.

The client script and template are shared in the sense that every school's build uses the same frozen release of them, so a fix to the client is a fix for every school in the next regeneration. They are not shared at serving time in a way that could let a later change alter an already-published report: each release tag publishes its own immutable copy of the client assets, and each report's core page references the tag it was built with.

The only data source for any build is a canonical, cleansed dataset (parquet) produced once from the response export, filtered by school identifier inside the build. No build reads a spreadsheet, a previous report, a previous package or another build's intermediate files.

A manifest, one row per report, is the register of what exists, what was built from what, what the gates said, and where it is published. It is the source of the links the website shows and the input to every check in section 8.

Hosting is static object storage behind a CDN. There is no application server in the serving path. The website's content management system holds, for each school and each local authority, a link to that report's directory; the report itself is not inside the CMS.

---

## 3. Hosting, links and access

### 3.1 Link scheme

Each report lives at a directory of the form

    https://reports.<sportwales-domain>/2026/<token>/

where `<token>` is derived from the school's identifier by a keyed hash (HMAC-SHA256 over the school id with a secret key held by Sport Wales, truncated to a fixed length). The token is stable for a given school and key, so links can be issued once and reused for the year, but it cannot be guessed from the school's name, number or position in any list, and knowing one school's token reveals nothing about another's. Local authority and regional reports use the same scheme over their own identifiers, under `/2026/la/<token>/` and `/2026/region/<token>/` so that the manifest and the checks can tell the three families apart.

The secret key is not stored in the repository, in the manifest or in any build output. It is held by Sport Wales; the build farm receives the computed tokens through the manifest, never the key. If the key is ever exposed, the response is to compute new tokens and republish the same files under new directories; the report contents do not change and do not need to be rebuilt, because the token is a property of the path, not of the file.

The directory index is the report's core page, so the link above opens the report directly. Within a report the existing URL contract continues to work: the filter state is carried in the fragment (`#scope=…&gender=…&cohort=…&lang=…`), so a reader can bookmark or share a particular view, and the language toggle is preserved.

### 3.2 Storage and delivery

The candidate platforms are Azure Blob Storage with static website hosting, Amazon S3 with CloudFront, or Cloudflare Pages. All three serve static files from a directory tree over HTTPS with a CDN in front, all three support the configuration items below, and the choice can follow whichever provider Sport Wales' web estate already uses. The plan does not depend on the choice.

The serving configuration must provide: HTTPS only; gzip or brotli compression of the JSON chunks (the payload compresses roughly nine to one, which is the difference between a usable and an unusable report on a school connection); long-lived immutable caching for chunk files and tagged client assets, which never change once published; an `X-Robots-Tag: noindex, nofollow` header on everything under `/2026/`, and a matching `robots.txt`, so that the reports are not indexed by search engines; directory listing disabled at every level, so that the set of tokens cannot be enumerated; and a 404 response, not a redirect to anything informative, for an unknown token.

### 3.3 Access control — a decision for Sport Wales

An unguessable link is a form of access control, but it is not authentication. Anyone who is given the link, or who finds it forwarded, can open the report. Sport Wales must decide which of the following it wants, and the decision determines part of the work in section 9.

The first option is unlisted links only. Each school receives its link directly; the CMS shows links to LA and regional reports openly, or behind whatever the website already uses for partner content. This is the simplest option, is fully compatible with static hosting, and is appropriate if the report content is aggregated and suppressed to the level Sport Wales is already comfortable publishing in other formats.

The second option is login-gated access. School reports sit behind a sign-in, most naturally the same Hwb or Sport Wales account a school already uses. This requires either an authenticating proxy in front of the static store or signed short-lived URLs issued after login. It is still compatible with pre-generated reports (the files are unchanged; only who can fetch them is controlled), but it adds a component to operate and to test.

The recommendation is to settle this before the pilot in section 9, because the pilot must exercise the real serving path. The plan is written so that either choice works; it is the suppression rules and the sensitivity of the smallest schools' figures that should drive the decision, and those are matters for the report owner.

### 3.4 Website integration

The Sport Wales website does not host the reports; it links to them. Integration is therefore a data import into the CMS: for each school and local authority, the token URL from the manifest, the report's title in both languages, and the publication status. The import is generated from the manifest by a small script and reviewed before it is applied. A later regeneration that changes files but not tokens needs no CMS change at all; a token rotation is a re-import of the same list.

---

## 4. The data source and the manifest

### 4.1 Canonical dataset

The response export that the prototype consumed is a workbook. For production, the export is cleansed once, by the existing cleansing steps, into a single canonical parquet file with one row per pupil response and a `school_id` column, and that file's sha256 is recorded. This is the only data input any report build may read. The build's loader takes a school id, reads the canonical file, filters to that school, and refuses if the school is absent or if the filtered frame has a shape the framework does not expect. The same loader with an LA or region filter feeds the LA and regional builds.

Producing the canonical file is itself a checked step: the row count per school and the national totals are written to a small reconciliation table at the time the file is made, and section 8 compares every report's headline counts back to it.

### 4.2 The manifest

The manifest is a plain table (CSV for reading, SQLite for querying; both derived from the same source) with one row per report and the following columns: report family (school, LA, region); identifier; display names in English and Welsh; the profile the build uses (see section 7 for LA and regional profiles); the token and the resulting URL; the release tag the report was built with; the canonical dataset sha256; the build start and end times and the machine that built it; the gate results headline (dev and release, and the renderer path count) copied from the report's own stamp; the sha256 of every file in the report directory; the hosting verification result and time; the publication status (built, verified, published, withdrawn); and free text for any exception raised during the build.

The manifest is written by the build runner and the checkers only, never by hand, and it is the single place the state of the whole set is read from. The rollup in section 8 is a query over it.

---

## 5. Guarding against hallucination and compounded error

This section answers the concern raised directly during planning, because it is the concern that matters most in a bilingual public report and because the answer is structural rather than a matter of vigilance.

There is no language model, and no non-deterministic component of any kind, in the path that produces a report. Every sentence of English narrative comes from a fixed template keyed by the fact record it describes; every Welsh sentence is generated by the grammar engine from the same fact record through the workbook's lexicon, frames and rulings. Given the same release tag, the same framework workbook and the same input rows, the output is the same bytes. Hallucination in the sense of a system inventing text it was not given is not possible in this pipeline, because there is no component capable of it.

The risks that do exist are of a different kind, and the pipeline is built to make each of them fail loudly rather than pass silently.

The first is a template path that no report has exercised yet. With 366 pupils in one school, some combinations of values in some modules have simply not occurred, and a thousand schools will exercise combinations the prototype never did. The design response is that the engine does not fall back: a Welsh string with no lexicon entry, a provisional ruling wording the PR_KEYS regexes do not recognise, a count noun phrase not in the sheet 50 table, or a static node without a handoff row each raises and stops the build. The `_MISSES` registry records every miss; in dev mode a `⟪missing:key⟫` marker is rendered so a reviewer sees it, and in release mode the build refuses. The expectation, stated plainly so that it is not mistaken for a failure of the plan, is that the first full run will produce a handful of refusals from schools whose data reach template paths the prototype did not. Each such refusal is fixed at source (a lexicon row, a ruling, a framework decision recorded in the compliance record) and the affected schools are rebuilt from scratch. A refusal is the system working.

The second is drift between the English and Welsh corpora or between two builds of the same school. The lock mechanism (`lock_V49_v7.json`, per-state hashes of both corpora and the FT-11 key set) already proves that V4.9 reproduces V4.8's text exactly. At scale the same mechanism is applied in two ways: the corpus of template strings and static keys is locked per release tag, so any change to what the pipeline is capable of saying is a deliberate, versioned event; and the byte-compare rebuild in section 8 proves that the same input produces the same output on a second machine.

The third is compounding, meaning an error in one output propagating into the next. This is addressed by the build contract in section 6: no build reads any output of any other build, so there is no channel through which an error could propagate. A defect in the release affects every report built from that release identically, which is precisely why it is detectable (the same gate fails on every report, and the rollup shows it) and precisely why the remedy is a new tag and a complete regeneration rather than a patch.

The fourth is a workbook defect. The workbook is the source of truth, and the rule that has governed nine rounds continues: the pipeline implements what the workbook says, and where the workbook is wrong the build raises it in the compliance record for the report owner or the linguist to correct in the workbook. No code ever "corrects" the workbook, and no gate is ever satisfied by matching its pattern rather than by meeting its intent. At scale the mechanism for raising a workbook defect is unchanged; what changes is that the first full run will surface more of them in one go, which the sequence in section 9 allows time for.

The fifth is the human lane. The translator's 356 values and the owner's signed D69 are inputs the pipeline cannot generate. Until they exist every build is a dev build, the review marker shows English under a pending flag for untranslated static furniture, and the release-mode gates CAT-values, CAT-marker and GOV-mode fail by design. Publication requires release mode; the plan therefore has a hard dependency on those inputs, and section 10 lists them.

---

## 6. The fresh-start build contract

These are the rules the production build runner enforces. They are written as rules because they will be encoded as checks in the runner, and because the answer to "is every one of these reports an exact, independent product of the original template and the source data?" must be yes by construction, not by assurance after the fact. A build that violates any rule stops and records the violation in the manifest; it never produces an output.

Rule 1, frozen release. A production build runs only from a tagged release of the repository. The tag's manifest lists the sha256 of every file that participates in a build: the pipeline modules, the client script and template, the framework workbook, the lexicon, the vendored gate packs, the locks, the fonts and cover media. At start-up the runner recomputes every hash and refuses on any mismatch. A working copy with an uncommitted change cannot build a production report.

Rule 2, empty working directory. Each build begins in a directory the runner has just created and verified to be empty, and ends by deleting it after the outputs have been copied to their write-once destination. Nothing survives from one build to the next on the build machine except the frozen release and the canonical dataset.

Rule 3, input allowlist. A build may read exactly three things: the frozen release, the canonical dataset (filtered to its school inside the loader), and its own row of the manifest, which supplies the identifier, the profile and the token. The runner records the sha256 of the release manifest and of the canonical dataset in the report's build identity. Any attempt to open another path, in particular anything under a previous build's output directory, is refused by the loader.

Rule 4, no reuse of intermediates. The staged build's chunk pickles, package pickle and assembled payload exist only inside the build's own working directory. Reusing a state chunk, a lexicon build or a stamped template from another school or a previous run is prohibited in production, and the runner does not expose an option for it. Where the prototype rounds used chunk reuse to save time during development, that path is disabled by the production flag.

Rule 5, full gates every time. Every build runs the complete vendored gate pack (selftest first, then the in-build run, then the two stock reruns on the written file with the bundle asserted) and the jsdom regression and browser-gate port. A blocking failure that is neither in the recorded pending list nor the recorded disputed list stops the build; no output is written. The gate stamp, the evidence files and the bundle are produced for every report exactly as they were for the prototype.

Rule 6, write-once outputs. A report directory is written once, into a location the runner does not have permission to modify afterwards. The sha256 of every file is recorded in the manifest at write time. The hosting verifier (section 8) compares what is served against those hashes, and a mismatch marks the report as withdrawn until it is regenerated.

Rule 7, identity written once. Each report carries a single build identity (release tag, framework sha256, runner version and sha256, gate manifest hash, canonical dataset sha256, mode), and every legacy or display field is derived from it. There is no second place a version can be stated.

Rule 8, change means regenerate. Any change to the release (a lexicon row, a template fix, a client change, a framework decision) is a new tag, and a new tag means every report is rebuilt from scratch under it. There is no partial patch, no editing of a published file, and no mixing of tags within one publication set. The manifest records the tag per report, and the rollup refuses to mark a publication set as complete while two tags are present.

Rule 9, dev until the human inputs exist. The runner will not build in release mode unless the translator's values and the owner's signed D69 are present in the framework it hashes. Dev-mode reports can be built, checked and hosted for internal review and for the pilot, but they carry the review marker and cannot be marked as published in the manifest.

Rule 10, independent reproduction. Five per cent of the set, chosen at random after the full run, is rebuilt from the same tag and the same canonical dataset on a second, separately provisioned machine, and every output file is compared byte for byte, allowing only for the build timestamp fields in the identity. Any other difference stops publication of the whole set until it is explained.

Rule 11, the workbook is not touched by code. This rule from the prototype rounds is restated here because it is the one most likely to be tempted at scale: a refusal caused by a workbook gap is fixed in the workbook by its owner and recorded in the compliance record, never in code, and the affected reports are rebuilt under the tag that includes the corrected workbook.

---

## 7. Local authority and regional reports

The LA and regional reports use the same pipeline, the same template family and the same gate packs, with a different profile in the manifest row. The profile supplies the identifier type (LA or region), the filter applied by the canonical loader, the set of scopes offered (an LA report's scopes are its schools' aggregate views rather than year groups within a single school), and two design decisions that Sport Wales must make before these reports are specified in detail.

The first decision is whether an LA report shows a breakdown by school. If it does, the report identifies individual schools and their figures side by side, which raises the question of whether a school should be able to see its neighbours' results; if it does not, the LA report is a larger version of a school report with the LA's aggregate as its whole-scope view. The two are different reports and the profile must say which.

The second decision is the suppression threshold: the minimum count below which a cell is not shown. The prototype follows whatever the framework workbook specifies for a single school; an LA breakdown by school multiplies the number of small cells, and the threshold and its rule (for example whether a suppressed cell also suppresses its complement so that it cannot be recovered by subtraction) must be stated in the workbook so that the pipeline implements it rather than interprets it.

The regional reports sit above the LA reports and inherit the same two decisions. The number of LA reports is fixed by the twenty-two Welsh local authorities; the number of regional reports depends on the regional grouping Sport Wales uses and is recorded in the manifest when that is confirmed.

Timing for these reports has not been measured. An LA report's state count depends on the profile (more schools means more scopes, but there are no year-group scopes to multiply against), so the per-report time may be higher or lower than a school's. The plan measures it in the LA pilot (section 9, phase 5) on two local authorities before the full LA run is scheduled, and does not quote a figure before then.

---

## 8. Checking at scale

The prototype was checked by reading it. A thousand reports cannot be, and the checking plan is layered so that the machine-checkable properties are checked on every report without exception, and human attention is spent on a stratified sample where it adds something a gate cannot.

Layer one is the per-build assurance, unchanged from the prototype and applied to every report by rule 5: selftest, in-build gate run, two stock reruns, jsdom regression and browser-gate port, bundle and evidence written, identity stamped. This layer is what makes a report eligible to exist.

Layer two is the rollup. After the run, the manifest is queried for every report's gate headline, path count, pending and disputed lists, and identity hashes. The expected values for a release-mode run are known (they are the values the pilot establishes for the tag, and for the V4.9 tag in dev mode they are 71/72, 71/75 and 17/18 with STK-caption-case disputed); every report must show exactly those values with exactly the same runner sha256, framework sha256 and manifest hash. Any report that differs in any field is listed, and the set is not publishable until every listed report is either rebuilt clean or the difference is explained and recorded. The rollup is a script over the manifest and it produces one page that says whether the set is uniform.

Layer three is reconciliation against the canonical dataset. For every report, the headline counts (pupils included in the whole-scope view, and the per-year-group and per-gender counts in the state index) are extracted from the payload and compared to counts computed independently with a plain dataframe query over the canonical file. Every LA report's whole-scope count must equal the sum of its schools' counts, and the sum of all LA counts must equal the national total recorded when the canonical file was made. This layer catches a wrong filter, a duplicated school or a dropped row, none of which a language gate would see.

Layer four is the byte-compare rebuild of rule 10, five per cent of the set on a second machine.

Layer five is the browser gate in real Chromium. The stock `02_browser_gate_provenance.py` harness, which could only be run under jsdom in the build environment, is run on the operations machine over a sample of reports at sixty states each, with the fixture toggle, exactly as the bundle's `RUN.md` describes for the prototype. The sample is stratified by school size band and by local authority so that small and large payloads and both ends of the country are covered.

Layer six is the linguist's sample. The linguist sheet's method (the 150-sentence proofreading sample, the fixtures, the tab 9 checks) is applied to a stratified sample of reports rather than to one. The stratification should cover school size (because small schools exercise the singular and low-count noun phrases that large schools never do), language medium of the school, and local authority, and it should deliberately include any report whose build raised and cleared a refusal, because those are the reports that exercised a path the prototype did not. The English is checked in the same sample against the source data for the reports concerned; the English narrative itself is locked by tag and does not need re-proofreading, but its numbers do need spot-checking against the dataframe.

Layer seven is hosting verification. After publication, a script walks the manifest, fetches every file of every report from its public URL, compares the bytes against the recorded sha256, checks the response headers (compression, cache policy, noindex), confirms that a request for a directory listing and for a wrong token both return 404, and records the result and time in the manifest. This is run at publication and again on a schedule for the life of the publication set.

---

## 9. Sequence and milestones

The order below is the order the work should happen in. Each phase has an exit condition; the next phase does not start until it is met.

Phase 0, decisions. Sport Wales settles: the access-control model (section 3.3); the LA and regional design, meaning the school breakdown question and the suppression threshold and rule, recorded in the workbook (section 7); the hosting platform and domain; and custody of the token secret. Exit: each decision is written into the compliance record and, where it affects the pipeline, into the workbook.

Phase 1, close the prototype. The "few final tweaks" identified on the rebuilt V4.9 are applied as a V4.10 round under the established process (reproduce, change, gate, ship, compliance record). In parallel the human lane completes: the translator's values, the owner's D69, Q17, PR-15 and EN-05 decisions, and the linguist's sheet v6. Exit: a release-mode build of the prototype passes every gate that is not disputed, with the dispute recorded, and the compliance record is current. This is the first tag that could be used for production.

Phase 2, production code. Four contained changes to the pipeline, each with its own tests: the write stage emits the core page and state chunks and a chunk verifier proves that the chunks concatenated are identical to the in-memory states the gates examined, while the monolithic package is still written into the build's assurance directory (not served) so that the stock gate runner, which reads one file, continues to run unmodified; the client's state lookup becomes fetch-and-cache with the first state inlined; the canonical loader replaces the workbook reader and filters by identifier from the manifest row; and the build runner enforces the eleven rules of section 6 and writes the manifest. The rollup, reconciliation and hosting-verification scripts of section 8 are written at the same time. Exit: the prototype school builds through the production runner, produces a chunked report whose gate results equal the monolithic build's, and the jsdom regression passes against the chunked client.

Phase 3, build farm. A cloud virtual machine with eight to sixteen cores, memory sized after measuring one build's peak (that figure is not yet known and is taken in the first pilot build), and a few hundred gigabytes of disk, is provisioned with the frozen release and the canonical dataset and nothing else. Exit: the fresh-start rules pass their own tests on the farm (a deliberately modified file is refused; a non-empty working directory is refused; a path outside the allowlist is refused).

Phase 4, school pilot. Twenty schools, chosen to span size bands and local authorities, are built on the farm, published to the real hosting path under the real link scheme, and put through every layer of section 8 including the linguist's sample and the Chromium browser gate. The per-school build time and peak memory are measured here and replace the estimates in section 10. Exit: all twenty are uniform in the rollup, reconcile to the canonical file, verify on the host, and the linguist's sample raises nothing that requires a tag change; or, if it does, the tag is cut, the twenty are rebuilt, and the exit is re-tested.

Phase 5, LA pilot. Two local authorities are built under the agreed profile, published and checked in the same way, and their build times measured. Exit: as phase 4.

Phase 6, full run. Every school, then every LA, then every region, is built under the single production tag with the concurrency the phase 4 measurements support. Refusals are collected, fixed at source, recorded, and the affected reports rebuilt; if a fix requires a tag change, the whole set is rebuilt under the new tag (rule 8). Exit: the rollup shows one tag and uniform results across the entire set.

Phase 7, verification of the set. Layers three, four, five and six of section 8 run over the full set. Exit: reconciliation is exact, the five per cent rebuild is byte-identical, the browser gate and linguist samples are clean or their findings are resolved by a new tag and a full rebuild.

Phase 8, publication. The manifest export is imported into the CMS, the reports are made reachable, layer seven runs, and the compliance record receives the publication entry naming the tag, the canonical dataset hash, the manifest hash and the date. Exit: every report the CMS links to verifies against its recorded hashes.

Phase 9, after publication. Layer seven runs on a schedule. Any change, from a corrected lexicon row to a rewording, follows rule 8: new tag, full regeneration, full verification, republication. The previous set is retained, unlinked, with its manifest, for the record. The token secret's custody and rotation procedure is tested once, on a non-production path, so that it is known to work before it is ever needed.

---

## 10. Timing and resources

The measured per-school time on the two-core cloud sandbox for the prototype school, running the complete V4.9 process, is between seven and eight minutes: state generation about two minutes, assembly about half a minute, the in-build gates about a minute and a half, the write stage about a quarter of a minute, the HTML build about half a minute, the two stock gate reruns about two minutes together, and the jsdom runs about a minute. These are single-run measurements for a 366-pupil school and will differ with school size, most of all in state generation, whose cost scales with the number of pupils and cohorts.

Run sequentially at that rate, a thousand schools is on the order of 115 to 130 hours (seven minutes over 990 schools is 6,930 minutes, or about 115.5 hours; eight minutes is about 132 hours), which is five to six days of unattended running, and the outputs alone at roughly 179 MB per school would be on the order of 180 GB before compression, far more than the sandbox's 29 GB of free disk. The working PC's local sandbox, with about 3 GB of memory and 1.6 GB free against a 600 MB per-build working set, cannot run even one build reliably. Neither machine is the answer, and the plan does not propose to use either for the production run.

On an eight-core virtual machine running several builds concurrently, the estimate is twelve to eighteen hours for the school set, and roughly half that on sixteen cores, subject to memory: if one build's peak memory is high, concurrency is bounded by memory rather than cores, which is why the peak is measured in the pilot before the farm's size is finalised. Disk on the farm should be a few hundred gigabytes to hold the outputs, the assurance directories and the five per cent rebuilds with margin. These are estimates derived from the two-core measurement and should be replaced by the phase 4 measurements in the manifest before the full run is scheduled.

The elapsed time for the programme as a whole is dominated not by the build but by the human lane in phase 1 and the decisions in phase 0. The pipeline work of phase 2 is bounded and well understood; the pilot phases are each a matter of days including the linguist's review; the full run and its verification are a matter of days on the farm. The dependency that cannot be shortened by machines is the translator's values and the owner's signed decisions.

---

## 11. What stays with humans

The following cannot be produced by the pipeline and are required before a release-mode production build exists. The translator supplies the 356 static values (342 page strings and the fourteen attribute strings, ui217 to ui230) through the handoff workbook. The report owner supplies the signed D69 value and the decisions on Q17, PR-15 and EN-05; EN-05 ("21th") remains the owner's and is not to be touched in code. The linguist supplies sheet v6 covering PR-19 and FT-11, the fixtures, the 150-sentence proofreading sample and tab 9, and later applies the same method to the stratified sample in section 8. Operations run the device, assistive-technology and real-Chromium checks that the build environment could not. Sport Wales makes the four decisions of phase 0 and holds the token secret.

The eight items raised against gate pack v7 in the V4.9 register remain open with the pack owners; the disputed STK-caption-case emulation and the 72/75 denominators in particular determine the exact "uniform" values the rollup expects, and any change to the pack is a new vendored version, a new tag, and a full regeneration like any other change.

---

## 12. Summary of what is fixed and what is open

Fixed by this plan: fully pre-generated reports from a frozen tag; one independent build per report from a canonical dataset; a core page plus lazily fetched state chunks; static hosting behind a CDN; per-report keyed-hash tokens under a dedicated reports domain; a manifest as the single register; eleven build rules enforced by the runner; seven layers of checking with every machine-checkable property checked on every report; a pilot of twenty schools and two local authorities on the real serving path before the full run; and the principle that every change is a new tag and a complete regeneration.

Open, and named as such: the access-control model; the LA and regional design decisions and suppression rule; the hosting platform and domain; token secret custody; the per-build peak memory and the LA build time, both measured in the pilots; the human-lane inputs that gate release mode; and the pack owners' response to the V4.9 register.


## 9. V4.10 translation register (summary)

See V4.10_translation_register.md / .xlsx in the kit (`repo/generated/V4.10_translation_register.*`).

## 10. Kit inventory

123 files. Full hashes in `MANIFEST.sha256`.

| file | bytes | sha256 |
|---|---|---|
| `inputs/18117 Chwaraeon Cymru 2026 School Sport Survey - School Reports.docx` | 122,396 | `15d726d0ceb95494…` |
| `inputs/SSS2026_YPD_export_headers_cleaned_copy.xlsx` | 1,265,519 | `e457bc8eccbecad2…` |
| `inputs/School Reports Accessibility Feedback.docx` | 16,306 | `71dffd0e4a17f583…` |
| `inputs/fonts/montserrat-latin-400-normal.woff2` | 18,780 | `e66bcd2761ab6924…` |
| `inputs/fonts/montserrat-latin-600-normal.woff2` | 18,688 | `d857325c360f7128…` |
| `inputs/fonts/montserrat-latin-800-normal.woff2` | 19,012 | `ba826fb84c2e9615…` |
| `inputs/yac images for report/basketball.png` | 1,306,763 | `d7af3c0a71edcbd0…` |
| `inputs/yac images for report/football.png` | 2,783,180 | `0c6684bbc64a8a28…` |
| `inputs/yac images for report/wheelchair javlin thrower.png` | 4,584,065 | `466b13b8f9b5b7d2…` |
| `repo/LIMITATIONS.md` | 10,228 | `b905a147431c1163…` |
| `repo/README.md` | 14,276 | `92ed24e6c3a91ba9…` |
| `repo/build_prototype.sh` | 1,060 | `4ce50ca172b4e35a…` |
| `repo/config/01_Framework_v2.2.xlsx` | 317,510 | `a540189fde986765…` |
| `repo/config/01_Framework_v2.3.xlsx` | 335,077 | `9356dee97dab37bf…` |
| `repo/config/01_Framework_v2.4.xlsx` | 336,935 | `b075f8e237a276c7…` |
| `repo/config/01_Framework_v2.5.xlsx` | 338,908 | `f4b9d00f448c7c50…` |
| `repo/config/01_Framework_v2.6.xlsx` | 342,991 | `e18c821908338802…` |
| `repo/config/01_Framework_v2.7.xlsx` | 359,934 | `972a3998e2a68cdb…` |
| `repo/config/02c_english_lock_V46.json` | 454,194 | `92519881b72a6cae…` |
| `repo/config/02c_english_lock_V47.json` | 454,194 | `92519881b72a6cae…` |
| `repo/config/02c_english_lock_V48.json` | 454,194 | `92519881b72a6cae…` |
| `repo/config/02c_lock_V415_v8.json` | 940,720 | `d5db3fb34d1a3589…` |
| `repo/config/02c_lock_V48_v7.json` | 940,341 | `ebb3b8ce5025f4f5…` |
| `repo/config/SSS2026_Welsh_Translation_Handoff_V4.10.xlsx` | 43,906 | `9ec9952f9590af2c…` |
| `repo/config/SSS2026_Welsh_Translation_Handoff_V4.11.xlsx` | 41,934 | `5bf0069c47d13c0b…` |
| `repo/config/SSS2026_Welsh_Translation_Handoff_V4.14.xlsx` | 41,976 | `b078f3fa5fc21754…` |
| `repo/config/SSS2026_Welsh_Translation_Handoff_V4.15.xlsx` | 52,958 | `329dd881fc7a14b5…` |
| `repo/config/SSS2026_Welsh_Translator_Handover_V4.14_COMPLETED.xlsx` | 80,133 | `fd715fe56791065e…` |
| `repo/config/SSS2026_Welsh_translation_document_15Sep2026.docx` | 122,396 | `15d726d0ceb95494…` |
| `repo/config/assets.yml` | 3,408 | `cf7366aa20577f0a…` |
| `repo/config/column_mapping.yml` | 8,065 | `0bbeca6905938a57…` |
| `repo/config/cover_media/README.txt` | 277 | `cfaa1109732b8f32…` |
| `repo/config/cover_media/image1.png` | 10,003 | `26c0259ab41c5143…` |
| `repo/config/cover_media/image3.png` | 40,307 | `0cd695de9146ce46…` |
| `repo/config/metrics.yml` | 25,377 | `6045636ea518b975…` |
| `repo/config/narratives.yml` | 6,079 | `5663e1d85d9c32d9…` |
| `repo/config/school_profile.json` | 1,719 | `c7ba6106a31e7d17…` |
| `repo/config/welsh_lexicon.json` | 244,689 | `26c0a54b2467e0c5…` |
| `repo/generated/SSS2026_V4.15_Translator_decisions_applied.json` | 90,568 | `2b1009ece5bcdeec…` |
| `repo/generated/SSS2026_V4.15_Translator_decisions_applied.xlsx` | 33,206 | `650f685ccd519224…` |
| `repo/generated/SSS2026_V4.15_Translator_flags_for_confirmation.md` | 10,773 | `696d4517542597b0…` |
| `repo/generated/SSS2026_Welsh_Translation_Handoff_V4.9.xlsx` | 32,118 | `5ba78d935af72ab8…` |
| `repo/generated/V4.10_translation_register.md` | 173,687 | `9a36d4a32ae0995e…` |
| `repo/generated/V4.10_translation_register.xlsx` | 69,828 | `efaa09041c5148a6…` |
| `repo/generated/V4.15_browser_gate_jsdom.json` | 494 | `c9fbe714b60b92f4…` |
| `repo/generated/bundle/01_Framework_v2.7.xlsx` | 359,934 | `972a3998e2a68cdb…` |
| `repo/generated/bundle/RUN.md` | 4,629 | `649cb97dd9bc6f7d…` |
| `repo/generated/bundle/browser_gate_provenance.py` | 12,617 | `1b053e89396e5097…` |
| `repo/generated/bundle/evidence.ndjson.gz` | 208,840 | `94f4a7a77dbb47db…` |
| `repo/generated/bundle/evidence_rerun_dev.ndjson.gz` | 209,060 | `011a6a27441345e5…` |
| `repo/generated/bundle/evidence_rerun_release.ndjson.gz` | 209,215 | `54046716e09e1e69…` |
| `repo/generated/bundle/lock_V415_v8.json` | 940,720 | `d5db3fb34d1a3589…` |
| `repo/generated/bundle/lock_V415_v8_emitted.json` | 940,341 | `16faa6a587ea6ade…` |
| `repo/generated/bundle/manifest.json` | 1,263 | `8b0f0e9c3f78ed18…` |
| `repo/generated/bundle/results_dev.json` | 37,308 | `9ec71bd18112d174…` |
| `repo/generated/bundle/results_release.json` | 37,474 | `d2c47a4b7c179bdf…` |
| `repo/generated/bundle/runner_bundle_dev.json` | 3,504 | `401af5e3e8f67fa1…` |
| `repo/generated/bundle/runner_bundle_release.json` | 3,482 | `d4aa3ca11854fd3d…` |
| `repo/generated/bundle/verify.json` | 723 | `51248b334e8aea6d…` |
| `repo/generated/bundle/welsh_acceptance_gates_v8.py` | 101,982 | `3057fef25b5d54bd…` |
| `repo/generated/bundle/write_verify.py` | 1,653 | `39f5fa460d31885b…` |
| `repo/generated/colour-mapping.md` | 28,122 | `daa717eb74adaa8f…` |
| `repo/generated/narrative-templates.md` | 5,008 | `49430a2dba9b9693…` |
| `repo/generated/validation-summary.txt` | 3,029 | `fc3c655de14e1521…` |
| `repo/pipeline/__init__.py` | 63 | `314698d0f536391f…` |
| `repo/pipeline/apply_review_corrections.py` | 4,219 | `73f82b183d5d48e8…` |
| `repo/pipeline/apply_translator_handover.py` | 55,030 | `2a55d80c7af76101…` |
| `repo/pipeline/build_html.py` | 5,119 | `9b4c52050ff35054…` |
| `repo/pipeline/build_report_package.py` | 38,175 | `c5629319b6fac2bc…` |
| `repo/pipeline/build_welsh_lexicon.py` | 23,213 | `cf47c274982242ec…` |
| `repo/pipeline/common.py` | 11,757 | `801e32fd589fbb80…` |
| `repo/pipeline/engine.py` | 14,088 | `46de9142b86b3814…` |
| `repo/pipeline/ingest_translation_doc.py` | 26,274 | `a6a84c0bff08c02a…` |
| `repo/pipeline/load_normalise.py` | 26,677 | `000ff28bdd044e86…` |
| `repo/pipeline/make_bundle.py` | 6,512 | `3080fbb866b46383…` |
| `repo/pipeline/make_framework_v23.py` | 21,207 | `4ebc2245200b89e5…` |
| `repo/pipeline/make_framework_v24.py` | 3,433 | `cd874d2bcaf9538d…` |
| `repo/pipeline/make_framework_v25.py` | 4,056 | `405c2bdcd8c1382c…` |
| `repo/pipeline/make_framework_v26.py` | 7,209 | `4fe07d318239a439…` |
| `repo/pipeline/make_rebuild_kit.py` | 16,687 | `2f21f5684ab52728…` |
| `repo/pipeline/make_translation_handoff.py` | 8,398 | `74fe3e41e7a5ceb3…` |
| `repo/pipeline/narrative.py` | 21,395 | `a22db6b876d38fd7…` |
| `repo/pipeline/narrative2.py` | 38,716 | `ac7cf084280f24b8…` |
| `repo/pipeline/narrative2_modules.py` | 58,350 | `376396ffa30b81e9…` |
| `repo/pipeline/narrative2_modules_b.py` | 66,948 | `1bea07c8a6ee78f8…` |
| `repo/pipeline/revert_review_corrections.py` | 1,857 | `0c6ad9a3db4053ff…` |
| `repo/pipeline/staged_build.py` | 24,418 | `b5d9da00b873849e…` |
| `repo/pipeline/static_lane.py` | 16,908 | `28e8b0d5df774247…` |
| `repo/pipeline/vendor_browser_gate_v3.py` | 12,617 | `1b053e89396e5097…` |
| `repo/pipeline/vendor_welsh_gates.py` | 10,040 | `76965b626bcc5da1…` |
| `repo/pipeline/vendor_welsh_gates17.py` | 12,169 | `79ce5e862ace4861…` |
| `repo/pipeline/vendor_welsh_gates_v3.py` | 15,338 | `47d8a5c534e53c9c…` |
| `repo/pipeline/vendor_welsh_gates_v4.py` | 51,935 | `2eb392bf4a1e21ff…` |
| `repo/pipeline/vendor_welsh_gates_v5.py` | 68,574 | `3d562f9d129a1e13…` |
| `repo/pipeline/vendor_welsh_gates_v6.py` | 78,580 | `127c9ae601cea838…` |
| `repo/pipeline/vendor_welsh_gates_v7.py` | 98,787 | `f036f5af4c6bd3cf…` |
| `repo/pipeline/vendor_welsh_gates_v8.py` | 101,982 | `3057fef25b5d54bd…` |
| `repo/pipeline/welsh.py` | 27,692 | `adb6ceb9be7aa673…` |
| `repo/pipeline/welsh_gates.py` | 3,668 | `0a07dc30f2d4ee36…` |
| `repo/pipeline/welsh_gates2.py` | 7,655 | `6c11ac425bbe3b49…` |
| `repo/pipeline/welsh_gates3.py` | 3,143 | `4796bf96b172a768…` |
| `repo/pipeline/welsh_gates4.py` | 2,989 | `36766b2449f04579…` |
| `repo/pipeline/welsh_gates5.py` | 4,286 | `d84a449d748ad87c…` |
| `repo/pipeline/welsh_gates6.py` | 5,017 | `c33d01cf841f504c…` |
| `repo/pipeline/welsh_gates7.py` | 8,919 | `9a8d2c62b1918e0a…` |
| `repo/pipeline/welsh_gates8.py` | 12,735 | `5f938bf82c1d9d19…` |
| `repo/pipeline/welsh_payload.py` | 5,609 | `376f2b33f36c2f31…` |
| `repo/pipeline/welsh_render.py` | 87,274 | `4f7e39c988c6cd30…` |
| `repo/sw-feedback-compliance-record.md` | 126,082 | `f1b7e7d8d111255a…` |
| `repo/tests/__init__.py` | 0 | `e3b0c44298fc1c14…` |
| `repo/tests/browser/__init__.py` | 0 | `e3b0c44298fc1c14…` |
| `repo/tests/browser/render_probe.py` | 3,321 | `ebc8555aaceb7e02…` |
| `repo/tests/fixtures/synthetic.xlsx` | 9,715 | `070b632d5847ee14…` |
| `repo/tests/jsdom/jsdom_provenance.js` | 9,855 | `df7cafee848776e9…` |
| `repo/tests/jsdom/jsdom_test.js` | 20,052 | `fce8189744fc32fd…` |
| `repo/tests/jsdom/make_mini.py` | 1,384 | `815c1d694e9ae378…` |
| `repo/tests/make_synthetic_fixture.py` | 7,031 | `84c80a88bc7b0499…` |
| `repo/tests/test_pipeline.py` | 11,592 | `8a0ea7df4367530a…` |
| `repo/tests/test_static_blocks_v410.py` | 2,745 | `60e6bfb21102001e…` |
| `repo/tests/test_v27_translator_rulings.py` | 3,441 | `bc85116d4e75fa0e…` |
| `repo/tests/test_welsh.py` | 11,244 | `c706aa370af0e762…` |
| `repo/web/app.js` | 77,955 | `78383fd000b79e71…` |
| `repo/web/template.html` | 84,543 | `7ba8066757455f37…` |
