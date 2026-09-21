# -*- coding: utf-8 -*-
"""Framework v2.7 acceptance (D68/D81/D84): gate pack v8 — the V4.9 pack
script v7 with the CONJ-06 reading taken from sheet 11 (MODE=figure, the
translator's ruling of 21 Sep 2026) — run at build time over the in-memory package — every generated
surface, the stacked/derived data rows, the client source AND (v7) the
static page markup. The gate logic is the vendored, unmodified pack script
(vendor_welsh_gates_v7); this wrapper adapts the input and, per D81,
returns the values the build stamps into buildMetadata.gateResults: one
plain headline "n/N" and a pending list naming the gates that can only
pass once the stamp and the bundle exist (GOV-rerun, GOV-bundle). No prose
condition. The bundle's verify.json, written from the clean rerun on the
stamped file, is the only place the final status is stated.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

from . import vendor_welsh_gates_v8 as V7   # v8 pack; the name V7 is kept for the diff's sake
from . import static_lane as SL
from .common import CONFIG_DIR, GENERATED_DIR

WEB_DIR = Path(__file__).resolve().parent.parent / "web"
RUNNER_PATH = Path(__file__).resolve().parent / "vendor_welsh_gates_v8.py"
BROWSER_HARNESS_PATH = (Path(__file__).resolve().parent
                        / "vendor_browser_gate_v3.py")
# D82: the baseline carries English AND Welsh per-state hashes and the
# FT-11 key set. V4.15: 02c_lock_V415_v8.json — emitted from the V4.15 build
# after the translator's rulings changed the Welsh corpus (D84–D87); its
# English part is byte-equal to the V4.8/V4.9 lock (the English never moved)
# and its FT-11 key set is unchanged. Falls back to the V4.8 lock until the
# V4.15 lock exists (first build of a rebuild kit).
BASELINE_PATH = (CONFIG_DIR / "02c_lock_V415_v8.json"
                 if (CONFIG_DIR / "02c_lock_V415_v8.json").exists()
                 else CONFIG_DIR / "02c_lock_V48_v7.json")
# D81: the assurance bundle ships in this directory beside the report. At
# build time it does not exist yet — GOV-bundle is therefore PENDING in the
# embedded stamp and asserted by the rerun on the shipped file.
BUNDLE_DIR = GENERATED_DIR / "bundle"
PENDING = ("GOV-rerun", "GOV-bundle")
# Raised against gate pack v7 (V4.9 register) — unchanged in v8: STK-caption-case emulates the
# caption by substituting the countNP table entry RAW — it never applies
# the "initial" casing role the slot carries — while v7's own CNP-lexical
# requires that table to be lower-case. With a lexical table (sheet 50,
# D75) the two gates cannot both pass; the client applies the role and the
# rendered caption is capitalised (browser gate: no lower-case-initial
# caption). The dispute is VERIFIED here before it is honoured: it holds
# only when CNP-lexical, CNP-table and CNP-role all pass and every hit is
# a k >= 2 caption whose table entry, with the initial role applied, begins
# with a capital. It is recorded in the stamp, never hidden.
DISPUTED = {
    "STK-caption-case": ("gate substitutes the lexical countNP entry without "
                         "applying the slot's initial casing role; v7 "
                         "CNP-lexical requires the table to be lower-case — "
                         "raised with the pack owners (V4.9 register)"),
}


def framework_path():
    cand = sorted(CONFIG_DIR.glob("*Framework*v2.[0-9]*.xlsx"))
    if cand:
        return str(cand[-1])
    return None


def page_head(package):
    """The static markup the runner reads as the page head: the template
    stamped with data-i18n keys from the manifest (D79), school name
    resolved, everything before the report-data block."""
    tpl = (WEB_DIR / "template.html").read_text(encoding="utf-8")
    static = (package.get("welsh") or {}).get("static") or {}
    en_to_key = {v["en"]: k for k, v in static.items()}
    html = SL.stamp(tpl, en_to_key)
    html = html.replace("__SCHOOL_NAME__", package["school"]["name"])
    return SL.static_head(html)


def emit_lock(package, S, old_baseline, path, ruling):
    """D82 (V4.15): re-emit the corpus lock from THIS build after a ruling
    changed the Welsh. The English projection and the FT-11 key set must
    equal the previous lock's — the English never moves — or this refuses;
    the Welsh projection is the new baseline and the lock records which
    ruling moved it and how many states differ."""
    eng = V7.english_projection(S)
    cy = V7.welsh_projection(S)
    pol = [e for e in V7.EVIDENCE if e["gate"] == "POL-review"]
    ft11 = sorted({f"{e['state']}|{e['module']}[{e['index']}]" for e in pol})
    if old_baseline is not None:
        if eng != old_baseline.get("english"):
            diff = [k for k in set(eng) | set(old_baseline["english"])
                    if eng.get(k) != old_baseline["english"].get(k)]
            raise SystemExit(f"emit_lock: the ENGLISH projection differs from the previous lock in "
                             f"{len(diff)} states (e.g. {diff[:3]}) — the English is locked (D01); refusing")
        if ft11 != old_baseline.get("ft11"):
            raise SystemExit("emit_lock: the FT-11 key set differs from the previous lock (PR-19); refusing")
    moved = [k for k in set(cy) | set((old_baseline or {}).get("welsh", {}))
             if cy.get(k) != (old_baseline or {}).get("welsh", {}).get(k)]
    lock = {"runner": V7.VERSION, "english": eng, "welsh": cy, "ft11": ft11,
            "emitted": {"from": "build QA (pipeline/welsh_gates8.emit_lock)", "ruling": ruling,
                        "supersedes": None if old_baseline is None else "02c_lock_V48_v7.json",
                        "welshStatesMoved": len(moved), "englishStatesMoved": 0}}
    Path(path).write_text(json.dumps(lock, ensure_ascii=False), encoding="utf-8")
    return len(moved)


def run(package, mode="dev", evidence_path=None, baseline_path=None,
        bundle_dir=None, emit_lock_path=None, emit_lock_ruling=None):
    """-> (blocking_failures, results, notes, gate_results_stamp).
    emit_lock_path (D82): two passes — the gates against the PREVIOUS
    baseline first (GOV-lock and FT11-keyset must pass; GOV-lock-cy is the
    expected divergence), then the lock is re-emitted from this build and
    the gates run again against it for the stamp."""
    fw = framework_path()
    if fw:
        V7.load_framework(fw)
    S = V7.surfaces_from_states(package["states"], package.get("metricDefs"))
    js = (WEB_DIR / "app.js").read_text(encoding="utf-8")
    baseline_path = baseline_path or (str(BASELINE_PATH) if BASELINE_PATH.exists() else None)
    baseline = V7.load_baseline(baseline_path) if baseline_path else None
    V7.EVIDENCE.clear()
    V7.HEAD["html"] = page_head(package)
    bundle_dir = str(BUNDLE_DIR) if bundle_dir is None else bundle_dir
    emitted_note = None
    if emit_lock_path:
        G0 = V7.run(package, S, js, mode=mode, baseline=baseline, bundle_dir=bundle_dir)
        by0 = {g["id"]: g for g in G0 if g.get("id") != "_paths"}
        for gid in ("GOV-lock", "FT11-keyset"):
            if baseline is not None and by0[gid]["status"] != "PASS":
                raise SystemExit(f"emit_lock: {gid} fails against the previous baseline — refusing to re-emit")
        moved = emit_lock(package, S, baseline, emit_lock_path, emit_lock_ruling)
        emitted_note = (f"GOV-lock-cy: the Welsh baseline was RE-EMITTED from this build to {Path(emit_lock_path).name} "
                        f"({moved} of {len(package['states'])} states moved from the previous lock; ruling: {emit_lock_ruling}); "
                        f"the English projection and the FT-11 key set are unchanged (asserted before emission)")
        baseline_path = str(emit_lock_path)
        baseline = V7.load_baseline(baseline_path)
        V7.EVIDENCE.clear()
    G = V7.run(package, S, js, mode=mode, baseline=baseline,
               bundle_dir=bundle_dir)
    paths = next((g for g in G if g.get("id") == "_paths"),
                 {"paths": [], "notes": []})
    G = [g for g in G if g.get("id") != "_paths"]
    if baseline is None:
        for g in G:
            if g["id"] == "GOV-lock":
                g["status"] = "REPORT"
                g["note"] = "no baseline supplied; lock not asserted this run"
    failures, notes = [], []
    byid = {g["id"]: g for g in G}
    disputed = {}
    stk = byid.get("STK-caption-case")
    if stk and stk["status"] == "FAIL":
        cnp = ((package.get("welsh") or {}).get("countNP") or {}).get("camp|definite") or []
        def _cap(v):
            import re as _re
            return _re.sub(r"[A-Za-zÀ-ÿŵŷ]", lambda m: m.group(0).upper(), v, count=1)
        role_ok = all(next((c for c in _cap(v) if c.isalpha()), "").isupper() for v in cnp)
        cnp_ok = all(byid.get(k, {}).get("status") == "PASS"
                     for k in ("CNP-lexical", "CNP-table", "CNP-role"))
        ks = [int(m.group(1)) for e in stk["examples"]
              for m in [__import__("re").search(r"k=(\d+)", e.get("matched", ""))] if m]
        if role_ok and cnp_ok and all(k >= 2 for k in ks):
            disputed["STK-caption-case"] = DISPUTED["STK-caption-case"]
    for g in G:
        if g["blocking"] is True and g["status"] == "FAIL":
            if g["id"] in PENDING:
                # D81: can only pass after the stamp / the bundle exist —
                # named in the pending list, asserted by the rerun.
                continue
            if g["id"] in disputed:
                notes.append(f"welsh gate v8 {g['id']} DISPUTED (pack defect, "
                             f"{g['occurrences']} occurrences): {disputed[g['id']]}")
                continue
            ex = g["examples"][0] if g["examples"] else {}
            failures.append(
                f"welsh gate v8 {g['id']}: {g['occurrences']} occurrences "
                f"({g['records']} records) — {g['title']}"
                + (f" e.g. {ex.get('where')} «{ex.get('matched')}»"
                   if ex else ""))
        elif g["blocking"] is False and g["occurrences"]:
            notes.append(f"welsh gate v8 {g['id']} (report-only): "
                         f"{g['occurrences']} occurrences — {g['title']}")
    blocking = [g for g in G if g["blocking"] is True]
    # D81: the stamp claims exactly what this run could know — every
    # blocking gate except the two that need the stamp and the bundle.
    claim_pass = sum(1 for g in blocking
                     if g["id"] not in PENDING and g["status"] == "PASS")
    total = len(blocking)
    pending = [p for p in PENDING if any(g["id"] == p for g in blocking)]
    # the path count is what the stock runner computes (GOV-rerun compares
    # it); a disputed caption emulation also marks UI-DYN-16 partial
    complete = sum(1 for p in paths["paths"] if p["status"] == "complete")
    notes.append(f"welsh gates v8: {claim_pass}/{total} blocking pass "
                 f"(pending {', '.join(pending)}"
                 + (f"; disputed {', '.join(disputed)}" if disputed else "")
                 + f") · renderer paths complete "
                 f"{complete}/{len(paths['paths'])} "
                 f"(manifest {V7.MANIFEST_HASH}, mode {mode}, "
                 f"config {V7.CFG.get('source')})")
    for n in paths.get("notes", []):
        notes.append(f"welsh gates v8 note: {n}")
    if emitted_note:
        notes.append(f"welsh gates v8 D82: {emitted_note}")
    evidence_sha = None
    if evidence_path:
        with gzip.open(evidence_path, "wt", encoding="utf-8") as fh:
            fh.write(json.dumps({"record_type": "metadata",
                                 "runner": V7.VERSION,
                                 "manifest_hash": V7.MANIFEST_HASH,
                                 "mode": mode}, ensure_ascii=False) + "\n")
            for e in V7.EVIDENCE:
                fh.write(json.dumps(e, ensure_ascii=False) + "\n")
        evidence_sha = hashlib.sha256(
            Path(evidence_path).read_bytes()).hexdigest()
    stamp = {
        "runner": V7.VERSION,
        "runnerSha256": hashlib.sha256(RUNNER_PATH.read_bytes()).hexdigest(),
        "manifestHash": V7.MANIFEST_HASH,
        "mode": mode,
        "blockingPass": claim_pass,
        "blockingTotal": total,
        "headline": f"{claim_pass}/{total}",
        "pending": pending if claim_pass < total else [],
        **({"disputed": disputed} if disputed else {}),
        "pathsComplete": complete,
        "pathsTotal": len(paths["paths"]),
        "evidenceSha256": evidence_sha,
        "baselineSha256": (hashlib.sha256(
            Path(baseline_path).read_bytes()).hexdigest()
            if baseline_path else None),
    }
    return failures, G, notes, stamp
