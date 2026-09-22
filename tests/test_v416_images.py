# -*- coding: utf-8 -*-
"""V4.16: the Young Artists Competition artwork — fourteen entries, each
placed once, each with an alt frame; nothing else about the page changed."""
import json
import re
from pathlib import Path

from pipeline.yac_assets import ALT_EN, RETIRED, YAC

ROOT = Path(__file__).resolve().parents[1]
TPL = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
APP = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
LEX = json.loads((ROOT / "config" / "welsh_lexicon.json").read_text(encoding="utf-8"))


def _imgs():
    return re.findall(r'<img src="(__IMG_YAC_[A-Z_]+__)"\s+alt="([^"]*)"\s+data-frame-attr="alt:([a-z_.]+)"', TPL)


def test_fourteen_entries_each_placed_exactly_once():
    imgs = _imgs()
    assert len(imgs) == len(YAC) == 14
    assert sorted(t for t, _, _ in imgs) == sorted(t for _, _, t, *_ in YAC)
    assert len({t for t, _, _ in imgs}) == 14


def test_every_alt_literal_equals_its_sheet43_frame_english():
    by_token = {t: k for k, _f, t, *_ in YAC}
    for token, alt, key in _imgs():
        assert by_token[token] == key
        assert alt == ALT_EN[key] == LEX["interface_frames"][key]["en"]


def test_frames_welsh_is_the_workbooks_verbatim_never_invented():
    # V4.16–V4.18: the fourteen frames were PENDING (empty Welsh). V4.19: Framework
    # v2.12 carries the Welsh the owner supplied on 22 Sep 2026; the lexicon must
    # equal the workbook cell character for character, and the workbook cell must
    # equal the recorded source text (pipeline/make_framework_v212.WELSH_ALT).
    import openpyxl
    from pipeline.common import latest_framework, CONFIG_DIR
    from pipeline.make_framework_v212 import WELSH_ALT
    fw = latest_framework(CONFIG_DIR)
    wb = openpyxl.load_workbook(fw, read_only=True, data_only=True)
    rows = {str(r[0]): r for r in wb["43 Interface frames"].iter_rows(min_row=4, values_only=True) if r and r[0]}
    for key, *_ in YAC:
        cy = LEX["interface_frames"][key]["cy"]
        assert cy and cy == rows[key][4] == WELSH_ALT[key], key
        assert cy.startswith("Darlun o’r Gystadleuaeth Artistiaid Ifanc: "), key
        assert "'" not in cy and '"' not in cy, key          # typographic apostrophes only
        assert "supplied by the owner" in str(rows[key][7]), key   # the status records the source


def test_no_pupil_name_in_any_alt_text():
    # the survey's mascot pages named the artists; the report never does
    names = ("Isla", "Sofia", "Simay", "Chloe", "Zoe", "Ada", "Isla-Boe")
    for key, alt in ALT_EN.items():
        assert not any(re.search(r"\b" + n + r"\b", alt) for n in names), key
        cy = LEX["interface_frames"][key]["cy"]                    # V4.19: the Welsh too
        assert not any(re.search(r"\b" + n + r"\b", cy) for n in names), key


def test_client_consumes_every_frame_and_none_of_the_retired():
    for key, *_ in YAC:
        assert f'"{key}": 1' in APP, key
    for key in RETIRED:
        assert key not in APP
        assert key not in TPL
        assert key in LEX["deprecated_frames"]
        assert key not in LEX["interface_frames"]


def test_brain_break_tokens_and_placeholder_are_gone():
    assert "__IMG_BRAIN_" not in TPL
    assert "brand-form graphic placeholder" not in TPL


def test_v417_switch_description_frame():
    assert '"ui.a11y_switch_desc": 1' in APP
    fr = LEX["interface_frames"]["ui.a11y_switch_desc"]
    assert fr["cy"] == "" and fr["en"].startswith("Turns on larger text")
    m = re.search(r'<p class="a11y-desc" id="a11y-desc" data-frame="ui.a11y_switch_desc">([^<]*)</p>', TPL)
    assert m and m.group(1) == fr["en"]
    assert 'aria-describedby="a11y-desc"' in TPL
