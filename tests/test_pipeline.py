"""Calculation, suppression and narrative tests (v2).

Run from the project root:  python -m pytest tests/ -q
Set SSS_REAL_XLSX to the real export's path to add the independent
reconciliation tests against the live workbook.

Suppression policy under test (agreed 2026-07-20): the rule of five applies
to the SELECTED VIEW only; within a reportable view exact counts are shown,
including values and question bases below five.
"""
import os
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.common import load_config, plural, slugify, parse_matrix  # noqa: E402
from pipeline.engine import (StateEngine, build_cohorts, build_metric_defs,  # noqa: E402
                             state_key)
from pipeline.load_normalise import load_and_normalise  # noqa: E402
from pipeline.narrative2_modules_b import FullNarrator  # noqa: E402
from pipeline.build_report_package import scope_present  # noqa: E402

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic.xlsx"
REAL = os.environ.get("SSS_REAL_XLSX")


@pytest.fixture(scope="module")
def built():
    if not FIXTURE.exists():
        from tests.make_synthetic_fixture import build
        FIXTURE.parent.mkdir(parents=True, exist_ok=True)
        build(FIXTURE)
    profile, mapping, metrics_cfg, narratives_cfg = load_config()
    records, log, meta, discovered = load_and_normalise(str(FIXTURE))
    defs = build_metric_defs(metrics_cfg, discovered)
    cohorts = build_cohorts(metrics_cfg, defs)
    engine = StateEngine(records, defs, cohorts, profile, 5).compute_all()
    nar = FullNarrator(engine, defs, cohorts, profile, 5)
    return records, log, engine, nar, defs, cohorts


# ------------------------------------------------------------ unit helpers
def test_slugify():
    assert slugify("Rock Climbing or Bouldering") == "rock_climbing_or_bouldering"
    assert slugify("Fitness Classes (e.g. Yoga, Circuits, Aerobics, etc.)") == "fitness_classes"


def test_parse_matrix():
    cells = parse_matrix('{"row_title": "PE lessons ", "column_title": "A lot"}; '
                         '{"row_title": "School sports clubs", "column_title": "Not much"}')
    assert cells == [("PE lessons", "A lot"), ("School sports clubs", "Not much")]


def test_plural():
    assert plural(1, "respondent") == "respondent"
    assert plural(2, "respondent") == "respondents"


# --------------------------------------------------- loading and validation
def test_acceptance_and_warnings(built):
    records, log, *_ = built
    reasons = [e["reason"] for e in log.exclusions]
    assert any("Partial" in r for r in reasons)
    assert any("Year 99" in r for r in reasons)
    assert any("gender" in w for w in log.warnings)
    assert len(records) == 40


def test_phase_definitions(built):
    records, *_ = built
    assert all(r["phase"] == "primary" for r in records if r["year"] <= 6)
    assert all(r["phase"] == "secondary" for r in records if r["year"] >= 7)


def test_multi_select_counting(built):
    records, *_ = built
    y7 = [r for r in records if r["year"] == 7]
    assert sum("football" in r["sports"] for r in y7) == 10
    assert sum("netball" in r["sports"] for r in y7) == 10


def test_organised_freq_derivation(built):
    records, *_ = built
    # community "1 time a week" was given to 6 Y7 boys in the fixture
    y7b = [r for r in records if r["year"] == 7 and r["gender"] == "boy"]
    assert sum(r["organised_freq"] == "once_week" for r in y7b) == 6
    assert sum(r["organised_freq"] == "none_reported" for r in y7b) == 4


def test_unmet_demand_derivation(built):
    records, *_ = built
    # Y7 boys demanded Swimming/Tennis/Golf but participate only in Football
    y7b = [r for r in records if r["year"] == 7 and r["gender"] == "boy"]
    assert sum("swimming" in r["unmet"] for r in y7b) == 6


# ------------------------------- demographic-view-only rule of five (P3 §16)
def test_small_views_suppressed(built):
    _, _, engine, *_ = built
    assert state_key("y4", "all", "none") in engine.suppressed      # 3 respondents
    assert state_key("y8", "girl", "none") in engine.suppressed     # 0 respondents
    assert state_key("y10", "boy", "none") in engine.suppressed     # 0 respondents
    assert state_key("y11", "all", "none") in engine.suppressed     # no Y11 rows


def test_no_complementary_suppression(built):
    """A visible sibling stays visible even when its pair is suppressed."""
    _, _, engine, *_ = built
    assert state_key("y8", "boy", "none") not in engine.suppressed   # 5 boys
    assert engine.bases[state_key("y8", "boy", "none")] == 5
    assert state_key("y10", "girl", "none") not in engine.suppressed  # 5 girls


def test_no_second_threshold_for_selected_groups(built):
    """Section 16.4: chart-derived groups inherit reportability from the
    demographic view — tiny group bases are never a reason to suppress."""
    _, _, engine, *_ = built
    for ck in engine.cohort_keys:
        k = state_key("y3", "all", ck)          # Year 3 = 6 respondents, reportable
        assert k not in engine.suppressed, k
    # and every overlay of a suppressed demographic view is suppressed
    for ck in engine.cohort_keys:
        assert state_key("y4", "all", ck) in engine.suppressed


def test_exact_small_values_within_visible_views(built):
    """Counts below five are shown exactly inside a reportable view."""
    _, _, engine, *_ = built
    res = engine.results[state_key("y3", "all", "none")]["club_freq_estimate"]
    assert res["status"] == "ok" and res["base"] == 6
    assert all(v is not None for v in res["disp"])
    assert any(0 < v < 5 for v in res["disp"])   # a count of 1 is shown exactly


def test_profile_chart_syncs_with_view_suppression(built):
    _, _, engine, *_ = built
    d = engine.results[state_key("whole", "all", "none")]["responses_by_year"]
    codes = [c for c, _ in engine.defs["responses_by_year"]["options"]]
    assert d["disp"][codes.index("y4")] is None      # Year 4 view suppressed
    assert d["disp"][codes.index("y3")] == 6


def test_not_asked_state(built):
    _, _, engine, *_ = built
    res = engine.results[state_key("y7", "all", "none")]["take_part_method"]
    assert res["status"] == "na"


def test_group_state_creation(built):
    _, _, engine, *_ = built
    assert engine.bases[state_key("y7", "all", "ep_a_lot")] == 12
    assert engine.bases[state_key("y7", "boy", "ep_a_lot")] == 7
    for ck in engine.cohort_keys:
        assert engine.bases[state_key("y7", "boy", ck)] <= \
               engine.bases[state_key("y7", "all", ck)]


# -------------------------------------------------------------- narrative
def test_tie_narrative_and_grammar(built):
    _, _, engine, nar, defs, _ = built
    st = nar.build_state(state_key("y7", "all", "none"))
    d7 = " ".join(p["t"] for p in st["mod"]["d7"]["p"])
    assert "tied" in d7 and "Football" in d7 and "Netball" in d7
    assert "were tied" in d7                       # plural verb for a tie


def test_scope_in_every_dynamic_sentence(built):
    _, _, engine, nar, *_ = built
    st = nar.build_state(state_key("y7", "boy", "none"))
    sc = st["scope"]
    for mid_, m in st["mod"].items():
        for p in m["p"]:
            if p["k"] in ("primary", "supporting", "comparison", "cross"):
                assert scope_present(p["t"], sc) or "Year 7" in p["t"], (mid_, p["t"])


def test_no_unresolved_placeholders(built):
    _, _, engine, nar, *_ = built
    for k in [state_key("y7", "all", "none"), state_key("y3", "all", "none")]:
        st = nar.build_state(k)
        for m in st["mod"].values():
            for p in m["p"]:
                assert not re.search(r"\{[a-z_0-9]+\}", p["t"])


def test_year_only_modules_omitted_in_year_view(built):
    _, _, engine, nar, *_ = built
    st = nar.build_state(state_key("y7", "all", "none"))
    # v5 (build 012): f2/e4/g4 respond to year filters instead of hiding;
    # only f12 remains gated to phase or whole-school views
    assert "f2" in st["mod"]
    assert ["f12", "na_view"] in st["avail"]


def test_cards_removed_v2(built):
    """v2 (Sport Wales feedback): the Key statistics page was removed, so
    states no longer carry per-view cards; the scoped view summary remains."""
    _, _, engine, nar, *_ = built
    st = nar.build_state(state_key("y7", "boy", "none"))
    assert "cards" not in st
    assert st["scope"]["short"].startswith("Year 7 · Boys")
    assert "h1" in st and "h2" in st


def test_grammar_rules_hold(built):
    """P3 section 13 gates on the synthetic fixture's audit output."""
    _, _, engine, nar, *_ = built
    for k in [state_key("y7", "all", "none"), state_key("y3", "all", "none"),
              state_key("y8", "boy", "none")]:
        nar.build_state(k)
    for row in nar.audit:
        txt = row["rendered_text"]
        assert not re.search(r"\b1 (selections|respondents|boys|girls)\b", txt), txt
        assert "i’m" not in txt and "i'm" not in txt, txt


# ------------------------------------------------- real-workbook fixtures
@pytest.mark.skipif(not REAL, reason="set SSS_REAL_XLSX to run")
def test_real_reconciliation():
    profile, mapping, metrics_cfg, narratives_cfg = load_config()
    records, log, meta, discovered = load_and_normalise(REAL)
    defs = build_metric_defs(metrics_cfg, discovered)
    cohorts = build_cohorts(metrics_cfg, defs)
    engine = StateEngine(records, defs, cohorts, profile, 5).compute_all()

    assert engine.bases[state_key("whole", "all", "none")] == 366
    assert engine.bases[state_key("primary", "all", "none")] == 96
    assert engine.bases[state_key("secondary", "all", "none")] == 270

    def count(mid, code, key="whole|all|none"):
        d = defs[mid]
        idx = [c for c, _ in d["options"]].index(code)
        return engine.results[key][mid]["raw"][idx]

    # content-spec test fixtures (section 11)
    assert count("sports_participated", "tennis") == 273
    assert count("sports_participated", "tennis", "whole|boy|none") == 143
    assert count("sports_participated", "rounders", "whole|girl|none") == 137
    assert count("sports_participated", "boxing", "y5|boy|none") == 7
    assert count("sports_participated", "football", "y5|boy|none") == 7
    assert count("sports_participated", "rounders", "y5|girl|none") == 12
    assert count("sports_wanted", "tennis") == 169
    assert count("unmet_demand", "dodgeball") == 81
    # organised_freq was retired in build 012 (flat square-root method,
    # register decision); the reconciliation invariant is now the club
    # weekly+ total under club_freq_estimate: 251 pupils in weekly bands
    d_cfe = defs["club_freq_estimate"]
    ebands = [i for i, (c, _) in enumerate(d_cfe["options"])
              if c.startswith("e")]
    assert sum(engine.results["whole|all|none"]["club_freq_estimate"]
               ["raw"][i] for i in ebands) == 251
    assert count("join_in_easily", "always") == 125
    assert count("join_in_easily", "sometimes") == 186
    assert count("ideas_listened", "always") == 70
    assert count("confidence_try_new", "very") == 143
    assert engine.results["whole|all|none"]["community_club_freq"]["base"] == 256
    assert engine.results["whole|all|none"]["school_club_freq"]["base"] == 156
    assert engine.results["whole|all|none"]["welsh_when_playing_sport"]["base"] == 345

    # required suppression states
    assert state_key("y11", "boy", "none") in engine.suppressed      # 3 respondents
    assert state_key("y11", "girl", "none") not in engine.suppressed  # 5 respondents
