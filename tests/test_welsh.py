# -*- coding: utf-8 -*-
"""Acceptance tests for the Welsh grammar engine, transcribed from the
Welsh Generation Framework v1.5 sheet '26 Test matrix'. Each test cites
its T-number."""
from pipeline import welsh as W


# --------------------------------------------------------------- article
def test_T001_article_fem_sg():
    assert W.with_article("camp", "f") == "y gamp"


def test_T002_article_fem_plural():
    assert W.with_article("merched", "f", plural=True) == "y merched"


def test_T003_article_rh():
    assert W.with_article("rhaw", "f") == "y rhaw"


def test_T004_article_vowel():
    assert W.with_article("ysgol", "f") == "yr ysgol"


def test_T005_article_after_vowel_final():
    assert W.article("12", prev_word="o") == "'r"


def test_T039_gem_never_mutates():
    assert W.with_article("gêm", "f") == "y gêm"


# --------------------------------------------------------------- numerals
def test_T007_un_fem():
    assert W.num_with_noun(1, "camp", "f") == "un gamp"


def test_T008_un_masc():
    assert W.num_with_noun(1, "disgybl", "m") == "un disgybl"


def test_T011_tair_camp():
    assert W.num_with_noun(3, "camp", "f") == "tair camp"


def test_T012_dwy_gamp():
    assert W.num_with_noun(2, "camp", "f") == "dwy gamp"


def test_T013_tri_chant():
    assert W.num_with_noun(3, "cant", "m") == "tri chant"


def test_T014_tair_merch():
    assert W.num_with_noun(3, "merch", "f") == "tair merch"


def test_T015_chwe_champ():
    assert W.num_with_noun(6, "camp", "f") == "chwe champ"


def test_T016_saith_disgybl():
    assert W.num_with_noun(7, "disgybl", "m") == "saith disgybl"


def test_T017_saith_diwrnod():
    assert W.num_with_noun(7, "diwrnod", "m") == "saith diwrnod"


def test_T006_partitive():
    assert W.partitive(12, "disgyblion") == "12 o ddisgyblion"


def test_partitive_bechgyn():
    assert W.partitive(43, "bechgyn") == "43 o fechgyn"


def test_T070_percent():
    assert W.pct(42) == "42%"


# --------------------------------------------------------------- ordinals
def test_T071_ordinal_fem():
    assert W.ordinal(3, "f", with_article=False) == "drydedd"
    assert W.ordinal(3, "f") + " " + W.soft("camp") == "y drydedd gamp"


def test_T072_ordinal_masc():
    assert W.ordinal(3, "m") == "y trydydd"


def test_T073_ordinal_articles():
    assert W.ordinal(2, "m") == "yr ail"
    assert W.ordinal(8, "m") == "yr wythfed"
    assert W.ordinal(5, "m") == "y pumed"


# ------------------------------------------------------------ conjunctions
def test_T022_a_aspirate():
    conj, item = W.conj_and("Criced")
    assert (conj, item) == ("a", "Chriced")


def test_T023_ac_vowel():
    conj, item = W.conj_and("Athletau")
    assert (conj, item) == ("ac", "Athletau")


def test_T024_a_before_h():
    conj, item = W.conj_and("Hwylio")
    assert (conj, item) == ("a", "Hwylio")


def _with_conj06(mode):
    """Run with sheet 11 CONJ-06 MODE=<mode> in the loaded lexicon."""
    import contextlib

    @contextlib.contextmanager
    def cm():
        lex = W.lexicon()
        old = lex.get("conj06_mode")
        lex["conj06_mode"] = mode
        try:
            yield
        finally:
            lex["conj06_mode"] = old
    return cm()


def test_T025_figure_rule_is_the_workbook_mode():
    # v2.7 (D84, the translator's ruling 21 Sep 2026): the workbook says
    # MODE=figure — a figure written in digits takes 'a' and never mutates
    assert W.conj06_mode() == "figure"
    assert W.conj_and("11")[0] == "a"
    assert W.conj_and("36")[0] == "a"
    assert W.conj_and("8")[0] == "a"
    assert W.article("11") == "y" and W.article("8") == "y"
    assert W.conj_and("un")[0] == "ac"          # words keep CONJ-01


def test_T025_vigesimal_reading_still_available():
    with _with_conj06("vigesimal"):
        assert W.conj_and("11")[0] == "ac"      # un ar ddeg
        assert W.conj_and("21")[0] == "ac"      # un ar hugain
        assert W.conj_and("12")[0] == "a"       # deuddeg
        assert W.conj_and("36")[0] == "ac"      # un ar bymtheg ar hugain
        assert W.article("11") == "yr"


def test_T025_decimal_reading_available():
    with _with_conj06("decimal"):
        assert W.conj_and("11")[0] == "ac"      # un deg un
        assert W.conj_and("36")[0] == "a"       # tri deg chwech
        assert W.conj_and("8")[0] == "ac"       # wyth
        assert W.conj_and("80")[0] == "ac"      # wyth deg
        assert W.conj_and("100")[0] == "a"      # cant
        assert W.conj_and("1000")[0] == "a"     # mil


def test_T028_list_arity3():
    out = W.join_list(["Tennis (52)", "Athletau (47)", "Pêl Rwyd (46)"])
    assert out == "Tennis (52), Athletau (47) a Phêl Rwyd (46)"


def test_T029_neu_immutable_l():
    assert W.conj_neu("loncian") == "neu loncian"


def test_T030_neu_soft():
    assert W.conj_neu("Caiacio") == "neu Gaiacio"


# --------------------------------------------------------------- mutations
def test_soft_g_deletion():
    assert W.soft("gwers") == "wers"


def test_soft_ll_exempt_after_article():
    assert W.with_article("llaw", "f") == "y llaw"


def test_nasal_blwyddyn():
    assert W.nasal("Blwyddyn") == "Mlwyddyn"


def test_T019_year_locative():
    assert W.year_loc("Year 8") == "ym Mlwyddyn 8"


def test_T037_unadapted_no_mutation():
    assert W.label_after_soft("BMX") == "BMX"


def test_T038_golff():
    assert W.soft("golff") == "golff"


# --------------------------------------------------------------- audiences
def test_audience_year8_pupils():
    assert W.audience("y8", "all", "bare") == "disgyblion ym Mlwyddyn 8"
    assert W.audience("y8", "all", "def_sg") == "disgybl ym Mlwyddyn 8"


def test_audience_whole_school_girls():
    assert W.audience("whole", "girl", "after_o") == "o ferched yn yr ysgol gyfan"


def test_T068_holl_parent():
    assert W.audience("y8", "all", "holl") == "yr holl ddisgyblion ym Mlwyddyn 8"


# --------------------------------------------------------------- qualifiers
def test_T032_subject_relative_sp():
    # v1.7 D21/PR-10 supersedes the sheet-26 golden surface: running prose
    # takes the case-folded prose form ('tennis'), unadapted so unmutated.
    # Sheet 26 was not updated for D21 — recorded for the linguist.
    cy = W.qualifier_cy("sp", "selected Tennis", answer_label="Tennis")
    assert cy == "a ddewisodd tennis"


def test_sp_football_object_mutation():
    # D21: case fold BEFORE mutation — pêl droed -> bêl droed (was
    # 'Bêl Droed' under the v1.5 title-case reading of T-035)
    cy = W.qualifier_cy("sp", "selected Football", answer_label="Football")
    assert cy is not None and "bêl droed" in cy


def test_T040_sydd_relative_ws():
    cy = W.qualifier_cy(
        "ws", "speak Welsh very well, a fair amount or a little")
    assert cy is not None and cy.startswith("sy’n siarad Cymraeg")


def test_T042_negative_relative_wl():
    cy = W.qualifier_cy("wl", "said they do not speak Welsh")
    assert cy == "a ddywedodd nad ydynt yn siarad Cymraeg"


def test_T041_imperfect_relative_ov():
    cy = W.qualifier_cy(
        "ov", "were active through sport an estimated three times a week")
    assert cy == "a oedd yn actif drwy chwaraeon tua theirgwaith yr wythnos"


def test_T044_coordinated_relative_gl():
    cy = W.qualifier_cy(
        "gl", "reported a learning difficulty and did sport in a school club")
    assert cy == ("a nododd anhawster dysgu ac a gymerodd ran mewn "
                  "chwaraeon mewn clwb ysgol")


def test_T047_oblique_relative_dy():
    cy = W.qualifier_cy(
        "dy",
        "preferred not to say whether they have a disability or long-term condition")
    assert cy is not None and cy.startswith("y byddai’n well ganddynt")


# --------------------------------------------------------------- labels
def test_label_lookup():
    assert W.label_cy("Archery") == "Saethyddiaeth"


def test_T075e_frequency_label():
    assert W.label_cy("1 time a week") == "1 waith yr wythnos"
    assert W.label_cy("2 times a week") == "2 waith yr wythnos"
    assert W.label_cy("3 times a week") == "3 gwaith yr wythnos"


# ---------------------------------------------- v1.6 additions (T-082..088)
from pipeline import welsh_render as WR


def _r(tid, facts, key="whole|all|none", module="e2"):
    return WR.render(tid, facts, key, module, {})


def test_T082_zero_branch_ft01():
    cy = _r("combined_nopct_v2",
            {"count": 0, "base": 6, "metric": "join_in_easily",
             "codes": ["not_often", "never"]})
    assert cy is not None and cy.startswith("Ni ddywedodd yr un o’r chwe disgybl")
    assert "0" not in cy


def test_T083_first_ordinal_postposed():
    assert WR._ord_np(1, "camp", "f") == "y gamp gyntaf"
    assert WR._ord_np(3, "camp", "f") == "y drydedd gamp"
    assert WR._ord_np(2, "lleoliad", "m") == "yr ail leoliad"


def test_T084_plural_tie_ft18():
    # v1.6 plural branch; the numeral is worded per D40/D03 (the sheet-26
    # row shows 'gyda 5 disgybl', which its own gate G3a would flag —
    # recorded deviation, referred to the linguist)
    cy = _r("important_runner_v5",
            {"runner": {"labels": ["Having fun", "Being with friends"],
                        "count": 5}, "tie_n": 2}, module="f6")
    assert "yn gyfartal fel yr ail opsiynau mwyaf cyffredin" in cy
    assert "gyda phum disgybl yr un" in cy
    assert "yn ei ddewis" not in cy


def test_T085_list_collapse_ft24():
    labs = [f"Sport{i}" for i in range(33)]
    cy = _r("current_vs_demand_v41",
            {"unmet": {"labels": labs, "count": 1},
             "current": {"labels": ["Cricket"], "count": 6},
             "unmet_tie_n": 33, "current_tie_n": 1})
    assert cy.startswith("Roedd 33 camp ar y cyd â’r galw mwyaf heb ei fodloni")
    # v1.7: '(un dewis)' — worded per D40, and the pupil noun is avoided
    # beside a plural cohort qualifier (G9b co-occurrence rule);
    # sheet 26 shows '(1 disgybl)' — recorded deviation for the linguist
    assert "(un dewis)" in cy


def test_T086_quotation_pair_ft05():
    cy = _r("pe_feelings_composite_v2",
            {"values": {"healthy": (312, 366), "confident": (274,),
                        "ready to learn": (280,)}}, module="f3f5")
    assert "‘iach iawn’" in cy and "’iach" not in cy.replace("neu’n", "")


def test_T087_definite_dual():
    from pipeline import welsh as W
    assert W.def_num_noun(2, "camp", "f") == "ddwy gamp"
    assert W.def_num_noun(2, "lleoliad", "m") == "ddau leoliad"


def test_T088_girl_singular_complement():
    # v1.8 D56 supersedes both earlier surfaces: behind a one-person base
    # NOTHING downstream may be plural or partitive, so the item is a
    # subject-elided singular clause ('nododd gymryd rhan yn sefyll'),
    # the base reads 'yr unig ddisgybl', and no pronoun is defaulted
    # (PR-03). Recorded deviation from sheet 26's T-088 for the linguist.
    cy = _r("take_part_prose_v3",
            {"pairs": [("standing", 1)], "base": 1}, key="whole|girl|none",
            module="e7")
    assert "unig ferch" in cy               # audience noun, soft after unig
    assert "nododd gymryd rhan yn sefyll" in cy
    assert "ohonynt" not in cy and "iddynt" not in cy
    assert "sut y mae fel arfer" in cy      # D48: singular frame


# ------------------------------------------- V6.0 production pilot review (23 Sep 2026)
def test_A03_immutable_labels_never_mutate_on_any_path():
    """PR-05 / EX-04 (unadapted loans) and EX-01..03 (recent g- borrowings):
    the sheet-23 'Mutable? NO' flag holds after a label has been joined into a
    list or a counted phrase — the pilot's 'a Pharkour', 'mwy o Barkour',
    'am Fadminton', 'am ymnasteg', 'a Thriathlon', 'mwy o FMX', 'am olff,'."""
    heads = W.immutable_heads()
    for h in ("parkour", "badminton", "boccia", "bmx", "triathlon", "gymnasteg", "golff"):
        assert h in heads
    assert "pêl" not in heads and "tennis" not in heads      # adapted labels still mutate
    assert W.soft_phrase("Parkour (44), trampolinio (44) a phêl osgoi (40)").startswith("Parkour (44)")
    assert W.soft_phrase("golff, pŵl neu snwcer") == "golff, pŵl neu snwcer"
    assert W.soft_phrase("gymnasteg") == "gymnasteg" and W.soft_phrase("BMX (3)") == "BMX (3)"
    assert W.soft_phrase("Badminton") == "Badminton" and W.soft_phrase("pêl droed") == "bêl droed"
    assert W.join_list(["criced", "Parkour"]) == "criced a Parkour"
    assert W.join_list(["athletau", "pêl fasged", "Triathlon"]) == "athletau, pêl fasged a Triathlon"
    assert W.join_list(["nofio", "pêl droed"]) == "nofio a phêl droed"      # CONJ-04 still applies
    assert W.aspirate_phrase("tennis") == "thennis"
    assert W.label_after_soft("Badminton") == "Badminton" and W.label_after_soft("Football") == "bêl droed"


def test_A02_runner_adjective_agrees_with_feminine_head():
    """ADJ-02 / ADJ-07: 'Yr ail gamp FWYAF cyffredin' (feminine singular
    head); masculine heads unmutated (ADJ-11: 'Yr ail opsiwn mwyaf cyffredin');
    the coordinated 'camp neu weithgaredd' agrees with the nearer, masculine
    conjunct (PR-06)."""
    cy = _r("runner_v2", {"runner": {"labels": ["Football"], "count": 37}, "noun": "sport"}, module="f10")
    assert cy.startswith("Yr ail gamp fwyaf cyffredin oedd pêl droed")
    cy = _r("runner_v2", {"runner": {"labels": ["Swimming"], "count": 5}, "noun": "sport or activity"}, module="f10")
    assert cy.startswith("Yr ail gamp neu weithgaredd mwyaf cyffredin oedd nofio")
    cy = _r("runner_v2", {"runner": {"labels": ["Having fun"], "count": 5}, "noun": "option"}, module="f6")
    assert cy.startswith("Yr ail opsiwn mwyaf cyffredin")


def test_A03_gender_leaders_take_the_conjunction_service():
    """CONJ-01..05: after 'a' the girls' leader takes a/ac and the ASPIRATE
    mutation — never the soft mutation ('a bêl droed', 'a Fadminton')."""
    def g(lbl):
        return _r("h1_an_gender_leaders_v3", {"boys": {"labels": ["Football"], "count": 30},
                                              "girls": {"labels": [lbl], "count": 20}, "apart": None}, module="h1")
    assert "ymhlith bechgyn a Badminton ymhlith merched" in g("Badminton")
    assert "ymhlith bechgyn a phêl rwyd ymhlith merched" in g("Netball")
    assert "ymhlith bechgyn ac athletau ymhlith merched" in g("Athletics")
    assert "ymhlith bechgyn a rhedeg neu loncian ymhlith merched" in g("Running or jogging")
    assert "ymhlith bechgyn a nofio ymhlith merched" in g("Swimming")


def test_T035_object_of_dewisodd_mutates_in_the_f10_cohort_sentence():
    """T-035: 'a ddewisodd bêl droed' — as the sheet-22 qualifier of the same
    cohort already reads; unadapted names stay put (PR-05)."""
    cohorts = {"wd_football": {"metric": "sports_wanted", "code": "football", "optionLabel": "Football"},
               "wd_badminton": {"metric": "sports_wanted", "code": "badminton", "optionLabel": "Badminton"}}
    WR.register_code_labels({"swimming": "Swimming", "parkour": "Parkour", "trampolining": "Trampolining"})
    facts = {"top3": [("swimming", 10), ("parkour", 9), ("trampolining", 8)], "base": 20}
    cy = WR.render("group_codemand_top3_v12", facts, "whole|all|wd_football", "f10", cohorts)
    assert cy.startswith("Roedd y disgyblion a ddewisodd bêl droed hefyd am gael mwy o nofio (10), Parkour (9) a thrampolinio (8)")
    cy = WR.render("group_codemand_top3_v12", facts, "whole|all|wd_badminton", "f10", cohorts)
    assert cy.startswith("Roedd y disgyblion a ddewisodd Badminton hefyd am gael mwy o nofio (10), Parkour (9) a thrampolinio (8)")
