# SSS2026 Interactive Learning Report — V5.0 real-school round (21 September 2026)

Three school-level bilingual reports built from the genuine cleansed 2026 response data, by the
V4.15 final prototype's pipeline, framework, gates and assurance — one primary school, one secondary
school and one 3–18 school. This document is the key record of the round: what was built, from what,
how it was checked, and what the real data exposed. The compliance record
(`sw-feedback-compliance-record.md`, entry "Build V5.0") carries the audit trail; Framework v2.8
sheet 63 and `generated/SSS2026_V5.0_Flags_for_confirmation.md` carry every open question.

## 1. The three schools

| School | Id | Authority · Sport Partnership | Type · years | Responses accepted (of the analytical set) | Response rate (PLASC Y3–11 roll) |
|---|---|---|---|---|---|
| New Inn Primary School | 6782320 | Torfaen · Gwent Sport Partnership [GSP] | primary, Years 3–6 | 272 of 272 (251 complete, 21 partial) | 97% of 281 |
| Castell Alun High School | 6644017 | Flintshire · Actif North Wales | secondary, Years 7–11 | 771 of 771 (747 complete, 24 partial) | 74% of 1,042 |
| Ysgol Bro Pedr | 6675500 | Ceredigion · Mid Wales Sport Partnership [MWSP] | 3–18 (combined), Years 3–11 | 439 of 439 (396 complete, 43 partial) | 66% of 666 |

Selection: one school of each type the design supports (primary, secondary, combined — the same
profile family as the prototype school), three different local authorities and Sport Partnerships,
English-medium and Welsh-medium, every year group taught present with at least 14 responses (well above
the rule-of-five threshold), no PLASC over-roll, impossible-year or serial-cluster flags, and a local
authority and partnership that Framework sheet 53 already carries in Welsh. The prototype school
(Ysgol Penrhyn Dewi, 6685900) is in the same dataset and was used to validate the data adapter
(§3), not as one of the three.

Report versions `2026-school-V5.0-bilingual` · pipeline 0.28.0 · Framework v2.8 · gate pack v8
(unchanged: runner sha256 3057fef2…, manifest c4221bba2cff4dcb) · review builds (dev mode banner),
as V4.15.

## 2. What the reports are built from

The **cleansed pupil dataset**: Industryline cleansing handover v2.3 (9 Sep 2026),
`01_cleaned_files/SSS2026_pupil_stage2_full_cleaned.parquet` (Stage 2 v2, 121,937 × 1,624; sha256
802eda98…), from `C:\Users\ASHow\Downloads\SSS2026 Data cleansing and pupil data\`
(`SSS2026_pupil_cleansing_handover_v2.3_2026-09-09.zip`; CLEANED_FILES_SHA256SUMS verified). Its
analytical set is "completed OR partial reaching page 48+" (the data owner's inclusion rule); every
row of a school's analytical set is accepted (profile `acceptedStatuses`), and the validation summary
states the complete/partial split.

The **data adapter** `pipeline/cleansed_to_export.py` writes one school's rows in the prototype's
SmartSurvey "Responses wide" layout (the ten sport tick questions and the "other sports" pages, the
setting grids, the four frequency grids, the enjoyment, confidence and PE-feeling grids, the fixed
multi-selects, the routed take-part and Welsh questions) so the loader, derivations, engine,
narrative, Welsh generation and gates run unchanged. Every value is a codebook label copied through;
every sport label is the live survey's own option text (S16, the SmartSurvey master import); free
text is withheld ("Other" becomes the bare prefix the loader already recodes). The export is
reproducible byte for byte (pinned timestamps), its sha256 is the build's `sourceChecksum`, and it is
input data: it stays beside the dataset, never in generated output, a kit or the repository.

**Validation of the adapter on the prototype school.** Its 391 analytical rows (366 complete +
25 partial) converted and loaded through the unchanged V4.15 loader give 366 records whose every
distribution — year, sex, disability, learning difficulty, Welsh, ethnicity and the ethnically-diverse
flag, join-in, ideas-listened, the three grids, settings, sports, demand, unmet demand, both
square-root frequency estimates, any-activity — equals the original SmartSurvey export's, except
for the cleansing team's own documented corrections: R26-02 (seven "None of these" co-selections set
to 0: `more_if` 56→53, `important` 14→10) and R26-01 (one PE setting cell for obstacle course racing
recoded: composite 79→78). The dataset codes a detail answer typed through the "Any other …" text box
as "Other (free text)"; the adapter restores the category the pupil ticked (the owner rule counts the
category, never the text) — verified: the prototype school's 11 such rows are exactly its 11
"Any other White background / …" answers.

## 3. What changed to run the prototype on real schools (pipeline 0.28.0, Framework v2.8)

* **Per-school profile** (`config/schools/<slug>.json`): name, id, authority, partnership, stages,
  the years taught and the scope groups offered (a primary school lists Whole school + Years 3–6; a
  secondary school Whole school + Years 7–11; a combined school the prototype's twelve), accepted
  statuses, the dataset reference. Chosen with `SSS_SCHOOL_PROFILE`; the output tree with
  `SSS_GENERATED_DIR`. The twelve internal scopes are still computed (structural year sets); the
  filter offers the profile's groups; the responses-by-year chart shows the school's years.
* **Framework v2.8** (`pipeline/make_framework_v28.py`, from v2.7 and S16; change log sheet 62,
  flags sheet 63): twelve sheet-23 sport rows the live survey offers and the prototype export did
  not contain (Baton Twirling … Softball), Welsh read from S16, features PROVISIONAL (PR-20, by the
  translator-confirmed rules PR-01/PR-05 and sibling rows); the year range fixed in two sheet-43
  frames becomes the `{first}`/`{last}` slots (EN-06/EN-07, digits only — the V4.11 note had raised
  exactly this "before other schools are built"); EN-08 pending owner (§4). On the V4.15 prototype the
  workbook reproduces the V4.15 corpus: **0 of 8,568 states moved**, English and Welsh, the emitted
  lock byte-equal to `02c_lock_V415_v8.json` in all three parts (regression build, below).
* **Corpus locks per school** (D82): a school's first build asserts against no earlier lock
  (`SSS_PREVIOUS_LOCK=none`; GOV-lock is REPORT for that run) and EMITS the school's own lock
  (`lock_<slug>_v8.json`), which the bundle's reruns then assert (GOV-lock-cy, FT11-keyset) and any
  rebuild must reproduce or cite a ruling.
* **Held cohorts** (`config/held_cohorts.json`): four answer groups whose qualifier has no Welsh
  relative clause on sheet 22 are not offered as filters — the bar keeps its count and shows "This
  value cannot be selected as a filter" (the report's existing behaviour for groups under the
  rule-of-five cap). The validation summary names each hold where it bites.
* **Six Welsh renderers** wrote a plural complement after a singleton subject in a nil-count
  sentence about ONE pupil (AGR-possessive / AGR-verb at real schools); they now use the singular the
  one-pupil count already uses (D48 pronoun-free forms; PR-03 impersonal negated for a sex-less view).
  The V4.15 corpus is unchanged.
* **Per-school assurance**: `pipeline/make_school_bundle.py` (the V4.15 bundle procedure per build
  tree), `pipeline/verify_school.py` (independent recomputation of the whole-school figures from the
  parquet, its own code path), `tests/jsdom/jsdom_school.js` (a school-agnostic jsdom regression whose
  every expectation is derived from the payload), the render probe on the school's own page.

## 4. What the real data exposed — held, never patched

1. **Missing Welsh qualifiers (four cohorts held).** "reported no sport in any setting" (ov),
   "identified with other ethnic groups" (et), "preferred not to say how they take part in sport" and
   "with communication aids" (tp): groups the prototype school had fewer than five pupils in, so the
   rows were never written. Welsh is never composed in code (D44). Translator: four sheet-22 rows.
2. **A one-pupil form missing from three locked English templates (EN-08).** Module f10's
   `leader_multi_v2` (a unique leader on a base of one), `group_codemand_top3_v12` and
   `wd_current_check_v3` produce "1 of the 1 pupil …", which the build's own English gate rejects.
   A sentence they would produce that the gate rejects is held (not rendered, not audited, logged);
   every sentence the gate accepts — ties, definition sentences, and the forms the V4.15 corpus already
   contains ("1 of the 1 boy …", "the 1 Year 3 pupil …") — is reproduced unchanged under the lock.
   Report owner: sanction one-pupil forms (sheet 49, EN-08).
3. **Singleton-antecedent agreement** in nil-count Welsh sentences (fixed as above, only for
   constructions the V4.15 corpus does not contain; the translator is asked to confirm the negated
   singular constructions, and to rule on the attested forms left as V4.15 has them — "un o’r 20
   disgybl … nad ydynt" and the PR-02 recast topic "… ynghylch gwrando ar eu syniadau").
4. **Partial responses**: counted as included per the data owner's rule; the profile charts' base line
   still reads "(complete survey response)". Sport Wales to confirm.
5. **Proper names**: four authorities spelt differently from sheet 53 (none of the three schools);
   the "School Stages Covered" values and the derived Sport Partnership have no Welsh/confirmation.

## 5. Assurance — every check the V4.15 prototype ran, per school

| School | Type / years | Responses (accepted) | States (visible) | Paragraphs | QA stamp | Reruns dev · release · paths | Lock = baseline | Figures verified | jsdom | Provenance EN/CY/typo | A4 pages EN/CY | Report (bytes, sha256) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| New Inn Primary School (Torfaen) | primary, Years 3–6 | 272 of 272 (251 complete, 21 partial) | 8100 (4050) | 146,589 | 69/72, paths 17/18 | 71/72 · 72/75 · 17/18 | yes | yes | 40/40 | 0 / 0 / 0 | 57 / 61 | 97,769,042 · 667c5a11d51ba7d2… |
| Castell Alun High School (Flintshire) | secondary, Years 7–11 | 771 of 771 (747 complete, 24 partial) | 8496 (4956) | 196,239 | 69/72, paths 17/18 | 71/72 · 72/75 · 17/18 | yes | yes | 40/40 | 0 / 0 / 0 | 60 / 64 | 129,750,270 · 9a5f52babd927046… |
| Ysgol Bro Pedr (Ceredigion) | combined, Years 3–11 | 439 of 439 (396 complete, 43 partial) | 8496 (8496) | 278,136 | 69/72, paths 17/18 | 71/72 · 72/75 · 17/18 | yes | yes | 40/40 | 0 / 0 / 0 | 60 / 64 | 182,163,805 · 005f276e9a8a7767… |

(Generated by `tools/school_round_summary.py`.) QA PASS with the same stamp as the prototype (69/72 blocking, pending GOV-rerun/GOV-bundle,
disputed STK-caption-case; renderer paths 17/18); stock reruns on the shipped file dev 71/72 ·
release 72/75 (the same three known items as V4.15: STK-caption-case, CAT-values 72, GOV-mode) · paths
17/18; the rerun's emitted lock equal to the school's baseline in all three parts; independent
recomputation of the whole-school figures from the dataset: all match; jsdom school regression
40/40 (English and Welsh, slots, scopes, held bars, language switch, accessibility switch);
provenance port 0 / 0 / 0, toggle 0 failures over 1,152; Chromium render probe (A4 page counts above;
cover, rail, profile table and year chart checked by eye); pytest 86 passed / 1 skipped after every
pipeline change. The f10 hold bit in five views at Ysgol Bro Pedr and nowhere else.

**Prototype regression under the final workbook and code**: the V4.15 export rebuilt with
Framework v2.8 and pipeline 0.28.0 — all 8,568 states byte-identical to the shipped V4.15 package,
emitted lock equal to `02c_lock_V415_v8.json` (english, welsh, ft11), QA PASS 69/72, paths 17/18.

## 6. Rebuild instructions

    # 0. the dataset (never copied into the repository or a kit)
    P="<…>/SSS2026_pupil_cleansing_handover_v2.3_2026-09-09/01_cleaned_files/SSS2026_pupil_stage2_full_cleaned.parquet"
    # 1. Framework v2.8 and the lexicon (reproducible from v2.7 + S16)
    python -m pipeline.make_framework_v28 config/01_Framework_v2.7.xlsx config/S16_Translations_MASTER_v6_English_import.xlsx config/01_Framework_v2.8.xlsx
    python -m pipeline.build_welsh_lexicon config/01_Framework_v2.8.xlsx config/SSS2026_Welsh_Translation_Handoff_V4.15.xlsx
    python -m pytest tests -q                                            # 86 passed, 1 skipped
    # 2. one school, end to end (export → staged build → QA with the school's lock emitted → single file)
    ./build_school.sh new-inn-primary-school 6782320 "$P" <private inputs dir> <yac assets dir> <fonts dir> <work root>
    # 3. the assurance bundle and reruns, the independent figure check, the jsdom and render checks
    SSS_GENERATED_DIR=<work root>/new-inn-primary-school/generated python -m pipeline.make_school_bundle new-inn-primary-school V5.0
    python -m pipeline.verify_school "$P" config/schools/new-inn-primary-school.json <…>/new-inn-primary-school.report.json out.json
    REPORT=<…>/new-inn-primary-school.report.json python -m tests.jsdom.make_mini <wd>
    JSDOM=<node_modules/jsdom> WD=<wd> node tests/jsdom/jsdom_school.js
    JSDOM=<node_modules/jsdom> WD=<wd> node tests/jsdom/jsdom_provenance.js
    python -m tests.browser.render_probe <wd> <probe dir>
    # 4. a rebuild of the same school asserts against its emitted lock
    SSS_PREVIOUS_LOCK=<…>/lock_new-inn-primary-school_v8.json ./build_school.sh …

The same commands with `castell-alun-high-school 6644017` and `ysgol-bro-pedr 6675500`.

## 7. Data handling

The pupil-level export each report was built from is input data: it lives beside the dataset on the
owner's machine (and in the build's private working tree), never in `generated/`, a bundle, a kit or
the repository (`.gitignore`: `*cleansed_export*.xlsx`, `*.parquet`). The shipped artefacts carry
aggregates and narrative only, under the report's disclosure model (view-level rule of five), plus
the export's sha256 as provenance.
