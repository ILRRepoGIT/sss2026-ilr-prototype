# School Sport Survey 2026 — Interactive Learning Report (bilingual)

## Status at 22 September 2026

**Production infrastructure: V6.0 (22 Sep 2026, branch `production/v6.0`, tag `v6.0-rc1`) — pipeline 0.31.0, Framework v2.13.** The machinery that builds every eligible school's report from the finalised Stage 2 dataset and publishes it under an unguessable link on `reports.schoolsportsurvey2026.co.uk`: `prod/` (register, runner, served package, checks, publication), `infra/` (the Azure estate as CLI steps and Bicep, the VM bootstrap), `docs/production/` (the provisioning guide for the colleague setting up Azure and the operations runbook), `docs/SSS2026_ILR_Key_Documents_V6.0.md` (the key record), compliance-record entry "Build V6.0". The three V5.3 schools rebuilt through the runner assert against their V5.3 locks with 0 states moved; nothing in a report changed.

The build is complete to the owner's instructions of 22 September 2026. **Prototype V4.19** (Framework v2.12, pipeline 0.30.0, corpus lock `config/02c_lock_V418_v8.json`) and the **real-school round V5.3** (New Inn Primary School, Castell Alun High School, Ysgol Bro Pedr — each with its own lock) are the current builds; every earlier build is recorded and tagged (`v4.15` … `v4.19`, `v5.0` … `v5.3`). What this repository holds: the pipeline (`pipeline/`), the page and client (`web/`), the Framework workbooks v2.1–v2.12 and the translator's handoffs (`config/`), the corpus locks, the tests (pytest 103, jsdom 123 prototype / 40 per school, the provenance port, the Chromium render probe), the assurance bundle of the current prototype (`generated/bundle/`), the per-round evidence (`docs/`), the artwork pack (`inputs/`) and the full audit trail (`sw-feedback-compliance-record.md`, `LIMITATIONS.md`). The report files themselves (170 MB and 93–172 MB) are build outputs reproduced from this repository and the exports by the recorded commands; they are not committed (GitHub's 100 MB limit) and are delivered with their sha256 beside them.

What is proven for the current builds: the English narrative is locked (every state byte-identical to the V4.18 ruling's corpus; the only sanctioned change since V4.1 is EN-09, recorded on Framework sheet 49 with its state-by-state proof); every Welsh string comes from the Framework workbook or the translator's handover (nothing composed in code); the stock gate pack v8 passes 69/72 in the build stamp and 71/72 · 72/75 in the bundle reruns, the three remaining items being the known ones (the disputed STK-caption-case pack defect, the 72 engine-owned catalogue rows, the unsigned D69); the whole-school figures of every real school are recomputed independently from the dataset and match; no pupil-level data is in the repository or in any deliverable.

What remains open, and with whom (the current flags file is `generated/SSS2026_V4.19_Flags_for_confirmation.md`): the translator — two sheet-43 frames (`ui.a11y_switch_desc`, `ui.a11y_glossary_heading`); the owner — the provenance of the fourteen Welsh alt texts, EN-10 (the chapter-summary club-sport sentence), the PDF page granularity; Sport Wales — O09/O10 (the view-level rule of five) and D69, publication approval and credit for the artwork, the off-route partial-response query (with the cleansing team). Builds stay review builds (dev mode) until D69 and the disclosure items are signed — that is the release rule, not a defect.

**Current prototype: V4.19 (22 Sep 2026) — against Framework v2.12, pipeline 0.30.0.** V4.18 with the fourteen Welsh alt texts for the Young Artists Competition artwork (supplied by the owner on 22 Sep 2026, entered verbatim on Framework sheet 43 — provenance to confirm, sheet 71): in the Welsh report every picture is described in Welsh and its accessibility-mode caption is Welsh; two frames remain pending with the translator (`ui.a11y_switch_desc`, `ui.a11y_glossary_heading`). No English changed; all 8,280 states byte-identical to V4.18; GOV-lock asserted against the V4.18 lock (`generated/SSS2026_V4.19_state_diff_vs_V4.18.json`). The record is the "Build V4.19" entry of `sw-feedback-compliance-record.md`; the open questions `generated/SSS2026_V4.19_Flags_for_confirmation.md`.

**V4.18 (22 Sep 2026) — Framework v2.11, pipeline 0.30.0 — the owner's instruction recorded as EN-09** (Framework sheet 49): the Club Sports section removed from the report (module d2, the club-estimate selected groups, the appendix table, five static rows retired to the V4.18 handoff with the translator's Welsh kept), and under a setting selection ("Where are our pupils taking part in Sport?") the weekly-frequency chart keeps the wider picture — the view's bars, still selectable — with its narrative leading with the selected-group definition sentence. The corpus lock moved by that ruling and by nothing else: 8,568 → 8,280 states (the 288 `cb_*` states gone), d2 gone from every visible state, one definition paragraph added to d0 in the 140 visible `st_*` states, every other paragraph byte-identical to V4.17 (`generated/SSS2026_V4.18_state_diff_vs_V4.17.json`); the lock re-emitted as `config/02c_lock_V418_v8.json`. Record: "Build V4.18"; flags `generated/SSS2026_V4.18_Flags_for_confirmation.md`; the artwork pack `inputs/yac images V4.16/`; the placements `config/assets.yml`.

**Real-school round: V5.3 (22 Sep 2026) — the three real-school reports rebuilt with the fourteen Welsh alt texts (Framework v2.12, pipeline 0.30.0, the V4.18 template).** Every school asserted against its V5.2 lock: 0 states moved (`docs/V5.3_schools/<slug>/lock_diff_V52_V53.json`). Round evidence in `docs/V5.3_schools/`; the record is the "Build V5.3" entry of `sw-feedback-compliance-record.md`. Earlier rounds: V5.2 (EN-09 applied to the schools — the `cb_*` states removed, d2 removed, the d0 definition added; `docs/V5.2_schools/`), V5.1 (pipeline 0.29.1, Framework v2.10 — Ysgol Bro Pedr's six `tp_other` states; `docs/V5.1_schools/`) and V5.0 (21 Sep 2026, Framework v2.8, pipeline 0.28.0; `docs/SSS2026_ILR_Key_Documents_V5.0.md`, `docs/V5.0_schools/`).

The V4.15 final prototype's pipeline, Framework and gates run unchanged on any school in the
cleansed dataset (Industryline cleansing handover v2.3): a per-school profile
(`config/schools/<slug>.json`), a data adapter that writes one school's rows in the prototype's
SmartSurvey layout (`pipeline/cleansed_to_export.py`, validated on the prototype school), a corpus
lock per school, Framework v2.8 (twelve live-survey sport labels from S16; the year range of two
frames as slots; on the prototype 0 of 8,568 states moved) and pipeline 0.28.0. Built: New Inn
Primary School (Torfaen, Years 3–6), Castell Alun High School (Flintshire, Years 7–11), Ysgol Bro
Pedr (Ceredigion, Years 3–11). What the real data exposed is held and flagged, never patched: four
cohorts whose Welsh qualifier the Framework does not carry, three f10 sentences with no one-pupil
form (EN-08), a singleton-agreement fault in nil-count Welsh sentences (fixed only where the V4.15
corpus has no such sentence). `./build_school.sh <slug> <id> <parquet> …` builds one school end to
end; `docs/SSS2026_ILR_Key_Documents_V5.0.md` is the key record; `sw-feedback-compliance-record.md`
("Build V5.0") the audit trail; `generated/SSS2026_V5.0_Flags_for_confirmation.md` the open questions.
The pupil-level exports are input data and never enter the repository.


---

**Previous build: V4.15 (21 Sep 2026) — the final prototype: the translator's completed handover applied, Framework v2.7, gate pack v8.**
Start with `docs/SSS2026_ILR_Key_Documents_V4.15.md` — the rulebook, the build identity and figures, the exact rebuild commands, the full feedback and compliance record (every round from Build 010 to V4.15), the deployment plan and the kit inventory. The V4.15 entry of `sw-feedback-compliance-record.md` is the record of this build.

What is here: `pipeline/` (data → fact records → English narrative locked to V4.1 → Welsh generated through the Framework workbook → single-file report), `web/` (template and client), `config/` (the Welsh Generation Framework v2.1–v2.12, the translation handoffs V4.10–V4.18, the translator's completed handover and document, corpus locks, metrics and narrative configuration), `tests/` (pytest, jsdom regression and provenance port, Chromium render probe), `generated/bundle/` (the V4.19 assurance bundle: vendored gate runner v8, framework, baseline lock, evidence, results, RUN.md), `tools/` (the translator-handover, label-query and fidelity-audit generators), `docs/` (key documents, deployment plan, accessibility register, render probe, earlier rounds' gate results), `inputs/` (fonts, the Young Artists Competition artwork pack, the retired character images, the translator's and the accessibility documents — the pupil-level export is deliberately excluded, see `inputs/README.md`).

The shipped reports (`SSS2026_ILR_Report_V4.19_Bilingual.html`, 169,614,714 bytes, sha256 923debbd97a99ccebb3cf72ccbecf361eca55302c10f2e34b93dbc712afa8e51; `SSS2026_ILR_Report_V4.18_Bilingual.html`, 169,612,636 bytes, sha256 c98de2619974354fe235c6ba658d7ac49f2cd752734bae2727824c805a4b3316; `SSS2026_ILR_Report_V4.17_Bilingual.html`, 180,866,975 bytes, sha256 44fb1f6ebc0e59445430ddb2680d4622761f3300d8bd5a63bda5963299b712d1; `SSS2026_ILR_Report_V4.16_Bilingual.html`, 180,863,609 bytes, sha256 4e565c3a7ad12404a956f6003fc3ee5bdd6cda63bcb7ca4e1ebe1e3838b8fb79; `SSS2026_ILR_Report_V4.15_Bilingual.html`, 179,534,432 bytes, sha256 dd5d9959d40c2ed417cdc8eeb937171ff50d3240b690c99583f462ba45891bfd) are build outputs reproduced from this repository and the export by the commands in the key documents §3; it is not committed (GitHub's 100 MB file limit) — see the release assets / the owner's Downloads and Data_Report_Outputs.

---

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
