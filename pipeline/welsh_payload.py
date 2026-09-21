# -*- coding: utf-8 -*-
"""Payload pieces of the language layer shared by the two builders
(staged_build.do_assemble and build_report_package) so they can never
drift apart — the count-NP tables (D75, sheet 50), the static manifest
(D79), and the build identity (D78). Framework v2.2 / gate pack v7.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from . import static_lane as SL
from .common import ROOT

WEB_DIR = ROOT / "web"


def count_np_tables(lex):
    """welsh.countNP — sheet 50 VERBATIM (lexical, lower-case; the client's
    'initial' role is the only place a capital is applied, D75). The
    numeral service is cross-checked against the sheet: a disagreement is
    a defect in one or the other and fails the build loudly — it is raised,
    never patched here (D51)."""
    from .welsh import num_noun, def_num_noun, article, with_article
    tables = lex.get("count_np_tables")
    if not tables:
        raise SystemExit("lexicon carries no count_np_tables — rebuild it "
                         "from Framework v2.2 (sheet 50)")
    diffs = []
    for noun in ("disgybl", "ateb", "ymateb disgybl"):
        for n in range(1, 11):
            want, got = tables.get(noun, [""] * 10)[n - 1], num_noun(n, noun)
            if want != got:
                diffs.append(f"{noun}[{n}]: sheet 50 {want!r} ≠ numeral service {got!r}")
    for n in range(1, 11):
        want = tables.get("camp|definite", [""] * 10)[n - 1]
        if n == 1:
            # 'yr un gamp': article + un + feminine singular (SM after un f.)
            body = "un " + with_article("camp", "f").split(" ", 1)[1]
        else:
            body = def_num_noun(n, "camp", "f")       # returns WITHOUT the article
        got = f"{article(body)} {body}"
        if want != got:
            diffs.append(f"camp|definite[{n}]: sheet 50 {want!r} ≠ numeral service {got!r}")
    if diffs:
        raise SystemExit("sheet 50 disagrees with the numeral service (D40/D75) "
                         "— raise, do not patch:\n  " + "\n  ".join(diffs))
    for tk, arr in tables.items():
        for v in arr:
            first = next((ch for ch in v if ch.isalpha()), "")
            if first and first.isupper():
                raise SystemExit(f"sheet 50 {tk}: {v!r} is capitalised — the "
                                 f"tables are lexical (D75)")
    return {tk: list(arr) for tk, arr in tables.items()}


def static_manifest(handoff_values, lex, school_name):
    """welsh.static = {key: {en, cy, consumer}} for every ui### handoff row,
    bound to the template's text nodes by the English (D79) and to the
    keyed fixed attributes (D80). Fails the build on any unbound row or
    node; returns (manifest, lane_record)."""
    rows = {s["key"]: s for s in lex.get("handoff", [])
            if SL.STATIC_KEY.match(str(s["key"]))}
    en_to_key = {}
    for k, s in rows.items():
        en = SL.norm(s["en"])
        if en in en_to_key and en_to_key[en] != k:
            raise SystemExit(f"handoff: two static keys share one English "
                             f"({en_to_key[en]}, {k}) — one key per distinct string (D79)")
        en_to_key[en] = k
    tpl = (WEB_DIR / "template.html").read_text(encoding="utf-8")
    bound, problems = SL.bind(tpl, en_to_key)
    attr_keys = {k for _, k in SL.attribute_keys(tpl)}
    for k in rows:
        if k not in bound and k not in attr_keys:
            problems.append(f"{k}: static handoff row with no page node and no "
                            f"keyed attribute ({rows[k]['en'][:60]!r})")
    if problems:
        raise SystemExit("D79/D80 static lane is not bound:\n  " + "\n  ".join(problems))
    manifest = {}
    for k in sorted(rows):
        s = rows[k]
        if k in bound:
            consumer = bound[k]["consumer"]
        else:
            consumer = " | ".join(sorted({a for a, kk in SL.attribute_keys(tpl) if kk == k}))
        manifest[k] = {"en": SL.norm(s["en"]),
                       "cy": handoff_values.get(k) or "",
                       "consumer": consumer}
        # V4.10 block row: the paragraph's inline emphasis travels as
        # `html` (English markup from the template; the Welsh value carries
        # the translator's own <strong>/<em> runs). `en` stays the
        # tag-stripped text the gates compare.
        if k in bound and bound[k].get("html"):
            manifest[k]["html"] = bound[k]["html"]
            manifest[k]["inline"] = True
    # the stamped head must verify the way the runner verifies it
    stamped = SL.stamp(tpl, en_to_key).replace("__SCHOOL_NAME__", school_name)
    v = SL.verify(stamped, manifest)
    if v:
        raise SystemExit("D79 stamped markup does not verify:\n  " + "\n  ".join(v))
    lane = {"rows": len(manifest),
            "textNodes": sum(r["count"] for r in bound.values()),
            "keyedAttributes": len(SL.attribute_keys(tpl)),
            "values": sum(1 for m in manifest.values() if m["cy"])}
    return manifest, lane


def identity(lex):
    """buildMetadata.identity (D78): written once; every legacy field is
    derived from it."""
    from . import vendor_welsh_gates_v8 as V7     # v8 pack (V4.15, D84)
    from . import welsh_gates8 as WG7
    return {
        "frameworkVersion": lex.get("version"),
        "frameworkFile": lex.get("framework_file"),
        "frameworkSha256": lex.get("framework_sha256"),
        "runnerVersion": V7.VERSION,
        "runnerSha256": hashlib.sha256(WG7.RUNNER_PATH.read_bytes()).hexdigest(),
        "manifestHash": V7.MANIFEST_HASH,
        "mode": "dev",
    }
