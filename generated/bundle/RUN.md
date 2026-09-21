# V4.15 assurance bundle — one command reproduces everything (D81, sheet 52)

Ships beside `SSS2026_ILR_Report_V4.15_Bilingual.html`. `manifest.json` lists the runner, framework,
baseline, phase-1 evidence, browser harness and the report with their sha256 values; the runner,
framework, baseline and evidence hashes equal the values stamped in the report's
`buildMetadata.gateResults` / `identity`. Prerequisites: Python 3.10+, `pip install openpyxl`; for the
browser gate `pip install playwright && playwright install chromium`.

    cd <this directory>
    python welsh_acceptance_gates_v8.py --selftest                                    # 68/68 + CONJ-06 modes OK
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V4.15_Bilingual.html --framework 01_Framework_v2.7.xlsx \
        --mode dev     --baseline lock_V415_v8.json --bundle-dir . --json results_dev.json \
        --evidence evidence_rerun_dev.ndjson.gz --emit-lock lock_V415_v8_emitted.json
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V4.15_Bilingual.html --framework 01_Framework_v2.7.xlsx \
        --mode release --baseline lock_V415_v8.json --bundle-dir . --json results_release.json \
        --evidence evidence_rerun_release.ndjson.gz
    python write_verify.py ../SSS2026_ILR_Report_V4.15_Bilingual.html results_release.json results_dev.json
    python browser_gate_provenance.py ../SSS2026_ILR_Report_V4.15_Bilingual.html --states 60 --fixture auto --json browser_gate.json

Gate pack v8 (V4.15): the v7 pack with ONE change — CONJ-06 (a/ac before a figure) is asserted against
the reading the Framework names on sheet 11 (`MODE=figure`, the translator's ruling of 21 Sep 2026,
D84) instead of the fixed vigesimal reading; the gate keeps its id, the manifest hash is unchanged
(c4221bba2cff4dcb), the self-test adds one seeded case per mode. The runner's sha256 is in the manifest.

Baseline (D82): `lock_V415_v8.json` was RE-EMITTED from the V4.15 build after the translator's rulings
moved the Welsh corpus (4,201 of 8,568 states) — `pipeline/welsh_gates8.emit_lock` asserted, before
emission, that the ENGLISH projection and the FT-11 key set equal the previous lock's
(`lock_V48_v7.json`, the baseline of every earlier V4 build); the lock records the ruling and the count under `emitted`.

Two-phase stamp (D81): the build ran the vendored, byte-identical v8 runner on the unstamped package,
stamped `gateResults {blockingPass, blockingTotal, headline, pending, disputed}`, and the runs above
re-run the same runner on the stamped file with the bundle asserted. `verify.json` is written from
that rerun and is the only statement of the final status. Expected on this file: dev 71/72 (the one
failure is STK-caption-case, disputed — see below), release 72/75 (adds CAT-values 72 — the engine- and
client-owned catalogue rows that carry no Welsh value, the translator's lane is complete — and GOV-mode,
the owner's unsigned D69), renderer paths 17/18 (the same disputed emulation marks UI-DYN-16 partial),
`lock_V415_v8_emitted.json` equal to `lock_V415_v8.json` in all three locked parts (english, welsh, ft11),
and its `english` and `ft11` parts equal to `lock_V48_v7.json`'s.

Notes on the pack as shipped (raised with the pack owners, V4.15 register):

* `evidence.ndjson.gz` is the PHASE-1 evidence the build wrote (its sha256 is the stamp's
  `evidenceSha256` and the manifest's). The reruns therefore write their evidence to
  `evidence_rerun_*.ndjson.gz` — the command on sheet 52 (`--evidence evidence.ndjson.gz`) would
  overwrite the manifest-listed file and make every later rerun fail GOV-bundle.
* The emitted lock is written under its own name (`_emitted`) because the baseline it is compared
  with is this version's own lock; writing it over the baseline would fail GOV-bundle on the rerun.
* The runner does not write `verify.json`; `write_verify.py` states the rerun's result next to the
  report's sha256 and computes nothing.
* STK-caption-case substitutes the countNP table entry into the caption frame without applying the
  slot's `initial` casing role, so with the lexical table sheet 50 / CNP-lexical require it cannot
  pass; the client applies the role and every rendered caption is capitalised (browser gate:
  0 lower-case-initial captions). The stamp names the gate as disputed.
* The browser gate's collection, classification, typography and fixture-toggle logic was executed
  under jsdom (`V4.15_browser_gate_jsdom.json`: 0 / 0 / 0, toggle 0 failures); the Chromium render
  probe (`tests/browser/render_probe.py`) rendered the mini page in both languages (61 / 65 A4 pages).
