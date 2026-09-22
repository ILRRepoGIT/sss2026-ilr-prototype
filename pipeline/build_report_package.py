"""Build the disclosure-safe school report package (v2).

Usage:
    python -m pipeline.build_report_package <responses.xlsx> [output-dir]

Outputs (default: generated/):
    <school>.report.json           versioned module-based report package
    <school>.qa.csv                reconciliation output for analyst checking
    <school>.narrative-audit.csv   every sentence + template id + fact object
    narrative-templates.md         template catalogue
    validation-summary.txt         counts, exclusions, warnings, QA results
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

from .common import (GENERATED_DIR, PIPELINE_VERSION, REPORT_VERSION,
                     SCHEMA_VERSION, load_config, load_held_cohorts)
from .engine import (GENDERS, SCOPES, StateEngine, build_cohorts,
                     build_metric_defs, restrict_year_options, state_key)
from .load_normalise import load_and_normalise
from .narrative2 import BASE1_GATES, T as TEMPLATES
from .narrative2_modules import MODULE_LABELS
from .narrative2_modules_b import FullNarrator

PIPELINE_VERSION_V2 = "0.31.0"
# v6 (0.28.0, V5.0 real-school round): the school is the profile's, not the
# module's. The prototype profile carries no slug or report version, so the
# defaults keep every V4.15 name; a school profile names its own.
_PROFILE0 = load_config()[0]
SCHOOL_SLUG = _PROFILE0.get("slug", "ysgol-penrhyn-dewi")
REPORT_VERSION_V2 = _PROFILE0.get("reportVersion", "2026-prototype-V4.19-bilingual")

# v2.1: "most likely" removed from the banned list - the Sport Wales
# page-by-page feedback mandates the sentence form "Pupils were most likely
# to say...", superseding the earlier caution.
BANNED_READER_TERMS = ["cohort", "most popular", "preferred by",
                       "statistically significant", " caused ", " proves "]


def check(errors, ok, msg):
    if not ok:
        errors.append(msg)


def scope_present(text, sc):
    """Every data-led sentence must identify whom it describes."""
    hooks = [sc["phrase"], sc["place"], sc["qual"], "this selected group"]
    t = text.lower()
    if any(h and h.lower() in t for h in hooks):
        return True
    # comparison sentences that explicitly name both reference groups are
    # self-scoping; in a selected-group view they must also carry the group
    if "primary phase" in t and "secondary phase" in t:
        gh = sc.get("groupHint")
        return not gh or gh.lower() in t
    return False


def run_qa_checks(engine, package, records, narrator):
    errors, warnings = [], []
    DIGIT_LABELS = sorted(
        {lbl for d in engine.defs.values() for _, lbl in d["options"]
         if re.search(r"\d", str(lbl))},
        key=len, reverse=True)
    states = package["states"]
    bases = engine.bases

    whole = bases[state_key("whole", "all", "none")]
    check(errors, whole == len(records), "whole-school base != accepted records")
    check(errors, sum(bases[state_key(f"y{n}", "all", "none")] for n in range(3, 12)) == whole,
          "sum of year bases != whole-school base")
    check(errors, bases[state_key("primary", "all", "none")] +
          bases[state_key("secondary", "all", "none")] == whole,
          "primary + secondary != whole school")
    # v6 (0.28.0, EN-06): ui.overview_note states that every year group from
    # the school's first to its last is represented — a profile year with
    # no accepted response would make that untrue, so the build refuses
    for _y in package["school"]["years"]:
        check(errors, bases[state_key(f"y{_y}", "all", "none")] >= 1,
              f"profile year {_y} has no accepted responses (ui.overview_note claims every year is represented)")

    for key, st in states.items():
        scope, gender, ck = key.split("|")
        if st.get("sup"):
            check(errors, "m" not in st and "mod" not in st,
                  f"suppressed state {key} carries data")
            continue
        if ck != "none":
            check(errors, st["b"] <= bases[state_key(scope, gender, "none")],
                  f"{key}: group base exceeds parent")
        # tautology guard: a group state must not lead with its own defining answer
        if ck != "none":
            cdef = engine.cohorts[ck]
            src_mod = {"sports_participated": "d7", "community_club_freq": "d5",
                       "enjoy_pe": "g2", "join_in_easily": "e2",
                       "confidence_try_new": "g8", "participation_settings": "d3",
                       "disability_condition": "e5", "learning_difficulty": "e6",
                       "would_do_more_if": "f7", "sports_wanted": "f10",
                       "ideas_listened": "g5", "most_important": "f6",
                       "freq_estimate": "d0",
                       "settings_dl": "n_dl", "settings_dy": "n_dl",
                       "settings_ly": "n_dl", "settings_ed": "n_ed",
                       "settings_wl": "n_wl",
                       "enjoy_school_clubs": "g2",
                       "enjoy_community_clubs": "g2",
                       "enjoy_other_settings": "g2",
                       "confidence_learn_skill": "g8",
                       "confidence_try_again": "g8",
                       "confidence_new_place": "g8"}
            m = st["mod"].get(src_mod.get(cdef["metric"], ""), None)
            if m and m["s"] == "ok" and m["p"]:
                first = m["p"][0]
                check(errors, first["k"] == "definition" or cdef["metric"] in
                      ("disability_condition", "learning_difficulty"),
                      f"{key}: source module lacks definition guard")

    # audit-based narrative-quality checks (template id known per sentence)
    SELF_SCOPING_TEMPLATES = {"f2_year_line_v12",
                              "parent_compare_v2", "group_defined_v2", "not_asked_v2",
                              "no_responses_v2", "not_enough_group_v2",
                              "ethnicity_compare_note_v2", "no_additional_conf_v2",
                              # v4.4: the variable h2 prompts entered the
                              # audit (D49); the locked English is
                              # self-scoping by design ("in this view")
                              "h2_join_prompt_v44", "h2_unmet_prompt_v44"}
    for row in narrator.audit:
        key = row["filter_state"]
        st = states.get(key)
        if st is None or st.get("sup"):
            continue
        scope = key.split("|")[0]
        txt = row["rendered_text"]
        loc = f"{key}/{row['module']}"
        check(errors, not re.search(r"\{[a-z_0-9]+\}", txt),
              f"{loc}: unresolved placeholder")
        for term in BANNED_READER_TERMS:
            check(errors, term not in txt.lower(),
                  f"{loc}: banned reader-facing term {term!r}")
        # grammar gates (Revision Brief section 27) — v6: the base-of-one
        # expressions are narrative2.BASE1_GATES, shared with the f10 hold
        check(errors, not BASE1_GATES[1].search(txt),
              f"{loc}: singular count with plural noun: {txt[:80]}")
        check(errors, "i’m" not in txt and "i'm" not in txt,
              f"{loc}: lower-case i'm: {txt[:80]}")
        # Prototype 4.1 §5 gates
        check(errors, not BASE1_GATES[0].search(txt),
              f"{loc}: plural template applied to a base of one: {txt[:80]}")
        check(errors, "respondents among respondents" not in txt and
              "pupils among pupils" not in txt,
              f"{loc}: 'respondents/pupils among respondents/pupils': {txt[:80]}")
        check(errors, not re.search(r"\bin pe\b", txt),
              f"{loc}: lower-case PE: {txt[:80]}")
        check(errors, len(txt.split()) <= 70,
              f"{loc}: sentence block over 70 words: {txt[:80]}")
        check(errors, not re.search(r"\b(\w{3,}) \1\b", txt, re.I),
              f"{loc}: duplicated word: {txt[:80]}")
        check(errors, not BASE1_GATES[2].search(txt),
              f"{loc}: '1 were': {txt[:80]}")
        # v4 (build 011) owner gate: never "Across boys across the whole
        # school" - gender-filtered views must read "Among boys ..."
        check(errors, not re.search(r"\bAcross (boys|girls|pupils) across\b",
                                    txt, re.I),
              f"{loc}: 'Across <group> across' construction: {txt[:80]}")
        # v2.3 gate (Finding 2): no unsigned 2022 equivalence claims
        check(errors, not re.search(
            r"matches the (measure|2022)|same measure as the 2022|"
            r"can be (directly )?compared with (the )?2022|"
            r"set alongside .{0,30}2022", txt),
              f"{loc}: unsigned 2022 equivalence claim: {txt[:80]}")
        if row["kind"] in ("primary", "supporting", "comparison", "cross") and \
                row["template_id"] not in SELF_SCOPING_TEMPLATES:
            check(errors, scope_present(txt, st["scope"]),
                  f"{loc}: sentence lacks scope: {txt[:90]}")
            # a filtered state must not present a whole-school figure as its
            # own finding (comparison-reference templates are exempt)
            if scope != "whole" and row["kind"] == "primary" and \
                    row["template_id"] not in ("rank_same_v2", "rank_changed_v2"):
                check(errors, "across the whole school" not in txt,
                      f"{loc}: whole-school qualifier in filtered state: {txt[:80]}")
        # a whole-school unfiltered state must not carry selected-view wording
        if key == "whole|all|none":
            check(errors, "this selected group" not in txt and
                  "who selected" not in txt,
                  f"{loc}: selected-view qualifier in whole-school state: {txt[:80]}")
        # numbers in sentences must come from their fact objects
        # v5 (build 012): option labels can themselves contain digits (for
        # example "Bowls (not 10-pin bowling)") - strip them before the check
        for lbl in DIGIT_LABELS:
            if lbl in txt:
                txt = txt.replace(lbl, "")
        for n in re.findall(r"\d+", txt):
            if n in ("2026", "2022"):
                continue
            check(errors, n in row["facts"] or f"Year {n}" in txt,
                  f"{loc}: number {n} not in facts: {txt[:80]}")

    # ---- V4.3 (Framework v1.6, D44/D45): Welsh corpus acceptance ----------
    # (1) fail-loud coverage: every narrative paragraph must carry its Welsh
    #     twin — a render miss is a dropped semantic role, never a fallback
    from .welsh import misses as _w_misses
    for miss in _w_misses():
        check(errors, False, f"welsh render miss (D44 fail-loud): {miss}")
    no_cy = sum(1 for st in states.values() if not st.get("sup")
                for m in (st.get("mod") or {}).values()
                for p in (m.get("p") or []) if p.get("t") and not p.get("c"))
    check(errors, no_cy == 0,
          f"welsh coverage: {no_cy} narrative paragraphs without Welsh")
    # (2) v2.2 acceptance (D65/D68/D81): the V4.9 handover pack's gate
    # script — v8 since V4.15 (CONJ-06 read from sheet 11, D84) — vendored
    # verbatim, over EVERY generated surface, the
    # stacked and derived data rows, the client source and the static page
    # markup. D68/D81: the run stamps its results into
    # buildMetadata.gateResults, with the evidence archive written beside
    # the build — the stamp is pre-seeded so GOV-results asserts against
    # this very run, then finalised with the measured values.
    from . import welsh_gates8 as _wg7          # v8 pack (V4.15, D84)
    from .vendor_welsh_gates_v8 import (MANIFEST_HASH as _v7mh,
                                        VERSION as _v7v)
    import hashlib as _hl
    from .common import GENERATED_DIR as _gdir
    _ev_path = str(_gdir / "welsh_gate_evidence_build.ndjson.gz")
    # D82: the V4.9 baseline (English + Welsh hashes + FT-11 key set)
    _bl = _wg7.BASELINE_PATH
    _bm = package.setdefault("buildMetadata", {})
    # D68/D78/D81: pre-seed the stamp with the IDENTITY of this very run
    # (runner, manifest, mode) and no score, so GOV-identity and
    # GOV-rerun assert against the run that is about to happen; the
    # measured values — one plain headline and the pending list — are
    # written back after it.
    _bm["gateResults"] = {
        "runner": _v7v,
        "runnerSha256": _hl.sha256(
            _wg7.RUNNER_PATH.read_bytes()).hexdigest(),
        "manifestHash": _v7mh, "mode": "dev",
        # D81: a plain headline even before measurement — nothing counted
        # yet — so the pre-seed is a well-formed stamp, never a condition
        "blockingPass": 0, "blockingTotal": 0, "headline": "0/0", "pending": [],
        "evidenceSha256": None, "baselineSha256": None}
    import os as _os
    # D82 (V4.15): SSS_EMIT_LOCK=<path> re-emits the Welsh baseline from
    # this build after a ruling moved the corpus — against the previous lock
    # first (English and FT-11 must be unchanged), then the stamp is taken
    # against the new lock. SSS_EMIT_LOCK_RULING names the ruling.
    _emit = _os.environ.get("SSS_EMIT_LOCK")
    # v6 (0.28.0): SSS_PREVIOUS_LOCK names the baseline THIS build is
    # asserted against — a school's own lock on a rebuild, or "none" for a
    # school's first build (there is nothing yet to assert; GOV-lock is
    # REPORT and the emitted lock becomes that school's baseline). Unset,
    # the prototype's behaviour is unchanged.
    _prev = _os.environ.get("SSS_PREVIOUS_LOCK")
    if _prev:
        _bl = Path("/nonexistent") if _prev.lower() == "none" else Path(_prev)
        if _prev.lower() != "none" and not _bl.exists():
            raise SystemExit(f"SSS_PREVIOUS_LOCK names a lock that does not exist: {_prev}")
    elif _emit:
        # the PREVIOUS lock is always the V4.8/V4.9 lock (the last one the
        # English was proven against); the emitted lock supersedes it
        from .common import CONFIG_DIR as _cfg
        _bl = _cfg / "02c_lock_V48_v7.json"
    _gf6, _gres6, _gn6, _stamp6 = _wg7.run(
        package, mode="dev", evidence_path=_ev_path,
        baseline_path=("none" if (_prev and _prev.lower() == "none")
                       else str(_bl) if _bl.exists() else None),
        emit_lock_path=_emit,
        emit_lock_ruling=_os.environ.get("SSS_EMIT_LOCK_RULING",
                                         "Framework v2.7 sheet 60 (D84–D87)") if _emit else None)
    _bm["gateResults"] = _stamp6
    for gfail in _gf6:
        check(errors, False, gfail)
    for gn in _gn6:
        warnings.append(gn)

    warnings.append("View-level rule of five only (agreed 2026-07-20): suppressed view "
                    "bases may be derivable by subtraction from visible parent totals. "
                    "Documented for disclosure sign-off in Appendix I11 / LIMITATIONS.md.")
    return errors, warnings


STACK_CODES = ["less_weekly", "once_week", "twice_week", "three_plus", "dont_know"]


def _stacked_sport_freq(rows, sport_labels, top_n=10):
    """v3 (build 010): stacked top-N sport x frequency data.

    Returns {context: [[sportLabel, [lt, w1, w2, w3plus, dk], base], ...]}
    for the four settings plus 'overall'. Overall counts each pupil once
    per sport at their highest frequency across settings.
    """
    from collections import Counter, defaultdict
    ORDER = {"dont_know": 0, "less_weekly": 1, "once_week": 2,
             "twice_week": 3, "three_plus": 4}
    out = {}
    contexts = {"pe_lessons": [], "school_club": [], "community_club": [],
                "somewhere_else": []}
    overall = []
    for r in rows:
        psf = r.get("per_sport_freq") or {}
        best = {}
        for (setting, sp), code in psf.items():
            contexts[setting].append((sp, code))
            if sp not in best or ORDER[code] > ORDER[best[sp]]:
                best[sp] = code
        overall.extend(best.items())
    for name, pairs in list(contexts.items()) + [("overall", overall)]:
        per_sport = defaultdict(Counter)
        for sp, code in pairs:
            per_sport[sp][code] += 1
        ranked = sorted(per_sport.items(),
                        key=lambda kv: -sum(kv[1].values()))[:top_n]
        # D70 (v2.0, sheet 46): every row carries the STABLE OPTION CODE of
        # its sport as a fourth element; the renderer resolves the display
        # label at the language boundary through optsCy. The English label
        # stays in position 0 so review evidence remains readable.
        out[name] = [[sport_labels.get(sp, sp),
                      [c.get(k, 0) for k in STACK_CODES],
                      sum(c.values()), sp] for sp, c in ranked]
    return out


def _participation_variation(records):
    """v2 (Sport Wales feedback): aggregated participation-variation table.

    Weekly+ club sport (school or community) for each aggregated
    characteristic group, on the whole-school accepted base. Exact raw
    counts - these are chart-derived-style groups, not year-and-gender
    views, so the view-level rule of five does not apply.
    """
    weekly = {"once_week", "twice_week", "three_plus"}

    def row(label, pred, definition=""):
        grp = [r for r in records if pred(r)]
        n = sum(1 for r in grp if r.get("organised_freq") in weekly)
        b = len(grp)
        pct = round(100 * n / b) if b >= 10 else None
        return {"label": label, "n": n, "base": b, "pct": pct,
                "def": definition}

    return [
        row("All pupils", lambda r: True),
        row("Boys", lambda r: r.get("gender") == "boy"),
        row("Girls", lambda r: r.get("gender") == "girl"),
        row("Primary phase (Years 3–6)", lambda r: r.get("year") in (3, 4, 5, 6)),
        row("Secondary phase (Years 7–11)",
            lambda r: r.get("year") in (7, 8, 9, 10, 11)),
        row("Pupils with a disability or long-term condition",
            lambda r: r.get("disability") == "yes"),
        row("Pupils without a disability or long-term condition",
            lambda r: r.get("disability") == "no"),
        row("Pupils with a learning difficulty",
            lambda r: r.get("learning") == "yes"),
        row("Pupils without a learning difficulty",
            lambda r: r.get("learning") == "no"),
        row("Welsh speakers", lambda r: r.get("welsh") in
            ("very_well", "fair_amount"),
            "spoke Welsh very well or a fair amount"),
        row("Pupils from ethnically diverse backgrounds",
            lambda r: r.get("ethnicity") in ("mixed", "asian", "other_grouped"),
            "selected any ethnic group other than White"),
    ]


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    xlsx = sys.argv[1]
    outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else GENERATED_DIR
    outdir.mkdir(parents=True, exist_ok=True)

    profile, mapping, metrics_cfg, narratives_cfg = load_config()
    threshold = profile["suppressionThreshold"]

    records, log, build_meta, discovered = load_and_normalise(
        xlsx, accepted_statuses=profile.get("acceptedStatuses"),
        available_years=profile.get("availableYears"))
    sport_labels = discovered["participated"]
    # V4.2: Welsh renderer needs code -> English label for slot lookups
    from . import welsh_render as _wr
    _wr.register_code_labels({**discovered["participated"],
                              **discovered["demand"]})
    defs = restrict_year_options(build_metric_defs(metrics_cfg, discovered), profile)
    cohorts = build_cohorts(metrics_cfg, defs, records,
                            held=load_held_cohorts(), log=log)
    engine = StateEngine(records, defs, cohorts, profile, threshold).compute_all()
    narrator = FullNarrator(engine, defs, cohorts, profile, threshold)

    states = {}
    for scope in SCOPES:
        for gender in GENDERS:
            for ck in engine.cohort_keys:
                key = state_key(scope, gender, ck)
                if key in engine.suppressed:
                    from .narrative2 import Scope
                    S = Scope(scope, gender, ck, cohorts, profile)
                    states[key] = {"sup": 1, "scope": S.as_dict()}
                    continue
                built = narrator.build_state(key)
                from .engine import filter_rows as _fr
                _rows = _fr(records, scope, gender, ck, cohorts, defs,
                            engine.scope_years)
                built["stk"] = _stacked_sport_freq(_rows, sport_labels)
                # v4 (build 011): per-view disability/learning-difficulty
                # display mode - sep / comb / sup (owner three-tier rule)
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
                # v5 (build 012): "all" means every option is selectable -
                # expand for the client, which expects a code list
                if k_src == "cohort_codes" and v == "all":
                    v = [c for c, _ in d["options"]]
                metric_defs_out[mid][k_dst] = v
        # V4.2: Welsh option labels from the framework lexicon (sheet 23);
        # the D32 grids select between the dual-scale readings
        from .welsh_render import label_cy as _lcy, grid_of as _grid_of
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

    from .welsh import lexicon as _wlex, misses as _wmisses
    _handoff = _wlex().get("handoff", [])
    welsh_block = {
        # Strings quoted by the framework itself (sheets 24/26/28) -
        # ATTESTED or framework-DERIVED; everything else awaits the
        # translator's handoff and falls back to English, flagged.
        "ui": {
            "based_on": "Yn seiliedig ar:",
            "pupil": "disgybl",
            "pupils": "disgybl",              # singular after every numeral
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
        # D63/D66 (v1.9) — see staged_build.do_assemble, mirrored here
        "frames": _wlex().get("interface_frames", {}),
        "stackLegend": _wlex().get("stack_legend", []),
        # D74 (see staged_build): CONTRACT separators as data
        "separators": _wlex().get("separators", {}),
    }
    # D75 / sheet 50: the count-NP tables are LEXICAL data read from the
    # workbook and emitted verbatim (cross-checked against the numeral
    # service; a disagreement fails the build). Casing is the client's
    # "initial" role, applied at realisation and nowhere else.
    from .welsh_payload import (count_np_tables as _cnp19,
                                static_manifest as _static19,
                                identity as _identity_of19)
    welsh_block["countNP"] = _cnp19(_wlex())
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
    if welsh_block.get("handoffMissing") is None:
        welsh_block["handoffMissing"] = sum(
            1 for v in welsh_block["handoff"].values() if not v)
    for _mid19, _md19 in metric_defs_out.items():
        _md19["labelCy"] = (welsh_block["handoff"].get(_mid19)
                            or f"⟪missing:{_mid19}⟫")
        if _md19.get("baseNote"):
            _bk19 = f"{_mid19}_base_note"
            _md19["baseNoteCy"] = (welsh_block["handoff"].get(_bk19)
                                   or f"⟪missing:{_bk19}⟫")
    # D79: the static lane is BOUND — welsh.static is the manifest the
    # client swaps from; the build fails on any unbound row or node.
    welsh_block["static"], _lane19 = _static19(
        welsh_block["handoff"], _wlex(), profile["schoolName"])
    _identity19 = _identity_of19(_wlex())
    _sc19 = {"module": 0, "h1": 0, "h2": 0, "scope": 0,
             "opts": sum(len(d.get("opts") or [])
                         for d in metric_defs_out.values())}
    for _st19 in states.values():
        for _m19 in (_st19.get("mod") or {}).values():
            _sc19["module"] += len(_m19.get("p") or [])
        for _v19 in (_st19.get("h1") or {}).values():
            _sc19["h1"] += sum(1 for x in _v19 if isinstance(x, dict))
        _sc19["h2"] += sum(1 for x in (_st19.get("h2") or [])
                           if isinstance(x, dict) and x.get("c"))
        _sc19["scope"] += 1
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
                          "identity": _identity19,
                          "welshFramework": _identity19["frameworkVersion"],
                          "welshFrameworkSha256": _identity19["frameworkSha256"],
                          "welshFrameworkFile": _identity19["frameworkFile"],
                          "gateManifestHash": _identity19["manifestHash"],
                          "gateRunnerVersion": _identity19["runnerVersion"],
                          "surfaceCounts": _sc19,
                          "mode": _identity19["mode"],
                          "staticLane": _lane19,
                          "provisionalRulings": __import__(
                              "pipeline.welsh", fromlist=["pr_set"]).pr_set(),
                          "suppressionThreshold": threshold,
                          "suppressionModel": "view-level rule of five (2026-07-20)"},
        "school": {
            "id": profile["schoolId"], "name": profile["schoolName"],
            "localAuthority": profile["localAuthority"],
            "profile": profile["profileId"], "years": profile["availableYears"],
            # V6.0 (EN-11): true when a year inside the profile's range is not taught/answered
            "yearsGap": profile["availableYears"] != list(range(profile["availableYears"][0], profile["availableYears"][-1] + 1)),
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

    errors, warnings = run_qa_checks(engine, package, records, narrator)

    report_path = outdir / f"{SCHOOL_SLUG}.report.json"
    report_path.write_text(json.dumps(package, ensure_ascii=False,
                                      separators=(",", ":")), encoding="utf-8")

    with (outdir / f"{SCHOOL_SLUG}.qa.csv").open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["filter_state", "metric_id", "question", "option_code", "option_label",
                    "respondent_count", "valid_base", "status"])
        for key in sorted(states):
            st = states[key]
            if st.get("sup"):
                w.writerow([key, "", "", "", "", "", "", "view_suppressed"])
                continue
            for mid, m in st["m"].items():
                d = defs[mid]
                if m["s"] != "ok":
                    w.writerow([key, mid, d["question"], "", "", "", "", m["s"]])
                    continue
                for (code, label), v in zip(d["options"], m["v"]):
                    if v in (0, None) and v != 0:
                        continue
                    if v == 0:
                        continue
                    w.writerow([key, mid, d["question"], code, label,
                                v if v is not None else "view suppressed", m["b"], "ok"])

    with (outdir / f"{SCHOOL_SLUG}.narrative-audit.csv").open(
            "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["filter_state", "module", "kind",
                                          "template_id", "facts", "rendered_text"])
        w.writeheader()
        w.writerows(narrator.audit)

    used_tids = sorted({r["template_id"] for r in narrator.audit})
    cat = ["# Narrative template catalogue", "",
           "Named core templates (pipeline/narrative2.py):", ""]
    cat += [f"- `{k}`: {v}" for k, v in TEMPLATES.items()]
    cat += ["", "Composed module templates used in this build:", ""]
    cat += [f"- `{t}`" for t in used_tids]
    (outdir / "narrative-templates.md").write_text("\n".join(cat), encoding="utf-8")

    # graph-colour mapping document (Corrective Brief deliverable 22)
    cyc = ["red", "blue", "grey"]
    cm = ["# Graph colour mapping (Prototype 3 corrected)", "",
          "Single-series bars cycle red → blue → grey by the answer's canonical",
          "option index, so each answer keeps its colour in every filter state.",
          "A selected value is overridden with yellow (blue outline + tick) and",
          "returns to its stored colour when deselected. Boys/girls comparison",
          "series use blue/red. Missing values use diagonal hatching.", ""]
    for mid, d in defs.items():
        if d["chart"] == "table_only":
            continue
        cm.append(f"## {mid}")
        for i, (code, label) in enumerate(d["options"]):
            cm.append(f"- {label} (`{code}`): {cyc[i % 3]}")
        cm.append("")
    (outdir / "colour-mapping.md").write_text("\n".join(cm), encoding="utf-8")

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
        f"narrative paragraphs: {len(narrator.audit)}",
        "",
        "warnings:",
    ]
    seen = set()
    for wmsg in log.warnings:
        if wmsg not in seen:
            seen.add(wmsg)
            lines.append(f"  - {wmsg}")
    lines += ["", "automated QA checks:"]
    lines += ([f"  FAIL  {e}" for e in errors] or
              ["  PASS  reconciliation, scope, tautology, placeholder and wording checks"])
    lines += [f"  NOTE  {w}" for w in warnings]
    (outdir / "validation-summary.txt").write_text("\n".join(lines), encoding="utf-8")

    print(f"report package: {report_path} ({report_path.stat().st_size/1e6:.1f} MB)")
    print(f"states: {len(states)}  paragraphs: {len(narrator.audit)}")
    print(f"QA: {'FAIL ' + str(len(errors)) if errors else 'PASS'}")
    if errors:
        for e in errors[:15]:
            print("  ", e)
        raise SystemExit(1)


if __name__ == "__main__":
    main()

# EOF sentinel
