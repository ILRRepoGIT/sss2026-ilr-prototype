"""Deterministic narrative generation.

For every visible filter state the generator:
  1. reads the SAME metric results used by the charts (one fact source),
  2. applies suppression-aware ranking (a leader below the reporting
     threshold is never named),
  3. selects a reviewed template from config/narratives.yml,
  4. renders the sentence and records the fact object for audit.

The same workbook, configuration and code version always produce the same
sentences. No language model is involved at any point.
"""
from __future__ import annotations

import json

INSIGHT_METRICS = [
    "sports_participated", "community_club_freq", "participation_settings",
    "join_in_easily", "sports_wanted", "would_do_more_if",
    "enjoy_pe", "confidence_try_new", "ideas_listened",
]

WEEKLY_PLUS = ["once_week", "twice_week", "three_plus"]
LISTENED_POS = ["always", "sometimes"]


def rw(n):
    return "respondent" if n == 1 else "respondents"


def join_labels(labels):
    if len(labels) == 1:
        return labels[0]
    return ", ".join(labels[:-1]) + " and " + labels[-1]


class NarrativeGenerator:
    def __init__(self, templates, defs, cohorts, threshold):
        self.t = templates
        self.defs = defs
        self.cohorts = cohorts
        self.th = threshold
        self.audit = []   # rows for narrative-audit.csv

    # ------------------------------------------------------------ helpers
    def _log(self, state, block, template_id, facts, text):
        self.audit.append({
            "filter_state": state, "block": block, "template_id": template_id,
            "facts": json.dumps(facts, ensure_ascii=False, sort_keys=True),
            "rendered_text": text,
        })
        return text

    def leader_facts(self, d, res, exclude_code=None):
        """Rank options safely. Returns dict or None when nothing reportable.

        Leaders below the threshold are never named (rank suppression)."""
        if res is None or res["status"] != "ok" or res["base"] < self.th:
            return None
        opts = d["options"]
        pairs = [(code, label, v) for (code, label), v in zip(opts, res["raw"])
                 if code != exclude_code]
        mx = max((v for _, _, v in pairs), default=0)
        if mx == 0:
            return {"kind": "all_zero", "base": res["base"]}
        if mx < self.th:
            return {"kind": "rank_suppressed", "base": res["base"]}
        leaders = [(c, l) for c, l, v in pairs if v == mx]
        below = sorted({v for _, _, v in pairs if v < mx}, reverse=True)
        runner = None
        if below and below[0] >= self.th:
            rl = [(c, l) for c, l, v in pairs if v == below[0]]
            runner = {"labels": [l for _, l in rl], "count": below[0]}
        return {"kind": "tie" if len(leaders) > 1 else "unique",
                "base": res["base"], "count": mx,
                "leaders": [l for _, l in leaders],
                "leader_codes": [c for c, _ in leaders],
                "runner": runner}

    def agg_count(self, d, res, codes):
        """Disclosure-checked aggregate of option counts (>= threshold or None)."""
        if res is None or res["status"] != "ok" or res["base"] < self.th:
            return None
        idx = {c: i for i, (c, _) in enumerate(d["options"])}
        total = sum(res["raw"][idx[c]] for c in codes if c in idx)
        return total if total >= self.th else None

    # ----------------------------------------------------- chart insights
    def chart_insight(self, state, mid, res):
        d = self.defs[mid]
        t = self.t["chart_insights"]
        block = f"insight:{mid}"
        if res is None:
            return None
        if res["status"] == "na":
            return self._log(state, block, "not_asked_v1", {}, t["not_asked_v1"])
        if res["status"] == "nd":
            return self._log(state, block, "no_valid_responses_v1", {}, t["no_valid_responses_v1"])
        if res["status"] == "sup" or res["base"] < self.th:
            return self._log(state, block, "suppressed_v1", {}, t["suppressed_v1"])

        lf = self.leader_facts(d, res)
        if lf["kind"] == "all_zero":
            return self._log(state, block, "no_valid_responses_v1", lf, t["no_valid_responses_v1"])
        if lf["kind"] == "rank_suppressed":
            return self._log(state, block, "rank_suppressed_v1", lf, t["rank_suppressed_v1"])

        multi = d["type"] == "multi_select"
        if lf["kind"] == "tie":
            if len(lf["leaders"]) == 2:
                tid = "two_way_tie_v1"
                text = t[tid].format(leader_1=lf["leaders"][0], leader_2=lf["leaders"][1],
                                     count=lf["count"])
            else:
                tid = "multi_way_tie_v1"
                lf = {**lf, "tie_n": len(lf["leaders"])}
                text = t[tid].format(tie_n=lf["tie_n"], leaders=join_labels(lf["leaders"]),
                                     count=lf["count"])
        else:
            tid = "unique_leader_count_v1" if multi else "unique_leader_count_single_v1"
            text = t[tid].format(base=lf["base"], leader=lf["leaders"][0],
                                 count=lf["count"], respondent_word=rw(lf["count"]))
            if lf["runner"]:
                text += " " + t["runner_up_clause_v1"].format(
                    runner_up=join_labels(lf["runner"]["labels"]),
                    count=lf["runner"]["count"],
                    respondent_word=rw(lf["runner"]["count"]))
                tid += "+runner_up_clause_v1"
        return self._log(state, block, tid, lf, text)

    # ------------------------------------------------------- key findings
    def key_findings(self, state, base, metrics, cohort_key):
        t = self.t["key_findings"]
        cohort = self.cohorts.get(cohort_key)
        src = cohort["metric"] if cohort else None
        parts = []
        facts = {"base": base}
        parts.append(t["base_sentence_v1"].format(
            are_word="is" if base == 1 else "are", base=base,
            response_word="response" if base == 1 else "responses"))

        sp = metrics.get("sports_participated")
        d_sp = self.defs["sports_participated"]
        if src == "sports_participated":
            lf = self.leader_facts(d_sp, sp) if sp else None
            # source metric absent in cohort states; caller passes sibling result
        else:
            lf = self.leader_facts(d_sp, sp) if sp else None
        if lf and lf["kind"] in ("unique", "tie"):
            if src == "sports_participated":
                lf2 = self.leader_facts(d_sp, sp, exclude_code=cohort["code"])
                if lf2 and lf2["kind"] == "unique":
                    parts.append(t["top_sport_excl_cohort_v1"].format(
                        cohort_sport=dict(d_sp["options"])[cohort["code"]],
                        leader=lf2["leaders"][0], count=lf2["count"],
                        respondent_word=rw(lf2["count"])))
                    facts["top_sport_excl_cohort"] = lf2
            elif lf["kind"] == "tie":
                parts.append(t["top_sport_tie_v1"].format(
                    leaders=join_labels(lf["leaders"]), count=lf["count"]))
                facts["top_sport"] = lf
            else:
                parts.append(t["top_sport_v1"].format(
                    leader=lf["leaders"][0], count=lf["count"],
                    respondent_word=rw(lf["count"])))
                facts["top_sport"] = lf

        dm = metrics.get("sports_wanted")
        d_dm = self.defs["sports_wanted"]
        lfd = self.leader_facts(d_dm, dm) if dm else None
        if lfd and lfd["kind"] == "unique":
            parts.append(t["demand_v1"].format(leader=lfd["leaders"][0], count=lfd["count"],
                                               respondent_word=rw(lfd["count"])))
            facts["demand"] = lfd
        elif lfd and lfd["kind"] == "tie":
            parts.append(t["demand_tie_v1"].format(leaders=join_labels(lfd["leaders"]),
                                                   count=lfd["count"]))
            facts["demand"] = lfd

        text = " ".join(parts)
        return self._log(state, "key_findings", "kf_composite_v1", facts, text)

    # ---------------------------------------------------------- conclusion
    def conclusion(self, state, metrics, cohort_key, sibling_metrics):
        """Four theme sentences. sibling_metrics = cohort=none results for the
        same scope+gender (used for the cohort's source chart)."""
        t = self.t["conclusion"]
        cohort = self.cohorts.get(cohort_key)
        src = cohort["metric"] if cohort else None
        out = {}

        def res_for(mid):
            if src == mid:
                return sibling_metrics.get(mid) if sibling_metrics else None
            return metrics.get(mid)

        # --- Active Nation
        d_sp = self.defs["sports_participated"]
        sp = metrics.get("sports_participated")
        if src == "sports_participated":
            # tautology guard: describe what ELSE the cohort does
            an_lf = self.leader_facts(d_sp, sp, exclude_code=cohort["code"]) if sp else None
        else:
            an_lf = self.leader_facts(d_sp, sp) if sp else None

        if src == "sports_participated":
            if an_lf and an_lf["kind"] == "unique":
                out["con_an"] = self._log(state, "con_an", "active_nation_cohort_alt_v1",
                                          {"leader": an_lf, "cohort": cohort_key},
                                          t["active_nation_cohort_alt_v1"].format(
                                              cohort_sport=dict(d_sp["options"])[cohort["code"]],
                                              leader=an_lf["leaders"][0], count=an_lf["count"],
                                              respondent_word=rw(an_lf["count"])))
            elif an_lf and an_lf["kind"] == "tie":
                out["con_an"] = self._log(state, "con_an", "active_nation_cohort_tie",
                                          {"leaders": an_lf, "cohort": cohort_key},
                                          f"Apart from {dict(d_sp['options'])[cohort['code']]}, "
                                          f"{join_labels(an_lf['leaders'])} were the most selected "
                                          f"sports in this cohort ({an_lf['count']} respondents each).")
            else:
                out["con_an"] = self._theme_fallback(state, "con_an", sp)
        elif an_lf and an_lf["kind"] == "unique":
            cf = metrics.get("community_club_freq")
            d_cf = self.defs["community_club_freq"]
            club = self.agg_count(d_cf, cf, WEEKLY_PLUS) if (cf and src != "community_club_freq") else None
            if club is not None:
                out["con_an"] = self._log(state, "con_an", "active_nation_v1",
                                          {"leader": an_lf, "club_count": club, "club_base": cf["base"]},
                                          t["active_nation_v1"].format(
                                              leader=an_lf["leaders"][0], count=an_lf["count"],
                                              respondent_word=rw(an_lf["count"]),
                                              club_count=club, club_base=cf["base"]))
            else:
                out["con_an"] = self._log(state, "con_an", "active_nation_no_club_v1",
                                          {"leader": an_lf},
                                          t["active_nation_no_club_v1"].format(
                                              leader=an_lf["leaders"][0], count=an_lf["count"],
                                              respondent_word=rw(an_lf["count"])))
        elif an_lf and an_lf["kind"] == "tie":
            out["con_an"] = self._log(state, "con_an", "active_nation_tie",
                                      {"leaders": an_lf},
                                      f"{join_labels(an_lf['leaders'])} were the most selected "
                                      f"sports in this view, with {an_lf['count']} respondents each.")
        else:
            out["con_an"] = self._theme_fallback(state, "con_an", sp)

        # --- Everyone
        d_ji = self.defs["join_in_easily"]
        if src == "join_in_easily":
            d_li = self.defs["ideas_listened"]
            li = metrics.get("ideas_listened")
            agg = self.agg_count(d_li, li, LISTENED_POS)
            if agg is not None:
                out["con_ev"] = self._log(state, "con_ev", "everyone_alt_v1",
                                          {"listened_pos": agg, "base": li["base"]},
                                          t["everyone_alt_v1"].format(count=agg, base=li["base"]))
            else:
                out["con_ev"] = self._theme_fallback(state, "con_ev", li)
        else:
            ji = metrics.get("join_in_easily")
            lf = self.leader_facts(d_ji, ji) if ji else None
            if lf and lf["kind"] == "unique":
                out["con_ev"] = self._log(state, "con_ev", "everyone_v1",
                                          {"leader": lf},
                                          t["everyone_v1"].format(count=lf["count"], base=lf["base"],
                                                                  leader_label=lf["leaders"][0]))
            elif lf and lf["kind"] == "tie":
                out["con_ev"] = self._log(state, "con_ev", "everyone_tie",
                                          {"leaders": lf},
                                          f"Asked whether they can join in easily, respondents were "
                                          f"evenly split between ‘{join_labels(lf['leaders'])}’, "
                                          f"with {lf['count']} each.")
            else:
                out["con_ev"] = self._theme_fallback(state, "con_ev", ji)

        # --- Lifelong
        d_dm = self.defs["sports_wanted"]
        dm = metrics.get("sports_wanted")
        lfd = self.leader_facts(d_dm, dm) if dm else None
        if lfd and lfd["kind"] == "unique":
            mi = metrics.get("would_do_more_if")
            d_mi = self.defs["would_do_more_if"]
            lfm = self.leader_facts(d_mi, mi, exclude_code="none_of_these") if mi else None
            if lfm and lfm["kind"] == "unique":
                out["con_ll"] = self._log(state, "con_ll", "lifelong_v1",
                                          {"demand": lfd, "more_if": lfm},
                                          t["lifelong_v1"].format(
                                              leader=lfd["leaders"][0], count=lfd["count"],
                                              respondent_word=rw(lfd["count"]),
                                              more_if_leader=lfm["leaders"][0],
                                              more_if_count=lfm["count"]))
            else:
                out["con_ll"] = self._log(state, "con_ll", "lifelong_demand_only_v1",
                                          {"demand": lfd},
                                          t["lifelong_demand_only_v1"].format(
                                              leader=lfd["leaders"][0], count=lfd["count"],
                                              respondent_word=rw(lfd["count"])))
        elif lfd and lfd["kind"] == "tie":
            out["con_ll"] = self._log(state, "con_ll", "lifelong_tie",
                                      {"demand": lfd},
                                      f"The strongest demand in this view is jointly for "
                                      f"{join_labels(lfd['leaders'])}, selected by {lfd['count']} "
                                      f"respondents each.")
        else:
            out["con_ll"] = self._theme_fallback(state, "con_ll", dm)

        # --- Enjoyment
        d_ep = self.defs["enjoy_pe"]
        if src == "enjoy_pe":
            sc = metrics.get("enjoy_school_clubs")
            d_sc = self.defs["enjoy_school_clubs"]
            agg = self.agg_count(d_sc, sc, ["a_lot"])
            if agg is not None:
                out["con_en"] = self._log(state, "con_en", "enjoyment_alt_v1",
                                          {"school_club_a_lot": agg, "base": sc["base"]},
                                          t["enjoyment_alt_v1"].format(count=agg, base=sc["base"]))
            else:
                out["con_en"] = self._theme_fallback(state, "con_en", sc)
        else:
            ep = metrics.get("enjoy_pe")
            a_lot = self.agg_count(d_ep, ep, ["a_lot"]) if ep else None
            li = metrics.get("ideas_listened")
            lag = self.agg_count(self.defs["ideas_listened"], li, LISTENED_POS) if li else None
            if a_lot is not None and lag is not None:
                out["con_en"] = self._log(state, "con_en", "enjoyment_v1",
                                          {"pe_a_lot": a_lot, "base": ep["base"], "listened_pos": lag},
                                          t["enjoyment_v1"].format(count=a_lot, base=ep["base"],
                                                                   listened_count=lag))
            elif a_lot is not None:
                out["con_en"] = self._log(state, "con_en", "enjoyment_pe_only",
                                          {"pe_a_lot": a_lot, "base": ep["base"]},
                                          f"{a_lot} of the {ep['base']} respondents who answered "
                                          f"enjoy sport in PE lessons ‘a lot’.")
            else:
                out["con_en"] = self._theme_fallback(state, "con_en", ep)
        return out

    def _theme_fallback(self, state, block, res):
        t = self.t["conclusion"]
        if res is None or res["status"] in ("sup",) or (res["status"] == "ok" and res["base"] < self.th):
            return self._log(state, block, "theme_suppressed_v1", {}, t["theme_suppressed_v1"])
        return self._log(state, block, "theme_no_data_v1", {}, t["theme_no_data_v1"])

    # ---------------------------------------------------------------- cards
    def cards(self, state, base, metrics, cohort_key, sibling_metrics):
        cohort = self.cohorts.get(cohort_key)
        src = cohort["metric"] if cohort else None
        out = [{"t": "Respondents in this view", "v": str(base), "s": "accepted survey responses"}]

        d_sp = self.defs["sports_participated"]
        if src == "sports_participated":
            sp = metrics.get("sports_participated")
            lf = self.leader_facts(d_sp, sp, exclude_code=cohort["code"]) if sp else None
            title = f"Top sport apart from {dict(d_sp['options'])[cohort['code']]}"
        else:
            sp = metrics.get("sports_participated")
            lf = self.leader_facts(d_sp, sp) if sp else None
            title = "Most selected sport"
        if lf and lf["kind"] == "unique":
            out.append({"t": title, "v": lf["leaders"][0], "s": f"{lf['count']} {rw(lf['count'])}"})
        elif lf and lf["kind"] == "tie":
            out.append({"t": title, "v": "Tied", "s": f"{join_labels(lf['leaders'])} ({lf['count']} each)"})
        else:
            out.append({"t": title, "v": "Not shown", "s": "below reporting threshold"})

        d_dm = self.defs["sports_wanted"]
        dm = metrics.get("sports_wanted")
        lfd = self.leader_facts(d_dm, dm) if dm else None
        if lfd and lfd["kind"] == "unique":
            out.append({"t": "Top sport to do more of", "v": lfd["leaders"][0],
                        "s": f"{lfd['count']} {rw(lfd['count'])}"})
        elif lfd and lfd["kind"] == "tie":
            out.append({"t": "Top sport to do more of", "v": "Tied",
                        "s": f"{join_labels(lfd['leaders'])} ({lfd['count']} each)"})
        else:
            out.append({"t": "Top sport to do more of", "v": "Not shown", "s": "below reporting threshold"})

        if src == "enjoy_pe":
            d_sc = self.defs["enjoy_school_clubs"]
            sc = metrics.get("enjoy_school_clubs")
            agg = self.agg_count(d_sc, sc, ["a_lot"]) if sc else None
            title, subbase = "Enjoy school club sport ‘a lot’", sc["base"] if sc else 0
        else:
            d_ep = self.defs["enjoy_pe"]
            ep = metrics.get("enjoy_pe")
            agg = self.agg_count(d_ep, ep, ["a_lot"]) if ep else None
            title, subbase = "Enjoy PE lessons ‘a lot’", ep["base"] if ep else 0
        out.append({"t": title, "v": str(agg), "s": f"of {subbase} who answered"} if agg is not None
                   else {"t": title, "v": "Not shown", "s": "below reporting threshold"})

        if src == "community_club_freq":
            d_scf = self.defs["school_club_freq"]
            scf = metrics.get("school_club_freq")
            agg = self.agg_count(d_scf, scf, WEEKLY_PLUS) if scf else None
            title, subbase = "Weekly+ school club sport", scf["base"] if scf and scf["status"] == "ok" else 0
        else:
            d_cf = self.defs["community_club_freq"]
            cf = metrics.get("community_club_freq")
            agg = self.agg_count(d_cf, cf, WEEKLY_PLUS) if cf else None
            title, subbase = "Weekly+ club sport outside school", cf["base"] if cf and cf["status"] == "ok" else 0
        out.append({"t": title, "v": str(agg), "s": f"of {subbase} asked"} if agg is not None
                   else {"t": title, "v": "Not shown", "s": "below threshold or not asked"})
        return out
