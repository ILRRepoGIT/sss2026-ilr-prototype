"""Deterministic module narrative engine (v2).

Every sentence is generated at build time from named templates and calculated
facts; every sentence self-scopes (states whom it describes); every rendered
paragraph is logged with its template id and fact object for audit.

Depth tiers (Revision Brief section 9 / spec section 9):
  broad   whole school or a phase, no selected group  -> full depth
  year    one year group, all respondents             -> medium
  narrow  one year group + gender                     -> concise
  group   any view with a chart-derived selected group-> concise + cross
"""
from __future__ import annotations

import json
import re

from .common import LABELS
from .engine import state_key

# rule-level singular agreement (Revision Brief section 13): applied to every
# rendered sentence so no template can emit "1 respondents" or "1 selections"
_SINGULAR_FIXES = [
    (re.compile(r"\b1 respondents\b"), "1 respondent"),
    (re.compile(r"\b1 pupils\b"), "1 pupil"),
    (re.compile(r"\b1 pupils were\b"), "1 pupil was"),
    (re.compile(r"\b1 selections\b"), "1 selection"),
    (re.compile(r"\b1 boys\b"), "1 boy"),
    (re.compile(r"\b1 girls\b"), "1 girl"),
    (re.compile(r"\b1 respondents were\b"), "1 respondent was"),
    # zero counts read as prose (Corrective Brief section 9.5)
    (re.compile(r"\b0 of the\b"), "none of the"),
    (re.compile(r"\b0 of\b"), "none of"),
]
_CAP_NONE = re.compile(r"(^|(?<=\. ))none")


# v6 (0.28.0): the build's own English gates for a base of one (the same
# expressions run_qa_checks applies to every audited sentence). A locked
# template that can only produce a sentence these reject on a one-pupil
# base has no one-pupil form; the sentence is HELD rather than shipped,
# and the hold is logged (sheet 49, EN-08). Kept here so the hold and the
# gate can never drift apart.
BASE1_GATES = [re.compile(r"\bof the 1 (respondent|pupil)\b"),
               re.compile(r"\b1 (selections|respondents|pupils|boys|girls)\b"),
               re.compile(r"\b1 were\b")]


def held_by_gate(text: str) -> bool:
    """Would run_qa_checks reject this (grammar-fixed) sentence as a plural
    template applied to a base of one?"""
    t = fix_grammar(text)
    return any(g.search(t) for g in BASE1_GATES)


def fix_grammar(text: str) -> str:
    for pat, rep in _SINGULAR_FIXES:
        text = pat.sub(rep, text)
    return _CAP_NONE.sub(lambda m: m.group(1) + "None", text)

ORD = ["zeroth", "first", "second", "third", "fourth", "fifth", "sixth", "seventh",
       "eighth", "ninth", "tenth", "11th", "12th", "13th", "14th", "15th", "16th",
       "17th", "18th", "19th", "20th"]

WEEKLY_PLUS = ["once_week", "twice_week", "three_plus"]
NO_FREQUENT = ["none_reported", "less_weekly"]
POS_LISTEN = ["always", "sometimes"]
POS_CONF = ["very", "quite"]
LOW_CONF = ["not_very", "not_at_all"]
LOW_ENJOY = ["not_much", "not_at_all"]
HARD_JOIN = ["not_often", "never"]

_SETTING_IN = {
    "pe_lessons": "in PE or lesson time",
    "school_club": "in a school club",
    "community_club": "in a club outside of school",
    "somewhere_else": "somewhere else",
}


def _ENJOY_VERB(setting, code):
    return {
        "a_lot": f"said they enjoy sport in {setting} \u2018a lot\u2019",
        "a_little": f"said they enjoy sport in {setting} \u2018a little\u2019",
        "not_much": f"said they do not enjoy sport in {setting} much",
        "not_at_all": f"said they do not enjoy sport in {setting} at all",
        "not_sure": f"were not sure whether they enjoy sport in {setting}",
    }[code]


def _CONF_VERB(action, code):
    return {
        "very": f"said they were very confident to {action}",
        "quite": f"said they were quite confident to {action}",
        "not_very": f"said they were not very confident to {action}",
        "not_at_all": f"said they were not at all confident to {action}",
    }[code]


GROUP_VERBS = {
    "sp": lambda label, code: f"selected {label}",
    "cf": lambda label, code: {
        "less_weekly_only": "did sport in a club outside school, but less than once a week",
        "w1": "did sport in a club outside school once a week",
        "w2": "did sport in a club outside school twice a week",
        "w3": "did sport in a club outside school three times a week",
        "w4": "did sport in a club outside school four times a week",
        "w5": "did sport in a club outside school five times a week",
        "w6": "did sport in a club outside school six times a week",
        "w7": "did sport in a club outside school seven or more times a week",
    }[code],
    "ep": lambda label, code: {
        "a_lot": "said they enjoy sport in PE lessons ‘a lot’",
        "a_little": "said they enjoy sport in PE lessons ‘a little’",
        "not_much": "said they do not enjoy sport in PE lessons much",
        "not_at_all": "said they do not enjoy sport in PE lessons at all",
        "not_sure": "were not sure whether they enjoy sport in PE lessons",
    }[code],
    "ji": lambda label, code: {
        "always": "said they can always join in with sports and games easily",
        "sometimes": "said they can sometimes join in with sports and games easily",
        "not_often": "said they do not often find it easy to join in with sports and games",
        "never": "said they never find it easy to join in with sports and games",
    }[code],
    "ct": lambda label, code: {
        "very": "said they were very confident to try a new sport",
        "quite": "said they were quite confident to try a new sport",
        "not_very": "said they were not very confident to try a new sport",
        "not_at_all": "said they were not at all confident to try a new sport",
    }[code],
    "st": lambda label, code: {
        "pe_lessons": "did sport in PE or lesson time",
        "school_club": "did sport in a school club",
        "community_club": "did sport in a club outside of school",
        "somewhere_else": "did sport somewhere else",
    }[code],
    "dy": lambda label, code: {
        "yes": "reported a disability or long-term condition",
        "no": "reported no disability or long-term condition",
        "not_sure": "were not sure whether they have a disability or long-term condition",
        "prefer_not_to_say": "preferred not to say whether they have a disability or long-term condition",
    }[code],
    "ly": lambda label, code: "reported a learning difficulty",
    "et": lambda label, code: {
        "white": "identified as White",
        "mixed": "identified with mixed or multiple ethnic groups",
        "asian": "identified as Asian, Asian Welsh or Asian British",
        "other_grouped": "identified with other ethnic groups",
        "not_sure": "selected ‘I’m not sure’ for their ethnicity",
        "prefer_not_to_say": "preferred not to say their ethnicity",
    }[code],
    "wl": lambda label, code: {
        "very_well": "said they can speak Welsh very well",
        "fair_amount": "said they can speak a fair amount of Welsh",
        "a_little": "said they can speak a little Welsh",
        "few_words": "said they can say just a few words in Welsh",
        "none": "said they do not speak Welsh",
    }[code],
    "ov": lambda label, code: (
        "reported no sport in any setting" if code == "none_reported"
        else "were active through sport an estimated nine or more times a week"
        if code == "e9plus"
        else "were active through sport an estimated " + {
            "e1": "once", "e2": "twice", "e3": "three times",
            "e4": "four times", "e5": "five times", "e6": "six times",
            "e7": "seven times", "e8": "eight times"}[code] + " a week"),
    "dl": lambda label, code: "reported a disability and/or learning difficulty",
    "ed": lambda label, code: "are from an ethnically diverse background",
    "ws": lambda label, code: "speak Welsh very well, a fair amount or a little",
    "cb": lambda label, code: (
        "reported no club sport" if code == "none_reported"
        else "were active through club sport an estimated nine or more times a week"
        if code == "e9plus"
        else "were active through club sport an estimated " + {
            "e1": "once", "e2": "twice", "e3": "three times",
            "e4": "four times", "e5": "five times", "e6": "six times",
            "e7": "seven times", "e8": "eight times"}[code] + " a week"),
    "gd": lambda label, code: ("reported a disability and/or learning difficulty "
                               "and did sport " + _SETTING_IN[code]),
    "gy": lambda label, code: ("reported a disability or long-term condition "
                               "and did sport " + _SETTING_IN[code]),
    "gl": lambda label, code: ("reported a learning difficulty and did sport "
                               + _SETTING_IN[code]),
    "ge": lambda label, code: ("are from an ethnically diverse background and "
                               "did sport " + _SETTING_IN[code]),
    "gw": lambda label, code: ("speak Welsh and did sport " + _SETTING_IN[code]),
    "eb": lambda label, code: _ENJOY_VERB("school sports clubs", code),
    "ec": lambda label, code: _ENJOY_VERB("clubs outside of school", code),
    "eo": lambda label, code: _ENJOY_VERB("other settings", code),
    "cs": lambda label, code: _CONF_VERB("learn a new skill", code),
    "cg": lambda label, code: _CONF_VERB("try again when sport is hard", code),
    "cn": lambda label, code: _CONF_VERB("try sport in a new place", code),
    "tp": lambda label, code: {
        "standing": "said they usually take part in sport standing",
        "seated": "said they usually take part in sport seated",
        "communication_aids": "said they take part in sport with communication aids",
        "not_sure": "were not sure how they usually take part in sport",
        "prefer_not_to_say": "preferred not to say how they take part in sport",
        "other": "take part in sport in another way",
    }[code],
    "mi": lambda label, code: {
        "more_sports_liked": "said they would do more sport if there were more sports they liked",
        "more_confident": "said they would do more sport if they felt more confident",
        "easier_to_take_part": "said they would do more sport if it was easier to take part",
        "more_motivated": "said they would do more sport if they felt more motivated",
        "more_comfortable": "said they would do more sport if it felt more comfortable for them",
        "equipment_or_cost": "said they would do more sport if they had what they need or it cost less",
        "other": "gave another reason they would do more sport",
    }[code],
    "wd": lambda label, code: f"said they would like to do more {label}",
    "li": lambda label, code: {
        "always": "said their ideas about sport are always listened to",
        "sometimes": "said their ideas about sport are sometimes listened to",
        "not_often": "said their ideas about sport are not often listened to",
        "never": "said their ideas about sport are never listened to",
    }[code],
    "im": lambda label, code: f"selected ‘{label}’ as important when they play sport",
}


def ordinal(n):
    return ORD[n] if 0 <= n < len(ORD) else f"{n}th"


def join_and(items):
    items = list(items)
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def tie_txt(labels, cap=3):
    """Long-tie rule (Prototype 4.1 §5.5): name up to three tied answers;
    return None for four or more so the caller uses a counted summary."""
    labels = list(labels)
    return join_and(labels) if len(labels) <= cap else None


def cap_first(s):
    return s[0].upper() + s[1:] if s else s


def rw(n):
    # v2.1 (Sport Wales page-by-page feedback): pupil-first language
    return "pupil" if n == 1 else "pupils"


def selw(n):
    return "selection" if n == 1 else "selections"


_STRUCTURAL_LABELS = None


def _structural_scope_labels():
    """sheet 58's English scope labels (Whole school, Primary phase, …,
    Year 11) for the internal scopes a school profile does not list."""
    global _STRUCTURAL_LABELS
    if _STRUCTURAL_LABELS is None:
        from .welsh import lexicon as _lex
        _STRUCTURAL_LABELS = dict(_lex()["chip_prefixes_en"]["scope label"])
    return _STRUCTURAL_LABELS


class Scope:
    """Reader-facing scope wording for one filter state."""

    def __init__(self, scope, gender, cohort_key, cohorts, profile):
        labels = {g["key"]: g["label"] for g in profile["scopeGroups"]}
        if scope not in labels:
            # v6 (0.28.0): an internal scope the profile does not offer (a
            # primary school's "secondary" / Years 7–11) — its English label
            # is the workbook's (sheet 58), read once, never composed here
            labels = {**_structural_scope_labels(), **labels}
        self.scope, self.gender, self.cohort = scope, gender, cohort_key
        self._cohorts = cohorts
        gword = {"all": None, "boy": "boys", "girl": "girls"}[gender]
        if scope == "whole":
            place, noun = "across the whole school", "pupils across the whole school"
        elif scope in ("primary", "secondary"):
            place = f"in the {scope} phase"
            noun = f"pupils in the {scope} phase"
        else:
            yr = labels[scope]
            place = f"in {yr}"
            noun = f"{yr} pupils"
        if gword:
            if scope == "whole":
                noun = f"{gword} across the whole school"
            elif scope in ("primary", "secondary"):
                noun = f"{gword} in the {scope} phase"
            else:
                noun = f"{labels[scope]} {gword}"
        self.demo_phrase = noun          # e.g. "Year 5 boys"
        self.place = place               # e.g. "across the whole school"
        short = labels[scope] + " · " + {"all": "All pupils", "boy": "Boys",
                                         "girl": "Girls"}[gender]
        self.group_phrase = None
        if cohort_key != "none":
            c = cohorts[cohort_key]
            prefix = cohort_key.split("_", 1)[0]
            self.group_code = c["code"]
            self.group_metric = c["metric"]
            self.group_verb = GROUP_VERBS[prefix](c.get("optionLabel", ""), c["code"])
            self.group_phrase = f"{noun} who {self.group_verb}"
            short += " · " + c["label"]
        self.short = short
        self.phrase = self.group_phrase or self.demo_phrase
        # group phrases already end in a verb clause; adding "who answered"
        # would double the relative clause
        self.ans = " who answered" if cohort_key == "none" else ""
        self.qual = f"among {self.phrase}" if not (scope == "whole" and gender == "all"
                                                   and cohort_key == "none") \
            else "across the whole school"
        # nearest meaningful parent view (Revision Brief section 14.1)
        if cohort_key != "none":
            self.parent_label = self.demo_phrase          # same view before selection
        elif gender != "all" and scope.startswith("y"):
            self.parent_label = f"all {labels[scope]} pupils"
        elif gender != "all":
            self.parent_label = ("all pupils across the whole school"
                                 if scope == "whole"
                                 else f"all pupils in the {scope} phase")
        elif scope.startswith("y"):
            phase = "primary" if int(scope[1:]) <= 6 else "secondary"
            self.parent_label = f"all pupils in the {phase} phase"
        else:
            self.parent_label = None

    def as_dict(self):
        # D50 (v1.7): the view descriptor is a typed record realised per
        # language — the finished English string stays for the locked EN
        # surfaces, the Welsh twin is generated, and the identifiers let
        # any client recompose either.
        from . import welsh_render as _wr
        return {"short": self.short, "phrase": self.phrase, "qual": self.qual,
                "place": self.place, "parentLabel": self.parent_label,
                "groupHint": getattr(self, "group_verb", None),
                "id": {"scope": self.scope, "sex": self.gender,
                       "cohort": self.cohort},
                "shortCy": _wr.scope_short_cy(self.scope, self.gender,
                                              self.cohort, self._cohorts)}


# ---------------------------------------------------------------------------
# Named sentence templates (catalogue exported to the template catalogue file)
# ---------------------------------------------------------------------------
T = {
    "leader_multi_v2": "{leader} was the most frequently selected {noun}, selected by "
                       "{count} of the {base} {who}{ans}.",
    "tie2_multi_v2": "{l1} and {l2} were tied as the most frequently selected {noun_pl}, "
                     "with {count} {selw} each, {qual}.",
    "tie3_multi_v2": "{l1}, {l2} and {l3} were jointly the most frequently selected "
                     "{noun_pl}, with {count} {selw} each, {qual}.",
    "tie4plus_multi_v2": "{n} {noun_pl} were tied for the highest number of selections, "
                         "with {count} {selw} each, {qual}. The full list is shown in "
                         "the chart.",
    "runner_v2": "Next came {runner}, with {count} {selw}, {qual}.",
    "runner_joint_v2": "Next came {runners} jointly, with {count} {selw} each, {qual}.",
    "runner_many_v2": "{n} answers were jointly next, with {count} {selw} each, {qual}; "
                      "the chart shows them all.",
    "leader_single_v2": "Of the {base} {who}{ans}, the largest group "
                        "({count}{pct}) said ‘{leader}’.",
    "tie_single_v2": "Answers were tied {qual}: ‘{l1}’ and ‘{l2}’ were each chosen by "
                     "{count} {rword}.",
    "combined_v2": "{count} of the {base} {who}{ans} ({pct}%) {verb}.",
    "combined_nopct_v2": "{count} of the {base} {who}{ans} {verb}.",
    "gender_pct_compare_v2": "Among boys {place}, {b_n} of {b_base} ({b_pct}%) {verb}, "
                             "compared with {g_n} of {g_base} ({g_pct}%) of girls.",
    "gender_count_compare_v2": "Among {who}, {b_n} of the {b_base} {bw} and "
                               "{g_n} of the {g_base} {gw} who answered {verb}.",
    "phase_pct_compare_v2": "{p_n} of {p_base} {p_rw} in the primary phase ({p_pct}%) "
                            "{verb}, compared with {s_n} of {s_base} ({s_pct}%) in the "
                            "secondary phase{grp}.",
    "parent_compare_v2": "For comparison, among {parent_phrase} the figure was "
                         "{p_n} of {p_base}.",
    "rank_diff_v2": "{item} was the {r1} most frequently selected {noun} among {g1} and "
                    "the {r2} among {g2}.",
    "shared_top_v2": "{items} featured among the leading selections for both boys and "
                     "girls {place}.",
    "gender_leader_pair_v2": "{b_leader} led among boys ({b_n}), while "
                             "{g_leader} led among girls ({g_n}), {place2}.",
    "year_leaders_v2": "{sentences}",
    "cross_insight_v2": "Among {group_phrase}, {finding}.",
    "not_enough_group_v2": "Your school’s data do not provide enough reportable "
                           "information about {topic} {qual}: fewer than five "
                           "pupils are included in that group.",
    "no_responses_v2": "No pupils in the selected view answered this question.",
    "not_asked_v2": "This question was not asked of pupils in the selected view.",
    "group_defined_v2": "This selected group contains {phrase}. The chart above keeps "
                        "the wider picture for {demo} for context, with the selected "
                        "answer highlighted.",
    "rank_same_v2": "{item} ranks first {qual}, as it does across the whole school.",
    "rank_changed_v2": "{item} leads {qual}, whereas {other} leads across the "
                       "whole school.",
}


class Narrator:
    def __init__(self, engine, defs, cohorts, profile, threshold):
        self.eng = engine
        self.defs = defs
        self.cohorts = cohorts
        self.profile = profile
        self.th = threshold
        self.audit = []
        # v6 (0.28.0): narrative HOLDS — views whose locked English templates
        # have no form for the case the data produced (recorded, never patched)
        self.holds = []

    # ------------------------------------------------------------ utilities
    def log(self, key, module, kind, tid, facts, text):
        text = fix_grammar(text)
        # V6.0 (pipeline 0.31.1, pilot of 23 Sep 2026 — first seen at six
        # small and special schools): the EN-08 hold is applied to EVERY
        # template, not only f10's three. A selected group of one pupil is a
        # reportable view under the agreed suppression policy (the rule of
        # five is tested on the demographic view only), and several locked
        # templates have no one-pupil form ("None of the 1 pupil …"). The
        # build's own English gate rejects such a sentence; rather than refuse
        # the whole report, the sentence is HELD — not rendered in either
        # language, not audited, logged in the validation summary — exactly as
        # f10's sentences have been since V5.0. Every sentence the gate accepts
        # is unchanged (D01: the English narrative is locked; the owner's
        # one-pupil forms lift the hold, sheet 49 EN-08).
        if any(g.search(text) for g in BASE1_GATES):
            self.holds.append({"module": module, "state": key,
                               "reason": f"{tid} has no one-pupil form the gate accepts (EN-08 pending owner)"})
            return None
        self.audit.append({"filter_state": key, "module": module, "kind": kind,
                           "template_id": tid,
                           "facts": json.dumps(facts, ensure_ascii=False, sort_keys=True),
                           "rendered_text": text})
        # V4.2: the Welsh sentence is generated from the same fact record,
        # never from the English text (Generation Framework v1.5)
        from . import welsh_render
        cy = welsh_render.render(tid, facts, key, module, self.cohorts)
        out = {"k": kind, "t": text}
        if cy:
            out["c"] = cy
        return out

    def visible(self, key):
        return key not in self.eng.suppressed

    def res(self, key, mid):
        return self.eng.results.get(key, {}).get(mid)

    def opt_labels(self, mid):
        return dict(self.defs[mid]["options"])

    def leader(self, mid, res, exclude=None):
        if res is None or res["status"] != "ok":
            return None
        excl = ({exclude} if isinstance(exclude, str) else set(exclude or ()))
        pairs = [(c, l, v) for (c, l), v in zip(self.defs[mid]["options"], res["raw"])
                 if c not in excl]
        mx = max((v for _, _, v in pairs), default=0)
        if mx == 0:
            return {"kind": "all_zero", "base": res["base"]}
        leaders = [(c, l) for c, l, v in pairs if v == mx]
        below = sorted({v for _, _, v in pairs if v < mx}, reverse=True)
        runner = None
        if below and below[0] > 0:
            rl = [l for c, l, v in pairs if v == below[0]]
            runner = {"labels": rl, "count": below[0]}
        return {"kind": "tie" if len(leaders) > 1 else "unique", "base": res["base"],
                "count": mx, "codes": [c for c, _ in leaders],
                "labels": [l for _, l in leaders], "runner": runner}

    def count_of(self, mid, res, codes):
        if res is None or res["status"] != "ok":
            return None
        idx = {c: i for i, (c, _) in enumerate(self.defs[mid]["options"])}
        return sum(res["raw"][idx[c]] for c in codes if c in idx)

    def rank_of(self, mid, res, code):
        """1-based dense rank of an option by count (multi-select ranking)."""
        if res is None or res["status"] != "ok":
            return None
        idx = {c: i for i, (c, _) in enumerate(self.defs[mid]["options"])}
        if code not in idx:
            return None
        target = res["raw"][idx[code]]
        distinct = sorted({v for v in res["raw"] if v > 0}, reverse=True)
        if target == 0 or target not in distinct:
            return None
        return distinct.index(target) + 1

    @staticmethod
    def pct(n, base):
        return round(n / base * 100) if base else None

    @staticmethod
    def pct_ok(base):
        """Percentages are withheld on small or unstable bases (section 5.2)."""
        return base is not None and base >= 10

    # --------------------------------------------------- composed sentences
    def s_leader_multi(self, key, S, module, mid, noun, noun_pl=None, exclude=None,
                       with_runner=True):
        noun_pl = noun_pl or noun + "s"
        res = self.res(key, mid)
        lf = self.leader(mid, res, exclude)
        if not lf:
            return None
        lf = {**lf, "metric": mid, "noun": noun}
        if lf["kind"] == "all_zero":
            return self.log(key, module, "primary", "no_responses_v2", lf, T["no_responses_v2"])
        if lf["kind"] == "tie":
            n = len(lf["labels"])
            if n == 2:
                t = T["tie2_multi_v2"].format(l1=lf["labels"][0], l2=lf["labels"][1],
                                              count=lf["count"], selw=selw(lf["count"]),
                                              noun_pl=noun_pl, qual=S.qual)
                tid = "tie2_multi_v2"
            elif n == 3:
                t = T["tie3_multi_v2"].format(l1=lf["labels"][0], l2=lf["labels"][1],
                                              l3=lf["labels"][2], count=lf["count"],
                                              selw=selw(lf["count"]),
                                              noun_pl=noun_pl, qual=S.qual)
                tid = "tie3_multi_v2"
            else:
                lf = {**lf, "tie_n": n}
                t = T["tie4plus_multi_v2"].format(n=n, noun_pl=noun_pl, count=lf["count"],
                                                  selw=selw(lf["count"]), qual=S.qual)
                tid = "tie4plus_multi_v2"
        else:
            t = T["leader_multi_v2"].format(leader=lf["labels"][0], noun=noun,
                                            count=lf["count"], base=lf["base"],
                                            who=S.phrase, ans=S.ans)
            tid = "leader_multi_v2"
            if with_runner and lf["runner"]:
                rl = lf["runner"]["labels"]
                rc = lf["runner"]["count"]
                named = tie_txt(rl)
                if named is None:
                    rt_, rtid = (T["runner_many_v2"].format(
                        n=len(rl), count=rc, selw=selw(rc), qual=S.qual),
                        "runner_many_v2")
                    lf = {**lf, "runner_n": len(rl)}
                elif len(rl) > 1:
                    rt_, rtid = (T["runner_joint_v2"].format(
                        runners=named, count=rc, selw=selw(rc), qual=S.qual),
                        "runner_joint_v2")
                else:
                    rt_, rtid = (T["runner_v2"].format(runner=rl[0], count=rc,
                                                       selw=selw(rc), qual=S.qual),
                                 "runner_v2")
                # sentence-length control (§5.6/§9.6): long scopes push the
                # runner into its own self-scoping sentence block
                if len((t + " " + rt_).split()) > 45:
                    p1 = self.log(key, module, "primary", tid, lf, t)
                    p2 = self.log(key, module, "supporting", rtid, lf, rt_)
                    return [p1, p2]
                t += " " + rt_
                tid += "+" + rtid
        return self.log(key, module, "primary", tid, lf, t)

    def s_leader_single(self, key, S, module, mid, broad):
        res = self.res(key, mid)
        lf = self.leader(mid, res)
        if not lf:
            if res and res["status"] == "na":
                return self.log(key, module, "primary", "not_asked_v2", {}, T["not_asked_v2"])
            if res and res["status"] == "nd":
                return self.log(key, module, "primary", "no_responses_v2", {}, T["no_responses_v2"])
            return None
        lf = {**lf, "metric": mid}
        if lf["kind"] == "all_zero":
            return self.log(key, module, "primary", "no_responses_v2", lf, T["no_responses_v2"])
        if lf["kind"] == "tie" and len(lf["labels"]) == 2:
            t = T["tie_single_v2"].format(qual=S.qual, l1=lf["labels"][0],
                                          l2=lf["labels"][1], count=lf["count"],
                                          rword=rw(lf["count"]))
            return self.log(key, module, "primary", "tie_single_v2", lf, t)
        pcttxt = ""
        if broad and lf["kind"] == "unique" and self.pct_ok(lf["base"]):
            p = self.pct(lf["count"], lf["base"])
            if p is not None:
                pcttxt = f", or {p}%"
                lf = {**lf, "pct": p}
        label = join_and(lf["labels"]) if lf["kind"] == "tie" else lf["labels"][0]
        t = T["leader_single_v2"].format(base=lf["base"], who=S.phrase, ans=S.ans,
                                         count=lf["count"], pct=pcttxt, leader=label)
        return self.log(key, module, "primary", "leader_single_v2", lf, t)

    def s_combined(self, key, S, module, mid, codes, verb, broad, kind="supporting"):
        res = self.res(key, mid)
        n = self.count_of(mid, res, codes)
        if n is None:
            return None
        base = res["base"]
        # v1.7 (PR-02): the answer labels behind the codes are a role the
        # zero recast consumes ("what was not chosen")
        opts = dict(self.defs[mid]["options"])
        facts = {"count": n, "base": base, "codes": codes, "metric": mid,
                 "code_labels": [opts[cd] for cd in codes if cd in opts],
                 "pct": self.pct(n, base) if base else None}
        # deliberate wording for a base of one (Prototype 4.1 §5.1) — only
        # chart-derived selected groups can be this small
        if base == 1:
            t = (f"The one pupil in this selected group {verb}." if n == 1
                 else f"No pupil in this selected group {verb}.")
            return self.log(key, module, kind,
                            "combined_base1_v41", facts, t)
        broad = broad and self.pct_ok(base)
        if broad and base:
            t = T["combined_v2"].format(count=n, base=base, who=S.phrase, ans=S.ans,
                                        pct=self.pct(n, base), verb=verb)
            tid = "combined_v2"
        else:
            t = T["combined_nopct_v2"].format(count=n, base=base, who=S.phrase, ans=S.ans,
                                              verb=verb)
            tid = "combined_nopct_v2"
        return self.log(key, module, kind, tid, facts, t)

    def s_gender_compare(self, key, S, module, mid, codes, verb, broad):
        """Boys/girls comparison from sibling states of the same scope+group."""
        scope, gender, ck = key.split("|")
        if gender != "all":
            return None
        kb, kg = state_key(scope, "boy", ck), state_key(scope, "girl", ck)
        if not (self.visible(kb) and self.visible(kg)):
            return None
        rb, rgg = self.res(kb, mid), self.res(kg, mid)
        nb, ng = self.count_of(mid, rb, codes), self.count_of(mid, rgg, codes)
        if nb is None or ng is None:
            return None
        if rb["base"] < 3 or rgg["base"] < 3:
            return None       # a comparison over 1-2 respondents is not prose-worthy
        # v1.6 (D44): the measure and answer codes are roles the Welsh
        # renderer must consume — their omission caused the G1a defect
        facts = {"boys": nb, "boys_base": rb["base"], "girls": ng, "girls_base": rgg["base"],
                 "boys_pct": self.pct(nb, rb["base"]), "girls_pct": self.pct(ng, rgg["base"]),
                 "metric": mid, "codes": list(codes)}
        if broad and self.pct_ok(rb["base"]) and self.pct_ok(rgg["base"]):
            t = T["gender_pct_compare_v2"].format(place=S.place, b_n=nb, b_base=rb["base"],
                                                  b_pct=facts["boys_pct"], verb=verb,
                                                  g_n=ng, g_base=rgg["base"],
                                                  g_pct=facts["girls_pct"])
            tid = "gender_pct_compare_v2"
        else:
            t = T["gender_count_compare_v2"].format(who=S.phrase, b_n=nb, b_base=rb["base"],
                                                    bw="boy" if rb["base"] == 1 else "boys",
                                                    g_n=ng, g_base=rgg["base"],
                                                    gw="girl" if rgg["base"] == 1 else "girls",
                                                    verb=verb)
            tid = "gender_count_compare_v2"
        return self.log(key, module, "comparison", tid, facts, t)

    def s_phase_compare(self, key, S, module, mid, codes, verb):
        scope, gender, ck = key.split("|")
        if scope != "whole":
            return None
        kp, ks = state_key("primary", gender, ck), state_key("secondary", gender, ck)
        if not (self.visible(kp) and self.visible(ks)):
            return None
        rp, rs = self.res(kp, mid), self.res(ks, mid)
        np_, ns = self.count_of(mid, rp, codes), self.count_of(mid, rs, codes)
        if np_ is None or ns is None:
            return None
        if not (self.pct_ok(rp["base"]) and self.pct_ok(rs["base"])):
            return None      # rate comparison unsafe on small phase bases
        facts = {"primary": np_, "primary_base": rp["base"],
                 "secondary": ns, "secondary_base": rs["base"],
                 "primary_pct": self.pct(np_, rp["base"]),
                 "secondary_pct": self.pct(ns, rs["base"])}
        grp = f", among those who {S.group_verb}" if ck != "none" else ""
        t = T["phase_pct_compare_v2"].format(p_n=np_, p_base=rp["base"],
                                             p_rw=rw(rp["base"]),
                                             p_pct=facts["primary_pct"], verb=verb,
                                             s_n=ns, s_base=rs["base"],
                                             s_pct=facts["secondary_pct"], grp=grp)
        return self.log(key, module, "comparison", "phase_pct_compare_v2", facts, t)

    def parent_of(self, key):
        """Nearest meaningful parent view (Prototype 4.1 §7): group -> its
        demographic view; year+gender -> the whole year; gender at
        whole/phase -> all respondents there; year -> its phase."""
        scope, gender, ck = key.split("|")
        if ck != "none":
            pk = state_key(scope, gender, "none")
        elif gender != "all":
            pk = state_key(scope, "all", "none")
        elif scope.startswith("y"):
            ph = "primary" if int(scope[1:]) <= 6 else "secondary"
            pk = state_key(ph, "all", "none")
        else:
            return None, None
        psc, pg, pck = pk.split("|")
        return pk, Scope(psc, pg, pck, self.cohorts, self.profile)

    def s_parent_compare(self, key, S, module, mid, codes):
        """Narrow or group views: compare with the nearest parent view."""
        scope, gender, ck = key.split("|")
        if ck != "none":
            pkey = state_key(scope, gender, "none")
            parent_S = Scope(scope, gender, "none", self.cohorts, self.profile)
        elif gender != "all":
            pkey = state_key(scope, "all", "none")
            parent_S = Scope(scope, "all", "none", self.cohorts, self.profile)
        else:
            return None
        if not self.visible(pkey) or pkey == key:
            return None
        rp = self.res(pkey, mid)
        n = self.count_of(mid, rp, codes)
        if n is None:
            return None
        facts = {"parent": pkey, "count": n, "base": rp["base"]}
        t = T["parent_compare_v2"].format(parent_phrase=parent_S.phrase, p_n=n,
                                          p_base=rp["base"])
        return self.log(key, module, "comparison", "parent_compare_v2", facts, t)

    def s_gender_leader_pair(self, key, S, module, mid, noun, exclude=None):
        """Leading multi-select answer among boys and among girls + rank shift."""
        scope, gender, ck = key.split("|")
        if gender != "all":
            return None
        kb, kg = state_key(scope, "boy", ck), state_key(scope, "girl", ck)
        if not (self.visible(kb) and self.visible(kg)):
            return None
        rb, rgg = self.res(kb, mid), self.res(kg, mid)
        if rb["base"] < 3 or rgg["base"] < 3:
            return None
        lb, lg = self.leader(mid, rb, exclude), self.leader(mid, rgg, exclude)
        if not lb or not lg or lb["kind"] == "all_zero" or lg["kind"] == "all_zero":
            return None
        b_named, g_named = tie_txt(lb["labels"]), tie_txt(lg["labels"])
        if b_named is None or g_named is None:
            return None       # long-tie rule (§5.5): no multi-answer listings here
        out = []
        place2 = S.place if scope != "whole" else "across the whole school"
        t = T["gender_leader_pair_v2"].format(
            b_leader=b_named, b_n=f"{lb['count']} {selw(lb['count'])}",
            g_leader=g_named, g_n=f"{lg['count']} {selw(lg['count'])}",
            place2=place2)
        out.append(self.log(key, module, "comparison", "gender_leader_pair_v2",
                            {"boys": lb, "girls": lg}, t))
        # rank-shift illustration: boys' unique leader ranked among girls
        if lb["kind"] == "unique" and lg["kind"] == "unique" and lb["codes"] != lg["codes"]:
            code = lb["codes"][0]
            r_b = self.rank_of(mid, rb, code)
            r_g = self.rank_of(mid, rgg, code)
            if r_b and r_g and r_g > 2:
                t2 = T["rank_diff_v2"].format(item=lb["labels"][0], r1=ordinal(r_b),
                                              noun=noun, g1=f"boys {S.place}",
                                              r2=ordinal(r_g), g2="girls")
                out.append(self.log(key, module, "comparison", "rank_diff_v2",
                                    {"item": code, "boys_rank": r_b, "girls_rank": r_g,
                                     "noun": noun}, t2))
        return out

    def s_rank_parent(self, key, S, module, mid, noun, noun_pl=None, exclude=None):
        """Ranked-metric comparison against the configured nearest parent
        (Prototype 4.1 §7), never routinely against the whole school."""
        noun_pl = noun_pl or noun + "s"
        pk, pS = self.parent_of(key)
        if not pk or not self.visible(pk):
            return None
        vlf = self.leader(mid, self.res(key, mid), exclude)
        plf = self.leader(mid, self.res(pk, mid), exclude)
        if not vlf or not plf or vlf["kind"] == "all_zero" or plf["kind"] == "all_zero":
            return None
        if vlf["kind"] != "unique":
            return None            # the tied case is already described in full
        code, label = vlf["codes"][0], vlf["labels"][0]
        facts = {"view": vlf, "parent": plf, "parent_key": pk,
                 "parent_tie_n": len(plf["codes"]), "noun": noun}
        if plf["kind"] == "unique" and plf["codes"][0] == code:
            t = f"{label} leads {S.qual}, as it does among {pS.phrase}."
            tid = "rank_parent_same_v41"
        elif code in plf["codes"]:
            t = (f"{label} was the leading {noun} {S.qual} and was also one of the "
                 f"{len(plf['codes'])} joint-leading {noun_pl} among {pS.phrase}.")
            tid = "rank_parent_joint_v41"
        else:
            named = tie_txt(plf["labels"])
            lead_p = named if named else f"{len(plf['labels'])} tied answers lead"
            verb = "leads" if len(plf["labels"]) == 1 else "lead"
            t = (f"{label} leads {S.qual}, whereas {named} {verb} among {pS.phrase}."
                 if named else
                 f"{label} leads {S.qual}, whereas {len(plf['labels'])} answers are "
                 f"tied in the lead among {pS.phrase}.")
            tid = "rank_parent_diff_v41"
        return self.log(key, module, "comparison", tid, facts, t)

    def s_cross_group(self, key, S, module, group_prefixopt, mid, finding_word):
        """Cross-question insight via a pre-calculated selected-group state.

        group_prefixopt: cohort key suffix, e.g. 'ji_not_often'."""
        scope, gender, ck = key.split("|")
        if ck != "none":
            return None                   # only offered in demographic views
        gkey = state_key(scope, gender, group_prefixopt)
        if not self.visible(gkey):
            return None
        res = self.res(gkey, mid)
        lf = self.leader(mid, res)
        if not lf or lf["kind"] != "unique":
            return None
        gS = Scope(scope, gender, group_prefixopt, self.cohorts, self.profile)
        finding = (f"‘{lf['labels'][0]}’ was the most frequently selected "
                   f"{finding_word} ({lf['count']} of {lf['base']} who answered)")
        t = T["cross_insight_v2"].format(group_phrase=gS.phrase, finding=finding)
        return self.log(key, module, "cross", "cross_insight_v2",
                        {"group": group_prefixopt, "leader": lf}, t)

# EOF sentinel
