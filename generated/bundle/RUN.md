# V4.17 assurance bundle — one command reproduces everything (D81, sheet 52)

Ships beside `SSS2026_ILR_Report_V4.17_Bilingual.html`. `manifest.json` lists the runner, framework,
baseline, phase-1 evidence, browser harness and the report with their sha256 values; the runner,
framework, baseline and evidence hashes equal the values stamped in the report's
`buildMetadata.gateResults` / `identity`. Prerequisites: Python 3.10+, `pip install openpyxl`; for the
browser gate `pip install playwright && playwright install chromium`.

    cd <this directory>
    python welsh_acceptance_gates_v8.py --selftest                                    # 68/68 + CONJ-06 modes OK
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V4.17_Bilingual.html --framework 01_Framework_v2.10.xlsx \
        --mode dev     --baseline lock_V415_v8.json --bundle-dir . --json results_dev.json \
        --evidence evidence_rerun_dev.ndjson.gz --emit-lock lock_V417_v8.json
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V4.17_Bilingual.html --framework 01_Framework_v2.10.xlsx \
        --mode release --baseline lock_V415_v8.json --bundle-dir . --json results_release.json \
        --evidence evidence_rerun_release.ndjson.gz
    python write_verify.py ../SSS2026_ILR_Report_V4.17_Bilingual.html results_release.json results_dev.json
    python browser_gate_provenance.py ../SSS2026_ILR_Report_V4.17_Bilingual.html --states 60 --fixture auto --json browser_gate.json

V4.17 is V4.16 (the Young Artists Competition artwork, Framework v2.9) with: the accessibility switch
made larger and more obvious and given a description a screen reader announces with it (new sheet-43
frame `ui.a11y_switch_desc`, Framework v2.10 — English; Welsh pending the translator); print rules so
that every page of the report starts on a new printed page and no heading ends one; the dragon-in-kit
and Welsh-symbols images swapped (the introduction carries one image, at its foot) and the footballer
moved to the appendix heading; and pipeline 0.29.1's loader rule (an off-route take-part answer is not
carried — it bites at no prototype respondent). No narrative surface, static row, label or client
string changed.

Gate pack v8 (unchanged since V4.15): the v7 pack with ONE change — CONJ-06 (a/ac before a figure) is
asserted against the reading the Framework names on sheet 11 (`MODE=figure`, the translator's ruling of
21 Sep 2026, D84) instead of the fixed vigesimal reading; the gate keeps its id, the manifest hash is
unchanged (c4221bba2cff4dcb), the self-test adds one seeded case per mode. The runner's sha256 is in
the manifest.

Baseline (D82): `lock_V415_v8.json` — the V4.15 corpus lock — is the baseline of this build, unchanged:
the build's QA asserted the English and Welsh projections and the FT-11 key set against it (GOV-lock,
GOV-lock-cy PASS), and the dev rerun above emits `lock_V417_v8.json`, which is byte-equal to the locks
the V4.15 and V4.16 reruns emitted (sha256 16faa6a5…) and equal to the baseline in all three locked parts.

Two-phase stamp (D81): the build ran the vendored, byte-identical v8 runner on the unstamped package,
stamped `gateResults {blockingPass, blockingTotal, headline, pending, disputed}`, and the runs above
re-run the same runner on the stamped file with the bundle asserted. `verify.json` is written from
that rerun and is the only statement of the final status. Expected on this file: dev 71/72 (the one
failure is STK-caption-case, disputed — see below), release 72/75 (adds CAT-values 72 — the engine- and
client-owned catalogue rows that carry no Welsh value, the translator's lane is complete — and GOV-mode,
the owner's unsigned D69), renderer paths 17/18 (the same disputed emulation marks UI-DYN-16 partial),
`lock_V417_v8.json` equal to `lock_V415_v8.json` in all three locked parts (english, welsh, ft11),
and its `english` and `ft11` parts equal to `lock_V48_v7.json`'s.

Notes on the pack as shipped (raised with the pack owners, V4.9–V4.17 register):

* `evidence.ndjson.gz` is the PHASE-1 evidence the build wrote (its sha256 is the stamp's
  `evidenceSha256` and the manifest's). The reruns therefore write their evidence to
  `evidence_rerun_*.ndjson.gz` — the command on sheet 52 (`--evidence evidence.ndjson.gz`) would
  overwrite the manifest-listed file and make every later rerun fail GOV-bundle.
* The emitted lock is written under this version's own name (`lock_V417_v8.json`), never over the
  baseline it is compared with.
* The runner does not write `verify.json`; `write_verify.py` states the rerun's result next to the
  report's sha256 and computes nothing.
* STK-caption-case substitutes the countNP table entry into the caption frame without applying the
  slot's `initial` casing role, so with the lexical table sheet 50 / CNP-lexical require it cannot
  pass; the client applies the role and every rendered caption is capitalised (browser gate:
  0 lower-case-initial captions). The stamp names the gate as disputed.
* No gate in the pack tests a sheet-43 frame for an EMPTY Welsh value (CAT-values walks the handoff
  catalogue; PUB-empty the rendered narrative surfaces): the sixteen pending frames of this build
  (fourteen `ui.alt_yac_*`, `ui.a11y_switch_desc`, `ui.a11y_glossary_heading`) render as marked English in Welsh mode and
  would not by themselves fail a release run — raised for the pack owners (V5.0 reviewer assessment).
* The browser gate's collection, classification, typography and fixture-toggle logic was executed
  under jsdom (`V4.17_browser_gate_jsdom.json`: 0 / 0 / 0, toggle 0 failures); the Chromium render
  probe rendered the mini page with the artwork embedded in both languages (64 / 67 A4 pages; 102
  with the accessibility switch on): every report page starts a printed page, no page ends with a
  heading, and every placement was checked by eye.
