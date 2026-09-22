# -*- coding: utf-8 -*-
"""0.29.1 loader rule: an answer to the take-part question from a respondent
who was not routed to it (disability answer not Yes / Not sure / Prefer not
to say) is not carried — chart, selected group and narrative then agree by
construction (the Ysgol Bro Pedr 5-vs-6 finding of the V5.0 review)."""
import pandas as pd

from pipeline.engine import build_cohorts, build_metric_defs, cohort_member, compute_metric
from pipeline.common import load_config
from pipeline.load_normalise import load_and_normalise
from tests.make_synthetic_fixture import FREQ_QIDS, QIDS, SETTINGS_QIDS, SPORT_QIDS, make_row


def _fixture(tmp_path):
    rows = []
    for i in range(6):     # six routed Year 7 girls: Yes → Seated
        rows.append(make_row(f"R{i}", year="Year 7", gender="a girl", sports="Netball", demand="Golf",
                             disability="Yes", take_part="Seated"))
    # the off-route case: "No" to the disability question, yet a take-part answer
    rows.append(make_row("OFF1", year="Year 7", gender="a girl", sports="Netball", demand="Golf",
                         disability="No", take_part="Other (please specify):"))
    for i in range(4):     # padding so the view is reportable
        rows.append(make_row(f"P{i}", year="Year 7", gender="a boy", sports="Football", demand="Golf"))
    all_cols = (["Response_ID", "Completion_Status", "School_Name", "School_ID", "Local_Authority"] +
                [f"Q_{q}_x" for q in QIDS.values()] +
                [f"Q_{q}_x" for q in SPORT_QIDS + SETTINGS_QIDS + FREQ_QIDS])
    df = pd.DataFrame(rows)
    for c in all_cols:
        if c not in df.columns:
            df[c] = None
    df = df[[c for c in all_cols if c in df.columns] + [c for c in df.columns if c not in all_cols]]
    p = tmp_path / "offroute.xlsx"
    df.to_excel(p, sheet_name="Responses wide", index=False)
    return p


def test_off_route_take_part_answer_is_not_carried(tmp_path):
    records, log, meta, discovered = load_and_normalise(str(_fixture(tmp_path)))
    off = [r for r in records if r["disability"] == "no" and r["gender"] == "girl"]
    assert len(off) == 1
    assert off[0]["take_part_routed"] is False
    assert off[0]["take_part"] is None            # the off-route answer is dropped
    routed = [r for r in records if r["take_part_routed"]]
    assert len(routed) == 6 and all(r["take_part"] == "seated" for r in routed)
    assert meta["offRouteTakePartDropped"] == 1
    assert any("off-route" in w for w in log.warnings)
    assert not any("_off_route_take_part" in r for r in records)


def test_chart_and_selected_group_agree(tmp_path):
    records, log, meta, discovered = load_and_normalise(str(_fixture(tmp_path)))
    profile, mapping, metrics_cfg, narratives_cfg = load_config()
    defs = build_metric_defs(metrics_cfg, discovered)
    d = defs["take_part_method"]
    res = compute_metric(records, d)
    codes = [c for c, _ in d["options"]]
    chart = dict(zip(codes, res["raw"]))
    members = {c: sum(1 for r in records if cohort_member(r, {"metric": "take_part_method", "code": c}, defs)) for c in codes}
    assert res["base"] == 6 and chart["seated"] == 6 and chart["other"] == 0
    assert members == chart                       # no selected group larger than its chart value
