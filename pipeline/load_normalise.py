"""Excel loader, schema validation and canonical response normalisation (v2).

Converts the SmartSurvey "Responses wide" sheet into canonical respondent
records. Columns are located by question id, never by cell address. The
canonical records are internal to the build and never reach the browser.

v2 additions (Content and Narrative Specification):
  - ethnicity top-level group (small groups aggregated - see notes below)
  - learning difficulty
  - per-setting sports (PE, school club, community club, other settings)
  - derived organised participation frequency outside the curriculum
    (highest frequency across SCHOOL CLUB and COMMUNITY CLUB settings -
    reproduces the agreed 106/29% whole-school headline)
  - unmet demand (desired sports not currently undertaken, label-crosswalked)
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from .common import (
    FREQ_ORDER,
    NON_SPORT_LABELS,
    RAW_TO_CODE,
    anon_id,
    file_checksum,
    norm_text,
    parse_matrix,
    slugify,
    split_multi,
)

SPORT_QIDS = [26871507, 26871508, 26871509, 26871510, 26871511,
              26871512, 26871513, 26871514, 26871515, 26871516]
SETTINGS_QIDS = [26871517, 26871518, 26871519, 26871520, 26871521,
                 26871522, 26871523, 26871524, 26871525, 26871526]
FREQ_GROUPS = {
    "pe_lessons": [26871531, 26871532, 26871533, 26871534, 26871535,
                   26871536, 26871537, 26871538, 26871539, 26871540],
    "school_club": [26871591, 26871592, 26871593, 26871594, 26871595,
                    26871596, 26871597, 26871598, 26871599, 26871600],
    "community_club": [26871541, 26871542, 26871543, 26871544, 26871545,
                       26871546, 26871547, 26871548, 26871549, 26871550],
    "somewhere_else": [26871568, 26871569, 26871570, 26871571, 26871572,
                       26871573, 26871574, 26871575, 26871576, 26871577],
}

REQUIRED_QIDS = [26871527, 26871497, 26871554, 26871551, 26871552, 26871586,
                 26871587, 26871565, 26871566, 26871588, 26871589, 26871567,
                 26871590, 26871504, 26871505, 26871506, 26871498] + \
                SPORT_QIDS + SETTINGS_QIDS + \
                [q for g in FREQ_GROUPS.values() for q in g]

# Desired-sport labels that differ from the participation label for the same
# activity. Applied when computing unmet demand.
DEMAND_TO_PARTICIPATION = {
    "fitness_activities_like_yoga_circuits_or_aerobics": "fitness_classes",
}

# Ethnic-group answers -> top-level codes. The two categories selected by a
# single respondent each in this export are aggregated into one combined
# category so that no pupil is individually identified by a demographic
# category of one (documented exception to the view-level rule of five -
# see LIMITATIONS.md and Appendix I11).
ETHNICITY_MAP = {
    "White": "white",
    "Mixed or multiple ethnic groups": "mixed",
    "Asian, Asian Welsh, or Asian British": "asian",
    "Black, Black Welsh, Black British, Caribbean, or African": "other_grouped",
    "Other ethnic groups [for example, Arab]": "other_grouped",
    "I'm not sure": "not_sure",
    "Prefer not to say": "prefer_not_to_say",
}


class ValidationLog:
    def __init__(self):
        self.exclusions: list[dict] = []
        self.warnings: list[str] = []

    def exclude(self, rid, reason):
        self.exclusions.append({"response_id": str(rid), "reason": reason})

    def warn(self, msg):
        self.warnings.append(msg)


def build_column_index(df: pd.DataFrame) -> dict[int, str]:
    idx = {}
    for col in df.columns:
        if col.startswith("Q_"):
            parts = col.split("_", 2)
            try:
                idx[int(parts[1])] = col
            except (ValueError, IndexError):
                continue
    return idx


def cell(row, qcol_index, qid):
    col = qcol_index.get(qid)
    if col is None:
        return None
    v = row.get(col)
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    return v


def map_single(raw, mapping: dict, log: ValidationLog, qname: str):
    if raw is None:
        return None
    label = norm_text(raw)
    if label in mapping:
        return mapping[label]
    log.warn(f"Unexpected answer for {qname}: {label!r} (treated as invalid)")
    return None


def load_and_normalise(xlsx_path: str, sheet: str = "Responses wide",
                       accepted_statuses=None, available_years=None):
    """Return (records, validation_log, build_meta, discovered_options).

    v6 (0.28.0, V5.0 real-school round): a school profile may widen the
    accepted completion statuses (the cleansed dataset's analytical set
    carries partial responses that reached page 48+, the data owner's
    inclusion rule) and restrict the year groups the school teaches; a
    year outside the profile's range is EXCLUDED with a logged reason,
    never silently dropped. Unset, the prototype's rules apply unchanged
    (status "Complete", Years 3–11)."""
    accepted = set(accepted_statuses or ["Complete"])
    years_ok = set(available_years or range(3, 12))
    log = ValidationLog()
    df = pd.read_excel(xlsx_path, sheet_name=sheet)
    qidx = build_column_index(df)

    missing = [q for q in REQUIRED_QIDS if q not in qidx]
    if missing:
        raise SystemExit(f"Missing required question columns: {missing}")
    for admin_col in ["Response_ID", "Completion_Status"]:
        if admin_col not in df.columns:
            raise SystemExit(f"Missing required administrative column: {admin_col}")

    dup = df["Response_ID"].duplicated().sum()
    if dup:
        log.warn(f"{dup} duplicate Response_ID values found - flagged, not auto-deleted")

    salt = file_checksum(xlsx_path)[:16]
    records = []
    status_counts: dict[str, int] = {}
    participated_labels: dict[str, str] = {}
    demand_labels: dict[str, str] = {}

    for _, row in df.iterrows():
        rid = row["Response_ID"]
        status = norm_text(row["Completion_Status"])
        if status not in accepted:
            log.exclude(rid, f"completion status '{status}' with no survey answers recorded"
                        if accepted == {"Complete"} else
                        f"completion status '{status}' outside the profile's accepted statuses")
            continue

        year_raw = cell(row, qidx, 26871554)
        year = None
        if year_raw is not None:
            label = norm_text(year_raw)
            if label.startswith("Year "):
                try:
                    year = int(label.split()[1])
                except ValueError:
                    year = None
        if year is None or year not in range(3, 12):
            log.exclude(rid, f"missing or invalid year group ({year_raw!r})")
            continue
        if year not in years_ok:
            log.exclude(rid, f"year group {year_raw!r} is not one the school's profile covers "
                             f"(Years {min(years_ok)}–{max(years_ok)})")
            continue

        screen = cell(row, qidx, 26871527)
        if screen is not None and norm_text(screen) != "Yes":
            log.warn(f"Response {anon_id(rid, salt)} answered {norm_text(screen)!r} to the "
                     "school screening question but completed the survey. Accepted to match "
                     "the SmartSurvey completed-response count; flagged for a decision.")

        status_counts[status] = status_counts.get(status, 0) + 1
        gender = map_single(cell(row, qidx, 26871497), RAW_TO_CODE["gender"], log, "gender")
        if gender is None:
            gender = "not_stated"
            log.warn(f"Response {anon_id(rid, salt)} has no usable gender answer; "
                     "recorded as not stated")

        rec = {
            "rid": anon_id(rid, salt),
            "year": year,
            "year_key": f"y{year}",
            "phase": "primary" if year <= 6 else "secondary",
            "gender": gender,
        }

        # ---- sports participated (10 category multi-selects) -------------
        sports = set()
        answered_sports = False
        for qid in SPORT_QIDS:
            v = cell(row, qidx, qid)
            if v is None:
                continue
            answered_sports = True
            for label in split_multi(v):
                if label in NON_SPORT_LABELS:
                    continue
                code = slugify(label)
                if not code:
                    continue
                sports.add(code)
                participated_labels.setdefault(code, label)
        rec["sports"] = sports
        rec["sports_answered"] = answered_sports

        # ---- settings matrix + per-setting sports -------------------------
        settings = set()
        setting_sports = {k: set() for k in FREQ_GROUPS}
        settings_answered = False
        for qid in SETTINGS_QIDS:
            v = cell(row, qidx, qid)
            if v is None:
                continue
            for row_title, col_title in parse_matrix(v):
                code = RAW_TO_CODE["settings_col"].get(col_title)
                if code is None:
                    log.warn(f"Unexpected settings column {col_title!r}")
                    continue
                settings.add(code)
                settings_answered = True
                sport = slugify(row_title)
                if sport:
                    setting_sports[code].add(sport)
                    participated_labels.setdefault(sport, norm_text(row_title))
        rec["settings"] = settings
        rec["settings_answered"] = settings_answered
        rec["pe_sports"] = setting_sports["pe_lessons"]
        rec["school_club_sports"] = setting_sports["school_club"]
        rec["community_club_sports"] = setting_sports["community_club"]
        rec["other_setting_sports"] = setting_sports["somewhere_else"]
        for k in FREQ_GROUPS:
            rec[f"{k}_sports_answered"] = bool(setting_sports[k])

        # ---- per-setting frequency (derived: highest across sports) ------
        for setting, qids in FREQ_GROUPS.items():
            best = None
            routed = False
            for qid in qids:
                v = cell(row, qidx, qid)
                if v is None:
                    continue
                for _, col_title in parse_matrix(v):
                    code = RAW_TO_CODE["freq_col"].get(col_title)
                    if code is None:
                        log.warn(f"Unexpected frequency column {col_title!r}")
                        continue
                    routed = True
                    if best is None or FREQ_ORDER[code] > FREQ_ORDER[best]:
                        best = code
            rec[f"freq_{setting}"] = best
            rec[f"freq_{setting}_routed"] = routed
        rec["community_freq"] = rec["freq_community_club"]
        rec["community_routed"] = rec["freq_community_club_routed"]
        rec["school_club_freq"] = rec["freq_school_club"]
        rec["school_club_routed"] = rec["freq_school_club_routed"]
        rec["pe_freq"] = rec["freq_pe_lessons"]
        rec["pe_freq_routed"] = rec["freq_pe_lessons_routed"]
        rec["other_freq"] = rec["freq_somewhere_else"]
        rec["other_freq_routed"] = rec["freq_somewhere_else_routed"]

        # ---- derived organised participation outside the curriculum -------
        # Agreed derivation: highest reported frequency across the SCHOOL
        # CLUB and COMMUNITY CLUB settings. Respondents with no frequency
        # data in either setting are 'none_reported'.
        best = None
        for setting in ("school_club", "community_club"):
            v = rec[f"freq_{setting}"]
            if v is not None and (best is None or FREQ_ORDER[v] > FREQ_ORDER[best]):
                best = v
        rec["organised_freq"] = best if best is not None else "none_reported"

        # ---- v2.2 (meeting decisions P01/P02/P06, reproduces the live
        # in-meeting test: 238 of 366 at 7+ all settings; 188 excluding
        # somewhere else): RAW ACCUMULATED weekly sporting occasions.
        # Each reported sport-frequency answer contributes its stated
        # weekly occasions (3+ counts as 3; 'less than once a week' and
        # 'I don't know' contribute 0 - open point O01). No weighting,
        # no assumed duration.
        ACC_VAL = {"three_plus": 3, "twice_week": 2, "once_week": 1,
                   "less_weekly": 0, "dont_know": 0}

        def acc_cat(total, routed, true_zero=False):
            if true_zero:
                return "none_reported"
            if total <= 0:
                return "less_weekly_only"
            return f"w{min(total, 7)}"

        setting_acc = {}
        for setting, qids in FREQ_GROUPS.items():
            tot, routed_s = 0, False
            for qid in qids:
                v = cell(row, qidx, qid)
                if v is None:
                    continue
                for _, col_title in parse_matrix(v):
                    code = RAW_TO_CODE["freq_col"].get(col_title)
                    if code is None:
                        continue
                    routed_s = True
                    tot += ACC_VAL[code]
            setting_acc[setting] = (tot, routed_s)
            rec[f"acc_{setting}"] = tot
            rec[f"acc_{setting}_cat"] = (acc_cat(tot, routed_s)
                                         if routed_s else None)

        # ---- any activity in any setting (true zero, decision D08) --------
        rec["any_activity"] = ("yes" if (settings or any(
            setting_sports[k] for k in setting_sports)) else "no")

        # ---- v2.3 (build 008): composite 'Other sports' membership --------
        # Display-level composite for the provisionally classified Tier 2
        # sports (P04): a pupil counts ONCE in the composite within each
        # chart population where they reported >= 1 Tier 2 sport. The
        # individual Tier 2 sports are retained for the data tables.
        from .common import TIER2_SPORTS, TIER2_COMPOSITE_CODE, \
            TIER2_COMPOSITE_LABEL
        any_t2 = False
        for skey in ("pe_sports", "school_club_sports",
                     "community_club_sports", "other_setting_sports"):
            if rec[skey] & TIER2_SPORTS:
                rec[skey].add(TIER2_COMPOSITE_CODE)
                any_t2 = True
        if any_t2:
            # Tier 2 sports are captured through the routed follow-up
            # questions and the setting grids, not the Tier 1 category
            # ticks, so the overall composite uses the settings basis
            # (79 pupils in this export - see companion reconciliation).
            rec["sports"].add(TIER2_COMPOSITE_CODE)
        participated_labels.setdefault(TIER2_COMPOSITE_CODE,
                                       TIER2_COMPOSITE_LABEL)

        overall_acc = sum(t for t, _ in setting_acc.values())
        rec["overall_acc"] = overall_acc
        rec["overall_freq"] = acc_cat(
            overall_acc, True, true_zero=(rec["any_activity"] == "no"))

        # ---- v3 (build 010): agreed estimated average weekly frequency.
        # Per setting: the mean of the sports done at least weekly there
        # ('less than once a week' and 'I don't know' excluded from the
        # averages). Setting averages are then summed. Pupils with no
        # weekly frequency answer fall into categorical columns so the
        # chart always totals the full base.
        est = 0.0
        any_weekly = any_lw = any_dk = False
        per_sport_freq = {}          # (setting, sport) -> code, for stacks
        for setting, qids in FREQ_GROUPS.items():
            weekly_vals = []
            for qid in qids:
                v = cell(row, qidx, qid)
                if v is None:
                    continue
                for row_title, col_title in parse_matrix(v):
                    code = RAW_TO_CODE["freq_col"].get(col_title)
                    if code is None:
                        continue
                    sp = slugify(row_title)
                    per_sport_freq[(setting, sp)] = code
                    if code == "less_weekly":
                        any_lw = True
                    elif code == "dont_know":
                        any_dk = True
                    else:
                        weekly_vals.append(ACC_VAL[code])
                        any_weekly = True
            if weekly_vals:
                est += sum(weekly_vals) / len(weekly_vals)
        # v5 (build 012): flat square-root method - total weekly occasions
        # across every weekly sport, divided once by the square root of the
        # number of weekly sports (Welsh Government submission method)
        entries = [ACC_VAL[c] for c in
                   (per_sport_freq[k] for k in per_sport_freq)
                   if c in ("once_week", "twice_week", "three_plus")]
        est = (sum(entries) / (len(entries) ** 0.5)) if entries else 0.0
        rec["freq_estimate_value"] = est
        rec["per_sport_freq"] = per_sport_freq
        if any_weekly:
            band = int(est + 0.5)   # half-up rounding
            rec["freq_estimate"] = "e9plus" if band >= 9 else f"e{max(band, 1)}"
        elif any_lw:
            rec["freq_estimate"] = "less_weekly_only"
        elif any_dk:
            rec["freq_estimate"] = "dont_know_only"
        else:
            rec["freq_estimate"] = "none_reported"

        # v5 (build 012): identical flat square-root formula restricted to
        # the two club settings (school club + community club)
        CLUB = ("school_club", "community_club")
        c_entries = []
        c_lw = c_dk = False
        for (s_, sp_), code_ in per_sport_freq.items():
            if s_ not in CLUB:
                continue
            if code_ in ("once_week", "twice_week", "three_plus"):
                c_entries.append(ACC_VAL[code_])
            elif code_ == "less_weekly":
                c_lw = True
            elif code_ == "dont_know":
                c_dk = True
        if c_entries:
            cb = int(sum(c_entries) / (len(c_entries) ** 0.5) + 0.5)
            rec["club_freq_estimate"] = "e9plus" if cb >= 9 else f"e{max(cb, 1)}"
        elif c_lw:
            rec["club_freq_estimate"] = "less_weekly_only"
        elif c_dk:
            rec["club_freq_estimate"] = "dont_know_only"
        else:
            rec["club_freq_estimate"] = "none_reported"


        # ---- demand and unmet demand --------------------------------------
        demand = set()
        v = cell(row, qidx, 26871551)
        rec["demand_answered"] = v is not None
        for label in split_multi(v):
            if label in NON_SPORT_LABELS:
                continue
            code = slugify(label)
            if code:
                demand.add(code)
                demand_labels.setdefault(code, label)
        rec["demand"] = demand
        rec["unmet"] = {d for d in demand
                        if DEMAND_TO_PARTICIPATION.get(d, d) not in sports}
        rec["unmet_answered"] = rec["demand_answered"]

        # ---- fixed-option multi-selects ------------------------------------
        for field, qid, key in [("more_if", 26871588, "more_if"),
                                ("important", 26871589, "important")]:
            v = cell(row, qidx, qid)
            chosen = set()
            for label in split_multi(v):
                if label in RAW_TO_CODE[key]:
                    chosen.add(RAW_TO_CODE[key][label])
                elif label.startswith("Other"):
                    chosen.add("other")   # free text recoded; text never retained
                else:
                    log.warn(f"Unexpected option for {field}: {label!r} -> recoded to Other")
                    chosen.add("other")
            rec[field] = chosen
            rec[f"{field}_answered"] = v is not None

        # ---- simple singles -------------------------------------------------
        rec["join_in"] = map_single(cell(row, qidx, 26871565), RAW_TO_CODE["join_in"], log, "join_in")
        rec["listened"] = map_single(cell(row, qidx, 26871566), RAW_TO_CODE["listened"], log, "listened")
        rec["welsh"] = map_single(cell(row, qidx, 26871567), RAW_TO_CODE["welsh"], log, "welsh")
        rec["welsh_sport"] = map_single(cell(row, qidx, 26871590), RAW_TO_CODE["yes_no"], log, "welsh_sport")
        rec["welsh_sport_routed"] = rec["welsh"] is not None and rec["welsh"] != "none"
        rec["disability"] = map_single(cell(row, qidx, 26871504), RAW_TO_CODE["disability"], log, "disability")
        rec["learning"] = map_single(cell(row, qidx, 26871505), RAW_TO_CODE["disability"], log, "learning")
        rec["take_part_routed"] = rec["disability"] in ("yes", "not_sure", "prefer_not_to_say")
        rec["ethnicity"] = map_single(cell(row, qidx, 26871498), ETHNICITY_MAP, log, "ethnicity")
        _eraw = cell(row, qidx, 26871498)
        rec["eth_raw"] = norm_text(_eraw) if _eraw is not None else None

        # ---- v3: combined disability and/or learning difficulty group -----
        rec["dl_any"] = ("yes" if (rec["disability"] == "yes" or
                                   rec["learning"] == "yes") else "no")
        # group-restricted settings fields for the demographic settings charts
        # v5 (build 012, owner rule): ethnically diverse includes positively
        # identified White minority backgrounds (category only, never free
        # text); Welsh speakers include all three top tiers
        wb_raw = cell(row, qidx, 26871499)
        wb = norm_text(wb_raw) if wb_raw is not None else ""
        white_minority = (wb in ("Irish", "Gypsy or Irish Traveller", "Roma")
                          or wb.startswith("Any other White background"))
        ed = (rec["ethnicity"] in ("mixed", "asian", "other_grouped")
              or (rec["ethnicity"] == "white" and white_minority))
        wl = rec["welsh"] in ("very_well", "fair_amount", "a_little")
        rec["settings_dl"] = set(settings) if rec["dl_any"] == "yes" else set()
        rec["settings_dl_answered"] = settings_answered and rec["dl_any"] == "yes"
        # v4 (build 011, owner decision): separate disability / learning
        # difficulty settings charts with a per-view combining rule
        dy = rec["disability"] == "yes"
        ly = rec["learning"] == "yes"
        rec["settings_dy"] = set(settings) if dy else set()
        rec["settings_dy_answered"] = settings_answered and dy
        rec["settings_ly"] = set(settings) if ly else set()
        rec["settings_ly_answered"] = settings_answered and ly
        rec["ed_any"] = "yes" if ed else "no"
        rec["wl_any"] = "yes" if wl else "no"
        rec["settings_ed"] = set(settings) if ed else set()
        rec["settings_ed_answered"] = settings_answered and ed
        rec["settings_wl"] = set(settings) if wl else set()
        rec["settings_wl_answered"] = settings_answered and wl
        # distinct sports count for the average-sports sentences
        rec["n_sports_all"] = len(set().union(
            rec["pe_sports"], rec["school_club_sports"],
            rec["community_club_sports"], rec["other_setting_sports"]) - {"other_sports"})

        tp_raw = cell(row, qidx, 26871506)
        if tp_raw is None:
            rec["take_part"] = None
        else:
            label = norm_text(tp_raw)
            if label in RAW_TO_CODE["take_part"]:
                rec["take_part"] = RAW_TO_CODE["take_part"][label]
            elif label.startswith("Other"):
                rec["take_part"] = "other"
            else:
                log.warn(f"Unexpected take-part answer {label!r} -> invalid")
                rec["take_part"] = None

        # ---- matrix singles --------------------------------------------------
        def matrix_field(qid, row_map, col_map, qname):
            out = {}
            v = cell(row, qidx, qid)
            for row_title, col_title in parse_matrix(v):
                rcode = row_map.get(row_title)
                ccode = col_map.get(col_title)
                if rcode is None or ccode is None:
                    log.warn(f"Unexpected matrix labels for {qname}: {row_title!r}/{col_title!r}")
                    continue
                if rcode in out and out[rcode] != ccode:
                    log.warn(f"Multiple answers for {qname} row {row_title!r}; first kept")
                    continue
                out[rcode] = ccode
            return out

        rec["enjoy"] = matrix_field(26871552, RAW_TO_CODE["enjoy_row"], RAW_TO_CODE["enjoy_col"], "enjoyment")
        rec["confidence"] = matrix_field(26871586, RAW_TO_CODE["confidence_row"], RAW_TO_CODE["confidence_col"], "confidence")
        rec["pe_feel"] = matrix_field(26871587, RAW_TO_CODE["pe_feel_row"], RAW_TO_CODE["confidence_col"], "pe_feelings")

        records.append(rec)

    # ---- v2 (Sport Wales feedback): completion distribution over ALL
    # exported rows for the appendix chart (per-capita completeness =
    # share of survey question groups with at least one answer recorded).
    import re as _re
    qgroups: dict[str, list] = {}
    for c in df.columns:
        m = _re.match(r"Q_(\d+)", str(c))
        if m:
            qgroups.setdefault(m.group(1), []).append(c)
    comp_dist = [0, 0, 0, 0, 0]  # 0% · 1-24% · 25-49% · 50-74% · 75-100%
    if qgroups:
        answered_any = pd.DataFrame({
            qid: df[cols].notna().any(axis=1) for qid, cols in qgroups.items()})
        share = answered_any.sum(axis=1) / len(qgroups)
        for s in share:
            if s == 0:
                comp_dist[0] += 1
            elif s < 0.25:
                comp_dist[1] += 1
            elif s < 0.50:
                comp_dist[2] += 1
            elif s < 0.75:
                comp_dist[3] += 1
            else:
                comp_dist[4] += 1

    # v2.1 (Sport Wales page-by-page feedback): "N sports to choose from".
    # The ten category questions are single multi-select columns, so the
    # export only evidences sports selected at least once school-wide (93
    # here); Sport Wales cite 92 on the survey list - to be confirmed.
    # v5 (build 012, owner hard rule): the school profile lists every
    # high-level ethnicity option from the survey, with exact counts and
    # zeros, nobody combined. Welsh Government terminology for White.
    ETH_PROFILE = [
        ("White", "White Welsh, English, Scottish, Northern Irish, or British"),
        ("Mixed or multiple ethnic groups", "Mixed or multiple ethnic groups"),
        ("Asian, Asian Welsh, or Asian British", "Asian, Asian Welsh, or Asian British"),
        ("Black, Black Welsh, Black British, Caribbean, or African",
         "Black, Black Welsh, Black British, Caribbean, or African"),
        ("Other ethnic groups [for example, Arab]", "Other ethnic groups (for example, Arab)"),
        ("I'm not sure", "I\u2019m not sure"),
        ("Prefer not to say", "Prefer not to say"),
    ]
    eth_counts = {}
    for r in records:
        if r.get("eth_raw"):
            eth_counts[r["eth_raw"]] = eth_counts.get(r["eth_raw"], 0) + 1
    ethnicity_profile = [[lbl, eth_counts.get(raw, 0)] for raw, lbl in ETH_PROFILE]

    build_meta = {
        "ethnicityProfile": ethnicity_profile,
        "ethnicityProfileBase": sum(eth_counts.values()),
        "sportOptionCount": len([c for c in participated_labels
                                 if c != "other_sports"]),
        "completionDist": comp_dist,
        "sourceRows": int(len(df)),
        "acceptedRows": len(records),
        "excludedRows": len(log.exclusions),
        "sourceChecksum": file_checksum(xlsx_path),
        "generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "weighting": "none",
    }
    if accepted != {"Complete"}:
        # v6: the data owner's inclusion rule admits partial responses —
        # the split is recorded so the validation summary can state it
        build_meta["acceptedByStatus"] = dict(sorted(status_counts.items()))
    discovered = {"participated": participated_labels, "demand": demand_labels}
    return records, log, build_meta, discovered

# EOF sentinel - do not remove
