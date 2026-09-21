# -*- coding: utf-8 -*-
"""Revert the V4.11 reviewer substitutions so the handoff carries the
translator's text VERBATIM (V4.14, owner's instruction 17 Sep 2026).

    python -m pipeline.revert_review_corrections <handoff_in.xlsx> <handoff_out.xlsx>

Exact inverse of apply_review_corrections: every (old, new) pair is applied
as (new, old) and must match exactly once; the Note column entry is replaced
by a provenance note. The reviewer's findings remain questions for the
translator (handover workbook, sheet 1); nothing is lost, only precedence
restored: the translator's document is the source of the page text.
"""
from __future__ import annotations
import sys
import openpyxl
from .apply_review_corrections import CORRECTIONS, NOTE

REVERT_NOTE = "translator's text restored verbatim (V4.14, owner's instruction 17 Sep 2026); reviewer finding remains open on the handover"


def main():
    src, dst = sys.argv[1], sys.argv[2]
    wb = openpyxl.load_workbook(src)
    ws = wb["Strings"]
    done = []
    for r in ws.iter_rows(min_row=2):
        key = str(r[3].value or "")
        if key not in CORRECTIONS:
            continue
        val = r[5].value or ""
        for old, new in reversed(CORRECTIONS[key]):
            if val.count(new) != 1:
                raise SystemExit(f"{key}: expected exactly one occurrence of {new!r}; found {val.count(new)}")
            val = val.replace(new, old)
        r[5].value = val
        note = r[6].value or ""
        r[6].value = (note.replace(NOTE, "").strip(" ·") + " · " if note.replace(NOTE, "").strip(" ·") else "") + REVERT_NOTE
        done.append(key)
    missing = sorted(set(CORRECTIONS) - set(done))
    if missing:
        raise SystemExit(f"rows not found: {missing}")
    wb.save(dst)
    print(f"reverted {len(done)} keys: {', '.join(done)}")


if __name__ == "__main__":
    main()
