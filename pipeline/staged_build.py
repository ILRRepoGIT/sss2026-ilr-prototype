# -*- coding: utf-8 -*-
"""Checkpointed build driver: the full report-package build split into
stages so each fits inside a short execution window. Produces byte-identical
output to pipeline.build_report_package (same code paths, same QA).

    python -m pipeline.staged_build states <xlsx> <workdir> <lo> <hi>
    python -m pipeline.staged_build assemble <xlsx> <workdir>
    python -m pipeline.staged_build qa <xlsx> <workdir>
    python -m pipeline.staged_build write <xlsx> <workdir> [outdir]

`states` narrates scopes SCOPES[lo:hi] and pickles the chunk. `assemble`
merges chunks into the package pickle. `qa` runs the full QA (including the
sheet-36 Welsh gates) and pickles errors/warnings. `write` refuses to write
if QA failed, then emits report.json + audit CSVs + validation summary.
"""
from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

from .build_report_package import (
    MODULE_LABELS, PIPELINE_VERSION_V2, REPORT_VERSION_V2,
    SCHEMA_VERSION, SCHOOL_SLUG, TEMPLATES, _participation_variation,
    _stacked_sport_freq, run_qa_checks)
from .common import GENERATED_DIR, load_config
from .engine import (GENDERS, SCOPES, StateEngine, build_cohorts,
                     build_metric_defs, filter_rows, state_key)
from .load_normalise import load_and_normalise
from .narrative2 import Scope
from .narrative2_modules_b import FullNarrator


def prep(xlsx):
    profile, mapping, metrics_cfg, narratives_cfg = load_config()
    threshold = profile["suppressionThreshold"]
    records, log, build_meta, discovered = load_and_normalise(xlsx)
    from . import welsh_render as _wr
    _wr.register_code_labels({**discovered["participated"],
                              **discovered["demand"]})
    defs = build_metric_defs(metrics_cfg, discovered)
    cohorts = build_cohorts(metrics_cfg, defs, records)
    engine = StateEngine(records, defs, cohorts, profile, threshold).compute_all()
    narrator = FullNarrator(engine, defs, cohorts, profile, threshold)
    return dict(profile=profile, metrics_cfg=metrics_cfg,
                narratives_cfg=narratives_cfg, threshold=threshold,
                records=records, log=log, build_meta=build_meta,
                discovered=discovered, defs=defs, cohorts=cohorts,
                engine=engine, narrator=narrator)


def do_states(xlsx, wd, lo, hi):
    t0 = time.time()
    P = prep(xlsx)
    engine, narrator = P["engine"], P["narrator"]
    records, cohorts, defs = P["records"], P["cohorts"], P["defs"]
    sport_labels = P["discovered"]["participated"]
    states = {}
    for scope in SCOPES[lo:hi]:
        for gender in GENDERS:
            for ck in engine.cohort_keys:
                key = state_key(scope, gender, ck)
                if key in engine.suppressed:
                    S = Scope(scope, gender, ck, cohorts, P["profile"])
                    states[key] = {"sup": 1, "scope": S.as_dict()}
                    continue
                built = narrator.build_state(key)
                _rows = filter_rows(records, scope, gender, ck, cohorts,
                                    defs, engine.scope_years)
                built["stk"] = _stacked_sport_freq(_rows, sport_labels)
                _dy = sum(1 for r in _rows if r.get("disability") == "yes")
                _ly = sum(1 for r in _rows if r.get("learning") == "yes")
                _dl = sum(1 for r in _rows if r.get("dl_any") == "yes")
                built["dlm"] = ("sep" if (_dy >= 5 and _ly >= 5)
                                else "comb" if _dl >= 5 else "sup")
                res = engine.results[key]
                m_out = {}
                for mid, r in res.items():
                    entry = {"s": r["status"]}
                    if r["status"] == "ok":
                        entry["b"] = r["base"]
                        entry["v"] = r["disp"]
                    m_out[mid] = entry
                states[key] = {"b": engine.bases[key], "m": m_out, **built}
    from .welsh import misses as _wmisses
    with open(Path(wd) / f"chunk_{lo}_{hi}.pkl", "wb") as f:
        pickle.dump({"states": states, "audit": narrator.audit,
                     "misses": _wmisses()}, f, protocol=4)
    print(f"chunk {lo}:{hi} states={len(states)} "
          f"paras={len(narrator.audit)} misses={len(_wmisses())} "
          f"({time.time()-t0:.0f}s)", flush=True)


def merge_chunks(wd):
    states, audit, misses = {}, [], set()
    for p in sorted(Path(wd).glob("chunk_*.pkl")):
        with open(p, "rb") as f:
            c = pickle.load(f)
        states.update(c["states"])
        audit.extend(c["audit"])
        misses.update(tuple(m) for m in c["misses"])
    return states, audit, misses


def do_assemble(xlsx, wd):
    t0 = time.time()
    P = prep(xlsx)
    engine, cohorts, defs = P["engine"], P["cohorts"], P["defs"]
    profile, records = P["profile"], P["records"]
    metrics_cfg, narratives_cfg = P["metrics_cfg"], P["narratives_cfg"]
    states, audit, misses = merge_chunks(wd)
    assert len(states) == len(SCOPES) * len(GENDERS) * len(engine.cohort_keys), \
        f"incomplete chunks: {len(states)} states"

    scope_opts = []
    from .welsh_render import SCOPE_CY as _SC_CY, SEX_CY as _SEX_CY
    for g in profile["scopeGroups"]:
        entry = {"key": g["key"], "label": g["label"]}
        # sheet 58 (v2.6): every scope option is a workbook row; a
        # missing key fails the build — never a composed default
        entry["labelCy"] = _SC_CY[g["key"]]
        if g.get("description"):
            entry["desc"] = g["description"]
            entry["descCy"] = (g["description"]
                               .replace("Years", "Blynyddoedd")
                               .replace("Year", "Blwyddyn"))
        entry["avail"] = state_key(g["key"], "all", "none") not in engine.suppressed
        scope_opts.append(entry)

    colours = metrics_cfg.get("base_colours", {})
    metric_defs_out = {}
    from .welsh_render import label_cy as _lcy, grid_of as _grid_of
    for mid, d in defs.items():
        metric_defs_out[mid] = {
            "sec": d["section"], "label": d["label"], "q": str(d["question"]),
            "type": "multi" if d["type"] == "multi_select" else "single",
            "chart": d["chart"], "cf": d["cross_filter"],
            "colour": colours.get(mid, "blue"),
            "selectable": d["cross_filter"] == "cohort",
            "opts": [[c, l] for c, l in d["options"]],
        }
        for k_src, k_dst in [("top_n", "topN"), ("exempt", "exempt"),
                             ("base_note", "baseNote"), ("tail_options", "tail"),
                             ("cohort_codes", "cohortCodes")]:
            if d.get(k_src):
                v = d[k_src]
                if k_src == "cohort_codes" and v == "all":
                    v = [c for c, _ in d["options"]]
                metric_defs_out[mid][k_dst] = v
        _grid = _grid_of(mid)          # D32 grids (v2.7: + take-part)
        # D54 (v1.8): a binary metric's chart labels echo its question's
        # verb from the sheet-31 mapping (Oes/Nac oes, Ydw/Nac ydw);
        # PR-11 names the derived ethnicity set instead
        from .welsh_render import yn_descriptor as _ynd
        from .welsh import lexicon as _wl54
        if mid in _wl54().get("yes_no_metrics", {}):
            _m54 = _wl54()["yes_no_metrics"][mid]
            _named = (_m54["aff"] or "").strip() in ("—", "")
            def _opt54(code, label):
                if code == "yes":
                    return (_m54["form"].split("/")[0].strip() if _named
                            else _m54["aff"])
                if code == "no":
                    return (_m54["form"].split("/")[1].strip() if _named
                            else _m54["neg"])
                return _lcy(label, _grid, form="cy")
            metric_defs_out[mid]["optsCy"] = [
                _opt54(c, l) for c, l in d["options"]]
        else:
            metric_defs_out[mid]["optsCy"] = [
                _lcy(l, _grid, form="cy") for _, l in d["options"]]

    from .welsh import lexicon as _wlex
    _handoff = _wlex().get("handoff", [])
    welsh_block = {
        "ui": {
            "based_on": "Yn seiliedig ar:",
            "pupil": "disgybl",
            "pupils": "disgybl",
            "whole_school_all": "Yr ysgol gyfan · Pob disgybl",
            "boys": "Bechgyn", "girls": "Merched",
            "what_showing": "Beth mae’r siart hwn yn ei ddangos?",
            "reset": "Ailosod i’r ysgol gyfan",
            "filter_applied": "Rhoddwyd hidlydd ar waith.",
            "selection_cleared": "Cliriwyd y dewis ar y siart.",
            "language_label": "Cymraeg",
            "language_label_en": "English",
            # D59 control strings — DERIVED from framework vocabulary,
            # flagged for the linguist alongside the descriptor frames
            "selection_applied": "Dewiswyd bar ar y siart.",
            "group_applied": "Dewiswyd grŵp disgyblion.",
            "group_cleared": "Cliriwyd y grŵp disgyblion.",
            "all_cleared": "Cliriwyd pob hidlydd.",
            "view_restored": "Adferwyd y golwg o’r cyfeiriad.",
            "showing": "Yn dangos",
            "responses_included": "ymateb disgybl wedi’u cynnwys",
            "response_included": "ymateb disgybl wedi’i gynnwys",
            "not_enough": "Dim digon o ymatebion i adrodd yn ddiogel",
            "not_reportable": "(methu adrodd)",
            "all_pupils": "Pob disgybl",
            # PR-18/D76: the language-neutral no-report marker, read from
            # sheet 43 (ui.no_report); the accessible name comes from the
            # ui.table_suppressed frame at the consumer.
            "no_report": _wlex().get("no_report_marker", "—"),
            # v2.0: the stacked-table caption moved to the sheet-43 frame
            # ui.stack_table_caption (count-aware, D71/PR-17); the v1.9
            # DERIVED fixed-count string is withdrawn. The FSM card stays
            # in the translator lane (no Welsh yet).
        },
        # Integration spec §5.2: client strings live in a catalogue in BOTH
        # languages, behind one lookup — never inline in the script
        "uiEn": {
            "you_are_viewing": "You are viewing:",
            "responses_included": "pupil responses included",
            "appendix_total_responses":
                "Total number of pupil responses included in this report",
            # v1.9 (D63): the English side of every cat() key the client
            # uses — the catalogue serves BOTH languages; no code literal.
            "what_showing": "What is this chart showing?",
            "not_reportable": "(not reportable)",
            "not_enough": "Not enough responses to report safely",
            "filter_applied": "Filter applied.",
            "selection_applied": "Chart selection applied.",
            "selection_cleared": "Chart selection cleared.",
            "group_applied": "Pupil group applied.",
            "group_cleared": "Pupil group cleared.",
            "all_cleared": "All filters cleared.",
            "view_restored": "View restored from address.",

            "no_report": _wlex().get("no_report_marker", "—"),
            "fsm_context_title": "Free school meals context",
            "fsm_context_body":
                "Sport Wales uses the proportion of pupils eligible for "
                "Free School Meals as an indicator for deprivation. Your "
                "school\u2019s figure (PLASC data):",
        },
        "handoff": {
            # sheet 38: the two generic discussion prompts route through
            # the translator catalogue, not the generator. v1.8 CAT-bind:
            # EVERY declared key is embedded, whatever its owner, so the
            # binding layer is generic.
            "h2_generic_reflect": None,
            "h2_generic_discussion": None,
            **{s["key"]: s["cy"] for s in _handoff},
            # v2.0 (sheet 28, CAT-destination): the five chart base-note
            # rows now exist in the workbook, so the translator's return
            # has somewhere to land — 342 keys, not 337.
        },
        # CAT-bind (v1.8): declared = the DISTINCT keys the binding layer
        # can address; several workbook rows share a key
        "handoffMissing": None,
        # D63: sheet-43 typed frames for t(key, params) — every dynamic
        # and assistive client string, both languages, as DATA.
        "frames": _wlex().get("interface_frames", {}),
        # D66: the stacked-chart legend, sourced from the workbook through
        # the catalogue — never re-typed in code.
        "stackLegend": _wlex().get("stack_legend", []),
        # D74: the CONTRACT separators — the only place a delimiter lives.
        # Delivered as data (a bare delimiter cannot be a clause frame).
        "separators": _wlex().get("separators", {}),
    }
    # D75 / sheet 50: the count-NP tables are LEXICAL data read from the
    # workbook and emitted verbatim (cross-checked against the numeral
    # service; a disagreement fails the build). Casing is the client's
    # "initial" role, applied at realisation and nowhere else.
    from .welsh_payload import (count_np_tables as _cnp,
                                static_manifest as _static,
                                identity as _identity_of)
    welsh_block["countNP"] = _cnp(_wlex())
    # v2.0 (sheet 28, CAT-destination): the five chart base-note rows must
    # exist as destinations; V4.11: they are added only when ABSENT — the
    # V4.9/V4.10 dict literal set them to None after the handoff spread and
    # silently discarded the translator's returned notes (assessment §6.4).
    for _bk in ("responses_by_gender_base_note", "take_part_method_base_note",
                "welsh_when_playing_sport_base_note", "ethnicity_group_base_note",
                "unmet_demand_base_note"):
        welsh_block["handoff"].setdefault(_bk, None)
    # v2.3 (sheet 53): the profile's data values in Welsh
    welsh_block["names"] = _wlex().get("proper_names", {})
    welsh_block["handoffMissing"] = sum(
        1 for v in welsh_block["handoff"].values() if not v)
    build_meta = P["build_meta"]
    # D63/D64: Welsh metric titles come from the translator catalogue,
    # keyed by metric id; a missing key carries the ⟪missing:key⟫ marker
    # in this dev-mode build (release mode fails instead) — never a
    # silent fallback (CAT-schema).
    for _mid, _md in metric_defs_out.items():
        _md["labelCy"] = (welsh_block["handoff"].get(_mid)
                          or f"⟪missing:{_mid}⟫")
        if _md.get("baseNote"):
            _bk = f"{_mid}_base_note"
            _md["baseNoteCy"] = (welsh_block["handoff"].get(_bk)
                                 or f"⟪missing:{_bk}⟫")
    # D60: the build is stamped with exactly what it was built from — the
    # framework workbook hash, the gate-manifest hash of the vendored v7
    # runner, and the surface counts the gates will see. D78: ONE identity
    # object; every legacy field is derived from it, never written twice.
    # D79: the static lane is BOUND — welsh.static is the manifest the
    # client swaps from; the build fails on any unbound row or node.
    welsh_block["static"], _lane = _static(
        welsh_block["handoff"], _wlex(), profile["schoolName"])
    _identity = _identity_of(_wlex())
    _surface_counts = {"module": 0, "h1": 0, "h2": 0, "scope": 0,
                       "opts": sum(len(d.get("opts") or [])
                                   for d in metric_defs_out.values())}
    for _st in states.values():
        for _m in (_st.get("mod") or {}).values():
            _surface_counts["module"] += len(_m.get("p") or [])
        for _v in (_st.get("h1") or {}).values():
            _surface_counts["h1"] += sum(1 for x in _v if isinstance(x, dict))
        _surface_counts["h2"] += sum(1 for x in (_st.get("h2") or [])
                                     if isinstance(x, dict) and x.get("c"))
        _surface_counts["scope"] += 1
    package = {
        "schemaVersion": SCHEMA_VERSION,
        "welsh": welsh_block,
        "reportVersion": REPORT_VERSION_V2,
        "buildMetadata": {**build_meta, "pipelineVersion": PIPELINE_VERSION_V2,
                          # v2.7: the ethnicity profile table's Welsh labels
                          # (sheet 23 rows keyed by the profile's long English
                          # labels) — until V4.14 the client matched the long
                          # labels against the chart's short options and fell
                          # back to English silently in Welsh mode
                          "ethnicityProfileCy": [
                              _lcy(_en, form="cy")
                              for _en, _ in build_meta["ethnicityProfile"]],
                          "identity": _identity,
                          # legacy fields DERIVED from the identity (D78)
                          "welshFramework": _identity["frameworkVersion"],
                          "welshFrameworkSha256": _identity["frameworkSha256"],
                          "welshFrameworkFile": _identity["frameworkFile"],
                          "gateManifestHash": _identity["manifestHash"],
                          "gateRunnerVersion": _identity["runnerVersion"],
                          "surfaceCounts": _surface_counts,
                          "mode": _identity["mode"],
                          "staticLane": _lane,
                          "provisionalRulings": __import__(
                              "pipeline.welsh", fromlist=["pr_set"]).pr_set(),
                          "suppressionThreshold": P["threshold"],
                          "suppressionModel": "view-level rule of five (2026-07-20)"},
        "school": {
            "id": profile["schoolId"], "name": profile["schoolName"],
            "localAuthority": profile["localAuthority"],
            "profile": profile["profileId"], "years": profile["availableYears"],
            "surveyYear": profile["surveyYear"], "type": profile["schoolType"],
            "regionalSportPartnership": profile.get(
                "regionalSportPartnership", "To be confirmed"),
            "schoolStages": profile.get("schoolStages", ""),
            "fieldworkDates": profile.get("fieldworkDates", ""),
            "fsmBand": profile.get("fsmBand", "To be confirmed by Sport Wales"),
        },
        "anyActivity": sum(1 for r in records
                           if r.get("any_activity") == "yes"),
        "tier2Codes": sorted(__import__(
            "pipeline.common", fromlist=["TIER2_SPORTS"]).TIER2_SPORTS),
        "participationVariation": _participation_variation(records),
        "filterOptions": {"scope": scope_opts,
                          "gender": [{"key": g["key"], "label": g["label"],
                                      "labelCy": _SEX_CY[g["key"]]}
                                     for g in profile["genderOptions"]]},
        "cohorts": {k: {"label": c["label"], "metric": c["metric"], "code": c["code"],
                        "labelCy": __import__(
                            "pipeline.welsh_render",
                            fromlist=["cohort_label_cy"]).cohort_label_cy(k, c),
                        "optionLabel": c.get("optionLabel", "")}
                    for k, c in cohorts.items()},
        "metricDefs": metric_defs_out,
        "moduleLabels": MODULE_LABELS,
        "messages": narratives_cfg["state_messages"],
        "states": states,
    }
    with open(Path(wd) / "package.pkl", "wb") as f:
        pickle.dump({"package": package, "audit": audit,
                     "misses": sorted(misses),
                     "log_warnings": list(P["log"].warnings)}, f, protocol=4)
    print(f"assembled: {len(states)} states, {len(audit)} paragraphs "
          f"({time.time()-t0:.0f}s)", flush=True)


class _NarrShim:
    def __init__(self, audit):
        self.audit = audit


def do_qa(xlsx, wd):
    t0 = time.time()
    P = prep(xlsx)
    with open(Path(wd) / "package.pkl", "rb") as f:
        A = pickle.load(f)
    # seed the fail-loud registry with the misses collected across chunks
    from . import welsh as _w
    _w._MISSES.update(tuple(m) for m in A["misses"])
    errors, warnings = run_qa_checks(P["engine"], A["package"], P["records"],
                                     _NarrShim(A["audit"]))
    # D68: run_qa_checks stamped buildMetadata.gateResults on the package;
    # persist it so the written report carries its own gate evidence.
    with open(Path(wd) / "package.pkl", "wb") as f:
        pickle.dump(A, f, protocol=4)
    with open(Path(wd) / "qa.pkl", "wb") as f:
        pickle.dump({"errors": errors, "warnings": warnings}, f, protocol=4)
    print(f"QA: {'FAIL ' + str(len(errors)) if errors else 'PASS'} "
          f"({time.time()-t0:.0f}s)", flush=True)
    for e in errors[:20]:
        print("  ", e, flush=True)
    for w_ in warnings:
        if w_.startswith(("welsh", "G3a+", "G4")):
            print("  NOTE ", w_, flush=True)


def do_write(xlsx, wd, outdir):
    import csv
    t0 = time.time()
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    with open(Path(wd) / "package.pkl", "rb") as f:
        A = pickle.load(f)
    with open(Path(wd) / "qa.pkl", "rb") as f:
        Q = pickle.load(f)
    if Q["errors"]:
        for e in Q["errors"][:15]:
            print("  FAIL", e)
        raise SystemExit("QA failed; refusing to write the package")
    package, audit = A["package"], A["audit"]
    states = package["states"]
    build_meta = package["buildMetadata"]

    report_path = outdir / f"{SCHOOL_SLUG}.report.json"
    report_path.write_text(json.dumps(package, ensure_ascii=False,
                                      separators=(",", ":")), encoding="utf-8")

    with (outdir / f"{SCHOOL_SLUG}.narrative-audit.csv").open(
            "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["filter_state", "module", "kind",
                                          "template_id", "facts", "rendered_text"])
        w.writeheader()
        w.writerows(audit)

    used_tids = sorted({r["template_id"] for r in audit})
    cat = ["# Narrative template catalogue", "",
           "Named core templates (pipeline/narrative2.py):", ""]
    cat += [f"- `{k}`: {v}" for k, v in TEMPLATES.items()]
    cat += ["", "Composed module templates used in this build:", ""]
    cat += [f"- `{t}`" for t in used_tids]
    (outdir / "narrative-templates.md").write_text("\n".join(cat), encoding="utf-8")

    lines = [
        "School Sport Survey 2026 - ILR prototype build (v2)",
        f"report version: {REPORT_VERSION_V2}   pipeline: {PIPELINE_VERSION_V2}",
        f"generated at:   {build_meta['generatedAt']}",
        f"source sha256:  {build_meta['sourceChecksum']}",
        "",
        f"source rows: {build_meta['sourceRows']}  accepted: {build_meta['acceptedRows']}"
        f"  excluded: {build_meta['excludedRows']}",
        f"filter states: {len(states)} (visible "
        f"{sum(1 for s in states.values() if not s.get('sup'))}, suppressed "
        f"{sum(1 for s in states.values() if s.get('sup'))})",
        f"narrative paragraphs: {len(audit)}",
        "",
        "warnings:",
    ]
    seen = set()
    for wmsg in A["log_warnings"]:
        if wmsg not in seen:
            seen.add(wmsg)
            lines.append(f"  - {wmsg}")
    lines += ["", "automated QA checks:"]
    lines += ["  PASS  reconciliation, scope, tautology, placeholder and wording checks"]
    lines += [f"  NOTE  {w}" for w in Q["warnings"]]
    (outdir / "validation-summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"report package: {report_path} "
          f"({report_path.stat().st_size/1e6:.1f} MB) ({time.time()-t0:.0f}s)",
          flush=True)


def main():
    cmd, xlsx, wd = sys.argv[1], sys.argv[2], sys.argv[3]
    Path(wd).mkdir(parents=True, exist_ok=True)
    if cmd == "states":
        do_states(xlsx, wd, int(sys.argv[4]), int(sys.argv[5]))
    elif cmd == "assemble":
        do_assemble(xlsx, wd)
    elif cmd == "qa":
        do_qa(xlsx, wd)
    elif cmd == "write":
        do_write(xlsx, wd, sys.argv[4] if len(sys.argv) > 4 else GENERATED_DIR)
    else:
        raise SystemExit(f"unknown stage {cmd}")


if __name__ == "__main__":
    main()
