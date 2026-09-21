"""Metric calculation and filter-state generation (v2).

Suppression policy v2 (agreed 2026-07-20, recorded in Appendix I11):
  - The rule of five applies to the SELECTED VIEW only: a view (phase/year x
    gender x selected group) with fewer than five respondents is fully
    suppressed and shows a "broaden your view" message.
  - Within a reportable view, exact counts are displayed even when below
    five, including question-specific bases below five, because the
    respondents behind those counts are not identifiable.
  - Two documented exceptions:
      * the year/gender profile charts blank a bar whose corresponding VIEW
        is suppressed (otherwise the chart would print the very number the
        suppressed view withholds);
      * ethnicity categories with fewer than five respondents school-wide
        are pre-aggregated in normalisation.
  - Cross-view complementary suppression was considered and deliberately
    NOT applied: small suppressed views may be derivable by subtraction from
    visible parent totals. Accepted and documented for disclosure sign-off.
"""
from __future__ import annotations

from .common import LABELS

TH_DEFAULT = 5

SCOPES = ["whole", "primary", "secondary"] + [f"y{n}" for n in range(3, 12)]
GENDERS = ["all", "boy", "girl"]
PHASE_FAMILIES = {"primary": [f"y{n}" for n in range(3, 7)],
                  "secondary": [f"y{n}" for n in range(7, 12)]}
# v6 (0.28.0, V5.0 real-school round): the twelve internal scopes are always
# computed. A profile that lists only the scopes its school teaches (a
# primary school: whole + Years 3–6) gets the structural year sets for the
# rest, so those states exist, hold no rows, are suppressed by the rule of
# five and are never offered — the filter offers the profile's groups only.
STRUCTURAL_SCOPE_YEARS = {"primary": set(range(3, 7)), "secondary": set(range(7, 12)),
                          **{f"y{n}": {n} for n in range(3, 12)}}


def restrict_year_options(defs, profile):
    """v6: the profile chart 'responses by year group' shows the school's
    years only (availableYears); unchanged for a 3–11 profile."""
    years = profile.get("availableYears")
    if years and "responses_by_year" in defs:
        keep = {f"y{n}" for n in years}
        d = defs["responses_by_year"]
        d["options"] = [(c, l) for c, l in d["options"] if c in keep]
    return defs

# response targets per year group (SmartSurvey dashboard guidance)
YEAR_TARGETS = {3: 15, 4: 15, 5: 15, 6: 15, 7: 22, 8: 22, 9: 22, 10: 22, 11: 22}

ANSWERED_FLAGS = {
    "sports": "sports_answered",
    "settings": "settings_answered",
    "demand": "demand_answered",
    "unmet": "unmet_answered",
    "more_if": "more_if_answered",
    "important": "important_answered",
    "pe_sports": "pe_lessons_sports_answered",
    "school_club_sports": "school_club_sports_answered",
    "community_club_sports": "community_club_sports_answered",
    "other_setting_sports": "somewhere_else_sports_answered",
    # v3 (build 010): group-restricted settings charts
    "settings_dl": "settings_dl_answered",
    "settings_dy": "settings_dy_answered",
    "settings_ly": "settings_ly_answered",
    "settings_ed": "settings_ed_answered",
    "settings_wl": "settings_wl_answered",
}
ROUTED_FLAGS = {
    "community_freq": "community_routed",
    "school_club_freq": "school_club_routed",
    "pe_freq": "pe_freq_routed",
    "other_freq": "other_freq_routed",
    "welsh_sport": "welsh_sport_routed",
    "take_part": "take_part_routed",
    # v2.2 accumulated per-setting frequency fields (decision P06)
    "acc_pe_lessons_cat": "pe_freq_routed",
    "acc_school_club_cat": "school_club_routed",
    "acc_community_club_cat": "community_routed",
    "acc_somewhere_else_cat": "other_freq_routed",
}


def state_key(scope, gender, cohort):
    return f"{scope}|{gender}|{cohort}"


def get_field(rec, field):
    if "." in field:
        head, tail = field.split(".", 1)
        return rec[head].get(tail)
    return rec[field]


def _label_map_for(mid):
    freq = LABELS["freq"]
    conf = LABELS["confidence"]
    enjoy = LABELS["enjoy"]
    table = {
        "responses_by_year": LABELS["years"],
        "responses_by_gender": LABELS["gender_display"],
        "organised_freq": LABELS["organised_freq"],
        "overall_freq": LABELS["overall_freq"],
        "freq_estimate": LABELS["freq_estimate"],
        "club_freq_estimate": LABELS["club_freq_estimate"],
        "settings_dl": LABELS["settings"],
        "settings_dy": LABELS["settings"],
        "settings_ly": LABELS["settings"],
        "settings_ed": LABELS["settings"],
        "settings_wl": LABELS["settings"],
        "participation_settings": LABELS["settings"],
        # v2.2: per-setting frequency uses the same raw accumulated
        # construction as the overall measure (meeting decision P06)
        "community_club_freq": LABELS["setting_acc"],
        "school_club_freq": LABELS["setting_acc"],
        "pe_freq": LABELS["setting_acc"],
        "other_setting_freq": LABELS["setting_acc"],
        "join_in_easily": LABELS["join_in"],
        "welsh_speaking": LABELS["welsh"],
        "welsh_when_playing_sport": LABELS["yes_no"],
        "disability_condition": LABELS["disability"],
        "learning_difficulty": LABELS["disability"],
        "dl_combined": LABELS["yes_no"],
        "ed_combined": LABELS["yes_no"],
        "ws_combined": LABELS["yes_no"],
        "take_part_method": LABELS["take_part"],
        "ethnicity_group": LABELS["ethnicity"],
        "would_do_more_if": LABELS["more_if"],
        "most_important": LABELS["important"],
        "pe_feel_healthy": conf, "pe_feel_confident": conf, "pe_feel_ready": conf,
        "enjoy_pe": enjoy, "enjoy_school_clubs": enjoy,
        "enjoy_community_clubs": enjoy, "enjoy_other_settings": enjoy,
        "confidence_try_new": conf, "confidence_learn_skill": conf,
        "confidence_try_again": conf, "confidence_new_place": conf,
        "ideas_listened": LABELS["listened"],
    }
    return table[mid]


def build_metric_defs(metrics_cfg, discovered):
    defs = {}
    for mid, m in metrics_cfg["metrics"].items():
        options = m["options"]
        if options == "discover_participated":
            src = discovered["participated"]
            codes = sorted(src.keys(), key=lambda c: src[c])
            opts = [(c, src[c]) for c in codes]
        elif options == "discover_demand":
            src = discovered["demand"]
            codes = sorted(src.keys(), key=lambda c: src[c])
            opts = [(c, src[c]) for c in codes]
        else:
            label_map = _label_map_for(mid)
            opts = [(c, label_map[c]) for c in options]
        defs[mid] = {**m, "id": mid, "options": opts}
    return defs


# v2.4 (owner rule): sensitive characteristic filters are only offered
# where at least five pupils school-wide gave that answer.
SENSITIVE_MIN5_PREFIXES = {"dy", "ly", "et", "wl", "tp", "ov", "dl", "ed", "ws",
                           # v5 (build 012): rule-of-five cap on every
                           # selectable answer group (owner decision)
                           "cb", "gd", "gy", "gl", "ge", "gw",
                           "sp", "wd", "eb", "ec", "eo", "cs", "cg", "cn"}


def build_cohorts(metrics_cfg, defs, records=None, held=None, log=None):
    """held (v6): {cohort key: {reason, needs}} — cohorts the Framework
    cannot yet render in Welsh (see common.load_held_cohorts). A held key
    is not offered; the hold is logged as a build warning when it bites."""
    cohorts = {}
    held = held or {}
    for mid, src in metrics_cfg["cohort_sources"].items():
        d = defs[mid]
        label_lookup = dict(d["options"])
        codes = d.get("cohort_codes", [])
        if codes == "all":     # v5 (build 012): every option selectable
            codes = [c for c, _ in d["options"]]
        for code in codes:
            if code not in label_lookup:
                continue
            key = f"{src['prefix']}_{code}"
            if key in held:
                n = (sum(1 for r in records if cohort_member(
                    r, {"metric": mid, "code": code}, defs))
                     if records is not None else None)
                # the hold is reported only where it bites: a group the
                # rule-of-five cap would not offer anyway is not a hold
                if log is not None and (n is None or n >= 5 or
                                        src["prefix"] not in SENSITIVE_MIN5_PREFIXES):
                    log.warn(f"cohort {key} HELD (not offered as a filter; its bar stays, "
                             f"non-selectable){'' if n is None else f' — {n} pupils'}: "
                             f"{held[key].get('reason', '')} Needs: {held[key].get('needs', '')}")
                continue
            cdef = {
                "label": src["label_template"].format(option=label_lookup[code]),
                "metric": mid,
                "code": code,
                "optionLabel": label_lookup[code],
            }
            if (records is not None and
                    src["prefix"] in SENSITIVE_MIN5_PREFIXES):
                n = sum(1 for r in records if cohort_member(r, cdef, defs))
                if n < 5:
                    continue
            cohorts[key] = cdef
    return cohorts


def cohort_member(rec, cohort_def, defs):
    mid, code = cohort_def["metric"], cohort_def["code"]
    field = defs[mid]["field"]
    if defs[mid]["type"] == "multi_select":
        return code in get_field(rec, field)
    return get_field(rec, field) == code


def filter_rows(records, scope, gender, cohort_key, cohorts, defs, scope_years):
    out = []
    for r in records:
        if scope != "whole" and r["year"] not in scope_years[scope]:
            continue
        if gender != "all" and r["gender"] != gender:
            continue
        if cohort_key != "none" and not cohort_member(r, cohorts[cohort_key], defs):
            continue
        out.append(r)
    return out


def compute_metric(rows, d):
    """{status: ok|nd|na, base, raw:[int per option]}. No cell suppression."""
    field = d["field"]
    option_codes = [c for c, _ in d["options"]]

    if d["type"] == "multi_select":
        flag = ANSWERED_FLAGS[field]
        answered = [r for r in rows if r[flag]]
        base = len(answered)
        if base == 0:
            return {"status": "nd", "base": 0, "raw": [0] * len(option_codes)}
        raw = [sum(1 for r in answered if c in get_field(r, field)) for c in option_codes]
        return {"status": "ok", "base": base, "raw": raw}

    if d["base_rule"] == "routed":
        eligible = [r for r in rows if r[ROUTED_FLAGS[field]]]
        if not eligible:
            return {"status": "na", "base": 0, "raw": [0] * len(option_codes)}
        answered = [r for r in eligible if get_field(r, field) is not None]
        base = len(answered)
    elif d["base_rule"] == "accepted":
        answered = [r for r in rows if get_field(r, field) is not None]
        base = len(rows)
    else:
        answered = [r for r in rows if get_field(r, field) is not None]
        base = len(answered)
    if base == 0 or not answered:
        return {"status": "nd", "base": 0, "raw": [0] * len(option_codes)}
    vals = {}
    for r in answered:
        v = get_field(r, field)
        if v is not None:
            vals[v] = vals.get(v, 0) + 1
    raw = [vals.get(c, 0) for c in option_codes]
    return {"status": "ok", "base": base, "raw": raw}


class StateEngine:
    def __init__(self, records, defs, cohorts, profile, threshold=TH_DEFAULT):
        self.records = records
        self.defs = defs
        self.cohorts = cohorts
        self.threshold = threshold
        self.scope_years = {g["key"]: set(g["years"]) for g in profile["scopeGroups"]}
        for sc, ys in STRUCTURAL_SCOPE_YEARS.items():
            self.scope_years.setdefault(sc, set(ys))
        self.cohort_keys = ["none"] + list(cohorts.keys())
        self.bases = {}
        self.suppressed = {}          # key -> "threshold"
        self.results = {}             # key -> {metric_id: result}

    def compute_bases(self):
        for scope in SCOPES:
            for gender in GENDERS:
                for ck in self.cohort_keys:
                    rows = filter_rows(self.records, scope, gender, ck,
                                       self.cohorts, self.defs, self.scope_years)
                    self.bases[state_key(scope, gender, ck)] = len(rows)

    def primary_suppression(self):
        """Prototype 3 rule (Revision Brief section 16): the five-response
        threshold is evaluated against the WIDER DEMOGRAPHIC VIEW ONLY
        (phase/year x gender). Chart-derived selected groups are never given
        a second suppression test: if the demographic view is reportable,
        every selected-group overlay of it is reportable too, with exact
        counts shown however small."""
        for scope in SCOPES:
            for gender in GENDERS:
                if self.bases[state_key(scope, gender, "none")] < self.threshold:
                    for ck in self.cohort_keys:
                        self.suppressed[state_key(scope, gender, ck)] = "demographic_view"

    def coverage_mark(self, scope, gender, ck):
        """Provisional evidence-coverage heuristic (Module A6). Documented in
        Appendix I11; requires Sport Wales sign-off."""
        years = sorted(self.scope_years[scope])
        met = sum(1 for y in years
                  if self.bases[state_key(f"y{y}", "all", "none")] >= YEAR_TARGETS[y])
        base = self.bases[state_key(scope, gender, ck)]
        if gender != "all" or ck != "none":
            return "limited" if base < 30 else ("broad" if met == len(years) else "partial")
        if met == len(years):
            return "broad"
        if met * 2 >= len(years):
            return "partial"
        return "limited"

    def compute_all(self):
        self.compute_bases()
        self.primary_suppression()
        for scope in SCOPES:
            for gender in GENDERS:
                for ck in self.cohort_keys:
                    key = state_key(scope, gender, ck)
                    if key in self.suppressed:
                        continue
                    rows = filter_rows(self.records, scope, gender, ck,
                                       self.cohorts, self.defs, self.scope_years)
                    out = {}
                    for mid, d in self.defs.items():
                        exempt = d.get("exempt")
                        if exempt == "scope":
                            mrows = filter_rows(self.records, "whole", gender, ck,
                                                self.cohorts, self.defs, self.scope_years)
                        elif exempt == "gender":
                            mrows = filter_rows(self.records, scope, "all", ck,
                                                self.cohorts, self.defs, self.scope_years)
                        else:
                            mrows = rows
                        out[mid] = compute_metric(mrows, d)
                    self.results[key] = out

        # profile-chart sync: a bar whose corresponding VIEW is suppressed is
        # blanked (see module docstring). All other values are exact.
        for key, metrics in self.results.items():
            scope, gender, ck = key.split("|")
            for mid, res in metrics.items():
                d = self.defs[mid]
                if res["status"] != "ok":
                    res["disp"] = None
                    continue
                if mid == "responses_by_year":
                    res["disp"] = [None if state_key(code, gender, ck) in self.suppressed
                                   else res["raw"][i]
                                   for i, (code, _) in enumerate(d["options"])]
                elif mid == "responses_by_gender":
                    res["disp"] = [None if state_key(scope, code, ck) in self.suppressed
                                   else res["raw"][i]
                                   for i, (code, _) in enumerate(d["options"])]
                else:
                    res["disp"] = list(res["raw"])
        return self

# EOF sentinel
