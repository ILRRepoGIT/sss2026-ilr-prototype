# -*- coding: utf-8 -*-
"""Build the self-contained REBUILD KIT: one consolidated key-documents file
and one archive from which the report can be rebuilt exactly.

    python -m pipeline.make_rebuild_kit <version> <out_dir> <export.xlsx> \
        <yac_assets_dir> <fonts_dir> [<translator.docx>] [<deployment_plan.md>]

Writes <out_dir>/SSS2026_ILR_Key_Documents_<v>.md (the one file) and
<out_dir>/SSS2026_ILR_Rebuild_Kit_<v>.zip (repo snapshot without the large
generated outputs, the assurance bundle, the inputs the build needs, the
three fonts, the cover/character images, MANIFEST.sha256 and the same
key-documents file). The key-documents file carries the rulebook, README,
LIMITATIONS, the engine's disclosure policy, the full compliance record,
the deployment plan, the V4.10 translation register summary, the exact
rebuild commands and the sha256 of every file in the kit.
"""
from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile
from pathlib import Path

from .common import CONFIG_DIR, GENERATED_DIR, ROOT

RULEBOOK = """
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
"""

REBUILD = """
All commands run from the `repo/` directory of this kit with Python 3.10+ (openpyxl, pyyaml, pytest, python-docx installed) and Node 18+ (jsdom 30.0.1 for the browser-gate port). Paths in angle brackets are the kit's own folders.

    # 0. verify the kit
    sha256sum -c ../MANIFEST.sha256

    # 1. the gate runner rejects its own seeded faults (v8: CONJ-06 read from sheet 11, D84)
    python pipeline/vendor_welsh_gates_v8.py --selftest                      # 68/68 + CONJ-06 modes OK

    # 2. the lexicon from the Framework workbook and the filled handoff
    python -m pipeline.build_welsh_lexicon config/01_Framework_v2.7.xlsx \\
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
    python -m pipeline.build_html generated/ysgol-penrhyn-dewi.report.json \\
        "../inputs/yac images for report" ../inputs/fonts config/cover_media   # generated/report.html

    # 6. the assurance bundle and the two stock reruns (v8 runner; baseline 02c_lock_V415_v8.json)
    python -m pipeline.make_bundle V4.15

    # 7. the jsdom regression and browser-gate port (Chromium optional)  — 97/97
    python -m tests.jsdom.make_mini /tmp/ilr_wd
    JSDOM=<node_modules/jsdom> WD=/tmp/ilr_wd node tests/jsdom/jsdom_test.js          # 97/97
    JSDOM=<node_modules/jsdom> WD=/tmp/ilr_wd node tests/jsdom/jsdom_provenance.js    # 0 / 0 / 0, toggle 0 failures

    # 8. (when a new translator document arrives) regenerate and fill the handoff
    python -m pipeline.make_translation_handoff config/01_Framework_v2.4.xlsx /tmp/handoff_empty.xlsx \\
        config/SSS2026_Welsh_Translation_Handoff_V4.11.xlsx
    python -m pipeline.ingest_translation_doc <translator.docx> /tmp/handoff_empty.xlsx \\
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
    python -m pipeline.apply_translator_handover config/SSS2026_Welsh_Translator_Handover_V4.14_COMPLETED.xlsx \\
        config/01_Framework_v2.6.xlsx config/01_Framework_v2.7.xlsx \\
        config/SSS2026_Welsh_Translation_Handoff_V4.14.xlsx config/SSS2026_Welsh_Translation_Handoff_V4.15.xlsx \\
        generated/SSS2026_V4.15_Translator_decisions_applied.xlsx           # 174 changes, 25 flags
    # 11. (optional, Chromium) render probe: default view pixel comparison and print PDF page count
    python -m tests.browser.render_probe /tmp/ilr_wd /tmp/probe            # and --a11y for the switch-on view

Expected on this kit: the ENGLISH corpus byte-identical to V4.14/V4.10/V4.9/V4.8 (0 differences over 308,400 records; the `english` part of the emitted lock byte-equal to config/02c_lock_V48_v7.json); the WELSH corpus changed only by the translator's rulings (Framework v2.7 sheet 60, D84–D87) — the emitted lock byte-equal to config/02c_lock_V415_v8.json in all three parts; report sha256 differs from the shipped file only through the build timestamp in buildMetadata.
"""

EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git"}
EXCLUDE_GENERATED = {"report.html", "ysgol-penrhyn-dewi.report.json", "welsh_gate_evidence_build.ndjson.gz",
                     "ysgol-penrhyn-dewi.narrative-audit.csv"}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else f"(missing: {p})"


def main():
    v, out_dir, export, yac, fonts = sys.argv[1:6]
    docx = Path(sys.argv[6]) if len(sys.argv) > 6 else None
    plan = Path(sys.argv[7]) if len(sys.argv) > 7 else None
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    kit = out / f"SSS2026_ILR_Rebuild_Kit_{v}"
    if kit.exists():
        shutil.rmtree(kit)
    (kit / "repo").mkdir(parents=True)
    # ---- repo snapshot ----------------------------------------------------
    for src in ("pipeline", "web", "config", "tests"):
        shutil.copytree(ROOT / src, kit / "repo" / src,
                        ignore=shutil.ignore_patterns(*EXCLUDE_DIRS))
    for f in ("README.md", "LIMITATIONS.md", "build_prototype.sh", "sw-feedback-compliance-record.md"):
        if (ROOT / f).exists():
            shutil.copy2(ROOT / f, kit / "repo" / f)
    (kit / "repo" / "generated").mkdir()
    for f in GENERATED_DIR.iterdir():
        if f.is_dir() and f.name == "bundle":
            shutil.copytree(f, kit / "repo" / "generated" / "bundle")
        elif f.is_file() and f.name not in EXCLUDE_GENERATED and not f.name.startswith("SSS2026_ILR_Report"):
            shutil.copy2(f, kit / "repo" / "generated" / f.name)
    # ---- inputs -------------------------------------------------------------
    inp = kit / "inputs"; inp.mkdir()
    shutil.copy2(export, inp / Path(export).name)
    shutil.copytree(yac, inp / "yac images for report")
    (inp / "fonts").mkdir()
    for w in ("400", "600", "800"):
        shutil.copy2(Path(fonts) / f"montserrat-latin-{w}-normal.woff2", inp / "fonts")
    if docx and docx.exists():
        shutil.copy2(docx, inp / docx.name)
    for extra in sys.argv[8:]:                    # V4.13: further input documents (accessibility feedback)
        if Path(extra).exists():
            shutil.copy2(extra, inp / Path(extra).name)
    # ---- key documents ----------------------------------------------------
    rep = json.load(io.open(GENERATED_DIR / "ysgol-penrhyn-dewi.report.json", encoding="utf-8"))
    bm = rep["buildMetadata"]
    engine_doc = read(ROOT / "pipeline" / "engine.py").split('"""')[1]
    html_path = GENERATED_DIR / f"SSS2026_ILR_Report_{v}_Bilingual.html"
    parts = [
        f"# SSS2026 Interactive Learning Report — key documents, {v}",
        "",
        f"Generated {datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')} from the {v} build. "
        f"This file and the companion archive `SSS2026_ILR_Rebuild_Kit_{v}.zip` are the complete record: if everything else were lost, the report is rebuilt exactly from the archive by the commands in section 3, and every decision, rule, limitation and open item is in sections 1, 4–8.",
        "",
        "## Contents",
        "",
        "1. The rulebook · 2. Build identity and figures · 3. Rebuild instructions · 4. README (build history) · 5. LIMITATIONS and the disclosure model · 6. The engine's suppression policy (as coded) · 7. Feedback and compliance record (every round) · 8. Production deployment plan · 9. V4.10 translation register (summary) · 10. Kit inventory with sha256",
        "",
        "## 1. The rulebook", RULEBOOK,
        "## 2. Build identity and figures", "",
        f"Report version `{rep['reportVersion']}` · pipeline {bm.get('pipelineVersion', '')} · identity `{json.dumps(bm.get('identity'))}` · gate stamp `{json.dumps(bm.get('gateResults'))}` · static lane `{json.dumps(bm.get('staticLane'))}` · suppression `{bm.get('suppressionModel')}` threshold {bm.get('suppressionThreshold')} · states {len(rep['states'])} · "
        + (f"shipped file {html_path.name} {html_path.stat().st_size:,} bytes sha256 {sha(html_path)}" if html_path.exists() else ""),
        "",
        "## 3. Rebuild instructions", REBUILD,
        "## 4. README (build history)", "", read(ROOT / "README.md"), "",
        "## 5. LIMITATIONS and the disclosure model", "", read(ROOT / "LIMITATIONS.md"), "",
        "## 6. The engine's suppression policy (pipeline/engine.py docstring)", "", "```", engine_doc.strip(), "```", "",
        "## 7. Feedback and compliance record", "", read(ROOT / "sw-feedback-compliance-record.md"), "",
        "## 8. Production deployment plan", "", (read(plan) if plan else "(not supplied)"), "",
        "## 9. V4.10 translation register (summary)", "",
        read(out / "V4.10_translation_register.md")[:0] or "See V4.10_translation_register.md / .xlsx in the kit (`repo/generated/V4.10_translation_register.*`).", "",
    ]
    # register copies into the kit
    for f in ("V4.10_translation_register.md", "V4.10_translation_register.xlsx"):
        src = out / f
        if src.exists():
            shutil.copy2(src, kit / "repo" / "generated" / f)
    # ---- manifest -----------------------------------------------------------
    lines, inv = [], []
    for p in sorted(kit.rglob("*")):
        if p.is_file():
            rel = p.relative_to(kit).as_posix()
            h = sha(p); lines.append(f"{h}  {rel}"); inv.append(f"| `{rel}` | {p.stat().st_size:,} | `{h[:16]}…` |")
    parts += ["## 10. Kit inventory", "", f"{len(inv)} files. Full hashes in `MANIFEST.sha256`.", "",
              "| file | bytes | sha256 |", "|---|---|---|", *inv, ""]
    key_md = "\n".join(parts)
    (kit / f"SSS2026_ILR_Key_Documents_{v}.md").write_text(key_md, encoding="utf-8")
    (out / f"SSS2026_ILR_Key_Documents_{v}.md").write_text(key_md, encoding="utf-8")
    kh = sha(kit / f"SSS2026_ILR_Key_Documents_{v}.md")
    lines.append(f"{kh}  SSS2026_ILR_Key_Documents_{v}.md")
    (kit / "MANIFEST.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (kit / "00_READ_ME_FIRST.md").write_text(
        f"# SSS2026 ILR rebuild kit {v}\n\nStart with `SSS2026_ILR_Key_Documents_{v}.md` (section 3 has the exact rebuild commands). "
        f"`sha256sum -c MANIFEST.sha256` verifies every file. `repo/` is the pipeline, client, configuration, tests and assurance bundle; "
        f"`inputs/` holds the response export, the character images, the three fonts and the translator's document.\n", encoding="utf-8")
    zpath = out / f"SSS2026_ILR_Rebuild_Kit_{v}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(kit.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(out).as_posix())
    print(json.dumps({"kit": str(kit), "zip": str(zpath), "zip_bytes": zpath.stat().st_size,
                      "files": len(lines), "key_documents_sha256": kh}, indent=1))


if __name__ == "__main__":
    main()
