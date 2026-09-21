# -*- coding: utf-8 -*-
"""V4.10: block rows in the static lane and the translator-document ingest
helpers (no Welsh is written by either; these tests use fixture strings)."""
from pipeline import static_lane as SL
from pipeline.ingest_translation_doc import emph_segments, runs_html, normA, normB


def test_block_row_requires_whitespace_boundaries():
    ok = "<body><p>Use the <strong>Explore results</strong> panel to select.</p></body>"
    bad = "<body><p>Each chart says <em>“Based on: X pupils”</em>. This is it.</p></body>"
    n_ok = SL.extract(ok)
    n_bad = SL.extract(bad)
    assert len(n_ok) == 1 and n_ok[0].html == "Use the <strong>Explore results</strong> panel to select."
    assert n_ok[0].text == "Use the Explore results panel to select."
    assert len(n_bad) == 3 and all(n.html is None for n in n_bad)


def test_block_row_excludes_slots_placeholders_and_sole_emphasis():
    slot = '<body><p>Pupils at <strong>__SCHOOL_NAME__</strong> who answered: <strong class="dyn-count"></strong> pupils.</p></body>'
    sole = "<body><li><strong>An Active Nation for Everyone</strong></li></body>"
    assert all(n.html is None for n in SL.extract(slot))
    s = SL.extract(sole)
    assert len(s) == 1 and s[0].html is None and s[0].text == "An Active Nation for Everyone"


def test_template_has_thirteen_block_rows_and_stamps_verify():
    tpl = (SL.__file__.rsplit("/pipeline/", 1)[0] + "/web/template.html")
    html = open(tpl, encoding="utf-8").read()
    nodes = SL.extract(html)
    blocks = [n for n in nodes if n.html]
    assert len(blocks) == 13
    en_to_key = {}
    for i, n in enumerate(nodes):
        en_to_key.setdefault(n.text, f"ui{i:03d}")
    stamped = SL.stamp(html, en_to_key).replace("__SCHOOL_NAME__", "X")
    manifest = {k: {"en": e} for e, k in en_to_key.items()}
    assert SL.verify(stamped, manifest) == []


def test_emphasis_segments_move_punctuation_out():
    runs = [("Trwy glicio ar ", False, False), ("“Ailosod i’r ysgol gyfan”. ", True, False), ("Bydd hyn yn clirio.", False, False)]
    segs = emph_segments(runs)
    assert [e for _, e in segs] == [False, True, False]
    assert segs[1][0] == "“Ailosod i’r ysgol gyfan”"
    assert segs[2][0].startswith(". ")


def test_runs_html_keeps_whitespace_outside_tags():
    assert runs_html([("Mae", False, False), (" barrau llwyd ", True, False), ("yn", False, False)]) == "Mae <strong>barrau llwyd</strong> yn"
    assert runs_html([("<b>x</b>", False, True)]) == "<em>&lt;b&gt;x&lt;/b&gt;</em>"


def test_norm_forms():
    assert normA("pupils” . This") == normA("pupils”. This")
    assert normB("Which sports are our pupils doing — and how often?") == normB("Which sports are our pupils doing, and how often?")
