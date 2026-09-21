# -*- coding: utf-8 -*-
"""Framework v2.7 — the translator's rulings of 21 Sep 2026 (handover
sheets 1–5) as executable expectations against the built lexicon."""
from pipeline import welsh as W
from pipeline import welsh_render as R


def test_ail_lenites_its_noun_D85():
    # sheet 4 rule 16 WRONG → "Yr ail gamp"; sheet 5 #34
    assert R.ail_np("camp") == "Yr ail gamp"
    assert R.ail_np("camp neu weithgaredd") == "Yr ail gamp neu weithgaredd"
    assert R.ail_np("lleoliad", cap=False) == "yr ail leoliad"
    assert R.ail_np("ateb") == "Yr ail ateb"
    assert R.ail_np("opsiwn") == "Yr ail opsiwn"


def test_label_grids_D32_v27():
    # confidence chips / charts quote the confidence question's own option
    assert R.label_cy("Not at all", "conf", form="cy") == "Ddim yn hyderus o gwbl"
    # enjoyment and PE-feel keep the survey's "Dim o gwbl"
    assert R.label_cy("Not at all", None, form="cy") == "Dim o gwbl"
    assert R.label_cy("Not at all", "pe", form="cy") == "Dim o gwbl"
    # the pre-v2.7 two-branch cell still resolves as before
    assert R.label_cy("Not very", "conf", form="cy") == "Ddim yn hyderus iawn"
    assert R.label_cy("Not very", "pe", form="cy") == "Dim llawer"
    assert R.label_cy("Not very", None, form="cy") == "Ddim yn hyderus iawn"
    # take-part "Other" is the survey option; every other "Other" stays "Arall"
    assert R.label_cy("Other", "tp", form="cy") == "Arall, rho fanylion"
    assert R.label_cy("Other", None, form="cy") == "Arall"
    # the code alias is gone: the survey's option (sheet 23 row added v2.7)
    assert R.label_cy("I don’t know", form="cy") == "Dydw i ddim yn gwybod"


def test_cohort_chips_from_sheet58():
    assert R.cohort_label_cy("ct_not_at_all", {"metric": "confidence_try_new", "code": "not_at_all",
                                                "optionLabel": "Not at all"}) == \
        "Hyder i roi cynnig ar gamp newydd: Ddim yn hyderus o gwbl"
    assert R.cohort_label_cy("ep_not_at_all", {"metric": "enjoy_pe", "code": "not_at_all",
                                                "optionLabel": "Not at all"}) == \
        "Yn Mwynhau Addysg Gorfforol: Dim o gwbl"
    assert R.cohort_label_cy("tp_other", {"metric": "take_part_method", "code": "other",
                                           "optionLabel": "Other"}) == "Cymryd rhan: Arall, rho fanylion"
    assert R.cohort_label_cy("dy_yes", {"metric": "disability_condition", "code": "yes",
                                         "optionLabel": "Yes"}) == "Anabledd neu gyflwr hirdymor: Oes"
    # PR-11: the derived set stays NAMED (AW-3 comment, rows 47–48)
    assert R.cohort_label_cy("ed_yes", {"metric": "ed_combined", "code": "yes",
                                         "optionLabel": "Yes"}) == "Cefndir ethnig amrywiol"
    assert R.SEX_CY["all"] == "Pob Ymatebwr"              # the filter option (2b row 2)
    assert R.BANNER_SEX_CY["all"] == "Pob disgybl"        # the banner's "All pupils"
    assert R.scope_short_cy("whole", "all", "none", {}) == "Yr ysgol gyfan · Pob disgybl"


def test_long_term_condition_term_D86():
    assert W.term("long-term condition") == "cyflwr hirdymor"
    assert R.group_mid_cy("settings_dy") == "disgybl a nododd anabledd neu gyflwr hirdymor"
    assert R.group_mid_cy("settings_ed") == "disgybl sy’n dod o gefndir ethnig amrywiol"
    assert "tymor hir" not in __import__("json").dumps(W.lexicon(), ensure_ascii=False)
