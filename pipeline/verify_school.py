# -*- coding: utf-8 -*-
"""Independent figure check for one real-school build (V5.0, pipeline 0.28.0).

    python -m pipeline.verify_school <stage2.parquet> <school profile.json> <report.json> [<out.json>]

Recomputes the whole-school figures straight from the cleansed dataset —
its own code path, none of the pipeline's loader, converter, engine or
label maps — and compares them with the shipped package's whole|all|none
state: accepted rows, responses by year and by sex, disability / learning
difficulty / Welsh-speaking / join-in / ideas-listened distributions, the
enjoyment and confidence grids, the ethnicity profile, the any-activity
headline, and the two square-root weekly-frequency estimates (D: flat
square-root method, Welsh Government submission method). A mismatch is a
defect in one side or the other; the result is written as JSON.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pyarrow.parquet as pq

SETTINGS = ["pe", "school_club", "outside_club", "somewhere_else"]
FREQ_W = {1: 3, 2: 2, 3: 1}          # three+ / twice / once a week; 4 = less than weekly; 5 = don't know


def band(entries, lw, dk):
    if entries:
        est = sum(entries) / math.sqrt(len(entries))
        b = int(est + 0.5)
        return "e9plus" if b >= 9 else f"e{max(b, 1)}"
    if lw:
        return "less_weekly_only"
    if dk:
        return "dont_know_only"
    return "none_reported"


def main():
    parq, prof_p, rep_p = sys.argv[1], sys.argv[2], sys.argv[3]
    out_p = sys.argv[4] if len(sys.argv) > 4 else None
    prof = json.loads(Path(prof_p).read_text(encoding="utf-8"))
    pk = json.loads(Path(rep_p).read_text(encoding="utf-8"))
    years = set(prof["availableYears"])
    names = pq.ParquetFile(parq).schema_arrow.names
    fcols = {(st, n[len(f"sport_freq_{st}__"):-5]): n for st in SETTINGS for n in names
             if n.startswith(f"sport_freq_{st}__") and n.endswith("_code")}
    scols = [n for n in names if n.startswith("sport_setting_")]
    tbl = pq.read_table(parq, filters=[("school_id", "=", prof["schoolId"])])
    rows = [r for r in tbl.to_pylist()
            if r.get("year_group_num") is not None and int(r["year_group_num"]) in years
            and (r.get("status") == "completed" or "Partial" in prof.get("acceptedStatuses", ["Complete"]))]
    res = {"school": pk["school"]["name"], "acceptedRows": {"package": pk["buildMetadata"]["acceptedRows"], "recomputed": len(rows)}}
    whole = pk["states"]["whole|all|none"]
    if "m" not in whole:
        # V6.0 (owner instruction, 22 Sep 2026): a school with fewer than five accepted
        # responses still receives a report; its whole-school view — and therefore every
        # view — is suppressed by the rule of five. The independent check then verifies
        # the suppression itself: the recomputed accepted count is under five, the
        # package says so, and no state in the package carries a figure.
        with_figures = [k for k, st in pk["states"].items() if isinstance(st, dict) and "m" in st]
        res["suppressedWholeSchool"] = {"package": bool(whole.get("sup")), "recomputedUnderFive": len(rows) < 5,
                                        "statesWithFigures": len(with_figures), "match": bool(whole.get("sup")) and len(rows) < 5 and not with_figures}
        res["allMatch"] = res["suppressedWholeSchool"]["match"] and res["acceptedRows"]["package"] == res["acceptedRows"]["recomputed"]
        txt = json.dumps(res, indent=1, ensure_ascii=False)
        if out_p:
            Path(out_p).write_text(txt, encoding="utf-8")
        print(txt if not out_p else f"{res['school']}: allMatch={res['allMatch']} (whole-school view suppressed, {len(rows)} accepted) -> {out_p}")
        sys.exit(0 if res["allMatch"] else 1)
    W = whole["m"]

    # V6.0 (pipeline 0.31.1, pilot of 23 Sep 2026 — first seen at six small
    # schools): the two profile charts blank a bar whose corresponding VIEW is
    # suppressed by the rule of five (engine.py, suppression policy v2: the
    # year × gender profile charts must not print the very number a suppressed
    # view withholds). The independent check therefore verifies the mask as
    # well as the figures: a blanked bar (None) is right exactly when the
    # recomputed count of that view is under the threshold, and a shown bar
    # must equal the recomputed count. Other codes (non-binary, not stated)
    # are never views, so they are shown exact. Nothing under five is written
    # to the check's output for a blanked bar — only the verdict.
    TH = int(pk.get("buildMetadata", {}).get("suppressionThreshold", 5) or 5)
    VIEW_CODES = {"responses_by_year": lambda code: code.startswith("y"),
                  "responses_by_gender": lambda code: code in ("boy", "girl")}

    def cmp(mid, counts_by_code, base=None):
        d = pk["metricDefs"][mid]; m = W[mid]
        got = [counts_by_code.get(code, 0) for code, _ in d["opts"]]
        pv = m.get("v")
        if mid in VIEW_CODES and isinstance(pv, list) and len(pv) == len(got):
            is_view = VIEW_CODES[mid]
            ok = True; masked = 0
            for (code, _), shown, real in zip(d["opts"], pv, got):
                if shown is None:
                    ok = ok and is_view(code) and real < TH; masked += 1
                else:
                    ok = ok and shown == real and not (is_view(code) and real < TH)
            entry = {"codes": [c for c, _ in d["opts"]], "package": pv,
                     "recomputed": [None if (v is None) else r for v, r in zip(pv, got)],
                     "blankedBars": masked, "blankedBarsUnderThreshold": ok, "match": ok}
        else:
            entry = {"codes": [c for c, _ in d["opts"]], "package": pv, "recomputed": got, "match": pv == got}
        if base is not None:
            entry["base"] = {"package": m.get("b"), "recomputed": base, "match": m.get("b") == base}
        res[mid] = entry

    def dist(key, mapping):
        c = {}
        for r in rows:
            v = r.get(key)
            if v is None:
                continue
            code = mapping[v]
            c[code] = c.get(code, 0) + 1
        return c, sum(c.values())

    # years / sex (base = accepted rows)
    cy = {}
    for r in rows:
        k = f"y{int(r['year_group_num'])}"; cy[k] = cy.get(k, 0) + 1
    cmp("responses_by_year", cy, len(rows))
    cg, _ = dist("gender", {"a boy": "boy", "a girl": "girl", "non-binary": "nonbinary", "I'd prefer not to say": "not_stated"})
    cmp("responses_by_gender", cg, len(rows))
    yn = {"Yes": "yes", "No": "no", "Not sure": "not_sure", "Prefer not to say": "prefer_not_to_say"}
    c, b = dist("condition_1", yn); cmp("disability_condition", c, b)
    c, b = dist("condition_2", yn); cmp("learning_difficulty", c, b)
    c, b = dist("welsh_ability", {"I can speak Welsh very well": "very_well", "I can speak a fair amount of Welsh": "fair_amount",
                                  "I can speak a little Welsh": "a_little", "I can say just a few words in Welsh": "few_words",
                                  "I do not speak Welsh": "none"}); cmp("welsh_speaking", c, b)
    c, b = dist("enjoy_pe", {"Yes, always": "always", "Yes, sometimes": "sometimes", "No, not often": "not_often", "Never": "never"}); cmp("join_in_easily", c, b)
    c, b = dist("take_part", {"Always": "always", "Sometimes": "sometimes", "Not often": "not_often", "Never": "never"}); cmp("ideas_listened", c, b)
    hm = {"A lot": "a_lot", "A little": "a_little", "Not much": "not_much", "Not at all": "not_at_all", "Not sure": "not_sure"}
    c, b = dist("grid_howmuch__pe_lessons", hm); cmp("enjoy_pe", c, b)
    c, b = dist("grid_howmuch__school_sports_clubs", hm); cmp("enjoy_school_clubs", c, b)
    c, b = dist("grid_howmuch__sports_clubs_outside_of_school", hm); cmp("enjoy_community_clubs", c, b)
    c, b = dist("grid_howmuch__other_settings_like_in_the_park_or_garden", hm); cmp("enjoy_other_settings", c, b)
    sc = {"Very": "very", "Quite": "quite", "Not very": "not_very", "Not at all": "not_at_all"}
    c, b = dist("grid_confidence__try_a_new_sport", sc); cmp("confidence_try_new", c, b)
    c, b = dist("grid_feel__healthy", sc); cmp("pe_feel_healthy", c, b)
    # ethnicity profile (whole-school table)
    eth = {}
    for r in rows:
        v = r.get("ethnicity")
        if v:
            eth[v] = eth.get(v, 0) + 1
    order = ["White", "Mixed or multiple ethnic groups", "Asian, Asian Welsh, or Asian British",
             "Black, Black Welsh, Black British, Caribbean, or African", "Other ethnic groups [for example, Arab]", "I'm not sure", "Prefer not to say"]
    res["ethnicityProfile"] = {"package": [n for _, n in pk["buildMetadata"]["ethnicityProfile"]],
                               "recomputed": [eth.get(k, 0) for k in order]}
    res["ethnicityProfile"]["match"] = res["ethnicityProfile"]["package"] == res["ethnicityProfile"]["recomputed"]
    # any activity: any setting selected for any sport
    any_act = sum(1 for r in rows if any(r.get(cn) == 1 for cn in scols))
    res["anyActivity"] = {"package": pk["anyActivity"], "recomputed": any_act, "match": pk["anyActivity"] == any_act}
    # the two square-root estimates
    ov, cb = {}, {}
    for r in rows:
        e_all, e_club, lw_all, dk_all, lw_c, dk_c = [], [], False, False, False, False
        for (st, sp), col in fcols.items():
            code = r.get(col)
            if code is None:
                continue
            code = int(code)
            club = st in ("school_club", "outside_club")
            if code in FREQ_W:
                e_all.append(FREQ_W[code])
                if club:
                    e_club.append(FREQ_W[code])
            elif code == 4:
                lw_all = True; lw_c = lw_c or club
            elif code == 5:
                dk_all = True; dk_c = dk_c or club
        k = band(e_all, lw_all, dk_all); ov[k] = ov.get(k, 0) + 1
        k2 = band(e_club, lw_c, dk_c); cb[k2] = cb.get(k2, 0) + 1
    cmp("freq_estimate", ov, len(rows))
    cmp("club_freq_estimate", cb, len(rows))
    res["allMatch"] = all(v.get("match", True) and v.get("base", {}).get("match", True)
                          for v in res.values() if isinstance(v, dict)) and res["acceptedRows"]["package"] == res["acceptedRows"]["recomputed"]
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if out_p:
        Path(out_p).write_text(txt, encoding="utf-8")
    print(txt if not out_p else f"{res['school']}: allMatch={res['allMatch']} -> {out_p}")
    if not res["allMatch"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
