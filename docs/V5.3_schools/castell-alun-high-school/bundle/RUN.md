# V5.3 assurance bundle — Castell Alun High School — one command reproduces everything (D81, sheet 52)

Ships beside `SSS2026_ILR_Report_V5.3_castell-alun-high-school_Bilingual.html`. `manifest.json` lists the runner, framework, baseline, phase-1 evidence, browser
harness and the report with their sha256 values; the runner, framework, baseline and evidence hashes equal
the values stamped in the report's `buildMetadata.gateResults` / `identity`. Prerequisites: Python 3.10+,
`pip install openpyxl`; for the browser gate `pip install playwright && playwright install chromium`.

    cd <this directory>
    python welsh_acceptance_gates_v8.py --selftest                                    # 68/68 + CONJ-06 modes OK
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V5.3_castell-alun-high-school_Bilingual.html --framework 01_Framework_v2.12.xlsx \
        --mode dev     --baseline lock_castell-alun-high-school_v8.json --bundle-dir . --json results_dev.json \
        --evidence evidence_rerun_dev.ndjson.gz --emit-lock lock_castell-alun-high-school_v8_emitted.json
    python welsh_acceptance_gates_v8.py ../SSS2026_ILR_Report_V5.3_castell-alun-high-school_Bilingual.html --framework 01_Framework_v2.12.xlsx \
        --mode release --baseline lock_castell-alun-high-school_v8.json --bundle-dir . --json results_release.json \
        --evidence evidence_rerun_release.ndjson.gz
    python write_verify.py ../SSS2026_ILR_Report_V5.3_castell-alun-high-school_Bilingual.html results_release.json results_dev.json
    python browser_gate_provenance.py ../SSS2026_ILR_Report_V5.3_castell-alun-high-school_Bilingual.html --states 60 --fixture auto --json browser_gate.json

Gate pack v8 (unchanged since V4.15, sha256 in the manifest): CONJ-06 asserted against the reading the
Framework names on sheet 11 (`MODE=figure`, D84). The Framework this build read is `01_Framework_v2.12.xlsx` (sha256
19655542a70a59ae04c324d5da87be11d2e4dc31df1d2a1a2c5e2a69c019a7a0); its own README row (sheet 00) states what changed in it and the round's entry in
`sw-feedback-compliance-record.md` names the ruling, if any, under which the corpus moved.

Baseline (D82): `lock_castell-alun-high-school_v8.json` is this school's OWN corpus lock, EMITTED by the build's QA stage
(asserted against the previous lock `lock_castell-alun-high-school_v8.json` during the build — 0 English and 0 Welsh states moved; ruling recorded: V5.3 re-emission for castell-alun-high-school: Framework v2.12 (Welsh for the fourteen Young Artists Competition alt frames, supplied by the owner 22 Sep 2026), pipeline 0.30.0, the V4.18 template — no state moved (asserted against the V5.2 lock)). The reruns here assert GOV-lock-cy and FT11-keyset against it. A rebuild of this school
asserts against this lock; a change must cite a ruling.

Two-phase stamp (D81): the build ran the vendored, byte-identical v8 runner on the unstamped package,
stamped `gateResults {blockingPass, blockingTotal, headline, pending, disputed}`, and the runs above re-run
the same runner on the stamped file with the bundle asserted. `verify.json` is written from that rerun and
is the only statement of the final status. STK-caption-case (disputed, pack defect, V4.9 register),
CAT-values in release mode (the 72 engine- and client-owned catalogue rows with no Welsh value) and
GOV-mode (the owner's unsigned D69) are the same known items as on the V4.15 prototype.

The pupil-level export this report was built from is INPUT DATA and is not part of this bundle; the
`sourceChecksum` in `buildMetadata` is its sha256, and `config/schools/castell-alun-high-school.json` records the dataset,
its sha256 and the inclusion rule.
