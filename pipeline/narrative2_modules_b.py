"""Module content builders (v2), part B: Lifelong, Enjoyment, closing
synthesis, key-statistics cards and full-state assembly."""
from __future__ import annotations

from .engine import state_key
from .narrative2 import (HARD_JOIN, LOW_CONF, NO_FREQUENT, POS_CONF, POS_LISTEN,
                         Scope, T, WEEKLY_PLUS, cap_first, join_and, ordinal, rw,
                         selw, tie_txt)
from .narrative2_modules import (BROAD_SCOPES, MODULE_LABELS, ModuleNarrator,
                                 V_CONF, V_HARDJOIN, V_HEALTHY, V_LISTEN,
                                 V_PEALOT, V_WEEKLY, V_WEEKLY_ALL, WEEKLY_ACC,
                                 YEAR_ONLY_MODULES, tier_of)
from .narrative2_modules import CLUB_WEEKLY

CONF_DIMS = [("confidence_try_new", "trying a new sport"),
             ("confidence_learn_skill", "learning a new skill"),
             ("confidence_try_again", "trying again when sport is hard"),
             ("confidence_new_place", "trying sport in a new place")]
ENJOY_SETTINGS = [("enjoy_pe", "PE lessons"),
                  ("enjoy_school_clubs", "school sports clubs"),
                  ("enjoy_community_clubs", "clubs outside of school"),
                  ("enjoy_other_settings", "other settings")]


class FullNarrator(ModuleNarrator):

    # ------------------------------------------------------------ lifelong
    def m_f2(self, key, S, tier):
        """v5 (build 012): responds to every filter, with a per-year
        breakdown sentence for each reportable year (feedback row 26)."""
        scope, gender, ck = key.split("|")
        # v3 (build 010, feedback row 27): stacked chart of participation
        # in each setting by year group, replacing the weekly-percentage
        # graphic. Rows carry per-setting counts for the stacked renderer.
        SETTINGS = ["pe_lessons", "school_club", "community_club",
                    "somewhere_else"]
        rows, per_setting = [], {c: [] for c in SETTINGS}
        for y in self.scope_years_list(scope):
            yk = state_key(f"y{y}", gender, ck)
            # D70 (sheet 46): every derived row carries the STABLE scope
            # key; the display label resolves through filterOptions labelCy.
            if not self.visible(yk):
                rows.append({"y": f"Year {y}", "yk": f"y{y}", "sup": 1})
                continue
            counts, base = self.counts_by_code(yk, "participation_settings")
            if counts is None:
                rows.append({"y": f"Year {y}", "yk": f"y{y}", "sup": 1})
                continue
            c = [counts.get(s, 0) for s in SETTINGS]
            rows.append({"y": f"Year {y}", "yk": f"y{y}", "c": c, "b": base})
            if self.pct_ok(base):
                for s, n in zip(SETTINGS, c):
                    per_setting[s].append((y, n, base, self.pct(n, base)))
        self._f2rows = rows
        out = []
        # per-year breakdown lines (feedback row 26)
        from .narrative2_modules import SETTING_PHRASES as _SP
        SLBL = dict(zip(SETTINGS, ["in PE or lesson time", "in a school club",
                                   "in a club outside of school", "somewhere else"]))
        for r in rows:
            if r.get("sup") or not r.get("b") or r["b"] < 2:
                continue
            c = r["c"]
            mi = max(range(4), key=lambda i: c[i])
            if c[mi] == 0:
                continue
            t = (f"{r['y']}: sport {SLBL[SETTINGS[mi]]} was the most common "
                 f"setting in this view, reported by {c[mi]} of the {r['b']} "
                 f"pupils who answered.")
            out.append(self.custom(key, "f2", "supporting", "f2_year_line_v12",
                                   {"year": r["y"], "counts": c, "base": r["b"]}, t))
        totals = {s: sum(v[1] for v in per_setting[s]) for s in SETTINGS}
        lead = max(totals, key=totals.get) if any(totals.values()) else None
        if lead and len(per_setting[lead]) >= 2:
            vals = per_setting[lead]
            hi = max(vals, key=lambda v: v[3])
            lo = min(vals, key=lambda v: v[3])
            gphrase = {"all": "pupils", "boy": "boys", "girl": "girls"}[gender]
            from .narrative2_modules import SETTING_PHRASES
            t = (f"Among {gphrase} {S.place}, participation {SETTING_PHRASES[lead]} "
                 f"was proportionally highest in Year {hi[0]} ({hi[1]} of "
                 f"{hi[2]}, or {hi[3]}%) and lowest in Year {lo[0]} ({lo[1]} of "
                 f"{lo[2]}, or {lo[3]}%).")
            out.append(self.custom(key, "f2", "primary", "age_setting_extremes_v10",
                                   {"values": vals, "setting": lead}, t))
        return ("ok", out) if out else ("insufficient", [])

    def m_f3f5(self, key, S, tier):
        out = []
        broad = tier == "broad"
        ns = {}
        for mid, word in [("pe_feel_healthy", "healthy"),
                          ("pe_feel_confident", "confident"),
                          ("pe_feel_ready", "ready to learn")]:
            res = self.res(key, mid)
            n = self.count_of(mid, res, POS_CONF)
            if n is not None:
                ns[word] = (n, res["base"])
        if not ns:
            return ("nd", [])
        parts = [f"{v[0]} of {v[1]} said ‘very’ or ‘quite’ {w}" for w, v in ns.items()]
        # v2.1 (row 36): no unexplained "positive" label - state the answers
        t = (f"Asked whether PE and Active Lessons make them feel healthy, confident and "
             f"ready to learn, {S.phrase} answered: {join_and(parts)}.")
        out.append(self.custom(key, "f3f5", "primary", "pe_feelings_composite_v2",
                               {"values": ns}, t))
        if broad:
            self.para(out, self.s_gender_compare(key, S, "f3f5", "pe_feel_healthy",
                                                 POS_CONF, V_HEALTHY, True))
        return ("ok", out)

    def m_f6(self, key, S, tier):
        # v2.1 (row 37 forms): leader, runner, then one line per gender.
        out = []
        scope, gender, ck = key.split("|")
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        excl = set()
        if src == "most_important":
            self.para(out, self.group_note(key, S, "f6"))
            excl = {self.cohorts[S.cohort]["code"]}
        res = self.res(key, "most_important")
        lf = self.leader("most_important", res, exclude=excl or None)
        if lf and lf["kind"] == "unique" and lf["base"] == 1:
            t = (f"The one pupil in this selected group chose "
                 f"‘{lf['labels'][0]}’ as what matters most to them.")
            out.append(self.custom(key, "f6", "primary", "important_base1_v5",
                                   {"leader": lf}, t))
        elif lf and lf["kind"] == "unique":
            apart = " (apart from the answer defining this selected group)" if excl else ""
            t = (f"‘{lf['labels'][0]}’ was the most commonly selected option{apart}, "
                 f"chosen by {lf['count']} of the {lf['base']} {S.phrase} who "
                 f"answered this question.")
            out.append(self.custom(key, "f6", "primary", "important_leader_v5",
                                   {"leader": lf}, t))
            if lf["runner"] and lf["runner"]["labels"]:
                rl, rc = lf["runner"]["labels"], lf["runner"]["count"]
                named = tie_txt(rl)
                named = tie_txt([f"‘{x}’" for x in rl])
                if named is None:
                    rt_ = (f"{len(rl)} options were tied as the next most common "
                           f"{S.qual}, with {rc} {selw(rc)} each; the chart shows "
                           f"them all.")
                else:
                    rt_ = (f"The next most common option chosen was {named}, with "
                           f"{rc} {S.phrase} choosing "
                           f"{'this option' if len(rl) == 1 else 'each of these options'}.")
                out.append(self.custom(key, "f6", "supporting", "important_runner_v5",
                                       {"runner": lf["runner"],
                                        "tie_n": len(rl)}, rt_))
        else:
            self.para(out, self.s_leader_multi(key, S, "f6", "most_important",
                                               "answer", exclude=excl or None))
        if tier == "broad" and gender == "all":
            for g, gword in (("boy", "boys"), ("girl", "girls")):
                gk = state_key(scope, g, ck)
                if not self.visible(gk):
                    continue
                gres = self.res(gk, "most_important")
                gl = self.leader("most_important", gres, exclude=excl or None)
                if gl and gl["kind"] == "unique" and gres["base"] >= 3:
                    gt = (f"‘{gl['labels'][0]}’ was the most common option chosen "
                          f"by {gword} {S.place} ({gl['count']} pupils).")
                    out.append(self.custom(key, "f6", "comparison",
                                           "important_gender_leader_v5",
                                           {"gender": g, "leader": gl}, gt))
        return ("ok", out) if out else ("nd", [])

    def m_f7(self, key, S, tier):
        out = []
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        excl = {"none_of_these"}
        if src == "would_do_more_if":
            self.para(out, self.group_note(key, S, "f7"))
            excl.add(self.cohorts[S.cohort]["code"])
        res = self.res(key, "would_do_more_if")
        lf = self.leader("would_do_more_if", res, exclude=excl)
        labels = self.opt_labels("would_do_more_if")
        if lf and lf["kind"] == "unique" and lf["base"] == 1:
            t = (f"The one pupil in this selected group chose "
                 f"‘{lf['labels'][0]}’ as what would help them do more sport.")
            out.append(self.custom(key, "f7", "primary", "barrier_base1_v5",
                                   {"leader": lf}, t))
        elif lf and lf["kind"] == "unique":
            t = (f"‘{lf['labels'][0]}’ was the most commonly chosen answer that "
                 f"would help {S.phrase} do more sport, selected by {lf['count']} of the "
                 f"{lf['base']} pupils who answered.")
            out.append(self.custom(key, "f7", "primary", "barrier_leader_v41",
                                   {"leader": lf}, t))
            if lf["runner"]:
                rl = lf["runner"]["labels"]
                rc = lf["runner"]["count"]
                named = tie_txt(rl)
                if named is None:
                    rt_ = T["runner_many_v2"].format(n=len(rl), count=rc,
                                                     selw=selw(rc), qual=S.qual)
                elif len(rl) > 1:
                    rt_ = T["runner_joint_v2"].format(
                        runners=join_and([f"‘{x}’" for x in rl]), count=rc,
                        selw=selw(rc), qual=S.qual)
                else:
                    rt_ = (f"Next came ‘{rl[0]}’, with {rc} pupils who chose this "
                           f"answer {S.qual}.")
                out.append(self.custom(key, "f7", "supporting", "barrier_runner_v41",
                                       {"runner": lf["runner"],
                                        "runner_n": len(rl)}, rt_))
        elif lf and lf["kind"] == "tie":
            self.para(out, self.s_leader_multi(key, S, "f7", "would_do_more_if",
                                               "condition", exclude=excl,
                                               with_runner=False))
        none_n = self.count_of("would_do_more_if", res, ["none_of_these"])
        if none_n:
            out.append(self.custom(key, "f7", "supporting", "barrier_none_v41",
                                   {"count": none_n},
                                   f"{cap_first(S.qual)}, {none_n} chose "
                                   f"‘None of these’."))
        if tier == "broad":
            self.para(out, self.s_cross_group(key, S, "f7", "ct_not_very",
                                              "would_do_more_if",
                                              "condition that would help them do more sport"))
        return ("ok", out) if out else ("nd", [])

    def m_f8(self, key, S, tier):
        scope, gender, ck = key.split("|")
        src = self.cohorts.get(ck, {}).get("metric") if ck != "none" else None
        excl = {"none_of_these"}
        if src == "would_do_more_if":
            excl.add(self.cohorts[ck]["code"])
        if gender == "all":
            pair = self.s_gender_leader_pair(key, S, "f8", "would_do_more_if", "condition",
                                             exclude=excl)
            return ("ok", pair) if pair else ("insufficient", [])
        if scope == "whole":
            sents = []
            for ph in ("primary", "secondary"):
                lf = self.leader("would_do_more_if",
                                 self.res(state_key(ph, gender, ck), "would_do_more_if"),
                                 exclude=excl)
                if lf and lf["kind"] == "unique":
                    sents.append(f"‘{lf['labels'][0]}’ led in the {ph} phase "
                                 f"({lf['count']} {selw(lf['count'])})")
            if sents:
                t = f"Among {S.phrase}, {'; '.join(sents)}."
                return ("ok", [self.custom(key, "f8", "comparison",
                                           "gender_phase_barriers_v2",
                                           {"sentences": sents}, t)])
        return ("na_view", [])

    def m_f9(self, key, S, tier):
        scope, gender, ck = key.split("|")
        if scope != "whole" or tier != "broad":
            return ("na_view", [])
        sents = []
        for ph in ("primary", "secondary"):
            lf = self.leader("would_do_more_if",
                             self.res(state_key(ph, gender, ck), "would_do_more_if"),
                             exclude="none_of_these")
            if lf and lf["kind"] in ("unique", "tie"):
                named = tie_txt(lf["labels"])
                if named is None:
                    continue
                verb = "were" if len(lf["labels"]) > 1 else "was"
                sents.append(f"‘{named}’ {verb} selected most often in the "
                             f"{ph} phase ({lf['count']} {selw(lf['count'])})")
        if not sents:
            return ("insufficient", [])
        t = ". ".join(sents) + f", {S.qual}." if S.qual != "across the whole school" \
            else ". ".join(sents) + ", across the whole school."
        return ("ok", [self.custom(key, "f9", "comparison", "phase_barriers_v2",
                                   {"sentences": sents}, t)])

    def m_f10(self, key, S, tier):
        out = []
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        if src == "sports_wanted":
            self.para(out, self.group_note(key, S, "f10"))
            code = self.cohorts[S.cohort]["code"]
            labels = self.opt_labels("sports_wanted")
            wres = self.res(key, "sports_wanted")
            if wres is not None and wres.get("status") == "ok":
                ranked = sorted(
                    ((c, v) for c, v in zip(
                        [o for o, _ in self.defs["sports_wanted"]["options"]],
                        wres["raw"]) if v and c != code),
                    key=lambda x: -x[1])[:3]
                if ranked:
                    parts = [f"{labels[c]} ({v})" for c, v in ranked]
                    t = (f"The pupils who selected {labels[code]} also most "
                         f"wanted {join_and(parts)}, out of the {wres['base']} "
                         f"{S.phrase}.")
                    self.para(out, self.custom(key, "f10", "primary",
                                               "group_codemand_top3_v12",
                                               {"top3": ranked,
                                                "base": wres["base"]}, t))
            # do they already do the wanted sport? (spec 20.2)
            pres = self.res(key, "sports_participated")
            pn = self.count_of("sports_participated", pres, [code]) if pres else None
            if pn is not None:
                t2 = (f"{pn} of the {pres['base']} {S.phrase} already reported doing "
                      f"{labels[code]} this school year.")
                self.para(out, self.custom(key, "f10", "cross", "wd_current_check_v3",
                                           {"count": pn, "base": pres["base"]}, t2))
            return ("ok", out)
        self.para(out, self.s_leader_multi(key, S, "f10", "sports_wanted", "sport"))
        return ("ok", out) if out else ("nd", [])

    def m_f11(self, key, S, tier):
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        excl = {self.cohorts[S.cohort]["code"]} if src == "sports_wanted" else None
        pair = self.s_gender_leader_pair(key, S, "f11", "sports_wanted", "desired sport",
                                         exclude=excl)
        if pair:
            return ("ok", pair)
        scope, gender, ck = key.split("|")
        if gender != "all" and scope == "whole":
            sents = []
            phase_facts = {}
            for ph in ("primary", "secondary"):
                lf = self.leader("sports_wanted",
                                 self.res(state_key(ph, gender, ck), "sports_wanted"))
                if lf and lf["kind"] in ("unique", "tie"):
                    named = tie_txt(lf["labels"])
                    if named is None:
                        continue
                    phase_facts[ph] = {"labels": lf["labels"],
                                       "count": lf["count"]}
                    sents.append(f"{named} led in the {ph} phase "
                                 f"({lf['count']} {selw(lf['count'])})")
            if sents:
                return ("ok", [self.custom(key, "f11", "comparison",
                                           "gender_phase_demand_v2",
                                           {"sentences": sents, **phase_facts},
                                           f"Among {S.phrase}, {'; '.join(sents)}.")])
        return ("na_view", [])

    def m_f12(self, key, S, tier):
        return self.m_d9(key, S, tier, mid="sports_wanted", module="f12",
                         noun="desired sport")

    def m_f13(self, key, S, tier):
        """v4 (build 011): SW leader form; the duplicate rank sentence is
        removed - s_gender_leader_pair already carries the rank shift."""
        out = []
        res = self.res(key, "unmet_demand")
        lf = self.leader("unmet_demand", res)
        if lf and res.get("base") == 1:
            if lf["kind"] in ("unique", "tie") and lf["labels"]:
                t = (f"The one pupil in this selected group who answered "
                     f"selected {lf['labels'][0]} as a sport they would like "
                     f"to do more of.")
                out.append(self.custom(key, "f13", "primary",
                                       "unmet_base1_v12", {"leader": lf}, t))
            return ("ok", out) if out else ("nd", [])
        if lf and lf["kind"] == "unique" and lf["base"] > 1:
            t = (f"Pupils were most likely to have unmet demand for "
                 f"{lf['labels'][0]}, selected by {lf['count']} of the "
                 f"{lf['base']} {S.phrase} who answered.")
            out.append(self.custom(key, "f13", "primary", "unmet_leader_v11",
                                   {"leader": lf}, t))
            if lf["runner"] and lf["runner"]["labels"]:
                rl, rc = lf["runner"]["labels"], lf["runner"]["count"]
                named = tie_txt(rl)
                if named is not None:
                    joint = " jointly" if len(rl) > 1 else ""
                    each = " each" if len(rl) > 1 else ""
                    t2 = (f"Next came {named}{joint}, with {rc} "
                          f"{selw(rc)}{each}, {S.qual}.")
                    out.append(self.custom(key, "f13", "supporting",
                                           "unmet_runner_v11",
                                           {"runner": lf["runner"]}, t2))
        else:
            self.para(out, self.s_leader_multi(key, S, "f13", "unmet_demand",
                                               "sport"))
        if tier == "broad":
            self.para(out, self.s_gender_leader_pair(key, S, "f13", "unmet_demand",
                                                     "unmet-demand sport"))
        return ("ok", out) if out else ("nd", [])

    def m_f14(self, key, S, tier):
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        excl = ({self.cohorts[S.cohort]["code"]}
                if src in ("sports_wanted", "sports_participated") else None)
        lu = self.leader("unmet_demand", self.res(key, "unmet_demand"), excl)
        lp = self.leader("sports_participated", self.res(key, "sports_participated"), excl)
        if not lu or not lp or lu["kind"] == "all_zero" or lp["kind"] == "all_zero":
            return ("insufficient", [])
        u_named, p_named = tie_txt(lu["labels"]), tie_txt(lp["labels"])
        u_txt = u_named if u_named else f"{len(lu['labels'])} sports jointly"
        p_txt = p_named if p_named else f"{len(lp['labels'])} sports jointly"
        t = (f"{cap_first(u_txt)} had the largest unmet-demand count "
             f"({lu['count']} {rw(lu['count'])}), while {p_txt} had the "
             f"largest current-participation count ({lp['count']}), {S.qual}.")
        return ("ok", [self.custom(key, "f14", "primary", "current_vs_demand_v41",
                                   {"unmet": lu, "current": lp,
                                    "unmet_tie_n": len(lu["labels"]),
                                    "current_tie_n": len(lp["labels"])}, t)])

    def m_f15(self, key, S, tier):
        """Chapter summary (v2): stage variation and barriers. The latent-
        and unmet-demand aggregate moved to the Enjoyment summary (g12) and
        sport-level demand detail to the Sport chapter, per the Sport Wales
        feedback."""
        out = []
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        src_code = self.cohorts[S.cohort]["code"] if S.cohort != "none" else None
        self.para(out, self.s_phase_compare(key, S, "f15", "organised_freq",
                                            WEEKLY_PLUS, V_WEEKLY))
        b_excl = {"none_of_these"} | ({src_code} if src == "would_do_more_if" else set())
        lb = self.leader("would_do_more_if", self.res(key, "would_do_more_if"), b_excl)
        if lb and lb["kind"] == "unique":
            aside = (" apart from the condition defining this selected group"
                     if src == "would_do_more_if" else "")
            out.append(self.custom(key, "f15", "supporting", "summary_barrier_v41",
                                   {"leader": lb},
                                   f"The most frequently selected enabling condition"
                                   f"{aside} {S.qual} was ‘{lb['labels'][0]}’ "
                                   f"({lb['count']} of {lb['base']})."))
        return ("ok", out) if out else ("insufficient", [])

    # ----------------------------------------------------------- enjoyment
    def m_g2(self, key, S, tier):
        vals = []
        for mid, name in ENJOY_SETTINGS:
            res = self.res(key, mid)
            n = self.count_of(mid, res, ["a_lot"])
            low = self.count_of(mid, res, ["not_much", "not_at_all"])
            if n is not None:
                vals.append((name, n, low, res["base"]))
        if not vals:
            return ("nd", [])
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        ENJ_MIDS = {"enjoy_pe": "PE lessons",
                    "enjoy_school_clubs": "school sports clubs",
                    "enjoy_community_clubs": "clubs outside school",
                    "enjoy_other_settings": "other settings"}
        if src in ENJ_MIDS and src != "enjoy_pe":
            # v5 (build 012): every enjoyment chart is selectable - report
            # the next-highest OTHER setting, never the defining one
            out = [self.group_note(key, S, "g2")]
            others = [v for v in vals if v[0] != ENJ_MIDS[src]
                      and v[0] != {"enjoy_pe": "PE lessons"}.get(src)]
            others = [v for v in vals
                      if v[0].lower() != ENJ_MIDS[src].lower()]
            if others:
                hi2 = max(others, key=lambda v: v[1])
                out.append(self.custom(key, "g2", "primary", "enjoy_group_next_v41",
                                       {"setting": hi2[0], "count": hi2[1],
                                        "base": hi2[3]},
                                       f"Among {S.phrase}, {hi2[0]} received "
                                       f"the next-highest ‘a lot’ count: {hi2[1]} of the "
                                       f"{hi2[3]} who answered."))
            return ("ok", out)
        if src == "enjoy_pe":
            # anti-tautology (Prototype 4.1 §6.1): report the next-highest
            # setting among the same respondents, never PE again
            out = [self.group_note(key, S, "g2")]
            others = [v for v in vals if v[0] != "PE lessons"]
            if others:
                hi2 = max(others, key=lambda v: v[1])
                out.append(self.custom(key, "g2", "primary", "enjoy_group_next_v41",
                                       {"setting": hi2[0], "count": hi2[1],
                                        "base": hi2[3]},
                                       f"Among {S.phrase}, {hi2[0]} received "
                                       f"the next-highest ‘a lot’ count: {hi2[1]} of the "
                                       f"{hi2[3]} who answered."))
            return ("ok", out)
        hi = max(vals, key=lambda v: v[1])
        lowmost = max(vals, key=lambda v: v[2])
        out = [self.custom(key, "g2", "primary", "enjoy_settings_v2",
                           {"values": vals},
                           f"{cap_first(S.phrase)} were most likely to say they enjoy "
                           f"sport ‘a lot’ in {hi[0]}: {hi[1]} of the {hi[3]} who "
                           f"answered.")]
        if lowmost[2] and lowmost[0] != hi[0]:
            out.append(self.custom(key, "g2", "supporting", "enjoy_low_setting_v2",
                                   {"setting": lowmost[0], "count": lowmost[2],
                                    "base": lowmost[3]},
                                   f"Lower enjoyment was most common for sport in "
                                   f"{lowmost[0]}, where {lowmost[2]} of {lowmost[3]} "
                                   f"answered ‘not much’ or ‘not at all’, {S.qual}."))
        return ("ok", out)

    def m_g3(self, key, S, tier):
        scope, gender, ck = key.split("|")
        if gender == "all":
            p = self.s_gender_compare(key, S, "g3", "enjoy_pe", ["a_lot"], V_PEALOT,
                                      tier == "broad")
            return ("ok", [p]) if p else ("insufficient", [])
        if scope == "whole":
            sents = []
            phase_facts = {}
            for ph in ("primary", "secondary"):
                res = self.res(state_key(ph, gender, ck), "enjoy_pe")
                n = self.count_of("enjoy_pe", res, ["a_lot"])
                if n is not None and self.pct_ok(res["base"]):
                    phase_facts[ph] = [n, res["base"],
                                       self.pct(n, res["base"])]
                    sents.append(f"{n} of {res['base']} ({self.pct(n, res['base'])}%) in "
                                 f"the {ph} phase")
            if sents:
                t = (f"Among {S.phrase}, enjoying PE lessons ‘a lot’ was reported by "
                     f"{join_and(sents)}.")
                return ("ok", [self.custom(key, "g3", "comparison",
                                           "gender_phase_enjoy_v2",
                                           {"sentences": sents, **phase_facts}, t)])
        return ("na_view", [])

    def m_g4(self, key, S, tier):
        scope, gender, ck = key.split("|")
        rows, vals = [], []
        ENJ = ["enjoy_pe", "enjoy_school_clubs", "enjoy_community_clubs",
               "enjoy_other_settings"]
        for y in self.scope_years_list(scope):
            yk = state_key(f"y{y}", gender, ck)
            if not self.visible(yk):
                rows.append({"y": f"Year {y}", "yk": f"y{y}", "sup": 1})
                continue
            cells = []
            for mid in ENJ:
                res = self.res(yk, mid)
                if res is None or res["status"] != "ok" or not res["base"]:
                    cells.append(None)
                    continue
                nn = self.count_of(mid, res, ["a_lot"])
                cells.append([nn, res["base"]])
            res = self.res(yk, "enjoy_pe")
            n = self.count_of("enjoy_pe", res, ["a_lot"])
            p = self.pct(n, res["base"]) if self.pct_ok(res["base"]) else None
            rows.append({"y": f"Year {y}", "yk": f"y{y}", "n": n,
                         "b": res["base"], "p": p, "all": cells})
            if p is not None:
                vals.append((y, n, res["base"], p))
        self._g4rows = rows
        if len(vals) < 2:
            return ("insufficient", [])
        hi = max(vals, key=lambda v: v[3])
        lo = min(vals, key=lambda v: v[3])
        t = (f"Enjoyment of PE was proportionally highest in Year {hi[0]} ({hi[1]} of "
             f"{hi[2]} answered ‘a lot’, or {hi[3]}%) and lowest in Year {lo[0]} "
             f"({lo[1]} of {lo[2]}, or {lo[3]}%), {S.qual}.")
        return ("ok", [self.custom(key, "g4", "primary", "enjoy_year_extremes_v2",
                                   {"values": vals}, t)])

    def m_g5(self, key, S, tier):
        out = []
        broad = tier == "broad"
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        if src == "ideas_listened":
            self.para(out, self.group_note(key, S, "g5"))
            jres = self.res(key, "join_in_easily")
            nj = self.count_of("join_in_easily", jres, ["always", "sometimes"])
            if nj is not None:
                t = (f"{nj} of the {jres['base']} {S.phrase} said they can join in with "
                     f"sports and games easily at least sometimes.")
                self.para(out, self.custom(key, "g5", "cross", "li_join_cross_v3",
                                           {"count": nj, "base": jres["base"]}, t))
            return ("ok", out)
        # v4 (build 011): the 2022-basis clause was struck in the V2
        # feedback and is removed at template level.
        res_a = self.res(key, "ideas_listened")
        na = self.count_of("ideas_listened", res_a, ["always"])
        if na is not None and res_a["base"] > 1:
            t = (f"{na} of the {res_a['base']} {S.phrase} who answered said "
                 f"their ideas about sport are always listened to.")
            self.para(out, self.custom(key, "g5", "primary", "listened_always_v11",
                                       {"count": na, "base": res_a["base"]}, t))
        self.para(out, self.s_leader_single(key, S, "g5", "ideas_listened", broad))
        self.para(out, self.s_combined(key, S, "g5", "ideas_listened",
                                       ["not_often", "never"],
                                       "said their ideas are not often or never "
                                       "listened to", broad))
        return ("ok", out) if out else ("nd", [])

    def m_g6g7(self, key, S, tier):
        scope, gender, ck = key.split("|")
        src = self.cohorts.get(ck, {}).get("metric") if ck != "none" else None
        if src == "ideas_listened":
            return ("na_view", [])     # comparisons of the defining answer are trivial
        out = []
        if gender == "all":
            self.para(out, self.s_gender_compare(key, S, "g6g7", "ideas_listened",
                                                 POS_LISTEN, V_LISTEN, tier == "broad"))
        if tier == "broad" and gender == "all":
            worst = None
            for y in self.scope_years_list(scope):
                yk = state_key(f"y{y}", gender, ck)
                if not self.visible(yk):
                    continue
                res = self.res(yk, "ideas_listened")
                n = self.count_of("ideas_listened", res, ["not_often", "never"])
                if n is not None and self.pct_ok(res["base"]):
                    p = self.pct(n, res["base"])
                    if worst is None or p > worst[3]:
                        worst = (y, n, res["base"], p)
            if worst:
                t = (f"Feeling unheard was proportionally most common in Year {worst[0]} "
                     f"{S.place}: {worst[1]} of {worst[2]} pupils ({worst[3]}%) said "
                     f"their ideas are not often or never listened to.")
                self.para(out, self.custom(key, "g6g7", "comparison",
                                           "listened_worst_year_v2", {"worst": worst}, t))
        elif gender != "all" and scope == "whole":
            sents = []
            for ph in ("primary", "secondary"):
                res = self.res(state_key(ph, gender, ck), "ideas_listened")
                n = self.count_of("ideas_listened", res, POS_LISTEN)
                if n is not None and res["base"]:
                    sents.append(f"{n} of {res['base']} in the {ph} phase")
            if sents:
                self.para(out, self.custom(key, "g6g7", "comparison",
                                           "gender_phase_listened_v2", {"sentences": sents},
                                           f"Among {S.phrase}, ideas were listened to always "
                                           f"or sometimes for {join_and(sents)}."))
        return ("ok", out) if out else ("na_view", [])

    def m_g8(self, key, S, tier):
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        out = []
        CONF_MIDS = ("confidence_try_new", "confidence_learn_skill",
                     "confidence_try_again", "confidence_new_place")
        if src in CONF_MIDS and src != "confidence_try_new":
            # v5 (build 012): every confidence chart is selectable
            self.para(out, self.group_note(key, S, "g8"))
            sib = "confidence_try_new"
            lf = self.leader(sib, self.res(key, sib))
            if lf and lf["kind"] == "unique":
                t = (f"Most of this selected group answered ‘{lf['labels'][0]}’ "
                     f"when asked how confident they are to try a new sport "
                     f"({lf['count']} of {lf['base']}).")
                self.para(out, self.custom(key, "g8", "cross",
                                           "group_sibling_trynew_v12",
                                           {"leader": lf}, t))
            else:
                t = (f"Your school’s data do not provide enough additional reportable "
                     f"information about the other confidence measures {S.qual}.")
                self.para(out, self.custom(key, "g8", "note", "no_additional_conf_v2", {}, t))
            return ("ok", out)
        if src == "confidence_try_new":
            self.para(out, self.group_note(key, S, "g8"))
            lf = self.leader("confidence_learn_skill", self.res(key, "confidence_learn_skill"))
            if lf and lf["kind"] == "unique":
                t = (f"Most of this selected group also answered ‘{lf['labels'][0]}’ when "
                     f"asked how confident they are to learn a new skill ({lf['count']} of "
                     f"{lf['base']}).")
                self.para(out, self.custom(key, "g8", "cross", "group_sibling_skill_v2",
                                           {"leader": lf}, t))
            else:
                t = (f"Your school’s data do not provide enough additional reportable "
                     f"information about the other confidence measures {S.qual}.")
                self.para(out, self.custom(key, "g8", "note", "no_additional_conf_v2", {}, t))
            return ("ok", out)
        tn = self.res(key, "confidence_try_new")
        if tn is not None and tn["status"] == "ok" and tn["base"] == 1:
            lf1 = self.leader("confidence_try_new", tn)
            if lf1 and lf1["kind"] == "unique":
                t = (f"The one pupil in this selected group answered "
                     f"‘{lf1['labels'][0]}’ when asked how confident they are to try a "
                     f"new sport.")
                return ("ok", [self.custom(key, "g8", "primary", "conf_base1_v41",
                                           {"leader": lf1}, t)])
            return ("insufficient", [])
        vals = []
        for mid, name in CONF_DIMS:
            res = self.res(key, mid)
            n = self.count_of(mid, res, POS_CONF)
            if n is not None:
                vals.append((name, n, res["base"]))
        if not vals:
            return ("nd", [])
        hi_n = max(v[1] for v in vals)
        lo_n = min(v[1] for v in vals)
        his = [v for v in vals if v[1] == hi_n]
        los = [v for v in vals if v[1] == lo_n]
        # tie handling (Revision Brief section 13.5): never label the same
        # measure both strongest and weakest
        if hi_n == lo_n:
            t = (f"Confidence was equally high across all four measures, with {hi_n} "
                 f"of the {vals[0][2]} {S.phrase} who answered selecting ‘Very’ or "
                 f"‘Quite’ for each measure.")
            tid = "confidence_equal_v3"
        elif len(his) > 1:
            t = (f"Confidence in {join_and([h[0] for h in his])} received the "
                 f"joint-highest positive response ({hi_n} of {his[0][2]} said ‘very’ or "
                 f"‘quite’), while {join_and([l[0] for l in los])} received the lowest "
                 f"({lo_n} of {los[0][2]}), among {S.phrase}.")
            tid = "confidence_joint_hi_v3"
        else:
            t = (f"{cap_first(S.phrase)} were most likely to say they were confident "
                 f"{his[0][0]}: {hi_n} of the {his[0][2]} who answered said ‘very’ or "
                 f"‘quite’.")
            t2_ = (f"They were {'jointly ' if len(los) > 1 else ''}least likely to say "
                   f"they were confident {join_and([l[0] for l in los])} "
                   f"({lo_n} of {los[0][2]}), {S.qual}.")
            out.append(self.custom(key, "g8", "primary", "confidence_dims_v5",
                                   {"values": vals}, t))
            out.append(self.custom(key, "g8", "supporting", "confidence_dims_low_v5",
                                   {"values": vals}, t2_))
            t = None
            tid = None
        if t is not None:
            out.append(self.custom(key, "g8", "primary", tid, {"values": vals}, t))
        res = self.res(key, "confidence_try_new")
        n = self.count_of("confidence_try_new", res, LOW_CONF)
        if n:
            out.append(self.custom(key, "g8", "supporting", "low_confidence_v2",
                                   {"count": n, "base": res["base"]},
                                   f"{n} of the {res['base']} {S.phrase}{S.ans} said they "
                                   f"were not very or not at all confident to try a new "
                                   f"sport."))
        return ("ok", out)

    def m_g9g10(self, key, S, tier):
        scope, gender, ck = key.split("|")
        out = []
        if gender == "all":
            self.para(out, self.s_gender_compare(key, S, "g9g10", "confidence_try_new",
                                                 POS_CONF, V_CONF, tier == "broad"))
        if tier == "broad" and gender == "all":
            vals = []
            for y in self.scope_years_list(scope):
                yk = state_key(f"y{y}", gender, ck)
                if not self.visible(yk):
                    continue
                res = self.res(yk, "confidence_try_new")
                n = self.count_of("confidence_try_new", res, POS_CONF)
                if n is not None and self.pct_ok(res["base"]):
                    vals.append((y, n, res["base"], self.pct(n, res["base"])))
            if len(vals) >= 2:
                hi = max(vals, key=lambda v: v[3])
                lo = min(vals, key=lambda v: v[3])
                t = (f"Confidence to try a new sport was proportionally highest in "
                     f"Year {hi[0]} ({hi[1]} of {hi[2]}, or {hi[3]}%) and lowest in "
                     f"Year {lo[0]} ({lo[1]} of {lo[2]}, or {lo[3]}%), {S.qual}.")
                self.para(out, self.custom(key, "g9g10", "comparison",
                                           "conf_year_extremes_v2", {"values": vals}, t))
        return ("ok", out) if out else ("na_view", [])

    def m_g11(self, key, S, tier):
        if tier != "broad":
            return ("na_view", [])
        out = []
        self.para(out, self.s_cross_group(key, S, "g11", "ji_not_often",
                                          "confidence_try_new",
                                          "answer about confidence to try a new sport"))
        self.para(out, self.s_cross_group(key, S, "g11", "ct_very", "enjoy_pe",
                                          "answer about enjoying sport in PE lessons"))
        return ("ok", out[:2]) if out else ("insufficient", [])

    def m_g12(self, key, S, tier):
        """Chapter synthesis with universal source-exclusion: a measure that
        defines the selected group is swapped for its nearest sibling."""
        out = []
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        ep_mid, ep_word = (("enjoy_school_clubs", "school sports clubs")
                           if src == "enjoy_pe" else ("enjoy_pe", "PE lessons"))
        li_mid, li_word = (("join_in_easily", None)
                           if src == "ideas_listened" else ("ideas_listened", None))
        ct_mid, ct_word = (("confidence_learn_skill", "learn a new skill")
                           if src == "confidence_try_new"
                           else ("confidence_try_new", "try a new sport"))
        ep = self.res(key, ep_mid)
        ct = self.res(key, ct_mid)
        ne = self.count_of(ep_mid, ep, ["a_lot"])
        nc = self.count_of(ct_mid, ct, POS_CONF)
        if src == "ideas_listened":
            li = self.res(key, "join_in_easily")
            nl = self.count_of("join_in_easily", li, ["always", "sometimes"])
            li_clause = "can join in with sports and games easily at least sometimes"
        else:
            li = self.res(key, "ideas_listened")
            nl = self.count_of("ideas_listened", li, POS_LISTEN)
            li_clause = "feel their ideas are listened to always or sometimes"
        if ne is not None and nl is not None and nc is not None:
            t = (f"Taking this chapter together, {S.phrase} report broadly positive "
                 f"experiences: {ne} of {ep['base']} enjoy sport in {ep_word} ‘a lot’ "
                 f"and {nl} of {li['base']} {li_clause}.")
            out.append(self.custom(key, "g12", "primary", "en_synthesis_v41",
                                   {"enjoy": ne, "enjoy_base": ep["base"],
                                    "listened": nl, "listened_base": li["base"]}, t))
            t2 = (f"Confidence follows the same pattern in this view, with {nc} of "
                  f"{ct['base']} very or quite confident to {ct_word}, {S.qual}.")
            out.append(self.custom(key, "g12", "supporting", "en_synthesis_conf_v41",
                                   {"confident": nc, "confident_base": ct["base"]}, t2))
        # v2.1: the merged chapter has ONE summary - fold in the former
        # Lifelong summary content (stage variation and barriers).
        self.para(out, self.s_phase_compare(key, S, "g12", "overall_freq",
                                            WEEKLY_ACC, V_WEEKLY_ALL))
        src_code = self.cohorts[S.cohort]["code"] if S.cohort != "none" else None
        b_excl = {"none_of_these"} | ({src_code} if src == "would_do_more_if" else set())
        lb = self.leader("would_do_more_if", self.res(key, "would_do_more_if"), b_excl)
        if lb and lb["kind"] == "unique":
            aside = (" apart from the condition defining this selected group"
                     if src == "would_do_more_if" else "")
            out.append(self.custom(key, "g12", "supporting", "summary_barrier_v41",
                                   {"leader": lb},
                                   f"The most commonly chosen enabling condition"
                                   f"{aside} {S.qual} was ‘{lb['labels'][0]}’ "
                                   f"({lb['count']} of {lb['base']})."))
        # v2 (Sport Wales feedback): the latent- and unmet-demand AGGREGATE
        # moved into this Enjoyment summary; sport-level detail now sits in
        # the Sport chapter. Skipped when the selected group is defined by a
        # demand measure (source-exclusion rule).
        if src not in ("sports_wanted", "unmet_demand", "would_do_more_if"):
            sw = self.res(key, "sports_wanted")
            lead = self.leader("sports_wanted", sw) if sw else None
            um = self.res(key, "unmet_demand")
            ul = self.leader("unmet_demand", um) if um else None
            if (lead and lead["kind"] == "unique" and
                    ul and ul["kind"] == "unique"):
                t3 = (f"Looking ahead, demand among {S.phrase} was strongest "
                      f"for {lead['labels'][0]} ({lead['count']} of "
                      f"{lead['base']} selected it), while {ul['labels'][0]} "
                      f"showed the largest unmet demand ({ul['count']} wanted "
                      f"more but are not currently doing it). The Sport "
                      f"chapter reports demand sport by sport.")
                out.append(self.custom(key, "g12", "supporting",
                                       "demand_aggregate_v5",
                                       {"demand_leader": lead["labels"][0],
                                        "demand_n": lead["count"],
                                        "demand_base": lead["base"],
                                        "unmet_leader": ul["labels"][0],
                                        "unmet_n": ul["count"]}, t3))
        return ("ok", out) if out else ("insufficient", [])

    # ------------------------------------------------------ closing + cards
    def build_h1(self, key, S, tier, mods):
        """Summary of the current view: freshly synthesised cross-theme
        sentences (Revision Brief section 18.5) — never copied verbatim from
        the chapter summaries, always source-selection aware."""
        scope, gender, ck = key.split("|")
        src = self.cohorts.get(ck, {}).get("metric") if ck != "none" else None
        src_code = self.cohorts[ck]["code"] if ck != "none" else None
        broad = tier == "broad"
        out = {"an": [], "ev": [], "ll": [], "en": []}
        # a one- or two-person selected group gets its findings from the
        # module charts; a cross-theme summary would only produce strained
        # singular prose (Prototype 4.1 §5.1)
        if self.eng.bases[key] <= 2:
            return out

        def add(theme, tid, facts, text, min_base=None):
            # a one-person view gets its findings from the modules, not the
            # cross-theme summary (Prototype 4.1 §5.1)
            if min_base is not None and min_base <= 1:
                return
            if text:
                # D49 (v1.7): the h1 summary is a generated surface inside
                # the acceptance boundary — keep the Welsh twin the
                # renderer produced instead of discarding it
                p = self.custom(key, "h1", "primary", tid, facts, text)
                out[theme].append({"t": p["t"], **({"c": p["c"]}
                                                   if p.get("c") else {})})

        # --- Active Nation
        fres = self.res(key, "club_freq_estimate")
        nw = self.count_of("club_freq_estimate", fres, CLUB_WEEKLY)
        if nw is not None:
            pct = (f", or {self.pct(nw, fres['base'])}%,"
                   if broad and self.pct_ok(fres["base"]) else "")
            add("an", "h1_an_freq_v3", {"count": nw, "base": fres["base"],
                                        "pct": (self.pct(nw, fres["base"])
                                                if pct else None)},
                f"{nw} of the {fres['base']} {S.phrase}{pct} took part in "
                f"club sport at least once a week.")
        excl = {src_code} if src == "sports_participated" else None
        if broad and gender == "all":
            kb, kg = state_key(scope, "boy", ck), state_key(scope, "girl", ck)
            if self.visible(kb) and self.visible(kg):
                lb = self.leader("sports_participated", self.res(kb, "sports_participated"), excl)
                lg = self.leader("sports_participated", self.res(kg, "sports_participated"), excl)
                if lb and lg and lb["kind"] == "unique" and lg["kind"] == "unique":
                    apart_lbl = (self.opt_labels("sports_participated")[src_code]
                                 if excl else None)
                    apart = f"Apart from {apart_lbl}, " if excl else ""
                    add("an", "h1_an_gender_leaders_v3",
                        {"boys": lb, "girls": lg, "apart": apart_lbl},
                        f"{apart}{lb['labels'][0]} ranked first among boys and "
                        f"{lg['labels'][0]} among girls, {S.place}.")
        else:
            lf = self.leader("sports_participated", self.res(key, "sports_participated"), excl)
            if lf and lf["kind"] in ("unique", "tie"):
                apart_lbl = (self.opt_labels("sports_participated")[src_code]
                             if excl else None)
                apart = f"apart from {apart_lbl}, " if excl else ""
                named = tie_txt(lf["labels"])
                if named is None:
                    add("an", "h1_an_leader_tie_v41",
                        {"leader": lf, "tie_n": len(lf["labels"]),
                         "apart": apart_lbl},
                        f"Among {S.phrase}, {apart}{len(lf['labels'])} sports were tied "
                        f"as the most selected ({lf['count']} {selw(lf['count'])} each); "
                        f"the current-sports chart shows them all.")
                else:
                    add("an", "h1_an_leader_v3", {"leader": lf,
                                                  "apart": apart_lbl},
                        f"Among {S.phrase}, {apart}{named} "
                        f"{'were' if len(lf['labels']) > 1 else 'was'} selected most often "
                        f"({lf['count']} {selw(lf['count'])}).")

        # --- Everyone
        if src == "join_in_easily":
            li = self.res(key, "ideas_listened")
            nl = self.count_of("ideas_listened", li, POS_LISTEN)
            if nl is not None:
                add("ev", "h1_ev_listened_v3", {"count": nl, "base": li["base"]},
                    f"{nl} of the {li['base']} {S.phrase} feel their ideas about sport "
                    f"are listened to always or sometimes.")
        else:
            jres = self.res(key, "join_in_easily")
            nh = self.count_of("join_in_easily", jres, HARD_JOIN)
            if nh is not None:
                jopts = dict(self.defs["join_in_easily"]["options"])
                add("ev", "h1_ev_join_v3",
                    {"count": nh, "base": jres["base"],
                     "metric": "join_in_easily", "codes": list(HARD_JOIN),
                     "code_labels": [jopts[cd] for cd in HARD_JOIN
                                     if cd in jopts]},
                    f"{nh} of the {jres['base']} {S.phrase} said they do not often or "
                    f"never find it easy to join in with sports and games.")
        if broad:
            counts, base = self.counts_by_code(key, "disability_condition")
            if counts is not None:
                add("ev", "h1_ev_disability_v3", {"count": counts.get("yes", 0), "base": base},
                    f"{counts.get('yes', 0)} of the {base} who answered reported a "
                    f"disability or long-term condition, {S.qual}.")

        # --- Lifelong
        dexcl = {src_code} if src == "sports_wanted" else None
        ld = self.leader("sports_wanted", self.res(key, "sports_wanted"), dexcl)
        lu = self.leader("unmet_demand", self.res(key, "unmet_demand"), dexcl)
        if ld and lu and ld["kind"] in ("unique", "tie") and lu["kind"] in ("unique", "tie"):
            apart_lbl = (self.opt_labels("sports_wanted")[src_code]
                         if dexcl else None)
            apart = f"apart from {apart_lbl}, " if dexcl else ""
            d_named, u_named = tie_txt(ld["labels"]), tie_txt(lu["labels"])
            d_txt = (d_named if d_named else
                     f"{len(ld['labels'])} sports jointly")
            u_txt = (u_named if u_named else
                     f"{len(lu['labels'])} sports jointly")
            add("ll", "h1_ll_demand_v41",
                {"demand": ld, "unmet": lu, "demand_tie_n": len(ld["labels"]),
                 "unmet_tie_n": len(lu["labels"]), "apart": apart_lbl},
                f"Among {S.phrase}, {apart}demand was strongest for "
                f"{d_txt} ({ld['count']} {selw(ld['count'])}), while "
                f"{u_txt} showed the largest unmet demand "
                f"({lu['count']}).")
        bexcl = {"none_of_these"} | ({src_code} if src == "would_do_more_if" else set())
        lb2 = self.leader("would_do_more_if", self.res(key, "would_do_more_if"), bexcl)
        if (broad or not out["ll"]) and lb2 and lb2["kind"] == "unique":
            aside = " apart from the condition defining this selected group" \
                if src == "would_do_more_if" else ""
            add("ll", "h1_ll_barrier_v3", {"leader": lb2,
                                           "aside": bool(aside)},
                f"The condition most often chosen{aside} as helping {S.phrase} do more "
                f"sport was ‘{lb2['labels'][0]}’ ({lb2['count']} of {lb2['base']}).")

        # --- Enjoyment
        ep_mid = "enjoy_school_clubs" if src == "enjoy_pe" else "enjoy_pe"
        ep_word = ("school sports clubs" if src == "enjoy_pe" else "PE lessons")
        ct_mid = "confidence_learn_skill" if src == "confidence_try_new" else "confidence_try_new"
        ct_word = ("learn a new skill" if src == "confidence_try_new" else "try a new sport")
        ep = self.res(key, ep_mid)
        ct = self.res(key, ct_mid)
        ne = self.count_of(ep_mid, ep, ["a_lot"])
        nc = self.count_of(ct_mid, ct, POS_CONF)
        if ne is not None and nc is not None:
            add("en", "h1_en_enjoy_conf_v3",
                {"enjoy": ne, "enjoy_base": ep["base"], "conf": nc,
                 "conf_base": ct["base"], "ep_mid": ep_mid, "ct_mid": ct_mid},
                f"Among {S.phrase}, {ne} of {ep['base']} enjoy sport in {ep_word} "
                f"‘a lot’, and {nc} of {ct['base']} are very or quite confident to "
                f"{ct_word}.")
        if broad and src != "ideas_listened":
            li = self.res(key, "ideas_listened")
            nl = self.count_of("ideas_listened", li, POS_LISTEN)
            if nl is not None:
                add("en", "h1_en_listened_v3", {"count": nl, "base": li["base"]},
                    f"{nl} of the {li['base']} who answered feel their ideas about sport "
                    f"are listened to always or sometimes, {S.qual}.")
        return out

    def build_h2(self, key, S, mods=None):
        """D49/sheet 38 (v1.7): the two VARIABLE prompts are generated
        narrative (typed fact record, Welsh realised independently); the
        two GENERIC prompts are static catalogue strings routed through
        the translator handoff, keyed so the client can substitute the
        translation when it lands."""
        qs = []
        lu = self.leader("unmet_demand", self.res(key, "unmet_demand"))
        if lu and lu["kind"] == "unique":
            p = self.custom(key, "h2", "primary", "h2_unmet_prompt_v44",
                            {"leader": lu},
                            f"{lu['labels'][0]} was selected by {lu['count']} {rw(lu['count'])} "
                            f"as something they would like to do more of but are not currently "
                            f"doing, {S.qual}. Do current opportunities reflect this interest?")
            qs.append({"t": p["t"], **({"c": p["c"]} if p.get("c") else {})})
        res = self.res(key, "join_in_easily")
        nj = self.count_of("join_in_easily", res, HARD_JOIN)
        if nj:
            p = self.custom(key, "h2", "primary", "h2_join_prompt_v44",
                            {"count": nj},
                            f"{nj} {rw(nj)} in this view said they do not often or never find "
                            f"it easy to join in. What would help them take part?")
            qs.append({"t": p["t"], **({"c": p["c"]} if p.get("c") else {})})
        qs.append({"t": "Which findings match what you see day to day, and "
                        "which are surprising?", "g": "h2_generic_reflect"})
        qs.append({"t": "Could further pupil discussion help explain these "
                        "findings before provision changes are planned?",
                   "g": "h2_generic_discussion"})
        return qs[:4]

    def build_cards(self, key, S, tier):
        scope, gender, ck = key.split("|")
        broad = tier == "broad"
        src = self.cohorts.get(ck, {}).get("metric") if ck != "none" else None
        cards = [{"t": "Respondents in this view", "v": str(self.eng.bases[key]),
                  "s": "included in every figure below"}]

        def add_combined(title, mid, codes, subverb):
            res = self.res(key, mid)
            n = self.count_of(mid, res, codes)
            if n is None:
                cards.append({"t": title, "v": "—", "s": "not available in this view"})
                return
            sub = f"of {res['base']} who answered"
            if broad and self.pct_ok(res["base"]):
                sub = f"{self.pct(n, res['base'])}% · of {res['base']} who answered"
            cards.append({"t": title, "v": str(n), "s": sub + " · " + subverb})

        def add_leader(title, mid, exclude=None):
            lf = self.leader(mid, self.res(key, mid), exclude)
            if not lf or lf["kind"] == "all_zero":
                cards.append({"t": title, "v": "—", "s": "not available in this view"})
            elif lf["kind"] == "tie":
                from .narrative2 import selw as _sw
                if len(lf["labels"]) == 2:
                    cards.append({"t": title, "v": " & ".join(lf["labels"]),
                                  "s": f"tied · {lf['count']} {_sw(lf['count'])} each"})
                else:
                    cards.append({"t": title, "v": f"{len(lf['labels'])}-way tie",
                                  "s": f"{lf['count']} {_sw(lf['count'])} each"})
            else:
                cards.append({"t": title, "v": lf["labels"][0],
                              "s": f"{lf['count']} of {lf['base']} selected this"})

        add_combined("Club sport 3+ times a week (estimated)", "club_freq_estimate",
                     ["e3", "e4", "e5", "e6", "e7", "e8", "e9plus"],
                     "school or community club")
        add_combined("Less than weekly club sport", "club_freq_estimate",
                     ["none_reported", "less_weekly_only", "dont_know_only"],
                     "including none reported")
        if src == "sports_participated":
            labels = self.opt_labels("sports_participated")
            add_leader(f"Top sport apart from {labels[self.cohorts[ck]['code']]}",
                       "sports_participated", exclude=self.cohorts[ck]["code"])
        else:
            add_leader("Most selected sport", "sports_participated")
        if gender == "all" and self.visible(state_key(scope, "boy", ck)) \
                and self.visible(state_key(scope, "girl", ck)):
            for g, ti in (("boy", "Top sport among boys"), ("girl", "Top sport among girls")):
                gk = state_key(scope, g, ck)
                lf = self.leader("sports_participated", self.res(gk, "sports_participated"))
                if lf and lf["kind"] == "unique":
                    cards.append({"t": ti, "v": lf["labels"][0],
                                  "s": f"{lf['count']} of {lf['base']} selected this"})
                elif lf and lf["kind"] == "tie" and len(lf["labels"]) == 2:
                    cards.append({"t": ti, "v": " & ".join(lf["labels"]),
                                  "s": f"tied · {lf['count']} each"})
        else:
            if src == "would_do_more_if":
                labels = self.opt_labels("would_do_more_if")
                add_leader(f"Next most helpful condition (after ‘{labels[self.cohorts[ck]['code']]}’)",
                           "would_do_more_if",
                           exclude={"none_of_these", self.cohorts[ck]["code"]})
            else:
                add_leader("Most helpful condition", "would_do_more_if",
                           exclude="none_of_these")
            if src == "join_in_easily":
                add_combined("Ideas listened to", "ideas_listened", POS_LISTEN,
                             "always or sometimes")
            else:
                add_combined("Can always join in easily", "join_in_easily", ["always"],
                             "sports and games")
        if src == "sports_wanted":
            labels = self.opt_labels("sports_wanted")
            add_leader(f"Top desired sport apart from {labels[self.cohorts[ck]['code']]}",
                       "sports_wanted", exclude={self.cohorts[ck]["code"]})
        else:
            add_leader("Top sport to do more of", "sports_wanted")
        if tier == "broad" and gender == "all" and ck == "none":
            best = None
            for y in self.scope_years_list(scope):
                yk = state_key(f"y{y}", "all", "none")
                if not self.visible(yk):
                    continue
                res = self.res(yk, "club_freq_estimate")
                n = self.count_of("club_freq_estimate", res, CLUB_WEEKLY)
                if res["base"]:
                    p = self.pct(n, res["base"])
                    if best is None or p > best[1]:
                        best = (y, p, n, res["base"])
            if best:
                cards.append({"t": "Highest participation year", "v": f"Year {best[0]}",
                              "s": f"{best[2]} of {best[3]} weekly+ ({best[1]}%)"})
        if src == "ideas_listened":
            add_combined("Can always join in easily", "join_in_easily", ["always"],
                         "sports and games")
        else:
            add_combined("Ideas listened to", "ideas_listened", POS_LISTEN,
                         "always or sometimes")
        add_combined("PE makes pupils feel healthy", "pe_feel_healthy", POS_CONF,
                     "‘very’ or ‘quite’")
        if src == "enjoy_pe":
            add_combined("Enjoy school club sport ‘a lot’", "enjoy_school_clubs", ["a_lot"],
                         "school sports clubs")
        else:
            add_combined("Enjoy PE lessons ‘a lot’", "enjoy_pe", ["a_lot"], "PE lessons")
        if src == "confidence_try_new":
            add_combined("Confident to learn a new skill", "confidence_learn_skill",
                         POS_CONF, "‘very’ or ‘quite’")
        else:
            add_combined("Confident to try a new sport", "confidence_try_new", POS_CONF,
                         "‘very’ or ‘quite’")
        for c in cards:
            c["sc"] = S.short
        return cards

    # ------------------------------------------------------- state assembly
    # v2 (Sport Wales feedback): dedicated boy/girl and by-year comparison
    # modules removed - the right-hand filters cover that exploration.
    # e4 (year x gender) is retained and relocated to A Lifelong Enjoyment
    # of Sport. d0 (overall frequency across all settings) added.
    MODULES = ["d0", "d2", "d3", "d4", "d5", "d6", "d7", "s1",
               "e2", "n_dl", "n_ed", "e4", "e7", "n_wl",
               "f2", "f3f5", "f6", "f7", "f10", "f11", "f12",
               "f13", "f14", "g2", "g3", "g4", "g5", "g8"]

    # narrative-volume control (Revision Brief section 9 / 18): these
    # secondary modules are omitted in chart-derived group views and listed
    # in "Data available in this view"
    # v6 (build 012.1): e7 stays visible under its own filter
    GROUP_TIER_SKIP = {"e8", "e9"}

    def build_state(self, key):
        scope, gender, ck = key.split("|")
        S = Scope(scope, gender, ck, self.cohorts, self.profile)
        tier = tier_of(scope, gender, ck)
        self._e4rows = self._f2rows = self._g4rows = None
        mods = {}
        for mid_ in self.MODULES:
            if tier == "group" and mid_ in self.GROUP_TIER_SKIP:
                mods[mid_] = {"s": "na_view", "p": []}
                continue
            builder = getattr(self, f"m_{mid_}")
            status, paras = builder(key, S, tier)
            mods[mid_] = {"s": status, "p": paras}
        h1 = self.build_h1(key, S, tier, mods)
        # package hygiene: only reportable modules carry narrative; every
        # other module appears in the availability list instead
        avail = [[m, mods[m]["s"]] for m in self.MODULES if mods[m]["s"] != "ok"]
        mod_out = {m: v for m, v in mods.items() if v["s"] == "ok"}
        # v2 (Sport Wales feedback): the Key statistics page was removed, so
        # per-state cards are no longer built or shipped.
        return {
            "scope": S.as_dict(),
            "tier": tier,
            "coverage": self.eng.coverage_mark(scope, gender, ck),
            "mod": mod_out,
            "h1": h1,
            "h2": self.build_h2(key, S),
            "avail": avail,
            "rows": {"f2": self._f2rows, "e4": self._e4rows, "g4": self._g4rows},
        }

# EOF sentinel
