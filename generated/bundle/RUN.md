# V4.18 assurance bundle — one command reproduces everything (D81, sheet 52)

Ships beside `SSS2026_ILR_Report_V4.18_Bilingual.html`. `manifest.json` lists the runner, framework,
baseline, phase-1 evidence, browser harness and the report with their sha256 values; the runner,
framework, baseline and evidence hashes equal the values stamped in the report's
`buildMetadata.gateResults` / `identity`. Prerequisites: Python 3.10+, `pip install openpyxl`; for the
browser gate `pip install playwright && playwright install chromium`.

    cd <this directory>
    python welsh_acceptance_gates_v8.py --selftest                                    # 68/68 + CONJ-06 modes OK
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V4.18_Bilingual.html --framework 01_Framework_v2.11.xlsx \
        --mode dev     --baseline lock_V418_v8.json --bundle-dir . --json results_dev.json \
        --evidence evidence_rerun_dev.ndjson.gz --emit-lock lock_V418_v8_emitted.json
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V4.18_Bilingual.html --framework 01_Framework_v2.11.xlsx \
        --mode release --baseline lock_V418_v8.json --bundle-dir . --json results_release.json \
        --evidence evidence_rerun_release.ndjson.gz
    python write_verify.py ../SSS2026_ILR_Report_V4.18_Bilingual.html results_release.json results_dev.json
    python browser_gate_provenance.py ../SSS2026_ILR_Report_V4.18_Bilingual.html --states 60 --fixture auto --json browser_gate.json

V4.18 is V4.17 (the Young Artists Competition artwork, the described accessibility switch, the print
page breaks, pipeline 0.29.1) with the owner's instructions of 22 Sep 2026 (EN-09, Framework v2.11
sheet 49): the Club Sports section is removed from the report (module d2 no longer generated, the
club-estimate cb_* selected groups gone, the appendix table gone, five static rows retired to the V4.18
handoff); and under a SETTING selection ("Where are our pupils taking part in Sport?") the
weekly-frequency chart keeps the wider picture — the demographic view's bars, still selectable,
announced as "Showing: <view>" — and its narrative leads with the selected-group definition sentence
(template group_defined_v2, wording unchanged). Pipeline 0.30.0.

Gate pack v8 (unchanged since V4.15): the v7 pack with ONE change — CONJ-06 (a/ac before a figure) is
asserted against the reading the Framework names on sheet 11 (`MODE=figure`, the translator's ruling of
21 Sep 2026, D84) instead of the fixed vigesimal reading; the gate keeps its id, the manifest hash is
unchanged (c4221bba2cff4dcb), the self-test adds one seeded case per mode. The runner's sha256 is in
the manifest.

Baseline (D82): `lock_V418_v8.json` was EMITTED from the V4.18 build under EN-09 (it supersedes the
V4.15 lock; the English moves by the ruling — every state loses its d2 paragraphs, the 288 cb_* states
go, and each of the 140 visible st_* states gains one definition paragraph in d0; every other paragraph
is byte-identical to V4.17, proven state by state in the V4.18 record). The dev rerun above re-emits it
as `lock_V418_v8_emitted.json`, equal to the baseline in all three locked parts; neither its `english`
part nor its FT-11 key set equals `lock_V48_v7.json`'s any more (EN-09: the FT-11 set is 837 keys against
1,013 — the 132 keys of the removed cb_* states and the 44 keys of removed d2 paragraphs are gone, none
added).

Two-phase stamp (D81): the build ran the vendored, byte-identical v8 runner on the unstamped package,
stamped `gateResults {blockingPass, blockingTotal, headline, pending, disputed}`, and the runs above
re-run the same runner on the stamped file with the bundle asserted. `verify.json` is written from
that rerun and is the only statement of the final status. Expected on this file: dev 71/72 (the one
failure is STK-caption-case, disputed — see below), release 72/75 (adds CAT-values 72 — the engine- and
client-owned catalogue rows that carry no Welsh value, the translator's lane is complete — and GOV-mode,
the owner's unsigned D69), renderer paths 17/18 (the same disputed emulation marks UI-DYN-16 partial),
`lock_V418_v8_emitted.json` equal to `lock_V418_v8.json` in all three locked parts (english, welsh, ft11).

Notes on the pack as shipped (raised with the pack owners, V4.9–V4.18 register):

* `evidence.ndjson.gz` is the PHASE-1 evidence the build wrote (its sha256 is the stamp's
  `evidenceSha256` and the manifest's). The reruns therefore write their evidence to
  `evidence_rerun_*.ndjson.gz` — the command on sheet 52 (`--evidence evidence.ndjson.gz`) would
  overwrite the manifest-listed file and make every later rerun fail GOV-bundle.
* The emitted lock is written under its own name (`lock_V418_v8_emitted.json`), never over the
  baseline it is compared with.
* The runner does not write `verify.json`; `write_verify.py` states the rerun's result next to the
  report's sha256 and computes nothing.
* STK-caption-case substitutes the countNP table entry into the caption frame without applying the
  slot's `initial` casing role, so with the lexical table sheet 50 / CNP-lexical require it cannot
  pass; the client applies the role and every rendered caption is capitalised (browser gate:
  0 lower-case-initial captions). The stamp names the gate as disputed.
* No gate in the pack tests a sheet-43 frame for an EMPTY Welsh value (CAT-values walks the handoff
  catalogue; PUB-empty the rendered narrative surfaces): the sixteen pending frames of this build
  (fourteen `ui.alt_yac_*`, `ui.a11y_switch_desc`, `ui.a11y_glossary_heading`) render as marked English
  in Welsh mode and would not by themselves fail a release run — raised for the pack owners (V5.0
  reviewer assessment).
* The browser gate's collection, classification, typography and fixture-toggle logic was executed
  under jsdom (`V4.18_browser_gate_jsdom.json`: 0 / 0 / 0, toggle 0 failures); the Chromium render
  probe rendered the mini page with the artwork embedded in both languages (62 / 65 A4 pages; 99 with
  the accessibility switch on), including the weekly-frequency chart and its narrative under a setting
  selection, and every page was checked by eye.
