"""Module content builders (v2): one entry per report module.

Implements the Content and Narrative Specification module inventory with
tiered depth, mandatory gender/year/phase comparisons in broad views,
parent-view comparisons in narrow views, cross-question insights through
pre-calculated selected-group states, tautology guards, and per-module
availability states feeding the "Data available in this view" panel.
"""
from __future__ import annotations

from .engine import state_key
from .narrative2 import (HARD_JOIN, LOW_CONF, NO_FREQUENT, POS_CONF, POS_LISTEN,
                         Narrator, Scope, T, WEEKLY_PLUS, cap_first, join_and,
                         ordinal, rw, selw, tie_txt)

BROAD_SCOPES = ("whole", "primary", "secondary")

V_WEEKLY = "took part in sport in a school club or community club at least once a week"
V_3PLUS = "took part in sport in a school club or community club three or more times a week"
V_NOFREQ = "reported no weekly sport in a school club or community club"
V_LISTEN = "said their ideas about sport are listened to always or sometimes"
V_PEALOT = "said they enjoy sport in PE lessons ‘a lot’"
V_HEALTHY = "said PE and Active Lessons make them feel ‘very’ or ‘quite’ healthy"
V_CONF = "said they were very or quite confident to try a new sport"
V_HARDJOIN = "said they do not often or never find it easy to join in"
V_WEEKLY_ALL = "did sport at least once a week in at least one setting"
WEEKLY_ACC = ["w1", "w2", "w3", "w4", "w5", "w6", "w7"]   # v2.2 accumulated scale

SETTING_PHRASES = {
    "pe_lessons": "in PE or lesson time",
    "school_club": "in a school club",
    "community_club": "in a club outside of school",
    "somewhere_else": "somewhere else",
}

CLUB_WEEKLY = ["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9plus"]
V_CLUB_WEEKLY = ("did club sport (in a school club or a club outside of "
                 "school) at least once a week")

MODULE_LABELS = {
    "d0": "How active are our pupils through sport?",
    "d3": "Where are our pupils taking part?",
    "d4": "What happens in our school clubs?",
    "d5": "What happens in clubs outside school?",
    "d6": "What sport happens somewhere else?",
    "d7": "Which sports do our pupils take part in?",
    "s1": "What sport happens in PE or lesson time?",
    "e2": "Do pupils feel able to join in?",
    "e4": "Participation by year and gender",
    "n_dl": "Where are pupils with a disability and/or learning difficulty active?",
    "n_ed": "Where are pupils from ethnically diverse backgrounds active?",
    "n_wl": "Where are pupils who speak Welsh active?",
    "e7": "How do our pupils take part in sport?",
    "f2": "How does participation change with age?",
    "f3f5": "PE and Active Lessons",
    "f6": "What matters to pupils when they play sport?",
    "f7": "Barriers — what would help pupils do more sport?",
    "f10": "Which sports would pupils like to do more of?",
    "f11": "Which sports do different groups want more of?",
    "f12": "Latent demand by year and phase",
    "f13": "Where is demand not being met?",
    "f14": "Current participation and demand together",
    "g2": "How much do pupils enjoy sport in each setting?",
    "g3": "Enjoyment among boys and girls",
    "g4": "Enjoyment by year",
    "g5": "Do pupils feel listened to?",
    "g8": "How confident are our pupils?",
}

# v5 (build 012): e4/f2/g4 now respond to year filters instead of hiding
YEAR_ONLY_MODULES = {"f12"}


def tier_of(scope, gender, ck):
    if ck != "none":
        return "group"
    if scope in BROAD_SCOPES:
        return "broad"
    return "year" if gender == "all" else "narrow"


class ModuleNarrator(Narrator):

    # ------------------------------------------------------------- helpers
    def para(self, out, p):
        if p is None:
            return
        if isinstance(p, list):
            out.extend(x for x in p if x)
        else:
            out.append(p)

    def group_note(self, key, S, module):
        demo_S = Scope(*key.split("|")[:2], "none", self.cohorts, self.profile)
        t = T["group_defined_v2"].format(phrase=S.phrase, demo=demo_S.phrase)
        return self.log(key, module, "definition", "group_defined_v2",
                        {"group": S.cohort}, t)

    def custom(self, key, module, kind, tid, facts, text):
        return self.log(key, module, kind, tid, facts, text)

    def counts_by_code(self, key, mid):
        res = self.res(key, mid)
        if res is None or res["status"] != "ok":
            return None, None
        return dict(zip([c for c, _ in self.defs[mid]["options"]], res["raw"])), res["base"]

    def year_states(self, gender, years):
        return [(y, state_key(f"y{y}", gender, "none")) for y in years]

    def scope_years_list(self, scope):
        return sorted(self.eng.scope_years[scope])

    # ------------------------------------------------------------ helpers
    # v2 (Sport Wales feedback): record-level cross-tab within the current
    # view, for the participation-inequality emphasis in cohort modules.
    def view_rows(self, key):
        from .engine import filter_rows
        scope, gender, ck = key.split("|")
        return filter_rows(self.eng.records, scope, gender, ck,
                           self.cohorts, self.defs, self.eng.scope_years)

    def weekly_club_split(self, key, field, yes_vals, no_vals):
        """(yes_n, yes_base), (no_n, no_base) for weekly+ club sport within
        the view, split by rec[field] membership."""
        weekly = {"once_week", "twice_week", "three_plus"}
        rows = self.view_rows(key)

        def cnt(vals):
            grp = [r for r in rows if r.get(field) in vals]
            return (sum(1 for r in grp if r.get("organised_freq") in weekly),
                    len(grp))
        return cnt(yes_vals), cnt(no_vals)

    @staticmethod
    def avg_phrase(avg):
        """v5 (build 012, owner rule): averages read as whole numbers only -
        no decimals, no brackets. Standard half-up rounding."""
        n = int(avg + 0.5)
        words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                 6: "six", 7: "seven", 8: "eight", 9: "nine"}
        if n == 0:
            return "fewer than one sport", n
        word = words.get(n, str(n))
        noun = "sport" if n == 1 else "sports"
        return f"{word} {noun}", n

    def chart_sport_rank(self, key, setting=None, top=3):
        """v7 (V4 final): rank sports exactly as the stacked charts do -
        by the number of pupils with a frequency answer for the sport
        (per setting, or once per pupil across settings for overall)."""
        from collections import Counter
        from .common import TIER2_COMPOSITE_CODE
        c = Counter()
        for r in self.view_rows(key):
            seen = set()
            for (s_, sp_), code_ in (r.get("per_sport_freq") or {}).items():
                if sp_ == TIER2_COMPOSITE_CODE:
                    continue
                if setting is None:
                    if sp_ not in seen:
                        seen.add(sp_)
                        c[sp_] += 1
                elif s_ == setting:
                    c[sp_] += 1
        return c.most_common(top)

    def avg_sports(self, key, setting_field=None):
        """v3 (build 010): mean distinct sports per pupil in the view (1 d.p.).
        setting_field limits to one setting's sports; None = any setting."""
        rows = self.view_rows(key)
        if not rows:
            return None, 0
        if setting_field is None:
            vals = [r.get("n_sports_all", 0) for r in rows]
        else:
            vals = [len(set(r.get(setting_field) or set()) - {"other_sports"})
                    for r in rows]
        return round(sum(vals) / len(vals), 1), len(rows)

    # ------------------------------------------------------------ modules
    def m_d0(self, key, S, tier):
        """v3 (build 010): the agreed estimated average weekly frequency.
        Sentences: distribution leader + average sports per pupil."""
        out = []
        broad = tier == "broad"
        src_m = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        if src_m == "freq_estimate":
            # anti-tautology: the group is defined by this chart's answer
            self.para(out, self.group_note(key, S, "d0"))
        else:
            if src_m == "participation_settings":
                # V4.18 (EN-09, owner instruction 22 Sep 2026): under a
                # SETTING selection the chart keeps the wider picture (the
                # client shows the demographic view's bars, still selectable);
                # the narrative leads with the selected-group definition, as
                # the settings chart does under its own selection, and then
                # describes the group as before.
                self.para(out, self.group_note(key, S, "d0"))
            self.para(out, self.s_leader_single(key, S, "d0", "freq_estimate",
                                                broad))
        avg, n = self.avg_sports(key)
        if avg is not None and n > 1:
            phrase, rnd = self.avg_phrase(avg)
            t = (f"On average, {S.phrase} participated in {phrase} "
                 f"throughout the academic year.")
            self.para(out, self.custom(key, "d0", "supporting",
                                       "avg_sports_v11", {"avg": avg, "rounded": rnd}, t))
        # v7 (V4 final, SW row 14): overall top three ranked exactly as the
        # overall stacked chart (one count per pupil per sport)
        if tier != "group":
            labels = self.opt_labels("sports_participated")
            ranked = self.chart_sport_rank(key, setting=None, top=3)
            if len(ranked) >= 2:
                parts = [f"{labels.get(c, c)} ({v})" for c, v in ranked]
                t5 = (f"The sports {S.phrase} selected most often were "
                      f"{join_and(parts)}.")
                self.para(out, self.custom(key, "d0", "supporting",
                                           "overall_top3_v13",
                                           {"top3": ranked}, t5))
        return ("ok", out) if out else ("nd", [])

    def m_d2(self, key, S, tier):
        """v5 (build 012): Club Sports on the flat square-root estimate -
        the single calculation used across the whole report."""
        out = []
        broad = tier == "broad"
        src_m = (self.cohorts.get(S.cohort, {}).get("metric")
                 if S.cohort != "none" else None)
        if src_m == "club_freq_estimate":
            self.para(out, self.group_note(key, S, "d2"))
        else:
            self.para(out, self.s_leader_single(key, S, "d2",
                                                "club_freq_estimate", broad))
        res = self.res(key, "club_freq_estimate")
        if res is not None and res.get("status") == "ok" and res["base"] > 1:
            CLUB3 = ["e3", "e4", "e5", "e6", "e7", "e8", "e9plus"]
            nw = self.count_of("club_freq_estimate", res, CLUB_WEEKLY)
            n3 = self.count_of("club_freq_estimate", res, CLUB3)
            b = res["base"]
            if broad and self.pct_ok(b):
                t = (f"{nw} of the {b} {S.phrase} who answered "
                     f"({self.pct(nw, b)}%) {V_CLUB_WEEKLY}, and {n3} of the "
                     f"{b} {S.phrase} who answered ({self.pct(n3, b)}%) did "
                     f"club sport (in a school club or a club outside of "
                     f"school) three or more times per week.")
                facts = {"weekly": nw, "three_plus": n3, "base": b,
                         "weekly_pct": self.pct(nw, b),
                         "three_plus_pct": self.pct(n3, b)}
            else:
                t = (f"{nw} of the {b} {S.phrase} who answered "
                     f"{V_CLUB_WEEKLY}, and {n3} did club sport (in a school "
                     f"club or a club outside of school) three or more times "
                     f"per week.")
                facts = {"weekly": nw, "three_plus": n3, "base": b}
            self.para(out, self.custom(key, "d2", "supporting",
                                       "club_weekly_3plus_v13", facts, t))
        return ("ok", out) if out else ("nd", [])

    def m_d3(self, key, S, tier):
        out = []
        labels = self.opt_labels("participation_settings")
        src_here = (S.cohort != "none" and
                    self.cohorts[S.cohort]["metric"] == "participation_settings")
        if src_here:
            # anti-tautology (Prototype 4.1 §6.2): describe the group's OTHER
            # settings using the selected-group base, never the source base
            self.para(out, self.group_note(key, S, "d3"))
            sel = self.cohorts[S.cohort]["code"]
            counts, base = self.counts_by_code(key, "participation_settings")
            if counts is None:
                return ("nd", out)
            others = sorted(((c, n) for c, n in counts.items() if c != sel and n > 0),
                            key=lambda x: -x[1])
            if others:
                oc, on = others[0]
                t = (f"Among {S.phrase} ({base} pupils), the next most common "
                     f"setting was sport {SETTING_PHRASES[oc]}, used by {on} pupils.")
                self.para(out, self.custom(key, "d3", "primary", "settings_group_next_v41",
                                           {"next": oc, "count": on, "base": base}, t))
            return ("ok", out)
        counts, base = self.counts_by_code(key, "participation_settings")
        if counts is None:
            return ("nd", out)
        ranked = sorted(counts.items(), key=lambda x: -x[1])
        parts = [f"{labels[c]} ({n})" for c, n in ranked[1:] if n > 0]
        lead_c, lead_n = ranked[0]
        if base == 1:
            used = [SETTING_PHRASES[c] for c, n in ranked if n > 0]
            t = (f"The one pupil in this selected group did sport "
                 f"{join_and(used)}." if used else
                 "The one pupil in this selected group did not report a setting.")
        else:
            t = (f"Sport {SETTING_PHRASES[lead_c]} was the most frequently selected "
                 f"setting, chosen by {lead_n} of the {base} {S.phrase} who answered"
                 + (f", followed by {join_and(parts)}." if parts else "."))
        self.para(out, self.custom(key, "d3", "primary", "settings_rank_v2",
                                   {"ranked": ranked, "base": base}, t))
        self.para(out, self.s_rank_parent(key, S, "d3", "participation_settings",
                                          "setting"))
        return ("ok", out)

    def _club_module(self, key, S, tier, module, setting_code, freq_mid, sports_mid,
                     setting_phrase):
        out = []
        # tautology guard: when the selected group was created from this
        # module's frequency chart, define the group and skip the trivially
        # true frequency sentence
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        guard = src == freq_mid
        if guard:
            self.para(out, self.group_note(key, S, module))
        counts, base = self.counts_by_code(key, "participation_settings")
        if counts is None:
            return ("nd", out)
        n = counts.get(setting_code, 0)
        if base == 1:
            t = (f"The one pupil in this selected group "
                 f"{'reported' if n else 'did not report'} doing sport {setting_phrase}.")
        else:
            # v2.1 (Sport Wales page-by-page feedback, pages 10-11 forms)
            t = (f"{n} of the {base} {S.phrase} who answered this question said "
                 f"they do at least one sport {setting_phrase}.")
        if not guard:
            self.para(out, self.custom(key, module, "primary", "setting_participation_v2",
                                       {"count": n, "base": base, "setting": setting_code}, t))
        # v3 (build 010): the separate per-setting frequency chart is
        # replaced by the stacked sport-frequency chart, so the orphaned
        # largest-group frequency sentence is retired (owner decision).
        lite = tier == "group"
        # v7 (V4 final, SW row 14): the top-three sentence now ranks sports
        # exactly as the stacked chart does, so text and chart always agree.
        if not lite:
            labels = self.opt_labels(sports_mid)
            ranked = self.chart_sport_rank(key, setting=setting_code, top=3)
            if ranked:
                lead_c, lead_n = ranked[0]
                lead_lbl = labels.get(lead_c, lead_c)
                t3 = (f"Pupils were most likely to say they did {lead_lbl} "
                      f"{setting_phrase}, reported by {lead_n} of the "
                      f"{S.phrase} who answered for that setting")
                if len(ranked) > 1:
                    nxt = [f"{labels.get(c, c)} ({v})" for c, v in ranked[1:]]
                    t3 += f", followed by {join_and(nxt)}."
                else:
                    t3 += "."
                self.para(out, self.custom(key, module, "supporting",
                                           "setting_top3_v13",
                                           {"top3": ranked,
                                            "setting": setting_code}, t3))
        # v3 (build 010): Tier 2 references removed from reader-facing copy
        # (register decision) - the composite sentence is retired. An
        # average-sports-per-pupil sentence is added for the setting.
        if not lite:
            sfield = {"pe_freq": "pe_sports",
                      "school_club_freq": "school_club_sports",
                      "community_club_freq": "community_club_sports",
                      "other_setting_freq": "other_setting_sports"}.get(freq_mid)
            avg, na = self.avg_sports(key, sfield) if sfield else (None, 0)
            if avg is not None and na > 1 and avg > 0:
                phrase, rnd = self.avg_phrase(avg)
                t4 = (f"On average, {S.phrase} participated in {phrase} "
                      f"{setting_phrase} throughout the academic year.")
                self.para(out, self.custom(key, module, "supporting",
                                           "avg_sports_setting_v11",
                                           {"avg": avg, "rounded": rnd,
                                            "setting": setting_code}, t4))
        return ("ok", out)

    def _group_settings_module(self, key, S, module, mid, group_phrase,
                               avg_line=False):
        """v3 (build 010): 'where are our pupils active' for a pupil group."""
        out = []
        counts, base = self.counts_by_code(key, mid)
        if counts is None or not base:
            return ("nd", [])
        # disclosure control: fewer than five pupils in the group within
        # this view would risk identifying individuals (rule of five)
        if base < 5:
            return ("insufficient", [])
        # v5 (build 012): the settings bars are now selectable; when the
        # selected group comes from this very chart, lead with the definition
        if (S.cohort != "none" and
                self.cohorts[S.cohort].get("metric") == mid):
            return ("ok", [self.group_note(key, S, module)])
        labels = self.opt_labels(mid)
        ranked = sorted(counts.items(), key=lambda x: -x[1])
        lead_c, lead_n = ranked[0]
        parts = [f"{labels[c]} ({n})" for c, n in ranked[1:] if n > 0]
        t = (f"Sport {SETTING_PHRASES[lead_c]} was the most frequently "
             f"selected setting, chosen by {lead_n} of the {base} "
             f"{group_phrase} {S.qual} who answered"
             + (f", followed by {join_and(parts)}." if parts else "."))
        followers_shown = bool(parts)
        if len(t.split()) > 65:
            # keep within the sentence-length gate in long-qualifier views
            t = (f"Sport {SETTING_PHRASES[lead_c]} was the most frequently "
                 f"selected setting, chosen by {lead_n} of the {base} "
                 f"{group_phrase} {S.qual} who answered.")
            followers_shown = False
        out.append(self.custom(key, module, "primary",
                               "group_settings_rank_v10",
                               {"ranked": ranked, "base": base,
                                "mid": mid,
                                "followers_shown": followers_shown}, t))
        if avg_line:
            rows = [r for r in self.view_rows(key)
                    if r.get("dl_any") == "yes"]
            if len(rows) > 1:
                avg = round(sum(r.get("n_sports_all", 0) for r in rows)
                            / len(rows), 1)
                phrase, rnd = self.avg_phrase(avg)
                t2 = (f"On average, pupils with a disability and/or learning "
                      f"difficulty {S.qual} participated in {phrase} "
                      f"throughout the academic year.")
                out.append(self.custom(key, module, "supporting",
                                       "group_avg_sports_v11",
                                       {"avg": avg, "rounded": rnd}, t2))
        return ("ok", out)

    def dl_mode(self, key):
        """v4 (build 011, owner decision): per-view three-tier rule.
        'sep'  - disability and learning difficulty each have 5+ pupils in
                 view: show the two charts separately;
        'comb' - either falls below 5 but the combined group reaches 5:
                 automatically combine;
        'sup'  - even combined the group is below 5: suppress."""
        rows = self.view_rows(key)
        dy = sum(1 for r in rows if r.get("disability") == "yes")
        ly = sum(1 for r in rows if r.get("learning") == "yes")
        dl = sum(1 for r in rows if r.get("dl_any") == "yes")
        if dy >= 5 and ly >= 5:
            return "sep", dy, ly, dl
        if dl >= 5:
            return "comb", dy, ly, dl
        return "sup", dy, ly, dl

    def m_n_dl(self, key, S, tier):
        # v5 (build 012): the settings bars are selectable - when the group
        # was created from any of this section's charts, lead with the
        # definition and add nothing trivially true
        src_m = (self.cohorts.get(S.cohort, {}).get("metric")
                 if S.cohort != "none" else None)
        if src_m in ("settings_dl", "settings_dy", "settings_ly"):
            return ("ok", [self.group_note(key, S, "n_dl")])
        mode, dy, ly, dl = self.dl_mode(key)
        self._dl_mode = mode
        if mode == "sup":
            return ("insufficient", [])
        if mode == "comb":
            status, out = self._group_settings_module(
                key, S, "n_dl", "settings_dl",
                "pupils with a disability and/or learning difficulty",
                avg_line=True)
            if status == "ok" and (dy < 5 or ly < 5):
                t = ("Disability and learning difficulty are shown as one "
                     "combined group in this view because one of the two "
                     "groups contains fewer than five pupils; each pupil is "
                     "counted once.")
                out.append(self.custom(key, "n_dl", "definition",
                                       "dl_combined_note_v11", {}, t))
            return (status, out)
        # separate mode: one rank sentence per chart, then the overlap note
        out = []
        for mid, gp in [("settings_dy",
                         "pupils with a disability or long-term condition"),
                        ("settings_ly", "pupils with a learning difficulty")]:
            st_, o = self._group_settings_module(key, S, "n_dl", mid, gp)
            if st_ == "ok":
                out.extend(o)
        rows = [r for r in self.view_rows(key) if r.get("dl_any") == "yes"]
        if len(rows) > 1:
            avg = round(sum(r.get("n_sports_all", 0) for r in rows)
                        / len(rows), 1)
            phrase, rnd = self.avg_phrase(avg)
            t2 = (f"On average, pupils with a disability and/or learning "
                  f"difficulty {S.qual} participated in {phrase} "
                  f"throughout the academic year.")
            out.append(self.custom(key, "n_dl", "supporting",
                                   "group_avg_sports_v11", {"avg": avg, "rounded": rnd}, t2))
        return ("ok", out) if out else ("nd", [])

    def m_n_ed(self, key, S, tier):
        return self._group_settings_module(
            key, S, "n_ed", "settings_ed",
            "pupils from ethnically diverse backgrounds")

    def m_n_wl(self, key, S, tier):
        st, out = self._group_settings_module(
            key, S, "n_wl", "settings_wl", "pupils who speak Welsh")
        if st != "ok":
            return (st, out)
        res = self.res(key, "welsh_when_playing_sport")
        if res is not None and res.get("status") == "ok":
            n = self.count_of("welsh_when_playing_sport", res, ["yes"])
            if n is not None:
                t = (f"Of the {res['base']} {S.phrase} asked whether they "
                     f"speak Welsh when playing sport, {n} said yes.")
                out.append(self.custom(key, "n_wl", "supporting",
                                       "welsh_when_playing_v10",
                                       {"count": n, "base": res["base"]}, t))
        return ("ok", out)

    def m_s1(self, key, S, tier):
        """v2: PE / lesson-time sport detail for the Sport chapter."""
        return self._club_module(key, S, tier, "s1", "pe_lessons", "pe_freq",
                                 "sports_pe", "in PE or lesson time")

    def m_d4(self, key, S, tier):
        return self._club_module(key, S, tier, "d4", "school_club", "school_club_freq",
                                 "sports_school_club", "in a school club")

    def m_d5(self, key, S, tier):
        return self._club_module(key, S, tier, "d5", "community_club", "community_club_freq",
                                 "sports_community_club", "in a club outside of school")

    def m_d6(self, key, S, tier):
        return self._club_module(key, S, tier, "d6", "somewhere_else", "other_setting_freq",
                                 "sports_other_setting", "somewhere else")

    def composite_sentence(self, key, S, module, mid):
        """v2.3 clarification 3: the Tier 2 composite is never ranked as if
        it were a single sport; it gets its own qualified sentence."""
        from .common import TIER2_COMPOSITE_CODE
        counts, base = self.counts_by_code(key, mid)
        if not counts:
            return None
        n = counts.get(TIER2_COMPOSITE_CODE, 0)
        if not n or not base or base <= 1:
            return None
        # v7 (V4 final, SW row 36): Sport Wales replacement wording
        t = (f"\u201cOther sports\u201d refers to any sports pupils selected from a "
             f"supplementary list of sports if their sport was not included "
             f"in the main list of sports ({n} of the {base} {S.phrase}). "
             f"These have been grouped together for ease of reporting, and "
             f"are reported in detail in the appendix.")
        return self.custom(key, module, "supporting", "other_sports_note_v13",
                           {"count": n, "base": base}, t)

    def m_d7(self, key, S, tier):
        from .common import TIER2_COMPOSITE_CODE
        out = []
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        if src == "sports_participated":
            self.para(out, self.group_note(key, S, "d7"))
            exclude = {self.cohorts[S.cohort]["code"], TIER2_COMPOSITE_CODE}
            labels = self.opt_labels("sports_participated")
            lf = self.leader("sports_participated", self.res(key, "sports_participated"),
                             exclude=exclude)
            if lf and lf["kind"] == "unique":
                t = (f"Apart from {labels[self.cohorts[S.cohort]['code']]}, "
                     f"which defines this selected group, "
                     f"{lf['labels'][0]} was the most frequently selected sport, chosen by "
                     f"{lf['count']} of the {lf['base']} {S.phrase}.")
                self.para(out, self.custom(key, "d7", "primary", "group_excl_leader_v2",
                                           {"leader": lf}, t))
            return ("ok", out)
        self.para(out, self.s_leader_multi(key, S, "d7", "sports_participated",
                                           "sport or activity",
                                           noun_pl="sports and activities",
                                           exclude={TIER2_COMPOSITE_CODE}))
        self.para(out, self.s_rank_parent(key, S, "d7", "sports_participated", "sport",
                                          exclude={TIER2_COMPOSITE_CODE}))
        self.para(out, self.composite_sentence(key, S, "d7", "sports_participated"))
        return ("ok", out)

    def m_d8(self, key, S, tier):
        scope, gender, ck = key.split("|")
        src = self.cohorts.get(ck, {}).get("metric") if ck != "none" else None
        excl = {self.cohorts[ck]["code"]} if src == "sports_participated" else set()
        out = []
        if gender == "all":
            pair = self.s_gender_leader_pair(key, S, "d8", "sports_participated", "sport",
                                             exclude=excl)
            if not pair:
                return ("insufficient", [])
            self.para(out, pair)
            # shared prominent sports
            def top5(g):
                res = self.res(state_key(scope, g, ck), "sports_participated")
                if not res or res["status"] != "ok":
                    return set()
                ranked = sorted(zip([c for c, _ in self.defs["sports_participated"]["options"]],
                                    res["raw"]), key=lambda x: -x[1])
                return {c for c, v in ranked[:5] if v > 0 and c not in excl}
            shared = top5("boy") & top5("girl")
            if shared:
                labels = self.opt_labels("sports_participated")
                t = T["shared_top_v2"].format(items=join_and(sorted(labels[c] for c in shared)),
                                              place=S.place)
                self.para(out, self.custom(key, "d8", "supporting", "shared_top_v2",
                                           {"shared": sorted(shared)}, t))
            return ("ok", out)
        # gender view: within-gender phase patterns
        if scope == "whole":
            sents = []
            labels = self.opt_labels("sports_participated")
            for ph in ("primary", "secondary"):
                lf = self.leader("sports_participated",
                                 self.res(state_key(ph, gender, ck), "sports_participated"))
                if lf and lf["kind"] in ("unique", "tie"):
                    named = tie_txt(lf["labels"])
                    if named is None:
                        continue     # long-tie rule: no multi-answer listings
                    sents.append(f"{named} led {'in the ' + ph + ' phase'}"
                                 f" ({lf['count']} {selw(lf['count'])})")
            if sents:
                t = f"Among {S.phrase}, {'; '.join(sents)}."
                self.para(out, self.custom(key, "d8", "comparison", "gender_phase_leaders_v2",
                                           {"sentences": sents}, t))
                return ("ok", out)
        return ("na_view", [])

    def m_d9(self, key, S, tier, mid="sports_participated", module="d9", noun="sport"):
        scope, gender, ck = key.split("|")
        if tier not in ("broad",):
            return ("na_view", [])
        out = []
        labels = self.opt_labels(mid)
        if scope == "whole":
            sents = []
            phase_facts = {}
            for ph in ("primary", "secondary"):
                lf = self.leader(mid, self.res(state_key(ph, gender, ck), mid))
                if lf and lf["kind"] in ("unique", "tie"):
                    phase_facts[ph] = {"labels": lf["labels"],
                                       "count": lf["count"]}
                    named = tie_txt(lf["labels"])
                    if named is None:
                        sents.append(f"{len(lf['labels'])} {noun}s were tied in the lead "
                                     f"in the {ph} phase ({lf['count']} "
                                     f"{selw(lf['count'])} each)")
                        continue
                    verb = "were" if len(lf["labels"]) > 1 else "was"
                    sents.append(f"{named} {verb} the most frequently "
                                 f"selected {noun} in the {ph} phase "
                                 f"({lf['count']} {selw(lf['count'])})")
            if sents:
                t = ". ".join(sents) + (f", {S.qual}." if S.qual else ".")
                self.para(out, self.custom(key, module, "comparison", "phase_leaders_v2",
                                           {"sentences": sents, "noun": noun,
                                            **phase_facts}, t))
        # year leaders grouped by leading option
        by_leader = {}
        years_visible = []
        tie_bits = []
        tie_struct = []
        for y, yk in self.year_states(gender, self.scope_years_list(scope)):
            if not self.visible(yk):
                continue
            lf = self.leader(mid, self.res(yk, mid))
            if lf and lf["kind"] == "unique":
                by_leader.setdefault(lf["labels"][0], []).append(f"Year {y}")
                years_visible.append(y)
            elif lf and lf["kind"] == "tie":
                # v7 (V4 final, SW row 38): tied years are named, not dropped
                named = tie_txt(lf["labels"])
                if named is not None:
                    tie_bits.append(f"in Year {y}, {named} were tied "
                                    f"({lf['count']} {selw(lf['count'])} each)")
                    tie_struct.append([y, lf["labels"], lf["count"]])
                    years_visible.append(y)
        if by_leader or tie_bits:
            bits = [f"{lead} led in {join_and(ys)}" for lead, ys in
                    sorted(by_leader.items(), key=lambda kv: -len(kv[1]))]
            prefix = ("Looking at each year group across the whole school"
                      if (scope == "whole" and gender == "all")
                      else f"Looking at each year group among {S.phrase}")
            # keep each sentence inside the 70-word gate: ties go in a
            # second sentence when the leaders sentence is already long
            joined = bits + tie_bits
            t = f"{prefix}, {'; '.join(joined)}."
            if len(t.split()) <= 65 or not bits:
                self.para(out, self.custom(key, module, "comparison", "year_leaders_v2",
                                           {"by_leader": by_leader,
                                            "ties": tie_bits,
                                            "ties_struct": tie_struct}, t))
            else:
                t1 = f"{prefix}, {'; '.join(bits)}."
                self.para(out, self.custom(key, module, "comparison", "year_leaders_v2",
                                           {"by_leader": by_leader}, t1))
                if tie_bits:
                    t2 = ("In the remaining reportable year groups, " +
                          "; ".join(b[3].upper() + b[4:] if b.startswith("in ")
                                    else b for b in [tie_bits[0]]) if False else
                          "; ".join(tie_bits) + f", among {S.phrase}.")
                    t2 = t2[0].upper() + t2[1:]
                    self.para(out, self.custom(key, module, "comparison",
                                               "year_ties_v13",
                                               {"ties": tie_bits,
                                                "ties_struct": tie_struct}, t2))
        return ("ok", out) if out else ("insufficient", [])

    def m_d10(self, key, S, tier):
        """Chapter synthesis: one integrated statement, not repeats of the
        module sentences (Revision Brief section 18.4)."""
        out = []
        broad = tier == "broad"
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        fres = self.res(key, "organised_freq")
        nw = self.count_of("organised_freq", fres, WEEKLY_PLUS)
        if fres is not None and fres["base"] <= 2:
            return ("insufficient", [])   # no chapter synthesis over 1-2 people
        excl = {self.cohorts[S.cohort]["code"]} if src == "sports_participated" else None
        lf = self.leader("sports_participated", self.res(key, "sports_participated"), excl)
        if nw is not None and lf and lf["kind"] in ("unique", "tie"):
            apart = (f"apart from {self.opt_labels('sports_participated')[list(excl)[0]]}, "
                     if excl else "")
            pcttxt = (f" ({self.pct(nw, fres['base'])}%)"
                      if broad and self.pct_ok(fres["base"]) else "")
            named = tie_txt(lf["labels"])
            lead_txt = (f"{named} {'were' if len(lf['labels']) > 1 else 'was'} selected "
                        f"most often" if named else
                        f"{len(lf['labels'])} sports were tied as the most selected")
            t = (f"Taking this chapter together: {nw} of the {fres['base']} {S.phrase}"
                 f"{pcttxt} took part in sport in a school club or community club at least weekly. "
                 f"Among their current sports, {apart}{lead_txt} ({lf['count']} "
                 f"{'selections' if lf['count'] != 1 else 'selection'}"
                 f"{' each' if len(lf['labels']) > 1 else ''}).")
            self.para(out, self.custom(key, "d10", "primary", "an_synthesis_v41",
                                       {"weekly": nw, "base": fres["base"], "leader": lf,
                                        "tie_n": len(lf["labels"]),
                                        "pct": self.pct(nw, fres["base"]) if fres["base"] else None}, t))
        if broad:
            self.para(out, self.s_cross_group(key, S, "d10", "cf_three_plus",
                                              "sports_participated",
                                              "sport among frequent club participants"))
        return ("ok", out) if out else ("insufficient", [])

    # ------------------------------------------------------------ everyone
    def m_e2(self, key, S, tier):
        out = []
        broad = tier == "broad"
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        if src == "join_in_easily":
            self.para(out, self.group_note(key, S, "e2"))
            lf = self.leader("confidence_try_new", self.res(key, "confidence_try_new"))
            if lf and lf["kind"] == "unique":
                t = (f"Asked how confident they are to try a new sport, the largest group "
                     f"of {S.phrase} ({lf['count']} of {lf['base']}) said ‘{lf['labels'][0]}’.")
                self.para(out, self.custom(key, "e2", "cross", "group_sibling_conf_v2",
                                           {"leader": lf}, t))
            return ("ok", out)
        self.para(out, self.s_leader_single(key, S, "e2", "join_in_easily", broad))
        self.para(out, self.s_combined(key, S, "e2", "join_in_easily", HARD_JOIN,
                                       V_HARDJOIN, broad))
        if broad:
            self.para(out, self.s_gender_compare(key, S, "e2", "join_in_easily",
                                                 HARD_JOIN, V_HARDJOIN, True))
            self.para(out, self.s_cross_group(key, S, "e2", "ji_not_often",
                                              "would_do_more_if",
                                              "condition that would help them do more sport"))
        if tier in ("narrow", "group"):
            self.para(out, self.s_parent_compare(key, S, "e2", "join_in_easily", HARD_JOIN))
        return ("ok", out)

    def m_e3(self, key, S, tier):
        scope, gender, ck = key.split("|")
        if tier == "narrow":
            return ("na_view", [])
        out = []
        if gender == "all":
            p = self.s_gender_compare(key, S, "e3", "organised_freq", WEEKLY_PLUS,
                                      V_WEEKLY, tier == "broad")
            if p is None:
                return ("insufficient", [])
            self.para(out, p)
            return ("ok", out)
        # gender view: year patterns within the gender
        vals = []
        for y, yk in self.year_states(gender, self.scope_years_list(scope)):
            if not self.visible(yk):
                continue
            res = self.res(yk, "organised_freq")
            n = self.count_of("organised_freq", res, WEEKLY_PLUS)
            if n is not None and self.pct_ok(res["base"]):
                vals.append((y, n, res["base"], self.pct(n, res["base"])))
        if len(vals) >= 2:
            hi = max(vals, key=lambda v: v[3])
            lo = min(vals, key=lambda v: v[3])
            t = (f"Among {S.phrase}, weekly club sport participation was proportionally "
                 f"highest in Year {hi[0]} ({hi[1]} of {hi[2]}, or {hi[3]}%) and lowest in "
                 f"Year {lo[0]} ({lo[1]} of {lo[2]}, or {lo[3]}%).")
            self.para(out, self.custom(key, "e3", "comparison", "gender_year_extremes_v2",
                                       {"values": vals}, t))
            return ("ok", out)
        return ("insufficient", [])

    def m_e4(self, key, S, tier):
        """v5 (build 012): responds to filters - a gender filter shows only
        that gender's bars, a year filter only that year."""
        scope, gender, ck = key.split("|")
        GENS = [("boy", "b"), ("girl", "g")] if gender == "all" else \
               [(gender, "b" if gender == "boy" else "g")]
        # v3 (build 010, feedback row 28): rows now carry per-setting
        # counts for each year-gender combination, for the stacked chart.
        SETTINGS = ["pe_lessons", "school_club", "community_club",
                    "somewhere_else"]
        rows, best = [], None
        for y in self.scope_years_list(scope):
            # D70 (sheet 46): stable scope key on every derived row
            row = {"y": f"Year {y}", "yk": f"y{y}"}
            for g, pre in GENS:
                yk = state_key(f"y{y}", g, ck)
                if not self.visible(yk):
                    row[pre + "sup"] = 1
                    continue
                counts, sbase = self.counts_by_code(yk, "participation_settings")
                if counts is not None:
                    row[pre + "c"] = [counts.get(s, 0) for s in SETTINGS]
                    row[pre + "cb"] = sbase
            rows.append(row)
        # v4 (build 011): the analysis describes the setting-based chart
        sbest = None
        for row in rows:
            for g, pre in (("boy", "b"), ("girl", "g")):
                c, sb = row.get(pre + "c"), row.get(pre + "cb")
                if not c or not sb or sb < 10:
                    continue
                for si, v in enumerate(c):
                    p = round(100 * v / sb)
                    if sbest is None or p > sbest[4]:
                        sbest = (row["y"], g, SETTINGS[si], v, p, sb)
        out = []
        if sbest:
            gw = "boys" if sbest[1] == "boy" else "girls"
            t = (f"Among groups large enough to report, the highest "
                 f"participation in a single setting {S.place} was "
                 f"{sbest[0]} {gw} {SETTING_PHRASES[sbest[2]]}: "
                 f"{sbest[3]} of {sbest[5]} pupils ({sbest[4]}%).")
            self.para(out, self.custom(key, "e4", "primary", "yg_setting_best_v11",
                                       {"best": sbest}, t))
        self._e4rows = rows
        return ("ok", out) if rows else ("insufficient", [])

    def _sensitive_profile_sentence(self, key, S, module, mid, subject):
        """Profile sentence with deliberate zero/one-category wording
        (Prototype 4.1 §5.2)."""
        counts, base = self.counts_by_code(key, mid)
        if counts is None:
            return None
        yes, ns_, pnts = (counts.get("yes", 0), counts.get("not_sure", 0),
                          counts.get("prefer_not_to_say", 0))
        if base == 1:
            only = ("reported" if yes else "did not report")
            t = f"The one pupil in this selected group {only} {subject}."
        else:
            t = (f"{yes} of the {base} {S.phrase} who answered reported {subject}")
            if ns_ == 0 and pnts == 0:
                t += ". No pupils selected ‘Not sure’ or ‘Prefer not to say’."
            else:
                bits = []
                if ns_:
                    bits.append(f"{ns_} {'was' if ns_ == 1 else 'were'} not sure")
                if pnts:
                    bits.append(f"{pnts} preferred not to say")
                t += "; " + " and ".join(bits) + "."
        return self.custom(key, module, "primary", "sensitive_profile_v41",
                           {"counts": counts, "base": base}, t)

    def m_e5(self, key, S, tier):
        out = []
        scope, gender, ck = key.split("|")
        src = self.cohorts.get(ck, {}).get("metric") if ck != "none" else None
        if src == "disability_condition":
            # v2.1 (row 27) / v2.4: plain-language filter explanation,
            # generalised to whichever answer defines the selected group
            lbl = self.cohorts[ck].get("optionLabel", "Yes")
            self.para(out, self.custom(
                key, "e5", "definition", "bar_filter_note_v5",
                {"answer": lbl},
                f"The bar selected filters the wider report by pupils who "
                f"responded ‘{lbl}’ to this question. Explore how these "
                f"pupils responded to other questions in the survey."))
            res_j = self.res(key, "join_in_easily")
            nj = self.count_of("join_in_easily", res_j, HARD_JOIN)
            res_f = self.res(key, "organised_freq")
            nf = self.count_of("organised_freq", res_f, WEEKLY_PLUS)
            if nj is not None and nf is not None and res_j["base"] > 1:
                t = (f"Among {S.phrase}, {nf} of {res_f['base']} {V_WEEKLY}, and "
                     f"{nj} of {res_j['base']} {V_HARDJOIN}.")
                self.para(out, self.custom(key, "e5", "cross", "disability_experience_v2",
                                           {"weekly": nf, "weekly_base": res_f["base"],
                                            "hard_join": nj, "join_base": res_j["base"]}, t))
            return ("ok", out)
        p = self._sensitive_profile_sentence(key, S, "e5", "disability_condition",
                                             "a disability or long-term condition")
        if p is None:
            return ("nd", [])
        self.para(out, p)
        if ck == "none":
            # v2 (Sport Wales feedback): the emphasis is how PARTICIPATION
            # differs, not a description of the group.
            (yn, yb), (nn, nb) = self.weekly_club_split(
                key, "disability", {"yes"}, {"no"})
            if yb > 1 and nb > 1:
                t2 = (f"Among {S.phrase}, {yn} of the {yb} pupils who reported "
                      f"a disability or long-term condition {V_WEEKLY}, compared "
                      f"with {nn} of the {nb} pupils who reported none.")
                self.para(out, self.custom(
                    key, "e5", "cross", "disability_participation_gap_v5",
                    {"yes_weekly": yn, "yes_base": yb,
                     "no_weekly": nn, "no_base": nb}, t2))
            gkey = state_key(scope, gender, "dy_yes")
            if self.visible(gkey):
                gS = Scope(scope, gender, "dy_yes", self.cohorts, self.profile)
                res_j = self.res(gkey, "join_in_easily")
                nj = self.count_of("join_in_easily", res_j, HARD_JOIN)
                if nj is not None:
                    t3 = (f"Among {gS.phrase}, {nj} of {res_j['base']} "
                          f"{V_HARDJOIN}.")
                    self.para(out, self.custom(key, "e5", "cross",
                                               "disability_experience_v2",
                                               {"hard_join": nj,
                                                "join_base": res_j["base"]}, t3))
            elif yb <= 1:
                t2 = T["not_enough_group_v2"].format(
                    topic="sporting experiences among pupils with a disability or "
                          "long-term condition", qual=S.qual)
                self.para(out, self.custom(key, "e5", "note", "not_enough_group_v2",
                                           {"group": "dy_yes"}, t2))
        return ("ok", out)

    def m_e6(self, key, S, tier):
        out = []
        scope, gender, ck = key.split("|")
        src = self.cohorts.get(ck, {}).get("metric") if ck != "none" else None
        if src == "learning_difficulty":
            # v2.1 (rows 28-29): filter explanation; join-in analysis removed
            self.para(out, self.custom(
                key, "e6", "definition", "bar_filter_note_v5", {},
                "The bar selected filters the wider report by pupils who "
                "responded ‘Yes’ to this question. Explore how these pupils "
                "responded to other questions in the survey."))
            res_f = self.res(key, "organised_freq")
            nf = self.count_of("organised_freq", res_f, WEEKLY_PLUS)
            if nf is not None and res_f["base"] > 1:
                t = (f"Among {S.phrase}, {nf} of {res_f['base']} {V_WEEKLY}.")
                self.para(out, self.custom(key, "e6", "cross", "learning_participation_v5",
                                           {"weekly": nf, "base": res_f["base"]}, t))
            return ("ok", out)
        p = self._sensitive_profile_sentence(key, S, "e6", "learning_difficulty",
                                             "a learning difficulty, such as dyslexia "
                                             "or dyspraxia")
        if p is None:
            return ("nd", [])
        self.para(out, p)
        if ck == "none":
            # v2 (Sport Wales feedback): emphasise the participation gap.
            (yn, yb), (nn, nb) = self.weekly_club_split(
                key, "learning", {"yes"}, {"no"})
            if yb > 1 and nb > 1:
                t2 = (f"Among {S.phrase}, {yn} of the {yb} pupils who reported "
                      f"a learning difficulty {V_WEEKLY}, compared with {nn} of "
                      f"the {nb} pupils who reported none.")
                self.para(out, self.custom(
                    key, "e6", "cross", "learning_participation_gap_v5",
                    {"yes_weekly": yn, "yes_base": yb,
                     "no_weekly": nn, "no_base": nb}, t2))
        return ("ok", out)

    def m_e7(self, key, S, tier):
        # v6 (build 012.1): visible under its own filter - lead with the
        # group definition instead of restating the defining answer
        src_m = (self.cohorts.get(S.cohort, {}).get("metric")
                 if S.cohort != "none" else None)
        if src_m == "take_part_method":
            return ("ok", [self.group_note(key, S, "e7")])
        res = self.res(key, "take_part_method")
        if res is None or res["status"] == "na":
            return ("na", [])
        if res["status"] == "nd":
            return ("nd", [])
        # complete prose with correct verbs (Revision Brief section 13.6)
        VERBS = {
            "standing": ("said that they usually took part standing",) * 2,
            "seated": ("said that they usually took part seated",) * 2,
            "communication_aids": ("used communication aids",) * 2,
            "not_sure": ("was not sure", "were not sure"),
            "prefer_not_to_say": ("preferred not to say",) * 2,
            "other": ("selected another approved category",
                      "selected other approved categories"),
        }
        pairs = [(c, v) for (c, _), v in
                 zip(self.defs["take_part_method"]["options"], res["raw"]) if v > 0]
        pairs.sort(key=lambda x: -x[1])
        clauses = [f"{n} {VERBS[c][0] if n == 1 else VERBS[c][1]}" for c, n in pairs]
        t = (f"Of the {res['base']} {S.phrase} asked how they usually take part in "
             f"sport, {join_and(clauses)}.")
        return ("ok", [self.custom(key, "e7", "primary", "take_part_prose_v3",
                                   {"pairs": pairs, "base": res["base"]}, t)])

    def m_e8(self, key, S, tier):
        # v2 (Sport Wales feedback): focus on participation inequality, not
        # the language profile; phase comparison removed (filters cover it).
        # "Welsh speakers" here means pupils who said they speak Welsh very
        # well or a fair amount.
        out = []
        scope, gender, ck = key.split("|")
        if ck == "none":
            (yn, yb), (nn, nb) = self.weekly_club_split(
                key, "welsh", {"very_well", "fair_amount"},
                {"a_little", "few_words", "none"})
            if yb > 1 and nb > 1:
                t = (f"Among {S.phrase}, {yn} of the {yb} Welsh speakers "
                     f"(pupils who said they speak Welsh very well or a fair "
                     f"amount) {V_WEEKLY}, compared with {nn} of the {nb} "
                     f"other pupils who answered.")
                self.para(out, self.custom(
                    key, "e8", "cross", "welsh_participation_gap_v5",
                    {"yes_weekly": yn, "yes_base": yb,
                     "no_weekly": nn, "no_base": nb}, t))
        res = self.res(key, "welsh_when_playing_sport")
        n = self.count_of("welsh_when_playing_sport", res, ["yes"])
        if n is not None:
            t = (f"Of the {res['base']} {S.phrase} who speak at least a few "
                 f"words of Welsh, {n} said they usually speak Welsh when playing sport.")
            self.para(out, self.custom(key, "e8", "supporting", "welsh_conditional_v2",
                                       {"count": n, "base": res["base"]}, t))
        return ("ok", out) if out else ("nd", [])

    def m_e9(self, key, S, tier):
        counts, base = self.counts_by_code(key, "ethnicity_group")
        if counts is None:
            return ("nd", [])
        # each category takes an appropriate verb (Corrective Brief 9.4)
        VERBS = {
            "white": "identified as White",
            "mixed": "identified with mixed or multiple ethnic groups",
            "asian": "identified as Asian, Asian Welsh or Asian British",
            "other_grouped": "identified with other ethnic groups",
            "not_sure": "selected ‘I’m not sure’",
            "prefer_not_to_say": "preferred not to say",
        }
        pairs = [(c, n) for c, n in counts.items() if n > 0]
        pairs.sort(key=lambda x: -x[1])
        listed = join_and([f"{n} {VERBS[c]}" for c, n in pairs])
        out = [self.custom(key, "e9", "primary", "ethnicity_profile_v3",
                           {"counts": counts, "base": base},
                           f"Of the {base} {S.phrase} who answered, {listed}.")]
        # v2 (Sport Wales feedback): look at "ethnically diverse" overall,
        # and make the focus how participation varies, not the profile.
        (yn, yb), (nn, nb) = self.weekly_club_split(
            key, "ethnicity", {"mixed", "asian", "other_grouped"}, {"white"})
        if yb > 1 and nb > 1:
            t = (f"Taken together, {yn} of the {yb} pupils from ethnically "
                 f"diverse backgrounds (any ethnic group other than White) "
                 f"{S.qual} {V_WEEKLY}, compared with {nn} of the {nb} pupils "
                 f"who identified as White.")
            out.append(self.custom(
                key, "e9", "cross", "ethnicity_participation_gap_v5",
                {"yes_weekly": yn, "yes_base": yb,
                 "no_weekly": nn, "no_base": nb}, t))
        # v2.4 (owner instruction): ethnicity IS now a filter source; the
        # note explains the under-five rule instead.
        out.append(self.custom(key, "e9", "note", "ethnicity_filter_note_v9", {},
                               "Ethnic groups can be selected to filter the "
                               "wider report. Where fewer than five pupils "
                               "selected a group, it cannot be used as a "
                               "filter, to protect the anonymity of pupils."))
        return ("ok", out)

    def m_e10(self, key, S, tier):
        """Chapter synthesis: integrated wording, not module repeats, with
        the joining-in measure swapped when it defines the selected group."""
        out = []
        src = self.cohorts.get(S.cohort, {}).get("metric") if S.cohort != "none" else None
        if src == "join_in_easily":
            li = self.res(key, "ideas_listened")
            nl = self.count_of("ideas_listened", li, ["always", "sometimes"])
            if nl is not None and li["base"] > 1:
                t = (f"Bringing this chapter together: {nl} of the {li['base']} "
                     f"{S.phrase} feel their ideas about sport are listened to always "
                     f"or sometimes.")
                self.para(out, self.custom(key, "e10", "primary", "ev_synthesis_ji_v41",
                                           {"listened": nl, "base": li["base"]}, t))
            return ("ok", out) if out else ("insufficient", [])
        # v2.1 (row 33): the "able to join in at least sometimes" analysis is
        # removed; the synthesis now points at participation variation, with
        # the source-exclusion rule applied.
        mid = ("learning_difficulty" if src == "disability_condition"
               else "disability_condition")
        word = ("a learning difficulty" if src == "disability_condition"
                else "a disability or long-term condition")
        counts, base = self.counts_by_code(key, mid)
        if counts is not None and base and base > 1:
            t = (f"Bringing this chapter together: {counts.get('yes', 0)} of the "
                 f"{base} {S.phrase} who answered reported {word}; the summary "
                 f"table above compares weekly club sport for every aggregated "
                 f"group of pupils on the same basis.")
            self.para(out, self.custom(key, "e10", "primary", "ev_synthesis_v5",
                                       {"yes": counts.get("yes", 0),
                                        "base": base}, t))
        return ("ok", out) if out else ("insufficient", [])

# EOF sentinel
