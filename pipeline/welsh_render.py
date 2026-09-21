# -*- coding: utf-8 -*-
"""Welsh narrative renderer — realises every report sentence from its
fact record using the Welsh templates of the Generation Framework v1.5
(sheet 05), the audience forms (21), the qualifier frames (22), the
answer labels (23) and the predicate inventory (19).

The Welsh sentence is NOT derived from the English sentence: both are
generated from the same fact record. Coverage is fail-loud: an unmapped
template id or missing lexicon entry is recorded and reported at build.
"""
from __future__ import annotations

import re

from . import welsh as W

# ---------------------------------------------------------------- lexical maps
# Framework sheet 32 (battery items) — verbatim survey Welsh.
ENJOY_SETTING_CY = {
    "PE lessons": "Gwersi Addysg Gorfforol",
    "school sports clubs": "Clybiau Chwaraeon Ysgol",
    "clubs outside of school": "Clybiau Chwaraeon y tu allan i’r ysgol",
    "other settings": "Lleoliadau eraill",
}
CONF_MEASURE_CY = {
    "trying a new sport": "rhoi cynnig ar gamp newydd",
    "learning a new skill": "dysgu sgil newydd",
    "trying again when sport is hard":
        "rhoi cynnig arall arni pan fydd camp yn anodd",
    "trying sport in a new place": "rhoi cynnig ar chwaraeon mewn lle newydd",
}
# Setting slot, MEWN form — matches the qualifier frames (sheet 22)
SETTING_MEWN = {
    "pe_lessons": "yn ystod Addysg Gorfforol neu Amser Gwersi",
    "school_club": "mewn clwb ysgol",
    "community_club": "mewn clwb y tu allan i’r ysgol",
    "somewhere_else": "rhywle arall",
}
# v2.7: the former LABEL_ALIASES ("I don’t know" → "Ddim yn gwybod") was
# Welsh written in code that contradicted the survey's own option
# ("Dydw i ddim yn gwybod", sheet 23 row added in v2.7 per the
# translator's AW-1 / sheet 2b row 58). Every label now comes from sheet 23.

# grids for the D32 question-dependent labels (Very / Quite / Not very /
# Not at all / Other): a sheet-23 cell may carry several branches tagged
# "[confidence grid]", "[PE and Active Lessons grid]", "[take-part grid]";
# the untagged branch is the default (see label_cy)
CONF_METRICS = {"confidence_try_new", "confidence_learn_skill",
                "confidence_try_again", "confidence_new_place"}
PE_FEEL_METRICS = {"pe_feel_healthy", "pe_feel_confident", "pe_feel_ready"}
TAKE_PART_METRICS = {"take_part_method"}
GRID_TAGS = {"conf": "confidence grid", "pe": "pe and active lessons grid",
             "tp": "take-part grid"}


def grid_of(metric):
    """The label grid a metric's answers belong to (D32), or None."""
    if metric in CONF_METRICS:
        return "conf"
    if metric in PE_FEEL_METRICS:
        return "pe"
    if metric in TAKE_PART_METRICS:
        return "tp"
    return None

# ------------------------------------------------- D44 role vocabularies
# Head nouns by the English template's noun role (sheet 18 + core nouns).
NOUN_CY = {
    "sport": ("camp", "f", "campau"),
    "sport or activity": ("camp neu weithgaredd", "f",
                          "campau a gweithgareddau"),
    "desired sport": ("camp", "f", "campau"),
    "unmet-demand sport": ("camp", "f", "campau"),
    "setting": ("lleoliad", "m", "lleoliadau"),
    "answer": ("ateb", "m", "atebion"),
    "option": ("opsiwn", "m", "opsiynau"),
    "condition": ("amod", "m", "amodau"),
}

# Predicate inventory lookup by (metric, sorted codes) — D44: an unmapped
# combination is a dropped role and fails loud (KeyError -> miss).
# Forms: pl = 'eu bod…' clause for a plural subject; sg carries the
# gendered third-singular where the subject is one pupil.
def _preds():
    P = W.lexicon()["predicates"]
    return {
        ("join_in_easily", ("never", "not_often")): {
            "pl": P["P-01"]["cy"],
            "sg": "nad yw’n aml, neu byth, yn ei chael hi’n hawdd ymuno"},
        ("ideas_listened", ("never", "not_often")): {
            "pl": P["P-02"]["cy"],
            "sg": "nad yw pobl yn aml, neu byth, yn gwrando ar ei syniadau"},
        ("ideas_listened", ("always",)): {
            "pl": P["P-03"]["cy"],
            "sg": "fod pobl bob amser yn gwrando ar ei syniadau am chwaraeon"},
        ("ideas_listened", ("always", "sometimes")): {
            "pl": ("fod pobl yn gwrando ar eu syniadau am chwaraeon bob "
                   "amser neu weithiau"),
            "sg": ("fod pobl yn gwrando ar ei syniadau am chwaraeon bob "
                   "amser neu weithiau")},
        ("enjoy_pe", ("a_lot",)): {
            "pl": ("eu bod yn mwynhau chwaraeon mewn Gwersi Addysg "
                   "Gorfforol ‘Llawer’"),
            "sg_m": ("ei fod yn mwynhau chwaraeon mewn Gwersi Addysg "
                     "Gorfforol ‘Llawer’"),
            "sg_f": ("ei bod yn mwynhau chwaraeon mewn Gwersi Addysg "
                     "Gorfforol ‘Llawer’"),
            "imp": ("mwynhau chwaraeon mewn Gwersi Addysg Gorfforol "
                    "‘Llawer’")},
        ("pe_feel_healthy", ("quite", "very")): {
            "pl": ("fod gwersi AG a Gwersi Actif yn gwneud iddynt deimlo’n "
                   "‘iach iawn’ neu’n ‘eithaf iach’"),
            "sg_m": ("fod gwersi AG a Gwersi Actif yn gwneud iddo deimlo’n "
                     "‘iach iawn’ neu’n ‘eithaf iach’"),
            "sg_f": ("fod gwersi AG a Gwersi Actif yn gwneud iddi deimlo’n "
                     "‘iach iawn’ neu’n ‘eithaf iach’"),
            "imp": ("fod gwersi AG a Gwersi Actif yn gwneud i’r disgybl "
                    "deimlo’n ‘iach iawn’ neu’n ‘eithaf iach’")},
        ("confidence_try_new", ("quite", "very")): {
            "pl": ("eu bod yn hyderus iawn neu’n eithaf hyderus i roi "
                   "cynnig ar gamp newydd"),
            "sg_m": ("ei fod yn hyderus iawn neu’n eithaf hyderus i roi "
                     "cynnig ar gamp newydd"),
            "sg_f": ("ei bod yn hyderus iawn neu’n eithaf hyderus i roi "
                     "cynnig ar gamp newydd"),
            "imp": ("bod yn hyderus iawn neu’n eithaf hyderus i roi "
                    "cynnig ar gamp newydd")},
        ("confidence_try_new", ("not_at_all", "not_very")): {
            "pl": P["P-05"]["cy"],
            "sg": ("nad oedd yn hyderus iawn, nac yn hyderus o gwbl, i roi "
                   "cynnig ar gamp newydd")},
        ("organised_freq", ("once_week", "three_plus", "twice_week")): {
            "pl": ("eu bod wedi cymryd rhan mewn chwaraeon mewn clwb ysgol "
                   "neu glwb cymunedol o leiaf unwaith yr wythnos"),
            "sg": ("ei fod wedi cymryd rhan mewn chwaraeon mewn clwb ysgol "
                   "neu glwb cymunedol o leiaf unwaith yr wythnos")},
        ("club_freq_estimate",
         tuple(sorted(["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8",
                       "e9plus"]))): {
            "pl": ("eu bod yn cymryd rhan mewn chwaraeon clwb (mewn clwb "
                   "ysgol neu glwb y tu allan i’r ysgol) o leiaf unwaith "
                   "yr wythnos"),
            "sg": ("ei fod yn cymryd rhan mewn chwaraeon clwb (mewn clwb "
                   "ysgol neu glwb y tu allan i’r ysgol) o leiaf unwaith "
                   "yr wythnos")},
    }


_PRED_CACHE = None


def pred_cy(metric, codes, number="pl", gender=None):
    """D44: the predicate is resolved from the measure + answer-code roles;
    an unknown pair raises (captured as a miss, failing the build).
    number: pl | sg (gendered where the view carries a sex) | imp
    (PR-03 impersonal verb-noun phrase, pronoun-free)."""
    global _PRED_CACHE
    if _PRED_CACHE is None:
        _PRED_CACHE = _preds()
    entry = _PRED_CACHE[(metric, tuple(sorted(codes)))]
    if number == "imp":
        return entry["imp"]
    if number == "pl":
        return entry["pl"]
    if gender == "girl" and "sg_f" in entry:
        return entry["sg_f"]
    if gender == "boy" and "sg_m" in entry:
        return entry["sg_m"]
    if "sg_m" in entry and gender in ("boy", "girl"):
        return entry["sg_m"]
    return entry.get("sg", entry.get("sg_m", entry["pl"]))


# ------------------------------------------------- D50 view descriptors
# The typed {scope, sex, cohort} record realised in Welsh: scope and sex
# from the audience components, the cohort frame per family (DERIVED from
# the framework's attested vocabulary — listed for the linguist), and the
# option label in its citation form from sheet 23.
#
# v2.6/v2.7 (sheet 58): the chip prefixes, the scope labels, the gender
# labels and the banner labels are WORKBOOK DATA, read lazily from the
# lexicon. Until v2.5 they were Python constants here (D50) — Welsh no
# translator had seen. A missing kind or key fails the build (KeyError);
# nothing is defaulted in code.
class _Sheet58:
    """Mapping view over one 'Kind' of sheet 58 in the built lexicon."""

    def __init__(self, kind):
        self.kind = kind

    def _table(self):
        chips = W.lexicon().get("chip_prefixes")
        if not chips or self.kind not in chips:
            raise SystemExit(f"framework sheet 58: kind {self.kind!r} missing — "
                             f"refusing to render chip / scope / gender labels "
                             f"without the workbook rows (v2.6)")
        return chips[self.kind]

    def __getitem__(self, key):
        return self._table()[key]

    def __contains__(self, key):
        return key in self._table()

    def get(self, key, default=None):
        return self._table().get(key, default)

    def items(self):
        return self._table().items()

    def keys(self):
        return self._table().keys()


SCOPE_CY = _Sheet58("scope label")          # whole / primary / secondary / y3…y11
SEX_CY = _Sheet58("gender label")           # the filter options (All respondents …)
BANNER_SEX_CY = _Sheet58("banner label")    # the banner's audience part (All pupils …)
COHORT_FRAME_CY = _Sheet58("cohort prefix")  # "Dewiswyd {x}" …


# D54 (v1.8, sheet 31): a binary metric's descriptor echoes its own
# question's verb, read from the metric->question mapping — never derived
# from the English label. PR-11: a derived set with no question is NAMED.
YN_FAMILY_METRIC = {"dy": "disability_condition", "ly": "learning_difficulty",
                    "dl": "dl_combined", "ws": "ws_combined",
                    "ed": "ed_combined", "wl": None}


def yn_descriptor(metric, code):
    """Descriptor text for a yes/no cohort answer (D54). A metric absent
    from sheet 31's table fails the build — never a note or fallback."""
    m = W.lexicon()["yes_no_metrics"][metric]
    if W.pr("PR-11") == "name_the_set" and (m["aff"] or "").strip() in ("—", ""):
        named = [s.strip() for s in m["form"].split("/")]
        return named[0] if code == "yes" else named[1]
    prefix = m["form"].split(":")[0]
    return f"{prefix}: {m['aff'] if code == 'yes' else m['neg']}"


def cohort_label_cy(ck, c):
    """The Welsh label of one selectable cohort — the D50 record's cohort
    component, also bound to the pupil-group selector (D59). v2.7: the
    answer part is resolved on the cohort's own metric grid (D32), so a
    confidence chip quotes the confidence question's option."""
    fam = ck.split("_", 1)[0]
    yn_metric = YN_FAMILY_METRIC.get(fam)
    if yn_metric and c.get("code") in ("yes", "no"):
        return yn_descriptor(yn_metric, c["code"])
    frame = COHORT_FRAME_CY[fam]
    x = label_cy(c.get("optionLabel", ""), grid_of(c.get("metric")), form="cy")
    return frame.format(x=x)


def scope_short_cy(scope, gender, ck, cohorts):
    """The banner's audience: scope label · banner label (sheet 58) ·
    cohort chip — the English is 'Whole school · All pupils · …'."""
    out = f"{SCOPE_CY[scope]} · {BANNER_SEX_CY[gender]}"
    if ck != "none" and cohorts.get(ck):
        out += " · " + cohort_label_cy(ck, cohorts[ck])
    return out


# Demographic group noun phrases (relative clauses, qualifier frames 22)
# keyed by the settings metric that defines the group — the role the V4.2
# assessment found conflated (G1c). v2.7: the four groups that have a
# sheet-22 qualifier frame are COMPOSED from it ('disgybl' + frame) so a
# term decision on the workbook (cyflwr hirdymor, AW-4) reaches them;
# the Welsh-speaking group keeps its attested short form.
_GROUP_MID_QUAL = {
    "settings_dy": ("dy", "reported a disability or long-term condition"),
    "settings_ly": ("ly", "reported a learning difficulty"),
    "settings_dl": ("dl", "reported a disability and/or learning difficulty"),
    "settings_ed": ("ed", "are from an ethnically diverse background"),
}


def group_mid_cy(mid):
    if mid == "settings_wl":
        return "disgybl sy’n siarad Cymraeg"
    fam, en = _GROUP_MID_QUAL[mid]
    q = W.qualifier_cy(fam, en)
    if not q:
        raise KeyError(f"sheet 22: no qualifier frame for {fam} / {en!r}")
    return f"disgybl {q}"


def _label_branches(cy):
    """D32 (v2.7): a sheet-23 cell may carry several forms separated by
    ' | ', each optionally tagged '[<grid> grid]'; -> [(tag|None, text)]."""
    out = []
    for part in re.split(r"\s+\|\s+", cy):
        m = re.search(r"\s*\[([^\]]+?)\s+grid\]\s*$", part, re.I)
        if m:
            out.append((m.group(1).strip().lower() + " grid",
                        part[:m.start()].strip()))
        else:
            out.append((None, part.strip()))
    return out


def label_cy(en_label, grid=None, quoted=False, form="prose"):
    """D21 / PR-10: running prose takes the case-folded prose form from
    sheet 23 (the default here, since renderers compose prose); citations
    and chart/table surfaces pass form="cy" for the title-case form.
    D32: a question-dependent label is chosen by the caller's grid — the
    tagged branch for that grid, else the untagged default branch, else
    (pre-v2.7 cells with no untagged branch) the first branch."""
    cy = W.label_cy(en_label, form)
    if re.search(r"\[[^\]]+ grid\]", cy, re.I):
        branches = _label_branches(cy)
        want = GRID_TAGS.get(grid)
        for tag, text in branches:
            if want and tag == want:
                return text
        for tag, text in branches:
            if tag is None:
                return text
        return branches[0][1]
    return cy


def q(label):
    return f"‘{label}’"


def joinlab(labels, grid=None):
    return W.join_list([label_cy(l, grid) for l in labels])


def joinlab_counts(pairs, grid=None):
    return W.join_list([f"{label_cy(l, grid)} ({n})" for l, n in pairs])


# ------------------------------------------------------------------ context
class Ctx:
    """Audience + qualifier context for one filter state."""

    def __init__(self, key, cohorts):
        self.scope, self.gender, self.ck = key.split("|")
        self.cohort = cohorts.get(self.ck) if self.ck != "none" else None
        self.qual = None
        if self.cohort:
            fam = self.ck.split("_", 1)[0]
            from .narrative2 import GROUP_VERBS
            en = GROUP_VERBS[fam](self.cohort.get("optionLabel", ""),
                                  self.cohort["code"])
            self.qual = W.qualifier_cy(fam, en,
                                       answer_label=self.cohort.get("optionLabel"))

    def aud(self, form):
        return W.audience(self.scope, self.gender, form)

    # -- composed forms -----------------------------------------------------
    def bare(self):
        """AUD:BARE + QUAL:REL."""
        a = self.aud("bare")
        return f"{a} {self.qual}" if self.qual else a

    def among(self):
        a = self.aud("ymhlith")
        return f"{a} {self.qual}" if self.qual else a

    def head_gender(self):
        a = self.aud("def_sg")
        return "f" if a.split(" ", 1)[0] in ("merch", "ferch") else "m"

    def of_the(self, n, base, answered=True):
        """'N o'r BASE AUD:DEF_SG [QUAL | a ymatebodd]' — numerator and
        base realised together by the D40 realiser (v1.7 G8a/G8b: words
        1-10 for both; the numerator's gender follows the counted noun)."""
        a = self.aud("def_sg")
        g = self.head_gender()
        qual = W.sg_qual(self.qual, self.gender) if base == 1 else self.qual
        tail = f" {qual}" if qual else (" a ymatebodd" if answered else "")
        if base == 1:
            # D56: no partitive over a singular set — the subject is the
            # only pupil, not 'one of' them
            return f"yr {W.of_base(1, a, g)[4:]}{tail}"
        return f"{W.numerator(n, g)} {W.of_base(base, a, g)}{tail}"

    def qual_negative(self):
        return bool(self.qual) and bool(
            re.search(r"\bnad\b|\bnac\b|\bbyth\b", self.qual))

    def def_np(self, base):
        """'y ddau fachgen yn yr ysgol gyfan ⟪qual⟫' — the definite set."""
        a = self.aud("def_sg")
        head, _, rest = a.partition(" ")
        g = self.head_gender()
        np = W.def_num_noun(base, head, g)
        art = "yr" if W.is_vowel_initial(np) else "y"
        tail = f" {self.qual}" if self.qual else ""
        return f"{art} {np}{(' ' + rest) if rest else ''}{tail}"

    def neg_subject(self, base, answered=True):
        """Subject of a negative existential: 'yr un ⟪o'r base…⟫' when the
        set is plural, 'yr unig ⟪noun⟫…' when it is one pupil (D56)."""
        if base == 1:
            a = self.aud("def_sg")
            qual = W.sg_qual(self.qual, self.gender)
            tail = f" {qual}" if qual else ""
            return f"yr {W.of_base(1, a, self.head_gender())[4:]}{tail}"
        return f"yr un {self.the_base(base, answered)}"

    def the_base(self, base, answered=True):
        a = self.aud("def_sg")
        # D48: a one-person base takes a singular relative clause
        qual = W.sg_qual(self.qual, self.gender) if base == 1 else self.qual
        tail = f" {qual}" if qual else (" a ymatebodd" if answered else "")
        return f"{W.of_base(base, a, self.head_gender())}{tail}"

    def scope_tail(self):
        """Trailing scope adjunct: ', ymhlith …' or ', yn yr ysgol gyfan.'"""
        return f", {self.among()}"


# ------------------------------------------------------------- FT renderers

def numz(n, gender="m"):
    """A count that may legitimately be zero inside a comparative frame:
    the English reads 'none of …' there (fix_grammar), so the Welsh reads
    'dim un'; positive values go through the D40 realiser."""
    return "dim un" if int(n) == 0 else W.numerator(n, gender)

def _pct_par(n, p=None):
    return f"({n}, neu {p}%)" if p is not None else f"({n})"


def r_leader_single(f, c):
    """FT-02: modal answer with base (leader_single_v2)."""
    grid = grid_of(f.get("metric"))
    ans = q(label_cy(f["labels"][0], grid, form="cy")) if len(f.get("labels", [])) == 1 \
        else joinlab(f.get("labels", []), grid)
    par = _pct_par(f["count"], f.get("pct"))
    ob = W.of_base(f["base"], c.aud("def_sg"), c.head_gender())
    qual = W.sg_qual(c.qual, c.gender) if f["base"] == 1 else c.qual
    return (f"O{ob[1:]}"
            f"{' ' + qual if qual else ' a ymatebodd'}, "
            f"{ans} oedd yr ateb a ddewiswyd amlaf {par}.")


def _neg_pred(metric, codes):
    """Is the predicate itself negative (a stacked-negation risk, PR-02)?"""
    p = pred_cy(metric, codes, "pl")
    return p.startswith(("nad ", "na "))


def _zero_recast(f, c, subj):
    """PR-02 (data value, sheet 39): a nil count with a negative predicate
    is recast as what was NOT chosen — 'Ni ddewisodd yr un o'r … ‘A’ na
    ‘B’ …' — instead of stacking two negatives. The measure stays in the
    sentence so distinct measures stay distinct (G5)."""
    labels = f.get("code_labels") or []
    topic = _PRED_TOPIC.get((f["metric"], tuple(sorted(f["codes"]))), "")
    bits = []
    for i, lab in enumerate(labels):
        cite = q(label_cy(lab, form="cy"))
        if i == 0:
            bits.append(cite)
        else:
            na = "nac" if W.is_vowel_initial(label_cy(lab, form="cy")) else "na"
            bits.append(f"{na} {cite}")
    listed = " ".join(bits)
    return f"Ni ddewisodd {subj} {listed}{topic}."


# The measure tail of a PR-02 recast, per (metric, codes) — a dropped
# measure would collapse distinct English zeros into one Welsh sentence.
_PRED_TOPIC = {
    ("join_in_easily", ("never", "not_often")):
        " ynghylch ymuno â chwaraeon a gemau",
    ("ideas_listened", ("never", "not_often")):
        " ynghylch gwrando ar eu syniadau",
    ("confidence_try_new", ("not_at_all", "not_very")):
        " ynghylch hyder i roi cynnig ar gamp newydd",
}


def r_combined(f, c):
    """FT-01 with the three v1.6 regimes (n=0 negative, n=1 singular,
    n>=2 partitive) and the predicate resolved from metric + codes.
    v1.7: the n=0 branch of a NEGATIVE predicate follows PR-02; the n=1
    branch of a sex-less view follows PR-03 (impersonal recast)."""
    n = f["count"]
    if n == 0:
        if (_neg_pred(f["metric"], f["codes"]) and f.get("code_labels")
                and W.pr("PR-02") == "answer_selection_recast"):
            return _zero_recast(f, c, c.neg_subject(f["base"]))
        if f["base"] == 1:
            # v6 (0.28.0): a nil count on a ONE-pupil base is a singleton
            # antecedent ('yr unig …'), so the complement takes the same
            # singular the n = 1 branch uses — never the plural 'eu bod'
            # (AGR-possessive, first seen at a real school); a sex-less
            # view keeps PR-03's pronoun-free impersonal, negated.
            if (c.gender not in ("boy", "girl") and _gendered_pred(f)
                    and W.pr("PR-03") == "impersonal_recast"):
                imp = pred_cy(f["metric"], f["codes"], "imp")
                return f"Ni nodwyd {imp} gan {c.neg_subject(1)}."
            pred = pred_cy(f["metric"], f["codes"], "sg", c.gender)
            return f"Ni ddywedodd {c.neg_subject(1)} {pred}."
        pred = pred_cy(f["metric"], f["codes"], "pl")
        return f"Ni ddywedodd {c.neg_subject(f['base'])} {pred}."
    if n == 1:
        pred = pred_cy(f["metric"], f["codes"], "sg", c.gender)
        if (c.gender not in ("boy", "girl") and _gendered_pred(f)
                and W.pr("PR-03") == "impersonal_recast"):
            imp = pred_cy(f["metric"], f["codes"], "imp")
            return f"Nodwyd {imp} gan {c.of_the(1, f['base'])}."
        return f"Dywedodd {c.of_the(1, f['base'])} {pred}."
    pred = pred_cy(f["metric"], f["codes"], "pl")
    if f.get("pct") is not None and "nopct" not in f.get("_tid", ""):
        return (f"Dywedodd {c.of_the(n, f['base'])} "
                f"({f['pct']}%) {pred}.")
    return f"Dywedodd {c.of_the(n, f['base'])} {pred}."


def _gendered_pred(f):
    """Does the singular predicate carry a gendered pronoun?"""
    global _PRED_CACHE
    if _PRED_CACHE is None:
        _PRED_CACHE = _preds()
    entry = _PRED_CACHE.get((f["metric"], tuple(sorted(f["codes"]))), {})
    return "sg_m" in entry or "sg_f" in entry


def r_setting_participation(f, c):
    """FT-01, predicate P-04, with the N=0 negative branch and the base-1
    branch (the English 'The one pupil in this selected group…')."""
    mewn = SETTING_MEWN[f["setting"]]
    if f["base"] == 1:
        lead = "Dim ond un disgybl sydd yn y grŵp a ddewiswyd"
        if f["count"] == 1:
            # PR-03: verb-noun object, no gendered complement
            return (f"{lead}; nododd y disgybl hwnnw wneud "
                    f"chwaraeon {mewn}.")
        return (f"{lead}, ac roedd heb nodi gwneud chwaraeon {mewn}.")
    if f["count"] == 0:
        if c.qual_negative() and f["base"] > 1:
            # POL (v1.8): 'heb' negates without a second particle, so a
            # negatively-defined cohort does not stack negatives
            return (f"Roedd {c.def_np(f['base'])} heb nodi gwneud unrhyw "
                    f"chwaraeon {mewn}.")
        return (f"Ni ddywedodd {c.neg_subject(f['base'])} "
                f"eu bod yn cymryd rhan mewn o leiaf un gamp {mewn}."
                if f["base"] > 1 else
                f"Ni ddywedodd {c.neg_subject(f['base'])} "
                f"ei bod yn cymryd rhan mewn unrhyw gamp {mewn}.")
    return (f"Dywedodd {c.of_the(f['count'], f['base'])} eu bod yn cymryd "
            f"rhan mewn o leiaf un gamp {mewn}.")


def r_settings_rank(f, c, group_cy=None):
    """FT-03: top-ranked setting with runners-up."""
    labels = {"pe_lessons": "In PE or lesson time",
              "school_club": "In a school club",
              "community_club": "In a club outside of school",
              "somewhere_else": "Somewhere else"}
    ranked = f["ranked"]
    top_code, top_n = ranked[0][0], ranked[0][1]
    runners = [(labels[cde], n) for cde, n in ranked[1:] if n > 0]
    top = label_cy(labels[top_code])
    if f.get("base") == 1 and not group_cy:
        used = [SETTING_MEWN[cde] for cde, n in ranked if n > 0]
        lead = "Dim ond un disgybl sydd yn y grŵp a ddewiswyd"
        if not used:
            return f"{lead}, ac roedd heb nodi lleoliad."
        return (f"{lead}; gwnaeth y disgybl hwnnw chwaraeon "
                f"{W.join_list(used, mutate_last=False)}.")
    if group_cy:
        # group noun phrase always heads with its counted noun (disgybl)
        base_np = W.of_base(f["base"], group_cy)
        t = (f"{top} oedd y lleoliad a ddewiswyd amlaf, gan "
             f"{W.numerator(top_n, prep='gan')} {base_np}")
    else:
        base_np = W.of_base(f["base"], c.aud("def_sg"), c.head_gender())
        t = (f"{top} oedd y lleoliad a ddewiswyd amlaf, gan "
             f"{W.numerator(top_n, prep='gan')} {base_np}"
             f"{' ' + c.qual if c.qual else ' a ymatebodd'}")
    if runners and f.get("followers_shown", True):
        t += f", ac yna {joinlab_counts(runners)}"
    return t + "."


def r_leader_multi(f, c):
    """FT-03: 'X oedd y gamp/yr ateb/yr amod a ddewiswyd amlaf…' — the
    head noun comes from the template's noun role (D44)."""
    lab = label_cy(f["labels"][0])
    noun, g, _pl = NOUN_CY[f.get("noun", "answer")]
    hd = W.with_article(noun, g)
    ob = W.of_base(f["base"], c.aud("def_sg"), c.head_gender())
    if f["base"] == 1:
        qual = W.sg_qual(c.qual, c.gender)
        agent = f"gan yr {ob[4:]}{' ' + qual if qual else ''}"
    else:
        agent = (f"gan {W.numerator(f['count'], prep='gan')} {ob}"
                 f"{' ' + c.qual if c.qual else ' a ymatebodd'}")
    return f"{lab} oedd {hd} a ddewiswyd amlaf, {agent}."


def _hd(f, default="answer"):
    return NOUN_CY[f.get("noun", default)]


def r_runner(f, c):
    """FT-18 singular branch: next-ranked single item."""
    r = f["runner"]
    lab = label_cy(r["labels"][0])
    noun, g, _pl = _hd(f)
    return (f"{ail_np(noun)} mwyaf cyffredin oedd {lab}, "
            f"{W.gyda_num(r['count'], 'dewis', 'dewisiadau')}, {c.among()}.")


def r_runner_joint(f, c):
    """FT-18 plural branch (D41): coordinated subject, distributive
    'yr un', plural head."""
    r = f["runner"]
    labs = joinlab(r["labels"])
    return (f"Roedd {labs} yn gyfartal yn ail, "
            f"{W.gyda_num(r['count'], 'dewis', 'dewisiadau')} yr un, "
            f"{c.among()}.")


def r_runner_many(f, c):
    """FT-18 collapsed branch (D42): the count is stated, as in English."""
    r = f["runner"]
    n = f.get("runner_n", len(r["labels"]))
    noun, g, _pl = _hd(f)
    return (f"Roedd {W.num_noun(n, noun, g)} yn gyfartal yn ail, "
            f"{W.gyda_num(r['count'], 'dewis', 'dewisiadau')} yr un, "
            f"{c.among()}; dangosir pob un yn y siart.")


def r_tie_multi(f, c):
    """FT-14: tie at the top; plural head noun from the noun role. The
    audience fronts (v4.5): an approved label like 'bowls (Nid bowlio
    10)' must not read as a negative matrix over a negatively-defined
    cohort's clause."""
    labs = joinlab(f["labels"])
    _n, _g, pl = _hd(f, "sport")
    art = "yr" if W.is_vowel_initial(pl) else "y"
    among = c.among()
    return (f"{among[0].upper()}{among[1:]}, roedd {labs} yn gyfartal "
            f"fel {art} {pl} a ddewiswyd amlaf, "
            f"{W.gyda_num(f['count'], 'dewis', 'dewisiadau')} yr un.")


def r_tie4plus(f, c):
    """FT-27 collapsed tie: counted head noun via the D40 realiser."""
    tied = f.get("tie_n", len(f.get("labels", [])))
    noun, g, _pl = _hd(f, "sport")
    return (f"Roedd {W.num_noun(tied, noun, g)} yn gyfartal am y "
            f"nifer uchaf o ddewisiadau, "
            f"{W.gyda_num(f['count'], 'dewis', 'dewisiadau')} yr un, "
            f"{c.among()}. Dangosir y rhestr lawn yn y siart.")


def r_tie_single(f, c):
    """FT-15: tie among answers, agent expressed."""
    grid = grid_of(f.get("metric"))
    labs = W.join_list([q(label_cy(l, grid, form="cy")) for l in f["labels"]])
    # v1.7: the aspirating 'gyda' frame — the soft form 'dri' after gan
    # is invisible to the pack script's figure-parity vocabulary
    agent = W.gyda_num(f["count"], "disgybl", "disgyblion") + " yr un"
    return (f"Roedd yr atebion yn gyfartal {c.among()}: "
            f"dewiswyd {labs}, {agent}.")


def r_no_responses(f, c):
    """FT-21."""
    return ("Ni chafwyd unrhyw ateb i’r cwestiwn hwn gan ddisgyblion yn y "
            "golwg a ddewiswyd.")


def r_parent_compare(f, c, cohorts):
    """FT-06 with ZERO branch."""
    pk = f.get("parent", "")
    ps, pg, _ = pk.split("|") if pk.count("|") == 2 else (c.scope, c.gender, "none")
    aud = W.audience(ps, pg, "def_sg")
    g = "f" if aud.split(" ", 1)[0] in ("merch", "ferch") else "m"
    ob = W.of_base(f["base"], aud, g)
    if f["count"] == 0:
        return f"O gymharu, nid oedd yr un {ob}."
    return f"O gymharu, {W.numerator(f['count'])} {ob} oedd y ffigur."


def r_group_defined(f, c):
    """FT-07."""
    wider = W.audience(c.scope, c.gender, "bare")
    return (f"Mae’r grŵp a ddewiswyd yn cynnwys {c.bare()}. "
            f"Mae’r siart uchod yn dangos y darlun ehangach ar gyfer "
            f"{wider} er mwyn rhoi cyd-destun, gyda’r ateb a ddewiswyd "
            f"wedi’i amlygu.")


def r_avg_sports(f, c, setting=None, group_cy=None):
    """FT-09 with the N=1 and sub-1 branches; the counting construction
    comes from the D40 realiser (D19)."""
    n = f.get("rounded", 0)
    subj = group_cy if group_cy else c.bare()
    obj = ("llai nag un gamp" if n == 0
           else W.count_partitive(n, "camp", "campau", "f"))
    tail = f" {SETTING_MEWN[setting]}" if setting else ""
    return (f"Ar gyfartaledd, cymerodd {subj} ran mewn {obj}{tail} "
            f"yn ystod y flwyddyn academaidd.")


def r_top3(f, c, setting=None):
    """FT-03 top-three for the stacked charts. The setting is a semantic
    role (D44): when present it must be realised, and the audience keeps
    its qualifier."""
    pairs = [(lab_from_code(cde), n) for cde, n in f["top3"]]
    if setting:
        top_lab, top_n = pairs[0]
        par = ("un o’r disgyblion" if top_n == 1
               else W.num_noun(top_n, "disgybl") if top_n <= 10
               else f"{top_n} disgybl")
        t = (f"{label_cy(top_lab)} oedd y gamp y dywedodd {c.bare()} "
             f"amlaf eu bod yn ei gwneud {SETTING_MEWN[setting]} "
             f"({par} a atebodd ar gyfer y lleoliad hwnnw)")
        if len(pairs) > 1:
            t += f", ac yna {joinlab_counts(pairs[1:])}"
        return t + "."
    labs = joinlab_counts(pairs)
    return (f"Y campau a ddewiswyd amlaf gan {W.soft_phrase(c.bare())} "
            f"oedd {labs}.")


_CODE_LABELS = {}


def register_code_labels(mapping):
    """code -> English display label, from the discovered metric options."""
    _CODE_LABELS.update(mapping)


def lab_from_code(code):
    return _CODE_LABELS.get(code, code)


def r_f2_year_line(f, c):
    """FT-04: setting modal in this view."""
    SET = ["pe_lessons", "school_club", "community_club", "somewhere_else"]
    counts = f["counts"]
    mi = max(range(4), key=lambda i: counts[i])
    mewn = SETTING_MEWN[SET[mi]]
    yr = W.year_cite(f["year"])
    return (f"{yr}: chwaraeon {mewn} oedd y lleoliad mwyaf cyffredin yn y "
            f"golwg hwn, yn ôl {W.numerator(counts[mi])} "
            f"{W.of_base(f['base'], 'disgybl')} a ymatebodd.")


def r_club_weekly_3plus(f, c):
    """FT-01 pair for the Club Sports analysis."""
    club = ("chwaraeon clwb (mewn clwb ysgol neu glwb y tu allan i’r ysgol)")
    if f["weekly"] == 0:
        pct0 = " (0%)" if "weekly_pct" in f else ""
        if c.qual_negative() and f["base"] > 1:
            first = (f"Roedd {c.def_np(f['base'])}{pct0} heb gymryd rhan "
                     f"mewn {club} o leiaf unwaith yr wythnos")
        else:
            first = (f"Ni chymerodd {c.neg_subject(f['base'])}{pct0} ran "
                     f"mewn {club} o leiaf unwaith yr wythnos")
    else:
        pct = f" ({f['weekly_pct']}%)" if "weekly_pct" in f else ""
        first = (f"Cymerodd {c.of_the(f['weekly'], f['base'])}{pct} ran "
                 f"mewn {club} o leiaf unwaith yr wythnos")
    tp = f["three_plus"]
    if tp == 0:
        pct0 = " (0%)" if "three_plus_pct" in f else ""
        second = (f"ni chymerodd yr un ohonynt{pct0} ran deirgwaith neu "
                  f"fwy yr wythnos")
    elif "three_plus_pct" in f:
        second = (f"cymerodd {W.numerator(tp)} o’r {W.numerator(f['base'])} "
                  f"({f['three_plus_pct']}%) ran mewn {club} deirgwaith "
                  f"neu fwy yr wythnos")
    else:
        second = (f"cymerodd {W.numerator(tp)} ran deirgwaith neu fwy yr "
                  f"wythnos")
    conj, second = W.conj_and(second)
    return f"{first}, {conj} {second}."


def r_pe_feelings(f, c):
    """FT-05: the healthy/confident/ready battery, per-item counts."""
    v = f["values"]
    h = v.get("healthy"); cf = v.get("confident"); r = v.get("ready to learn")
    bits = []
    # FT-05, quotation characters corrected v1.6 (D27): ‘…’, never ’…’
    if h:
        bits.append(
            f"ni ddywedodd yr un o’r {W.numerator(h[1])} eu bod yn teimlo’n "
            f"‘iach iawn’ nac yn ‘eithaf iach’" if h[0] == 0 else
            f"dywedodd {W.numerator(h[0])} o’r {W.numerator(h[1])} eu bod yn teimlo’n "
            f"‘iach iawn’ neu’n ‘eithaf iach’")
    if cf:
        bits.append("dim un ohonynt eu bod yn hyderus" if cf[0] == 0
                    else f"{W.numerator(cf[0])} eu bod yn hyderus")
    if r:
        bits.append("dim un ohonynt eu bod yn barod i ddysgu" if r[0] == 0
                    else f"{W.numerator(r[0])} eu bod yn barod i ddysgu")
    if not bits:
        return None
    listed = W.join_list(bits)
    return (f"Pan ofynnwyd iddynt a yw gwersi AG a Gwersi Actif yn gwneud "
            f"iddynt deimlo’n iach, yn hyderus ac yn barod i ddysgu, "
            f"ymatebodd {c.bare()} fel a ganlyn: {listed}.")


def r_enjoy_settings(f, c):
    """FT-10 highest across the enjoyment measure set."""
    vals = f["values"]
    hi = max(vals, key=lambda v: v[1])
    cy_set = ENJOY_SETTING_CY[hi[0]]
    if hi[1] == 0:
        cnt = f"dim un o’r {W.numerator(hi[3])} a ymatebodd"
    else:
        cnt = f"{W.numerator(hi[1])} o’r {W.numerator(hi[3])} a ymatebodd"
    return (f"Mewn {W.soft_phrase(cy_set) if False else cy_set} yr oedd "
            f"{c.bare()} fwyaf tebygol o ddweud eu bod yn mwynhau "
            f"chwaraeon ‘Llawer’: {cnt}.")


def r_enjoy_low_setting(f, c):
    """FT-17: lowest-enjoyment setting, with the N=0 negative branch."""
    cy_set = ENJOY_SETTING_CY.get(f["setting"], f["setting"])
    lead = (f"Ymhlith {c.aud('bare')}{' ' + c.qual if c.qual else ''}, "
            f"y mwynhad isaf oedd am chwaraeon mewn {cy_set}, ")
    if f["count"] == 0:
        return (lead + f"lle nad atebodd yr un o’r {W.numerator(f['base'])} "
                f"‘Dim Llawer’ na ‘Dim o gwbl’.")
    return (lead + f"lle atebodd {W.numerator(f['count'])} o’r {W.numerator(f['base'])} "
            f"‘Dim Llawer’ neu ‘Dim o gwbl’.")


def r_enjoy_year_extremes(f, c):
    """FT-28: ar ei uchaf / ar ei isaf, nasal on the year."""
    vals = f["values"]
    hi = max(vals, key=lambda v: v[3]); lo = min(vals, key=lambda v: v[3])
    return (f"Roedd mwynhad o wersi AG ar ei uchaf ym Mlwyddyn {hi[0]} "
            f"({numz(hi[1])} o’r {W.numerator(hi[2])} yn ateb ‘Llawer’, neu {hi[3]}%) "
            f"ac ar ei isaf ym Mlwyddyn {lo[0]} ({numz(lo[1])} o’r {W.numerator(lo[2])}, "
            f"neu {lo[3]}%), {c.among()}.")


def r_age_setting_extremes(f, c):
    """FT-28 for the year-by-setting chart."""
    vals = f["values"]
    hi = max(vals, key=lambda v: v[3]); lo = min(vals, key=lambda v: v[3])
    mewn = SETTING_MEWN[f["setting"]]
    return (f"Roedd cyfranogiad mewn chwaraeon {mewn} ar ei uchaf "
            f"ym Mlwyddyn {hi[0]} ({numz(hi[1])} o’r {W.numerator(hi[2])}, neu {hi[3]}%) "
            f"ac ar ei isaf ym Mlwyddyn {lo[0]} ({numz(lo[1])} o’r {W.numerator(lo[2])}, "
            f"neu {lo[3]}%), {c.among()}.")


def r_confidence_dims(f, c):
    """FT-10 highest across the confidence measure set."""
    vals = f["values"]
    hi = max(vals, key=lambda v: v[1])
    m = CONF_MEASURE_CY[hi[0]]
    return (f"Roedd {c.bare()} fwyaf tebygol o ddweud eu bod yn hyderus i "
            f"{W.soft_phrase(m)}: dywedodd {W.numerator(hi[1])} o’r {W.numerator(hi[2])} a ymatebodd "
            f"‘Hyderus Iawn’ neu ‘Eithaf hyderus’.")


def r_confidence_dims_low(f, c):
    """FT-36 anaphoric lowest."""
    vals = f["values"]
    lo = min(vals, key=lambda v: v[1])
    m = CONF_MEASURE_CY[lo[0]]
    return (f"Roeddent leiaf tebygol o ddweud eu bod yn hyderus i "
            f"{W.soft_phrase(m)} ({numz(lo[1])} o’r {W.numerator(lo[2])}), {c.among()}.")


def r_confidence_joint_hi(f, c):
    """FT-26: joint highest / lowest across the measure set."""
    vals = f["values"]
    hi_n = max(v[1] for v in vals); lo_n = min(v[1] for v in vals)
    highs = [CONF_MEASURE_CY[v[0]] for v in vals if v[1] == hi_n]
    lows = [CONF_MEASURE_CY[v[0]] for v in vals if v[1] == lo_n]
    base = vals[0][2]
    return (f"Hyder wrth {W.soft_phrase(W.join_list(highs))} a gafodd yr "
            f"ymateb cadarnhaol uchaf ar y cyd ({numz(hi_n)} o’r {W.numerator(base)}), tra mai "
            f"hyder wrth {W.soft_phrase(W.join_list(lows))} a gafodd yr "
            f"ymateb isaf ({numz(lo_n)} o’r {W.numerator(base)}), {c.among()}.")


def r_confidence_equal(f, c):
    vals = f["values"]
    n, base = vals[0][1], vals[0][2]
    if n == 0:
        return (f"Roedd hyder yr un mor uchel ar draws y pedwar mesur, "
                f"heb i’r un {c.the_base(base)} ddewis "
                f"‘Hyderus Iawn’ neu ‘Eithaf hyderus’ ar gyfer unrhyw "
                f"fesur.")
    return (f"Roedd hyder yr un mor uchel ar draws y pedwar mesur, gyda "
            f"{W.numerator(n)} "
            f"{W.of_base(base, c.aud('def_sg'), c.head_gender())}"
            f"{' ' + c.qual if c.qual else ''} a ymatebodd yn dewis "
            f"‘Hyderus Iawn’ neu ‘Eithaf hyderus’ ar gyfer pob mesur.")


def r_low_confidence(f, c):
    P = W.lexicon()["predicates"]
    if f["count"] == 0:
        if f["base"] == 1:      # v6: singleton antecedent — the n = 1 singular
            sg = P["P-05"]["cy"].replace("nad oeddent", "nad oedd")
            return f"Ni ddywedodd {c.neg_subject(1)} {sg}."
        return f"Ni ddywedodd {c.neg_subject(f['base'])} {P['P-05']['cy']}."
    if f["count"] == 1:
        sg = P["P-05"]["cy"].replace("nad oeddent", "nad oedd")
        return f"Dywedodd {c.of_the(1, f['base'])} {sg}."
    return (f"Dywedodd {c.of_the(f['count'], f['base'])} "
            f"{P['P-05']['cy']}.")


def r_unmet_leader(f, c):
    """FT-20: the oblique relative with resumptive 'amdani'."""
    l = f["leader"]
    lab = label_cy(l["labels"][0])
    ob = W.of_base(l["base"], c.aud("def_sg"), c.head_gender())
    if l["base"] == 1:
        qual = W.sg_qual(c.qual, c.gender)
        agent = f"gan yr {ob[4:]}{' ' + qual if qual else ''}"
    else:
        agent = (f"gan {W.numerator(l['count'], prep='gan')} {ob}"
                 f"{' ' + c.qual if c.qual else ' a ymatebodd'}")
    return (f"Y gamp yr oedd y galw mwyaf heb ei fodloni amdani oedd "
            f"{lab}, a ddewiswyd {agent}.")


def r_unmet_runner(f, c):
    r = f["runner"]
    labs = joinlab(r["labels"])
    joint = " yr un" if len(r["labels"]) > 1 else ""
    return (f"Yna daeth {labs}, "
            f"{W.gyda_num(r['count'], 'dewis', 'dewisiadau')}{joint}, "
            f"{c.among()}.")


def r_unmet_base1(f, c):
    l = f["leader"]
    lab = label_cy(l["labels"][0])
    return (f"Dim ond un disgybl sydd yn y grŵp a ddewiswyd a atebodd; "
            f"dewisodd y disgybl hwnnw {lab} fel camp yr hoffai wneud "
            f"mwy ohoni.")


def r_current_vs_demand(f, c):
    """FT-24 with the v1.6 list-collapse branch (D42): where the English
    summarises a long tie as a count, the Welsh does the same and keeps
    the count — expanding it was the G6c/G4 defect."""
    d = f["unmet"]; p = f["current"]
    dn = f.get("unmet_tie_n", len(d["labels"]))
    pn = f.get("current_tie_n", len(p["labels"]))
    dl = (joinlab(d["labels"]) if dn <= 3
          else f"Roedd {W.num_noun(dn, 'camp', 'f')} ar y cyd")
    pl = (joinlab(p["labels"]) if pn <= 3
          else W.num_noun(pn, "camp", "f"))
    par = ("(un dewis)" if d["count"] == 1
           else f"({W.num_noun(d['count'], 'disgybl')})")
    if dn <= 3:
        t = f"{dl} oedd â’r galw mwyaf heb ei fodloni {par}"
    else:
        t = f"{dl} â’r galw mwyaf heb ei fodloni {par}"
    if pn <= 3:
        t += (f", tra bo {pl} â’r cyfranogiad presennol uchaf "
              f"({p['count']})")
    else:
        t += (f", tra bo {pl} ar y cyd â’r cyfranogiad presennol uchaf "
              f"({p['count']})")
    return f"{t}, {c.among()}."


def r_gender_leader_pair(f, c):
    """FT-23."""
    b = f["boys"]; g = f["girls"]
    bl = joinlab(b["labels"]); gl = joinlab(g["labels"])
    scope_cy = {"whole": "yn yr ysgol gyfan",
                "primary": "yn yr ysgol gynradd",
                "secondary": "yn yr ysgol uwchradd"}.get(
        c.scope, W.year_loc(c.scope[1:]) if c.scope.startswith("y") else "")
    bn = W.count_partitive(b["count"], "dewis", "dewisiadau")
    gn = W.count_partitive(g["count"], "dewis", "dewisiadau")
    return (f"{bl} oedd ar y brig ymhlith bechgyn ({bn}), "
            f"tra bo {gl} ar y brig ymhlith merched "
            f"({gn}), {scope_cy}.")


_ORD_ABBR = {11: "11eg", 12: "12fed", 13: "13eg", 14: "14eg", 15: "15fed",
             16: "16eg", 17: "17eg", 18: "18fed", 19: "19eg", 20: "20fed"}


def ord_cy(rank, gender):
    """Ordinal WITHOUT article: words to 10 (gendered), the conventional
    digit abbreviations from 11 (D03: digits for 11+ — mirrors the
    English, which switches to '11th'). Tens take -fed, the rest -ain;
    flagged in the compliance record for the linguist."""
    rank = int(rank)
    if rank <= 10:
        return W.ordinal(rank, gender, with_article=False)
    if rank in _ORD_ABBR:
        return _ORD_ABBR[rank]
    return f"{rank}fed" if rank % 10 == 0 else f"{rank}ain"


def ail_np(noun, cap=True):
    """'yr ail ⟪noun⟫' — the second-ranked head. Sheet 09 (v2.7, the
    translator's ruling of 21 Sep 2026, handover sheet 4 rule 16 / sheet 5
    #34): 'ail' takes the SOFT mutation of the following noun in both
    genders — yr ail gamp, yr ail leoliad — as _ord_np already did; the
    runner-up templates used to write the noun unmutated ('Yr ail camp',
    2,465 sentences in the test school)."""
    n = W.soft_phrase(noun)
    return f"{'Yr' if cap else 'yr'} ail {n}"


def _ord_np(rank, noun, gender):
    """FT-33 v1.6: cyntaf POSTPOSES (D43, ORD-1-POSTNOMINAL); every other
    ordinal is prenominal with gender agreement and ART selection."""
    rank = int(rank)
    if rank == 1:
        n = W.soft(noun, mutable=True) if gender in ("f", "b") else noun
        adj = "gyntaf" if gender in ("f", "b") else "cyntaf"
        return f"y {n} {adj}" if not W.is_vowel_initial(n) else f"yr {n} {adj}"
    o = ord_cy(rank, gender)
    art = "yr" if rank > 10 and W.article(str(rank)) == "yr" else (
        "yr" if W.is_vowel_initial(o) else "y")
    # ail lenites its noun in both genders; feminine ordinals lenite too;
    # no mutation after a digit abbreviation
    n = (W.soft(noun, mutable=True)
         if rank <= 10 and (rank == 2 or gender in ("f", "b")) else noun)
    return f"{art} {o} {n}"


# The noun role of FT-33, per emitting module (D44): what the ranked item
# was ranked AS. Distinct English measures must stay distinct in Welsh.
RANK_NOUN_CY = {
    "desired sport": ("camp", "f", "a ddewiswyd amlaf fel camp yr hoffent "
                                   "wneud mwy ohoni"),
    "unmet-demand sport": ("camp", "f", "a ddewiswyd amlaf fel camp yr "
                                        "oedd galw amdani heb ei fodloni"),
    "condition": ("amod", "m", "a ddewiswyd amlaf fel amod a fyddai’n eu "
                               "helpu i wneud mwy o chwaraeon"),
    "sport": ("camp", "f", "a ddewiswyd amlaf"),
}
RANK_NOUN_PL_CY = {
    "desired sport": ("campau", "a ddewiswyd amlaf fel campau yr hoffent "
                                "wneud mwy ohonynt"),
    "unmet-demand sport": ("campau", "a ddewiswyd amlaf fel campau yr oedd "
                                     "galw amdanynt heb ei fodloni"),
    "condition": ("amodau", "a ddewiswyd amlaf"),
    "sport": ("campau", "a ddewiswyd amlaf"),
}


def r_rank_diff(f, c):
    """FT-33 with the v1.6 first-ordinal branch. Mirrors the English role
    set exactly: audience is 'boys ⟪place⟫' with no cohort tail."""
    lab = label_cy(lab_from_code(f["item"]))
    noun, g, rel = RANK_NOUN_CY[f.get("noun", "desired sport")]
    first = _ord_np(f["boys_rank"], noun, g)
    rb = ord_cy(f["girls_rank"], g)
    return (f"{lab} oedd {first} {rel} ymhlith bechgyn {aud_scope_cy(c)}, "
            f"a’r {rb} ymhlith merched.")


def r_gender_count_compare(f, c):
    """FT-31: the measure is a role (D44) — predicate from metric+codes;
    bases realised by the D40 realiser."""
    pred = pred_cy(f["metric"], f["codes"], "pl")
    b, g_ = f["boys"], f["girls"]
    bb = W.of_base(f["boys_base"], "bachgen")
    gb = W.of_base(f["girls_base"], "merch", "f")
    lead = f"Ymhlith {c.aud('bare')}{' ' + c.qual if c.qual else ''}, "
    if b == 0 and g_ == 0:
        return (f"{lead}ni ddywedodd yr un {bb} na’r un {gb} "
                f"a ymatebodd {pred}.")
    if b == 0:
        return (f"{lead}ni ddywedodd yr un {bb}, ond dywedodd "
                f"{W.numerator(g_, 'f')} {gb} a ymatebodd, {pred}.")
    if g_ == 0:
        return (f"{lead}dywedodd {W.numerator(b)} {bb} a ymatebodd {pred}, "
                f"ond ni ddywedodd yr un {gb}.")
    g_np = f"{W.numerator(g_, 'f')} {gb} a ymatebodd"
    conj, g_np = W.conj_and(g_np)
    return (f"{lead}dywedodd {W.numerator(b)} {bb} {conj} "
            f"{g_np} {pred}.")


def r_gender_pct_compare(f, c):
    """FT-31 (pct form): predicate resolved from the measure role (D44) —
    the V4.2 assessment's G1a defect was a fixed P-01 here."""
    pred = pred_cy(f["metric"], f["codes"], "pl")
    b_np = (f"ni ddywedodd yr un o’r {W.numerator(f['boys_base'])} ({f['boys_pct']}%)"
            if f["boys"] == 0 else
            f"dywedodd {W.numerator(f['boys'])} o’r {W.numerator(f['boys_base'])} "
            f"({f['boys_pct']}%)")
    g_np = (f"dim un o’r {W.numerator(f['girls_base'], 'f')} ({f['girls_pct']}%) o ferched"
            if f["girls"] == 0 else
            f"{W.numerator(f['girls'])} o’r {W.numerator(f['girls_base'], 'f')} "
            f"({f['girls_pct']}%) o ferched")
    return (f"Ymhlith bechgyn {aud_scope_cy(c)}, {b_np} {pred}, o "
            f"gymharu â {g_np}.")


def aud_scope_cy(c):
    if c.scope.startswith("y") and c.scope[1:].isdigit():
        return W.year_loc(c.scope[1:])
    return {"whole": "yn yr ysgol gyfan", "primary": "yn yr ysgol gynradd",
            "secondary": "yn yr ysgol uwchradd"}[c.scope]


def r_take_part_prose(f, c):
    """FT-25: enumeration of response modes. The audience-gender role is
    threaded to the singular complement (v1.6 F6): a girl-filtered
    singular is 'un ferch … ei bod', never a defaulted 'ei fod'."""
    one = {"boy": ("un bachgen", "ei fod"),
           "girl": ("un ferch", "ei bod")}.get(
        c.gender, ("un disgybl", "ei fod"))
    CLAUSES = {
        "standing": ("dywedodd {n} eu bod fel arfer yn cymryd rhan yn sefyll",
                     f"dywedodd {one[0]} {one[1]} fel arfer yn cymryd rhan "
                     f"yn sefyll"),
        "seated": ("dywedodd {n} eu bod fel arfer yn cymryd rhan yn eistedd",
                   f"dywedodd {one[0]} {one[1]} fel arfer yn cymryd rhan "
                   f"yn eistedd"),
        "communication_aids": ("roedd {n} yn defnyddio cymhorthion cyfathrebu",
                               "roedd un yn defnyddio cymhorthion cyfathrebu"),
        "not_sure": ("nid oedd {n} yn siŵr", "nid oedd un yn siŵr"),
        # sheet 44 (e7): at N >= 2 the numeral after gan is SOFT-MUTATED by
        # the numeral service (gan ddau, gan dri); at N = 1 the possessor
        # is REALISED (ganddo / ganddi — PR-14 masculine where unknown).
        "prefer_not_to_say": ("byddai’n well gan {n} beidio â dweud",
                              "roedd yn well "
                              f"{'ganddi' if c.gender == 'girl' else 'ganddo'}"
                              " beidio â dweud"),
        "other": ("dewisodd {n} gategori cymeradwy arall",
                  "dewisodd un gategori cymeradwy arall"),
    }
    if c.gender not in ("boy", "girl") and W.pr("PR-03") == "impersonal_recast":
        # sex not carried by the view: pronoun-free clauses (D48/PR-03).
        # 'un ohonynt' keeps the singular item inside a plural list
        # without a gendered complement or a bare 'un disgybl' (G9b).
        CLAUSES = {**CLAUSES,
                   "standing": (CLAUSES["standing"][0],
                                "nododd un ohonynt gymryd rhan yn sefyll "
                                "fel arfer"),
                   "seated": (CLAUSES["seated"][0],
                              "nododd un ohonynt gymryd rhan yn eistedd "
                              "fel arfer")}
    else:
        CLAUSES = {**CLAUSES,
                   "standing": (CLAUSES["standing"][0],
                                f"dywedodd un ohonynt {one[1]} fel arfer yn "
                                f"cymryd rhan yn sefyll"),
                   "seated": (CLAUSES["seated"][0],
                              f"dywedodd un ohonynt {one[1]} fel arfer yn "
                              f"cymryd rhan yn eistedd")}
    if f["base"] == 1:
        ONE = {"standing": "nododd gymryd rhan yn sefyll fel arfer",
               "seated": "nododd gymryd rhan yn eistedd fel arfer",
               "communication_aids": "roedd yn defnyddio cymhorthion "
                                     "cyfathrebu",
               "not_sure": "nid oedd yn siŵr",
               # sheet 44 (e7, N = 1): the possessor is REALISED, never
               # deleted — deleting it orphans the SM on beidio (PR-14).
               "prefer_not_to_say": ("roedd yn well "
                                     + ("ganddi" if c.gender == "girl"
                                        else "ganddo")
                                     + " beidio â dweud"),
               "other": "dewisodd gategori cymeradwy arall"}
        bits = [ONE[code] for code, n in f["pairs"] if code in ONE]
        if len(bits) != len(f["pairs"]):
            return None
    else:
        bits = []
        for code, n in f["pairs"]:
            forms = CLAUSES.get(code)
            if not forms:
                return None
            # D40: the numeral after gan is realised BY THE NUMERAL SERVICE
            # with the soft mutation gan licenses (gan ddau, gan dri).
            num = (W.numerator(n, prep="gan")
                   if code == "prefer_not_to_say" else W.numerator(n))
            bits.append(forms[1] if n == 1 else forms[0].format(n=num))
    listed = W.join_list(bits, mutate_last=False)
    ob = W.of_base(f["base"], c.aud("def_sg"), c.head_gender())
    # D48: the frame's own agreement follows the base — a one-person base
    # cannot take 'iddynt … y maent'
    if f["base"] == 1:
        frame = (" y gofynnwyd sut y mae fel arfer yn cymryd rhan mewn "
                 "chwaraeon, ")
    else:
        frame = (" y gofynnwyd iddynt sut y maent fel arfer yn cymryd "
                 "rhan mewn chwaraeon, ")
    qual = (W.sg_qual(c.qual, c.gender) if f["base"] == 1 else c.qual)
    return (f"O{ob[1:]}"
            f"{' ' + qual if qual else ''}{frame}{listed}.")


def r_welsh_when_playing(f, c):
    """FT-22: the yes/no answer echoes the question verb (QV-03), with
    the NUM-N0-NEG branch — never 'atebodd 0'."""
    ob = W.of_base(f["base"], c.aud("def_sg"), c.head_gender())
    ask = (" y gofynnwyd a yw’n siarad Cymraeg wrth gymryd rhan mewn "
           "chwaraeon, " if f["base"] == 1 else
           " y gofynnwyd iddynt a ydynt yn siarad Cymraeg wrth gymryd "
           "rhan mewn chwaraeon, ")
    qual = (W.sg_qual(c.qual, c.gender) if f["base"] == 1 else c.qual)
    lead = f"O{ob[1:]}{' ' + qual if qual else ''}{ask}"
    if f["count"] == 0 and f["base"] == 1:
        return lead + "nid atebodd ‘Ydw’."
    if f["count"] == 0:
        return lead + "nid atebodd yr un ohonynt ‘Ydw’."
    if f["count"] == 1 and f["base"] == 1:
        return lead + "‘Ydw’ oedd yr un ateb a gafwyd."
    return lead + f"atebodd {W.numerator(f['count'])} ohonynt ‘Ydw’."


def _group_tail(c):
    """The outer audience+cohort of a demographic-group sentence (D44:
    the outer qualifier is a role and must be consumed — scope, gender
    and cohort all distinguish states)."""
    return f" {c.among()}"


def r_group_settings_rank(f, c, module):
    """FT-03 for the demographic settings charts. The respondent group is
    identified by the METRIC role (v1.6 G1c: disability-only, LD-only and
    the combined group are three different groups), and the outer cohort
    qualifier is appended (G1e)."""
    grp = group_mid_cy(f["mid"])
    # D61 (v1.9): the fact record carries TWO roles — the outer cohort and
    # the inner subgroup — and BOTH are realised. The V4.5 anaphoric
    # shortcut ('yn y grŵp a ddewiswyd') consumed the outer role without
    # realising it and is reverted here (ROLE-outer).
    tail = _group_tail(c)
    subj = f"{grp}{tail}"
    return r_settings_rank(f, c, group_cy=subj)


def r_dl_combined_note(f, c):
    """FT-30 COMBINED branch — GDPR disclosure note."""
    return ("Dangosir anabledd ac anhawster dysgu fel un grŵp cyfun yn y "
            "golwg hwn am fod un o’r ddau grŵp yn cynnwys llai na phum "
            "disgybl; cyfrifir pob disgybl unwaith.")


def r_group_defined_note(f, c):
    return r_group_defined(f, c)


def r_no_additional_conf(f, c):
    return (f"Nid yw data eich ysgol yn rhoi digon o wybodaeth ychwanegol "
            f"y gellir ei hadrodd am y mesurau hyder eraill "
            f"{c.among()}.")


def r_not_enough_group(f, c):
    return ("Nid yw data eich ysgol yn rhoi digon o wybodaeth ychwanegol "
            "y gellir ei hadrodd ar gyfer y golwg hwn.")


def r_base1_choice(f, c, purpose_cy):
    l = f["leader"]
    grid = grid_of(f.get("metric"))
    lab = q(label_cy(l["labels"][0], grid, form="cy"))
    return (f"Dim ond un disgybl sydd yn y grŵp a ddewiswyd; "
            f"dewisodd y disgybl hwnnw {lab} {purpose_cy}.")


def r_group_sibling(f, c, measure_en):
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], "conf", form="cy"))
    m = CONF_MEASURE_CY[measure_en]
    return (f"Atebodd y rhan fwyaf o’r grŵp hwn {lab} pan ofynnwyd pa mor "
            f"hyderus ydynt i {W.soft_phrase(m)} ({W.numerator(l['count'])} o’r "
            f"{W.numerator(l['base'])}).")


def r_group_sibling_conf(f, c):
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], "conf", form="cy"))
    return (f"Pan ofynnwyd pa mor hyderus ydynt i roi cynnig ar gamp "
            f"newydd, atebodd y grŵp mwyaf o’r {c.aud('def_sg')} "
            f"{c.qual or ''} ({W.numerator(l['count'])} o’r {W.numerator(l['base'])}) {lab}.")


# ------------------------------------------------------- remaining renderers
def r_barrier_leader(f, c):
    """FT-13: modal answer for a stated purpose."""
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], form="cy"))
    ob = W.of_base(l["base"], "disgybl")
    agent = (f"gan yr {ob[4:]}" if l["base"] == 1 else
             f"gan {W.numerator(l['count'], prep='gan')} {ob} a ymatebodd")
    return (f"{lab} oedd yr ateb a ddewiswyd amlaf a fyddai’n helpu "
            f"{c.bare()} i wneud mwy o chwaraeon, a ddewiswyd {agent}.")


def r_barrier_runner(f, c):
    """FT-18 arity branches for the enabling-conditions runner (D41/D42)."""
    r = f["runner"]
    n_items = f.get("runner_n", len(r["labels"]))
    gnum = W.gyda_num(r["count"], "disgybl", "disgyblion")
    if n_items == 1:
        lab = q(label_cy(r["labels"][0], form="cy"))
        return (f"{ail_np('ateb')} mwyaf cyffredin oedd {lab}, {gnum} "
                f"yn ei ddewis, {c.among()}.")
    labs = W.join_list([q(label_cy(l, form="cy")) for l in r["labels"]])
    if n_items <= 3:
        return (f"Roedd {labs} yn gyfartal fel {ail_np('atebion', cap=False)} mwyaf "
                f"cyffredin, {gnum} yr un, {c.among()}.")
    return (f"Roedd {W.num_noun(n_items, 'ateb')} yn gyfartal yn ail, "
            f"{gnum} yr un, {c.among()}; dangosir pob un yn y siart.")


def r_barrier_none(f, c):
    """FT-16: the citation count comes from the numeral service (D40) —
    'dewisodd chwech ‘Dim un o’r rhain’', never a figure before a quote."""
    return (f"{c.among().capitalize() if False else 'Ymhlith ' + c.bare()}, "
            f"dewisodd {W.numerator(f['count'])} {q('Dim un o’r rhain')}.")


def r_important_leader(f, c):
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], form="cy"))
    ob = W.of_base(l["base"], c.aud("def_sg"), c.head_gender())
    # D61 / PR-16: when the selected group is itself defined by an answer
    # to this question, the exclusion of the defining answer is a ROLE on
    # the fact record and BOTH languages realise it.
    apart = (" (ac eithrio’r ateb sy’n diffinio’r grŵp hwn)"
             if (c.cohort and c.cohort.get("metric") == "most_important"
                 and W.pr("PR-16") == "realise_exclusion") else "")
    if l["base"] == 1:
        qual = W.sg_qual(c.qual, c.gender)
        agent = f"gan yr {ob[4:]}{' ' + qual if qual else ''}"
    else:
        agent = (f"gan {W.numerator(l['count'], prep='gan')} {ob}"
                 f"{' ' + c.qual if c.qual else ' a atebodd y cwestiwn hwn'}")
    return f"{lab} oedd yr opsiwn a ddewiswyd amlaf{apart}, {agent}."


def r_important_runner(f, c):
    """FT-18 with the v1.6 arity branches (D41) and collapse (D42).
    The singular keeps the count with a 'yn dewis yr opsiwn hwn' clause
    (the 'yn ei ddewis' resumptive over a coordination was the G6b
    defect); the plural takes the coordinated 'Roedd … yn gyfartal'
    shape with distributive 'yr un'; four or more collapse to a count,
    exactly as the English does."""
    r = f["runner"]
    n_items = f.get("tie_n", len(r["labels"]))
    gnum = W.gyda_num(r["count"], "disgybl", "disgyblion")
    if n_items == 1:
        lab = q(label_cy(r["labels"][0], form="cy"))
        return (f"{ail_np('opsiwn')} mwyaf cyffredin oedd {lab}, {gnum} "
                f"yn dewis yr opsiwn hwn, {c.among()}.")
    labs = W.join_list([q(label_cy(l, form="cy")) for l in r["labels"]])
    if n_items <= 3:
        return (f"Roedd {labs} yn gyfartal fel {ail_np('opsiynau', cap=False)} mwyaf "
                f"cyffredin, {gnum} yr un, {c.among()}.")
    return (f"Roedd {W.num_noun(n_items, 'opsiwn')} yn gyfartal yn ail, "
            f"{gnum} yr un, {c.among()}; dangosir pob un yn y siart.")


def r_important_gender_leader(f, c):
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], form="cy"))
    gcy = "fechgyn" if f.get("gender") == "boy" else "ferched"
    return (f"{lab} oedd yr opsiwn a ddewiswyd amlaf gan {gcy} "
            f"{aud_scope_cy(c)} ({W.num_noun(l['count'], 'disgybl')}).")


def r_barrier_base1(f, c):
    return r_base1_choice(f, c, "fel yr hyn a fyddai’n ei helpu i wneud mwy o chwaraeon")


def r_important_base1(f, c):
    return r_base1_choice(f, c, "fel yr hyn sydd bwysicaf")


def r_conf_base1(f, c):
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], "conf", form="cy"))
    return (f"Dim ond un disgybl sydd yn y grŵp a ddewiswyd; atebodd y "
            f"disgybl hwnnw {lab} pan ofynnwyd pa mor hyderus ydyw i roi "
            f"cynnig ar gamp newydd.")


def r_combined_base1(f, c):
    """FT-01 for a base of one: the polarity is a role (D44). n=1 is the
    POSITIVE 'the one pupil said…'; only n=0 takes the negative verb.
    v1.7: PR-02 recast for negative predicates at zero, PR-03 impersonal
    where the view carries no sex."""
    if f["count"] == 0:
        if (_neg_pred(f["metric"], f["codes"]) and f.get("code_labels")
                and W.pr("PR-02") == "answer_selection_recast"):
            return _zero_recast(f, c, "yr un disgybl yn y grŵp a ddewiswyd")
        pred = pred_cy(f["metric"], f["codes"], "pl")
        return (f"Ni ddywedodd yr un disgybl yn y grŵp a ddewiswyd "
                f"{pred}.")
    if (c.gender not in ("boy", "girl") and _gendered_pred(f)
            and W.pr("PR-03") == "impersonal_recast"):
        imp = pred_cy(f["metric"], f["codes"], "imp")
        return (f"Dim ond un disgybl sydd yn y grŵp a ddewiswyd; nodwyd "
                f"{imp} gan y disgybl hwnnw.")
    pred = pred_cy(f["metric"], f["codes"], "sg", c.gender)
    return (f"Dim ond un disgybl sydd yn y grŵp a ddewiswyd; dywedodd y "
            f"disgybl hwnnw {pred}.")


def r_group_codemand_top3(f, c):
    pairs = [(lab_from_code(cde), n) for cde, n in f["top3"]]
    want = c.cohort.get("optionLabel", "") if c.cohort else ""
    base_np = W.def_num_noun(f["base"], c.aud("def_sg").split(" ", 1)[0],
                             c.head_gender())
    rest = c.aud("def_sg").split(" ", 1)
    tail = f" {rest[1]}" if len(rest) > 1 else ""
    art = "yr" if W.is_vowel_initial(base_np) else "y"
    qual = W.sg_qual(c.qual, c.gender) if f["base"] == 1 else c.qual
    return (f"Roedd y disgyblion a ddewisodd {label_cy(want)} hefyd am "
            f"gael mwy o {W.soft_phrase(joinlab_counts(pairs))}, "
            f"o blith {art} {base_np}{tail} {qual or ''}.")


def r_wd_current_check(f, c):
    want = c.cohort.get("optionLabel", "") if c.cohort else ""
    if f["count"] == 0:
        return (f"Nid oedd {c.neg_subject(f['base'], answered=False)} "
                f"eisoes wedi nodi gwneud {label_cy(want)} yn "
                f"ystod y flwyddyn ysgol hon.")
    # D48/PR-03: pronoun-free verb-noun object — 'wedi nodi gwneud X' —
    # so a one-person count needs no gendered complement
    doing = ("wedi nodi gwneud" if f["count"] == 1
             else "wedi nodi eu bod yn gwneud")
    return (f"Roedd {c.of_the(f['count'], f['base'], answered=False)} "
            f"eisoes {doing} {label_cy(want)} yn ystod y flwyddyn ysgol "
            f"hon.")


# D48: the one-pupil form of P-15 — 'y gall' carries no pronoun, so it
# serves a boy, a girl and a pupil whose sex the view does not carry alike
_P15_SG = "y gall, o leiaf weithiau, ymuno’n hawdd â chwaraeon a gemau"


def r_li_join_cross(f, c):
    P = W.lexicon()["predicates"]
    if f["count"] == 0:
        # v6 (0.28.0, V5.0 real-school round — first seen at a real school,
        # AGR-possessive): a nil count on a ONE-pupil base is a singleton
        # antecedent ('yr unig ferch …'), so the complement takes the same
        # pronoun-free D48 clause as the one-pupil count, never the plural
        # 'eu bod' of P-15. Flagged for the translator (sheet 63).
        pred = _P15_SG if f["base"] == 1 else P["P-15"]["cy"]
        return (f"Ni ddywedodd {c.neg_subject(f['base'], answered=False)} "
                f"{pred}.")
    if f["count"] == 1:
        # D48: gender-free singular — 'y gall' carries no pronoun
        return (f"Dywedodd {c.of_the(1, f['base'], answered=False)} "
                f"{_P15_SG}.")
    return (f"Dywedodd {c.of_the(f['count'], f['base'], answered=False)} "
            f"{P['P-15']['cy']}.")


def r_cross_insight(f, c, cohorts):
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], form="cy"))
    grp = f.get("group")
    qual = None
    if grp and grp in cohorts:
        fam = grp.split("_", 1)[0]
        from .narrative2 import GROUP_VERBS
        en = GROUP_VERBS[fam](cohorts[grp].get("optionLabel", ""),
                              cohorts[grp]["code"])
        qual = W.qualifier_cy(fam, en,
                              answer_label=cohorts[grp].get("optionLabel"))
    if not qual:
        return None
    return (f"Ymhlith {c.aud('bare')} {qual}, {lab} oedd yr amod a "
            f"ddewiswyd amlaf a fyddai’n eu helpu i wneud mwy o chwaraeon "
            f"({W.numerator(l['count'])} o’r {W.numerator(l['base'])} a ymatebodd).")


def r_rank_parent_same(f, c):
    v = f["view"]; p = f["parent"]
    vl = joinlab(v["labels"]); pk = f.get("parent_key", "")
    ps, pg, _ = pk.split("|")
    parent = W.audience(ps, pg, "holl")
    return (f"{vl} sydd ar y brig ymhlith {c.aud('bare')}"
            f"{' ' + c.qual if c.qual else ''}, fel y mae ymhlith "
            f"{parent}.")


def r_rank_parent_diff(f, c):
    v = f["view"]; p = f["parent"]
    vl = joinlab(v["labels"]); pl = joinlab(p["labels"])
    pk = f.get("parent_key", "")
    ps, pg, _ = pk.split("|")
    parent = W.audience(ps, pg, "holl")
    return (f"{vl} sydd ar y brig ymhlith {c.aud('bare')}"
            f"{' ' + c.qual if c.qual else ''}, tra bo {pl} ar y brig "
            f"ymhlith {parent}.")


def r_rank_parent_joint(f, c):
    """The head-noun role (D44): a leading SETTING is 'y lleoliad
    blaenaf … y ddau leoliad', never 'y gamp' (v1.6 G2b); the definite
    dual mutates (y ddau / y ddwy, sheet 08 — v1.6 G3e)."""
    v = f["view"]; pk = f.get("parent_key", "")
    vl = joinlab(v["labels"])
    ps, pg, _ = pk.split("|")
    parent = W.audience(ps, pg, "holl")
    n = f.get("parent_tie_n", 1)
    noun, g, _pl = NOUN_CY[f.get("noun", "sport")]
    head_sg = W.with_article(noun, g)     # y gamp / y lleoliad
    dual = W.def_num_noun(n, noun, g)     # ddwy gamp / ddau leoliad / …
    return (f"{vl} oedd {head_sg} ar y brig ymhlith {c.aud('bare')}"
            f"{' ' + c.qual if c.qual else ''}, ac roedd hefyd yn un o’r "
            f"{dual} a oedd ar y brig ymhlith {parent}.")


def r_phase_leaders(f, c):
    """FT-32 — needs structured facts (primary/secondary leaders)."""
    pr = f.get("primary"); se = f.get("secondary")
    if not pr and not se:
        return None
    bits = []
    if pr:
        labs = joinlab(pr["labels"])
        bits.append(f"{labs} oedd ar y brig yn yr ysgol gynradd "
                    f"({W.count_partitive(pr['count'], 'dewis', 'dewisiadau')})")
    if se:
        labs = joinlab(se["labels"])
        bits.append(f"{labs} oedd ar y brig yn yr ysgol uwchradd "
                    f"({W.count_partitive(se['count'], 'dewis', 'dewisiadau')})")
    lead = "; ".join(bits)
    return f"Ymhlith {c.bare()}, {lead}."


def r_phase_top(f, c):
    """phase_leaders_v2 (d9/f12): 'X was the most frequently selected
    ⟪noun⟫ in the ⟪phase⟫ phase (N selections).' with the long-tie
    collapsed branch and the trailing audience qualifier — a different
    English template from the gender-view 'led in the primary phase'
    shape, so a different Welsh one (D45 distinctness)."""
    noun_sg, g, rel_sg = RANK_NOUN_CY[f.get("noun", "sport")]
    pl, rel_pl = RANK_NOUN_PL_CY[f.get("noun", "sport")]
    bits = []
    for ph, ph_cy in (("primary", "yn yr ysgol gynradd"),
                      ("secondary", "yn yr ysgol uwchradd")):
        e = f.get(ph)
        if not e:
            continue
        n_items = len(e["labels"])
        cp = W.count_partitive(e["count"], "dewis", "dewisiadau")
        if n_items > 3:
            bits.append(f"Roedd {W.num_noun(n_items, noun_sg, g)} yn "
                        f"gyfartal ar y brig {ph_cy} ({cp} yr un)")
        elif n_items > 1:
            art = "yr" if W.is_vowel_initial(pl) else "y"
            bits.append(f"{joinlab(e['labels'])} oedd {art} {pl} {rel_pl} "
                        f"{ph_cy} ({cp})")
        else:
            bits.append(f"{joinlab(e['labels'])} oedd "
                        f"{W.with_article(noun_sg, g)} {rel_sg} "
                        f"{ph_cy} ({cp})")
    if not bits:
        return None
    return ". ".join(bits) + f", {c.among()}."


def r_gender_phase_enjoy(f, c):
    pr = f.get("primary"); se = f.get("secondary")
    if not pr and not se:
        return None
    bits = []
    if pr:
        bits.append(f"{numz(pr[0])} o’r {W.numerator(pr[1])} ({pr[2]}%) yn yr ysgol gynradd")
    if se:
        bits.append(f"{numz(se[0])} o’r {W.numerator(se[1])} ({se[2]}%) yn yr ysgol uwchradd")
    listed = W.join_list(bits, mutate_last=False)
    return (f"Ymhlith {c.bare()}, nododd {listed} eu bod yn mwynhau "
            f"chwaraeon mewn Gwersi Addysg Gorfforol ‘Llawer’.")


def r_year_leaders(f, c):
    by = f.get("by_leader", {})
    bits = []
    for lead, years in sorted(by.items(), key=lambda kv: -len(kv[1])):
        yrs = W.join_list([f"Mlwyddyn {y.split()[-1]}" for y in years],
                          mutate_last=False)
        bits.append(f"{label_cy(lead)} oedd ar y brig ym {yrs}")
    for y, labels, count in f.get("ties_struct") or []:
        each = f"{W.count_partitive(count, 'dewis', 'dewisiadau')} yr un"
        bits.append(f"ym Mlwyddyn {y}, roedd {joinlab(labels)} yn gyfartal "
                    f"({each})")
    if not bits:
        return None
    opener = ("O edrych ar bob grŵp blwyddyn yn yr ysgol gyfan"
              if (c.scope == "whole" and c.gender == "all")
              else f"O edrych ar bob grŵp blwyddyn ymhlith {c.bare()}")
    return f"{opener}, {'; '.join(bits)}."


def r_year_ties(f, c):
    bits = []
    for y, labels, count in f.get("ties_struct") or []:
        each = f"{W.count_partitive(count, 'dewis', 'dewisiadau')} yr un"
        bits.append(f"ym Mlwyddyn {y}, roedd {joinlab(labels)} yn gyfartal "
                    f"({each})")
    if not bits:
        return None
    t = "; ".join(bits)
    return f"{t[0].upper() + t[1:]}, ymhlith {c.bare()}."


def r_yg_setting_best(f, c):
    y, g, setting, n, p, b = f["best"]
    yr = y.split()[-1]
    gcy = "bechgyn" if g == "boy" else "merched"
    mewn = SETTING_MEWN[setting]
    return (f"Ymhlith y grwpiau sy’n ddigon mawr i’w hadrodd, y "
            f"cyfranogiad uchaf mewn un lleoliad {aud_scope_cy(c)} oedd "
            f"{gcy} ym Mlwyddyn {yr} {mewn}: {W.numerator(n)} "
            f"{W.of_base(b, 'disgybl')} ({p}%).")


def r_other_sports_note(f, c):
    ob = W.of_base(f["base"], c.aud("def_sg"), c.head_gender())
    qual = f" {c.qual}" if c.qual else ""
    return (f"Mae ‘Campau eraill’ yn cyfeirio at unrhyw gampau a ddewisodd "
            f"disgyblion o restr atodol o gampau os nad oedd eu camp wedi’i "
            f"chynnwys yn y brif restr ({W.numerator(f['count'])} {ob}"
            f"{qual}). Mae’r rhain wedi’u grwpio gyda’i gilydd "
            f"er hwylustod adrodd, ac fe’u hadroddir yn fanwl yn yr "
            f"atodiad.")


def r_listened_always(f, c):
    P = W.lexicon()["predicates"]
    if f["count"] == 0:
        if f["base"] == 1:      # v6: singleton antecedent — the n = 1 singular
            sg = P["P-03"]["cy"].replace("ar eu syniadau", "ar ei syniadau")
            return f"Ni ddywedodd {c.neg_subject(1)} {sg}."
        return f"Ni ddywedodd {c.neg_subject(f['base'])} {P['P-03']['cy']}."
    if f["count"] == 1:
        # D48: singular possessive (same surface for either sex)
        sg = P["P-03"]["cy"].replace("ar eu syniadau", "ar ei syniadau")
        return f"Dywedodd {c.of_the(1, f['base'])} {sg}."
    return (f"Dywedodd {c.of_the(f['count'], f['base'])} "
            f"{P['P-03']['cy']}.")


def r_group_excl_leader(f, c):
    l = f["leader"]
    lab = label_cy(l["labels"][0])
    excl = c.cohort.get("optionLabel", "") if c.cohort else ""
    ob = W.of_base(l["base"], c.aud("def_sg"), c.head_gender())
    if l["base"] == 1:
        qual = W.sg_qual(c.qual, c.gender)
        agent = f"gan yr {ob[4:]}{' ' + qual if qual else ''}"
    else:
        agent = (f"gan {W.numerator(l['count'], prep='gan')} {ob}"
                 f"{' ' + c.qual if c.qual else ''}")
    return (f"Ar wahân i {W.label_after_soft(excl)}, sy’n diffinio’r grŵp "
            f"a ddewiswyd, {lab} oedd y gamp a ddewiswyd amlaf, {agent}.")


def r_enjoy_group_next(f, c):
    cy_set = ENJOY_SETTING_CY.get(f["setting"], f["setting"])
    return (f"Ymhlith {c.bare()}, {cy_set} a gafodd y cyfrif ‘Llawer’ "
            f"nesaf-uchaf: {numz(f['count'])} o’r {W.numerator(f['base'])} a ymatebodd.")


def r_settings_group_next(f, c):
    labels = {"pe_lessons": "In PE or lesson time",
              "school_club": "In a school club",
              "community_club": "In a club outside of school",
              "somewhere_else": "Somewhere else"}
    nxt = SETTING_MEWN[f["next"]]
    n = f["count"]
    if n > 10:
        used = f"a ddefnyddiwyd gan {n} o ddisgyblion"
    else:
        used = f"{W.gyda_num(n, 'disgybl', 'disgyblion')} yn ei ddefnyddio"
    return (f"Ymhlith {c.bare()} ({W.num_noun(f['base'], 'disgybl')}), "
            f"{ail_np('lleoliad', cap=False)} mwyaf cyffredin oedd chwaraeon {nxt}, {used}.")


def r_h1_an_freq(f, c):
    club = "chwaraeon clwb"
    p = f.get("pct")
    par = f", neu {p}%," if p is not None else ""
    if f["count"] == 0:
        return (f"Ni chymerodd {c.neg_subject(f['base'], answered=False)} "
                f"ran mewn {club} o leiaf unwaith yr wythnos.")
    return (f"Cymerodd {c.of_the(f['count'], f['base'], answered=False)}"
            f"{par} ran mewn {club} o leiaf unwaith yr wythnos.")


def r_h1_an_leader(f, c):
    l = f["leader"]
    labs = joinlab(l["labels"])
    return (f"Ymhlith {c.bare()}, {_apart_cy(f)}{labs} a ddewiswyd amlaf "
            f"({W.count_partitive(l['count'], 'dewis', 'dewisiadau')}).")


def r_h1_an_leader_tie(f, c):
    l = f["leader"]
    n = f.get("tie_n", len(l.get("labels", [])))
    excl = c.cohort.get("optionLabel", "") if c.cohort else ""
    each = W.count_partitive(l["count"], "dewis", "dewisiadau")
    return (f"Ymhlith {c.bare()}, {_apart_cy(f)}roedd "
            f"{W.num_noun(n, 'camp', 'f')} yn gyfartal "
            f"fel y rhai a ddewiswyd amlaf ({each} yr "
            f"un); dangosir pob un yn y siart campau presennol.")


def _apart_cy(f, cap=False):
    """The 'apart from ⟪defining answer⟫' role of an h1 summary (D44):
    driven by the fact record, not by the presence of any cohort."""
    if not f.get("apart"):
        return ""
    t = f"ar wahân i {W.label_after_soft(f['apart'])}, "
    return t[0].upper() + t[1:] if cap else t


def r_h1_an_gender_leaders(f, c):
    b = f["boys"]; g = f["girls"]
    return (f"{_apart_cy(f, cap=True)}{joinlab(b['labels'])} oedd ar y "
            f"brig ymhlith bechgyn a "
            f"{W.soft_phrase(joinlab(g['labels']))} ymhlith merched, "
            f"{aud_scope_cy(c)}.")


H1_ENJOY_CY = {
    "enjoy_pe": "mewn Gwersi Addysg Gorfforol",
    "enjoy_school_clubs": "mewn Clybiau Chwaraeon Ysgol",
}
H1_CONF_CY = {
    "confidence_try_new": "i roi cynnig ar gamp newydd",
    "confidence_learn_skill": "i ddysgu sgil newydd",
}


def r_h1_en_enjoy_conf(f, c):
    """The enjoyment setting and confidence measure are roles (D44): the
    English varies them when the view was selected from one of the
    charts, and the Welsh must vary with it."""
    ep = H1_ENJOY_CY[f.get("ep_mid", "enjoy_pe")]
    ct = H1_CONF_CY[f.get("ct_mid", "confidence_try_new")]
    if f["enjoy"] == 0:
        first = (f"nid oes yr un o’r {W.numerator(f['enjoy_base'])} yn "
                 f"mwynhau chwaraeon {ep} ‘Llawer’")
    else:
        first = (f"mae {W.numerator(f['enjoy'])} o’r "
                 f"{W.numerator(f['enjoy_base'])} "
                 f"yn mwynhau chwaraeon {ep} ‘Llawer’")
    if f["conf"] == 0:
        second = (f"nid oes yr un o’r {W.numerator(f['conf_base'])} yn "
                  f"hyderus iawn neu’n eithaf hyderus {ct}")
    else:
        second = (f"mae {W.numerator(f['conf'])} o’r "
                  f"{W.numerator(f['conf_base'])} yn hyderus iawn neu’n "
                  f"eithaf hyderus {ct}")
    conj, second = W.conj_and(second)
    return f"Ymhlith {c.bare()}, {first}, {conj} {second}."


def r_h1_en_listened(f, c):
    if f["count"] == 0:
        return (f"Nid yw’r un o’r {W.numerator(f['base'])} a ymatebodd yn teimlo bod "
                f"pobl yn gwrando ar eu syniadau am chwaraeon bob amser "
                f"neu weithiau, {c.among()}.")
    return (f"Mae {W.numerator(f['count'])} o’r {W.numerator(f['base'])} a ymatebodd "
            f"yn teimlo bod pobl yn gwrando ar eu syniadau am chwaraeon "
            f"bob amser neu weithiau, {c.among()}.")


def r_h1_ev_disability(f, c):
    if f["count"] == 0:
        return (f"Ni nododd yr un o’r {W.numerator(f['base'])} a ymatebodd anabledd na "
                f"{W.aspirate_phrase(W.term('long-term condition'))}, {c.among()}.")
    return (f"Nododd {W.numerator(f['count'])} o’r {W.numerator(f['base'])} a ymatebodd "
            f"anabledd neu {W.soft_phrase(W.term('long-term condition'))}, {c.among()}.")


def r_h1_ev_join(f, c):
    P = W.lexicon()["predicates"]
    if f["count"] == 0:
        # D55 (v1.8): the PR-02 recast applies to EVERY surface that
        # produces the construction — the closing summary included
        if (f.get("code_labels")
                and W.pr("PR-02 (status)",
                         "answer_selection_recast_all_surfaces")):
            return _zero_recast(f, c, c.neg_subject(f["base"],
                                                    answered=False))
        if f["base"] == 1:      # v6: singleton antecedent — the sg predicate
            sg = pred_cy("join_in_easily", ("never", "not_often"), "sg")
            return f"Ni ddywedodd {c.neg_subject(1, answered=False)} {sg}."
        return (f"Ni ddywedodd {c.neg_subject(f['base'], answered=False)} "
                f"{P['P-01']['cy']}.")
    if f["count"] == 1 and f["base"] == 1:
        # v6 (AGR-verb at a real school): 'yr unig ferch …' is a singleton
        # antecedent — the singular predicate the e2 module already uses.
        # A one-of-N count ('un o’r 20 disgybl … nad ydynt') is left as the
        # V4.15 corpus attests it and is listed for the translator (sheet 63).
        sg = pred_cy("join_in_easily", ("never", "not_often"), "sg")
        return f"Dywedodd {c.of_the(1, 1, answered=False)} {sg}."
    return (f"Dywedodd {c.of_the(f['count'], f['base'], answered=False)} "
            f"{P['P-01']['cy']}.")


def r_h1_ev_listened(f, c):
    if f["count"] == 0:
        poss = "ei" if f["base"] == 1 else "eu"   # v6: singleton antecedent
        return (f"Nid yw’r {c.neg_subject(f['base'], answered=False)[3:]} yn "
                f"teimlo bod pobl yn gwrando ar {poss} syniadau am chwaraeon "
                f"bob amser neu weithiau.")
    poss = "ei" if (f["count"] == 1 and f["base"] == 1) else "eu"   # v6: singleton antecedent
    return (f"Mae {c.of_the(f['count'], f['base'], answered=False)} yn "
            f"teimlo bod pobl yn "
            f"gwrando ar {poss} syniadau am chwaraeon bob amser neu weithiau.")


def r_h1_ll_barrier(f, c):
    l = f["leader"]
    lab = q(label_cy(l["labels"][0], form="cy"))
    aside = (" — ar wahân i’r amod sy’n diffinio’r grŵp a ddewiswyd —"
             if f.get("aside") else "")
    return (f"Yr amod a ddewiswyd amlaf{aside} fel un a fyddai’n helpu "
            f"{c.bare()} "
            f"i wneud mwy o chwaraeon oedd {lab} "
            f"({W.numerator(l['count'])} o’r {W.numerator(l['base'])}).")


def r_h1_ll_demand(f, c):
    """h1 lifelong summary: apart-role + the same list-collapse rule the
    English applies (D42 — '4 sports jointly' stays a count)."""
    d = f["demand"]; u = f["unmet"]
    dn = W.count_partitive(d["count"], "dewis", "dewisiadau")
    d_tie = f.get("demand_tie_n", len(d["labels"]))
    u_tie = f.get("unmet_tie_n", len(u["labels"]))
    d_txt = (W.soft_phrase(joinlab(d["labels"])) if d_tie <= 3
             else W.soft_phrase(W.num_noun(d_tie, "camp", "f") + " ar y cyd"))
    u_txt = (joinlab(u["labels"]) if u_tie <= 3
             else W.num_noun(u_tie, "camp", "f") + " ar y cyd")
    return (f"Ymhlith {c.bare()}, {_apart_cy(f)}roedd y galw cryfaf am "
            f"{d_txt} ({dn}), "
            f"tra mai {u_txt} a ddangosodd y "
            f"galw mwyaf heb ei fodloni ({u['count']}).")


def r_h2_unmet(f, c):
    """Sheet 38: variable discussion prompt — unmet-demand interest."""
    l = f["leader"]
    lab = label_cy(l["labels"][0])
    n = l["count"]
    if n == 1:
        subj = "un o’r disgyblion"
    elif n > 10:
        subj = f"{n} o ddisgyblion"
    else:
        subj = W.count_partitive(n, "disgybl", "disgyblion")
    return (f"Dewisodd {subj} {W.label_after_soft(l['labels'][0])} "
            f"fel rhywbeth yr hoffent wneud mwy ohono ond nad ydynt yn ei "
            f"wneud ar hyn o bryd, {c.among()}. A yw’r cyfleoedd presennol "
            f"yn adlewyrchu’r diddordeb hwn?")


def r_h2_join(f, c):
    """Sheet 38: variable discussion prompt — joining-in difficulty."""
    n = f["count"]
    if n == 1:
        return ("Dywedodd un disgybl yn y golwg hwn nad yw’n aml, neu "
                "byth, yn ei chael hi’n hawdd ymuno. Beth fyddai’n helpu’r "
                "disgybl hwn i gymryd rhan?")
    return (f"Dywedodd {W.count_partitive(n, 'disgybl', 'disgyblion')} yn "
            f"y golwg hwn nad ydynt yn aml, neu byth, yn ei chael hi’n "
            f"hawdd ymuno. Beth fyddai’n eu helpu i gymryd rhan?")


def r_an_synthesis(f, c):
    return None   # module removed from the visible report (summary only)


# ---------------------------------------------------------------- dispatch
def render(tid, facts, key, module, cohorts):
    if "+" in tid:
        parts = [render(t, facts, key, module, cohorts)
                 for t in tid.split("+")]
        if any(p is None for p in parts):
            return None
        return " ".join(parts)
    c = Ctx(key, cohorts)
    f = dict(facts or {})
    f["_tid"] = tid
    R = {
        "leader_single_v2": lambda: r_leader_single(f, c),
        "combined_v2": lambda: r_combined(f, c),
        "combined_nopct_v2": lambda: r_combined(f, c),
        "combined_base1_v41": lambda: r_combined_base1(f, c),
        "setting_participation_v2": lambda: r_setting_participation(f, c),
        "settings_rank_v2": lambda: r_settings_rank(f, c),
        "group_settings_rank_v10": lambda: r_group_settings_rank(f, c, module),
        "leader_multi_v2": lambda: r_leader_multi(f, c),
        "runner_v2": lambda: r_runner(f, c),
        "runner_joint_v2": lambda: r_runner_joint(f, c),
        "runner_many_v2": lambda: r_runner_many(f, c),
        "tie2_multi_v2": lambda: r_tie_multi(f, c),
        "tie3_multi_v2": lambda: r_tie_multi(f, c),
        "tie4plus_multi_v2": lambda: r_tie4plus(f, c),
        "tie_single_v2": lambda: r_tie_single(f, c),
        "no_responses_v2": lambda: r_no_responses(f, c),
        "parent_compare_v2": lambda: r_parent_compare(f, c, cohorts),
        "group_defined_v2": lambda: r_group_defined(f, c),
        "avg_sports_v11": lambda: r_avg_sports(f, c),
        "avg_sports_setting_v11": lambda: r_avg_sports(
            f, c, setting=f.get("setting")),
        "group_avg_sports_v11": lambda: r_avg_sports(
            f, c, group_cy="disgyblion a nododd anabledd a/neu anhawster "
            "dysgu" + _group_tail(c)),
        "overall_top3_v13": lambda: r_top3(f, c),
        "setting_top3_v13": lambda: r_top3(f, c, setting=f.get("setting")),
        "f2_year_line_v12": lambda: r_f2_year_line(f, c),
        "club_weekly_3plus_v13": lambda: r_club_weekly_3plus(f, c),
        "pe_feelings_composite_v2": lambda: r_pe_feelings(f, c),
        "enjoy_settings_v2": lambda: r_enjoy_settings(f, c),
        "enjoy_low_setting_v2": lambda: r_enjoy_low_setting(f, c),
        "enjoy_year_extremes_v2": lambda: r_enjoy_year_extremes(f, c),
        "age_setting_extremes_v10": lambda: r_age_setting_extremes(f, c),
        "confidence_dims_v5": lambda: r_confidence_dims(f, c),
        "confidence_dims_low_v5": lambda: r_confidence_dims_low(f, c),
        "confidence_joint_hi_v3": lambda: r_confidence_joint_hi(f, c),
        "confidence_equal_v3": lambda: r_confidence_equal(f, c),
        "low_confidence_v2": lambda: r_low_confidence(f, c),
        "unmet_leader_v11": lambda: r_unmet_leader(f, c),
        "unmet_runner_v11": lambda: r_unmet_runner(f, c),
        "unmet_base1_v12": lambda: r_unmet_base1(f, c),
        "current_vs_demand_v41": lambda: r_current_vs_demand(f, c),
        "gender_leader_pair_v2": lambda: r_gender_leader_pair(f, c),
        "rank_diff_v2": lambda: r_rank_diff(f, c),
        "gender_count_compare_v2": lambda: r_gender_count_compare(f, c),
        "gender_pct_compare_v2": lambda: r_gender_pct_compare(f, c),
        "take_part_prose_v3": lambda: r_take_part_prose(f, c),
        "welsh_when_playing_v10": lambda: r_welsh_when_playing(f, c),
        "dl_combined_note_v11": lambda: r_dl_combined_note(f, c),
        "no_additional_conf_v2": lambda: r_no_additional_conf(f, c),
        "not_enough_group_v2": lambda: r_not_enough_group(f, c),
        "barrier_leader_v41": lambda: r_barrier_leader(f, c),
        "barrier_runner_v41": lambda: r_barrier_runner(f, c),
        "barrier_none_v41": lambda: r_barrier_none(f, c),
        "barrier_base1_v5": lambda: r_barrier_base1(f, c),
        "important_leader_v5": lambda: r_important_leader(f, c),
        "important_runner_v5": lambda: r_important_runner(f, c),
        "important_gender_leader_v5": lambda: r_important_gender_leader(f, c),
        "important_base1_v5": lambda: r_important_base1(f, c),
        "conf_base1_v41": lambda: r_conf_base1(f, c),
        "group_sibling_skill_v2": lambda: r_group_sibling(
            f, c, "learning a new skill"),
        "group_sibling_trynew_v12": lambda: r_group_sibling(
            f, c, "trying a new sport"),
        "group_sibling_conf_v2": lambda: r_group_sibling_conf(f, c),
        "group_codemand_top3_v12": lambda: r_group_codemand_top3(f, c),
        "wd_current_check_v3": lambda: r_wd_current_check(f, c),
        "li_join_cross_v3": lambda: r_li_join_cross(f, c),
        "cross_insight_v2": lambda: r_cross_insight(f, c, cohorts),
        "rank_parent_same_v41": lambda: r_rank_parent_same(f, c),
        "rank_parent_diff_v41": lambda: r_rank_parent_diff(f, c),
        "rank_parent_joint_v41": lambda: r_rank_parent_joint(f, c),
        "phase_leaders_v2": lambda: r_phase_top(f, c),
        "gender_phase_demand_v2": lambda: r_phase_leaders(f, c),
        "gender_phase_leaders_v2": lambda: r_phase_leaders(f, c),
        "gender_phase_enjoy_v2": lambda: r_gender_phase_enjoy(f, c),
        "year_leaders_v2": lambda: r_year_leaders(f, c),
        "year_ties_v13": lambda: r_year_ties(f, c),
        "yg_setting_best_v11": lambda: r_yg_setting_best(f, c),
        "other_sports_note_v13": lambda: r_other_sports_note(f, c),
        "listened_always_v11": lambda: r_listened_always(f, c),
        "group_excl_leader_v2": lambda: r_group_excl_leader(f, c),
        "enjoy_group_next_v41": lambda: r_enjoy_group_next(f, c),
        "settings_group_next_v41": lambda: r_settings_group_next(f, c),
        "h1_an_freq_v3": lambda: r_h1_an_freq(f, c),
        "h1_an_leader_v3": lambda: r_h1_an_leader(f, c),
        "h1_an_leader_tie_v41": lambda: r_h1_an_leader_tie(f, c),
        "h1_an_gender_leaders_v3": lambda: r_h1_an_gender_leaders(f, c),
        "h1_en_enjoy_conf_v3": lambda: r_h1_en_enjoy_conf(f, c),
        "h1_en_listened_v3": lambda: r_h1_en_listened(f, c),
        "h1_ev_disability_v3": lambda: r_h1_ev_disability(f, c),
        "h1_ev_join_v3": lambda: r_h1_ev_join(f, c),
        "h1_ev_listened_v3": lambda: r_h1_ev_listened(f, c),
        "h1_ll_barrier_v3": lambda: r_h1_ll_barrier(f, c),
        "h1_ll_demand_v41": lambda: r_h1_ll_demand(f, c),
        "h2_unmet_prompt_v44": lambda: r_h2_unmet(f, c),
        "h2_join_prompt_v44": lambda: r_h2_join(f, c),
        "cross_insight_v2+": lambda: None,
    }
    fn = R.get(tid)
    if fn is None:
        W._MISSES.add(("tid", tid))
        return None
    try:
        out = fn()
    except Exception as e:                      # noqa: BLE001
        W._MISSES.add(("render_error", tid, str(e)[:80]))
        return None
    # D21: prose labels are case-folded, so a sentence can begin with a
    # lower-case label; normal sentence capitalisation applies at the
    # sentence boundary (after all mutation decisions are made)
    if out and out[:1].islower():
        out = out[0].upper() + out[1:]
    if out:
        out = re.sub(r"(\. )([a-zàâêîôûŵŷáéíóú])",
                     lambda m: m.group(1) + m.group(2).upper(), out)
    return out
