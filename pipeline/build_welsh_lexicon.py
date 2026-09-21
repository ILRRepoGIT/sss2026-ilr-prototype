# -*- coding: utf-8 -*-
"""Convert the Welsh Generation Framework workbook (v1.5) into
config/welsh_lexicon.json — the machine-readable lexical database the
Welsh renderer consumes.

Usage:
    python -m pipeline.build_welsh_lexicon <framework.xlsx> [<handoff.xlsx>]

Everything in the output is transcribed from the framework sheets; nothing
is invented here. Handoff strings whose Welsh column is blank are carried
as null so the front end can fail loudly / fall back with a marker.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import openpyxl

from .common import CONFIG_DIR


def rows_of(ws):
    return [[("" if v is None else str(v).strip()) for v in row]
            for row in ws.iter_rows(values_only=True)]


def build(framework_path, handoff_path=None):
    import hashlib
    wb = openpyxl.load_workbook(framework_path, data_only=True)
    import re as _re0
    _mv = _re0.search(r"v(\d+\.\d+)", Path(framework_path).name)
    # D78: the version is derived from the governing file's own name, so
    # the identity object can never disagree with the file it names.
    out = {"version": f"v{_mv.group(1)}" if _mv else "unversioned"}
    # D60: the build is stamped with the exact framework it was built from.
    out["framework_sha256"] = hashlib.sha256(
        Path(framework_path).read_bytes()).hexdigest()
    out["framework_file"] = Path(framework_path).name

    # ---- 21 Audience forms -------------------------------------------------
    aud = {}
    for r in rows_of(wb["21 Audience forms"]):
        if len(r) < 8 or not r[0] or r[0].startswith(("All 36", "English")):
            continue
        aud[r[0]] = {"bare": r[1], "def_sg": r[2], "after_o": r[3],
                     "after_or": r[4], "ymhlith": r[5], "def_pl": r[6],
                     "holl": r[7]}
    out["audiences"] = aud

    # ---- 22 Qualifier frames ----------------------------------------------
    # D47 (v1.7): a frame may reference an answer label by ID, never carry
    # literal label Welsh. IDs are resolved here, at build time, from the
    # single authoritative copy on sheet 23 — so a sheet-23 correction
    # propagates on rebuild with no frame edit.
    ANSWER_IDS = {
        "ethnicity_mixed": "Mixed or multiple ethnic groups",
    }
    import re as _re
    quals = []
    for r in rows_of(wb["22 Qualifier frames"]):
        if len(r) < 3 or not r[0] or r[0].startswith(("All 116", "Each", "Family")):
            continue
        quals.append({"family": r[0], "en": r[1], "cy": r[2]})
    out["qualifiers"] = quals

    # ---- 23 Answer labels --------------------------------------------------
    # v1.7: gender is PROVISIONAL under PR-01 and written like "g (m)";
    # normalise to m / f / pl / "" but keep the raw value for the audit.
    def norm_gender(g):
        g = (g or "").strip().lower()
        if g.startswith(("g", "m")) and "f" not in g[:1]:
            return "m"
        if g.startswith(("b", "f")):
            return "f"
        if g.startswith("plural"):
            return "pl"
        return ""

    labels = {}
    for r in rows_of(wb["23 Answer labels"]):
        if len(r) < 7 or not r[0] or r[0].startswith(("All 178", "Gender is", "English")):
            continue
        labels[r[0]] = {"cy": r[1], "prose": r[2], "cat": r[3],
                        "gender": norm_gender(r[4]), "gender_raw": r[4],
                        "initial": r[5],
                        "mutable": r[6].upper().startswith("YES")}
    out["answer_labels"] = labels

    # D47 resolution pass: replace ⟪ANSWER-ID: x⟫ in qualifier frames from
    # the single authoritative sheet-23 copy (labels parsed above).
    for q in quals:
        for m in _re.finditer(r"⟪ANSWER-ID:\s*([a-z_]+)⟫", q["cy"]):
            q["cy"] = q["cy"].replace(m.group(0),
                                      labels[ANSWER_IDS[m.group(1)]]["cy"])

    # ---- 17 Core nouns -----------------------------------------------------
    nouns = {}
    for r in rows_of(wb["17 Lexicon core nouns"]):
        if len(r) < 6 or not r[0] or r[0].startswith(("Core noun", "Each entry", "English")):
            continue
        nouns[r[0]] = {"cy": r[1], "gender": r[2][:1], "plural": r[3],
                       "initial": r[4], "mutable": r[5].upper().startswith("YES")}
    out["core_nouns"] = nouns

    # ---- 18 Head nouns -----------------------------------------------------
    heads = {}
    for r in rows_of(wb["18 Head nouns"]):
        if len(r) < 6 or not r[0] or r[0].startswith(("Superlative", "The head", "English")):
            continue
        heads[r[0]] = {"cy": r[1], "gender": r[2][:1], "plural": r[3],
                       "superl": r[4], "am3sg": r[5]}
    out["head_nouns"] = heads

    # ---- 19 Predicates -----------------------------------------------------
    preds = {}
    for r in rows_of(wb["19 Predicates"]):
        if len(r) < 4 or not r[0] or not r[0].startswith("P-"):
            continue
        preds[r[0]] = {"en": r[1], "cy": r[3], "type": r[4] if len(r) > 4 else ""}
    out["predicates"] = preds

    # ---- 32 Battery items --------------------------------------------------
    battery = {}
    for r in rows_of(wb["32 Battery items"]):
        if len(r) < 3 or not r[0] or not r[0].startswith("M-"):
            continue
        battery[r[1]] = r[2]
    out["battery"] = battery

    # ---- 31 Yes-No forms ---------------------------------------------------
    yesno = {}
    metric_map = {}
    in_map = False
    for r in rows_of(wb["31 Yes-No forms"]):
        if r and r[0].startswith("METRIC"):
            in_map = True
            continue
        if not in_map:
            if len(r) < 7 or not r[0] or not r[0].startswith("QV-"):
                continue
            yesno[r[0]] = {"topic": r[1], "aff": r[5], "neg": r[6]}
        else:
            # v1.8 (D54): every binary metric mapped to its question's verb.
            # A metric absent from this table FAILS THE BUILD — never a
            # note, never a fallback.
            if len(r) < 5 or not r[0] or " " in r[0]:
                continue          # header/prose rows; metric ids have no spaces
            metric_map[r[0]] = {"question": r[1], "aff": r[2], "neg": r[3],
                                "form": r[4],
                                "note": r[5] if len(r) > 5 else ""}
    out["yes_no"] = yesno
    out["yes_no_metrics"] = metric_map

    # ---- 20 scope phrases (locative + citation) ---------------------------
    scopes = {}
    started = False
    for r in rows_of(wb["20 Audience components"]):
        if r and r[0] == "Scope phrases":
            started = True
            continue
        if started and len(r) >= 3 and r[0] and not r[0].startswith("English"):
            scopes[r[0]] = {"loc": r[1], "cite": r[2]}
    out["scopes"] = scopes

    # ---- 39 Provisional rulings (D51) --------------------------------------
    # Every ruling is DATA: the generator reads the operative value from
    # here, never hard-codes it. The value is extracted from the ruling
    # text's leading keyword; if the workbook wording changes materially
    # the extraction fails loud rather than guessing.
    PR_KEYS = [
        (r"^\s*Gender assigned by two productive rules", "sheet23_provisional"),
        # v1.9 rulings — specific patterns first (PR-13 'AC:' before PR-04 'AC.')
        (r"^\s*AC:\s*[\"“]ac mae", "ac_fnwords"),
        (r"^\s*AGREE WITH THE GRAMMATICAL GENDER OF THE ANTECEDENT NOUN",
         "antecedent_gender"),
        (r"^\s*WELSH KEEPS THE QUALIFIER", "keep_qualifier"),
        (r"^\s*REALISE IT", "realise_exclusion"),
        (r'^\s*["“]\{k:count camp', "definite_count_np"),
        (r'^\s*LANGUAGE-NEUTRAL', "language_neutral_dash"),
        # v2.2 PR-19 (FT-11 / Q32): the faithful clause-bounded construction
        # is RETAINED and its record set locked until the linguist rules;
        # the ruling, when given, is one of retain / affirmative_zero /
        # noun_phrase / other and lands here as a new wording → new value.
        (r"^\s*RETAIN THE FAITHFUL CLAUSE-BOUNDED CONSTRUCTION UNCHANGED",
         "retain"),
        (r"^\s*NAME THE SET", "name_the_set"),
        (r"^\s*SUPPRESS IN WELSH", "suppress_welsh"),
        (r"^\s*UNCHANGED as a ruling", "answer_selection_recast_all_surfaces"),
        (r"^\s*ANSWER-SELECTION RECAST", "answer_selection_recast"),
        (r"^\s*IMPERSONAL RECAST", "impersonal_recast"),
        (r"^\s*AC\b", "ac"),
        (r"^\s*THEY DO NOT MUTATE", "no_mutation"),
        (r"^\s*AGREE WITH THE NEARER CONJUNCT \(gweithgaredd, masculine\)", "m"),
        (r"^\s*MASCULINE", "m"),
        (r"^\s*Rendered as the identificational cleft", "cleft"),
        (r"^\s*AMHARIAD", "amhariad"),
        (r"^\s*IN FORCE AND UNCHANGED: lower case in running prose", "prose_lowercase"),
    ]
    rulings = []
    if "39 Provisional rulings" in wb.sheetnames:
        for r in rows_of(wb["39 Provisional rulings"]):
            if len(r) < 6 or not r[0] or not r[0].startswith("PR-"):
                continue
            value = None
            for pat, val in PR_KEYS:
                if _re.match(pat, r[2]):
                    value = val
                    break
            if value is None:
                raise SystemExit(f"provisional ruling {r[0]}: unrecognised "
                                 f"ruling wording — refusing to guess (D51)")
            rulings.append({"id": r[0], "question": r[1], "value": value,
                            "ruling": r[2], "alternative": r[3],
                            "volume": r[4], "ruled_by": r[5]})
    out["provisional_rulings"] = rulings

    # ---- 11 Conjunctions — CONJ-03 function-word list (D67 / PR-13) --------
    # The list that takes 'ac' is CONFIGURATION, read from the workbook.
    # A missing or unparsable row fails the build; the list is never
    # hard-coded in the engine.
    ac_fnwords = None
    for r in rows_of(wb["11 Conjunctions"]):
        if r and r[0] == "CONJ-03" and len(r) > 2 and r[2]:
            m = _re.search(r"one of:\s*(.+)$", r[2])
            if m:
                ac_fnwords = [w.strip() for w in _re.split(r"[,;]", m.group(1))
                              if w.strip()]
    if not ac_fnwords:
        raise SystemExit("sheet 11 CONJ-03: function-word list not found — "
                         "refusing to build without it (D67)")
    out["ac_fnwords"] = ac_fnwords

    # ---- 11 Conjunctions — CONJ-06 reading of a FIGURE (v2.7) ------------
    # The translator's ruling (21 Sep 2026, handover sheet 4 rule 15 and
    # sheet 5 #12) is carried on the CONJ-06 row as "MODE=figure" (a
    # before every figure), "MODE=decimal" or "MODE=vigesimal"; a
    # workbook without the marker is a pre-v2.7 workbook and keeps the
    # vigesimal reading the engine was built with.
    conj06 = "vigesimal"
    for r in rows_of(wb["11 Conjunctions"]):
        if r and r[0] == "CONJ-06":
            m = _re.search(r"MODE=(figure|decimal|vigesimal)\b",
                           " ".join(r[1:5]))
            if m:
                conj06 = m.group(1)
            elif "MODE=" in " ".join(r[1:5]):
                raise SystemExit("sheet 11 CONJ-06: unrecognised MODE — "
                                 "refusing to guess")
    out["conj06_mode"] = conj06

    # ---- 58 Chip prefixes (v2.6/v2.7) ---------------------------------------
    # The Welsh of the side-panel chips (the part before the answer), the
    # scope options, the gender options and the banner labels — DATA read
    # from the workbook (v2.6 moved them out of welsh_render.py; v2.7
    # applies the translator's decisions). A missing sheet fails the
    # build; the renderer never carries a default.
    if "58 Chip prefixes" not in wb.sheetnames:
        raise SystemExit("sheet 58 Chip prefixes missing — refusing to build "
                         "without the chip/scope/gender labels (v2.6)")
    chips, chips_en = {}, {}
    for r in rows_of(wb["58 Chip prefixes"]):
        if len(r) < 4 or not r[0] or r[0] == "Kind" or not r[1]:
            continue
        if r[0].startswith("Chip prefixes"):
            continue
        chips.setdefault(r[0], {})[r[1]] = r[3]
        chips_en.setdefault(r[0], {})[r[1]] = r[2]
    for kind, need in (("cohort prefix", 30), ("scope label", 12),
                       ("gender label", 3)):
        if len(chips.get(kind, {})) < need:
            raise SystemExit(f"sheet 58: {kind!r} has {len(chips.get(kind, {}))} "
                             f"rows, expected at least {need}")
    blank = [(k, key) for k, d in chips.items() for key, v in d.items() if not v]
    if blank:
        raise SystemExit(f"sheet 58: blank Welsh for {blank} — a chip label "
                         f"is never defaulted")
    out["chip_prefixes"] = chips
    out["chip_prefixes_en"] = chips_en

    # ---- 44 Singleton frames (D62) -----------------------------------------
    # The N = 1 realisation of every qualifier family carrying a plural
    # feature: three gendered columns (boy / girl / unknown, PR-14).
    singleton_frames = []
    if "44 Singleton frames" in wb.sheetnames:
        for r in rows_of(wb["44 Singleton frames"]):
            if len(r) < 6 or not r[0] or r[0].startswith(
                    ("Singleton", "Sheet 22", "Family")):
                continue
            singleton_frames.append({"family": r[0], "en": r[1],
                                     "pl": r[2], "m": r[3], "f": r[4],
                                     "u": r[5]})
    out["singleton_frames"] = singleton_frames

    # ---- 43 Interface frames (D63) -----------------------------------------
    # Every dynamic/assistive string as one typed frame for t(key, params).
    # Rows marked as code fixes (chip_label, language_toggle) carry no frame.
    interface_frames = {}
    stack_legend_cy = None
    deprecated = []
    for r in (rows_of(wb["43 Interface frames"])
              if "43 Interface frames" in wb.sheetnames else []):
        if len(r) < 6 or not r[0] or not _re.match(r"^(ui|msg)\.", r[0]):
            continue
        key, en, cy, slots = r[0], r[3], r[4], r[5]
        status = (r[7] if len(r) > 7 else "").strip().upper()
        if status.startswith("DEPRECATED") or cy.startswith("DEPRECATED"):
            deprecated.append(key)
            continue              # withdrawn on the sheet, never embedded
        if status == "CONTRACT" or key in ("ui.join_dot", "ui.join_dash"):
            continue              # read unstripped below (D74)
        if key == "ui.no_report":
            # PR-18/D76: a bare delimiter cannot be a clause frame (D74
            # forbids it), so the language-neutral marker is delivered as
            # CATALOGUE DATA; the accessible name comes from
            # ui.table_suppressed at the consumer.
            out["no_report_marker"] = cy.split()[0] if cy else "—"
            continue
        if status == "CODE FIX" or "CODE FIX" in cy or key in (
                "ui.chip_label", "ui.language_toggle", "ui.setting_segments",
                "ui.appx_metric_title", "ui.appx_option_label",
                # RAISED against the workbook: the EN cell "{year} — Boys /
                # Girls" is a description, not a renderable template; the
                # row label is composed from filterOptions labelCy through
                # the existing helpers instead (same effect as the frame).
                "ui.row_sex_suffix"):
            if key == "ui.stack_legend":
                m = _re.search(r"never re-typed:\s*(.+)$", cy)
                if not m:
                    raise SystemExit("sheet 43 ui.stack_legend: cannot "
                                     "extract legend labels")
                stack_legend_cy = [s.strip() for s in m.group(1).split("|")]
            continue              # code fixes / data sources, not frames
        # sheet 49 (D77): an EN cell may carry its sanctioned en_sg note
        # inline after a wide dot — strip the note; the singular is
        # derived below from the frame itself.
        en = _re.sub(r"\s{2,}·\s{2,}en_sg[^\t]*$", "", en).strip()
        entry = {"en": en, "cy": cy, "slots": slots}
        if status.startswith("EXCEPTION"):
            # D73: a deliberate English-in-Welsh value is a catalogue
            # RECORD with its exception id — never a code literal. The
            # Welsh value equals the approved English until the legal
            # translation arrives.
            entry["cy"] = en
            entry["exceptionId"] = status.split()[-1]
        # D71/PR-17: a frame cell may carry its k = 1 form inline as
        # "(k = 1: …)"; split it into the _sg variant here, at build time.
        for col in ("en", "cy"):
            m = _re.search(r"\s*\(k = 1:\s*(.+?)\)\s*$", entry[col])
            if m:
                entry[col + "_sg"] = m.group(1).strip().rstrip(".")
                entry[col] = entry[col][:m.start()].strip()
        interface_frames[key] = entry
    out["deprecated_frames"] = deprecated
    # N = 1 variants (sheet 28: English switches the noun's number at
    # N = 1; the Welsh singular participle 'wedi'i gynnwys' is the
    # attested sheet-28 View-banner row). Derived HERE, at build time,
    # so the client never edits a frame.
    for f in interface_frames.values():
        en, cy = f["en"], f["cy"]
        # D77: the singular contract applies to EVERY count slot; the slot
        # that controls selection is recorded so t() tests exactly it.
        en_sg = en.replace("{n} pupil responses included",
                           "{n} pupil response included")
        m_sl = _re.search(r"\{(\w+)\} pupils\b", en_sg)
        if m_sl:
            en_sg = en_sg.replace(f"{{{m_sl.group(1)}}} pupils",
                                  f"{{{m_sl.group(1)}}} pupil")
            f["sg_slot"] = m_sl.group(1)
        elif "{n} pupil response included" in en_sg:
            f["sg_slot"] = "n"
        if en_sg != en and "en_sg" not in f:
            f["en_sg"] = en_sg
        cy_sg = cy.replace("wedi’u cynnwys", "wedi’i gynnwys")
        if cy_sg != cy and "cy_sg" not in f:
            f["cy_sg"] = cy_sg
    # D71/PR-17 (sheet 43 v2.1 note: "en_sg / cy_sg unchanged for k = 1"):
    # the k = 1 caption forms come from the PR-17 ruling wording on sheet
    # 39 ("at one, ...") for the Welsh, and from the frame's own singular
    # recast for the English — never typed here.
    _cap = interface_frames.get("ui.stack_table_caption")
    if _cap and "cy_sg" not in _cap:
        for r39 in rows_of(wb["39 Provisional rulings"]):
            if r39 and r39[0] == "PR-17":
                m1 = _re.search(r'at one,\s*[“"]([^”"]+)[”"]', r39[2])
                if m1:
                    _cap["cy_sg"] = m1.group(1).strip()
        if "cy_sg" not in _cap:
            raise SystemExit("PR-17: at-one caption form not found (D71)")
        _cap["en_sg"] = _cap["en"].replace(
            "The {k} most selected sports", "The most selected sport")
    out["interface_frames"] = interface_frames
    # D74: the two separators are CONTRACT rows, read UNSTRIPPED — the
    # only place a delimiter lives; frames never carry one.
    seps = {}
    for row in wb["43 Interface frames"].iter_rows(values_only=True):
        if row and row[0] in ("ui.join_dot", "ui.join_dash") and row[4]:
            seps["dot" if row[0].endswith("dot") else "dash"] = str(row[4])
    if len(seps) != 2:
        raise SystemExit("sheet 43: CONTRACT separator rows missing (D74)")
    out["separators"] = seps
    if stack_legend_cy:
        legend_en = [s.strip() for s in
                     "Less than once a week | 1 time a week | 2 times a week "
                     "| 3 or more times a week | I don’t know".split("|")]
        # Sheet 43 mandates SOURCE FROM SHEET 23; where sheet 23 carries the
        # row (none of the five in v1.9 — raised with the linguist) prefer
        # it, else the values the frame row itself spells out.
        cys = []
        for en, cy in zip(legend_en, stack_legend_cy):
            row = labels.get(en)
            cys.append(row["cy"] if row and row.get("cy") else cy)
        out["stack_legend"] = [{"en": e, "cy": c}
                               for e, c in zip(legend_en, cys)]

    # ---- 50 Count-NP tables (D75 / D51, v2.2) -------------------------------
    # THE SOURCE OF TRUTH for payload.welsh.countNP: every entry is the
    # LEXICAL form (lower-case initial); the client's "initial" role is the
    # only place a capital is applied. The build emits these forms verbatim
    # (gates CNP-table / CNP-lexical) and cross-checks them against the
    # numeral service at assembly (a disagreement fails the build loudly —
    # it is raised, never patched in code). A missing or short table
    # refuses to build.
    if "50 Count-NP tables" not in wb.sheetnames:
        raise SystemExit("sheet 50 Count-NP tables missing — refusing to "
                         "build without the lexical tables (D75)")
    cnp = {}
    for r50 in rows_of(wb["50 Count-NP tables"]):
        if len(r50) >= 3 and r50[0] and r50[1].isdigit():
            cnp.setdefault(r50[0], {})[int(r50[1])] = r50[2]
    for tk, forms in cnp.items():
        missing = [n for n in range(1, 11) if not forms.get(n)]
        if missing:
            raise SystemExit(f"sheet 50 table {tk!r}: forms missing for "
                             f"n = {missing} (D75)")
    if not cnp:
        raise SystemExit("sheet 50 Count-NP tables: no rows read (D75)")
    out["count_np_tables"] = {tk: [forms[n] for n in range(1, 11)]
                              for tk, forms in cnp.items()}

    # ---- 53 Proper names (v2.3): the profile's data values in Welsh ------
    names = {}
    if "53 Proper names" in wb.sheetnames:
        for r53 in rows_of(wb["53 Proper names"]):
            if len(r53) >= 3 and r53[0] and r53[1] and r53[0] != "Kind" and r53[2]:
                names[r53[1]] = r53[2]
    out["proper_names"] = names

    # ---- handoff strings ---------------------------------------------------
    strings = []
    if handoff_path:
        hwb = openpyxl.load_workbook(handoff_path, data_only=True)
        for r in rows_of(hwb["Strings"]):
            if len(r) < 6 or not r[0] or r[0] == "#":
                continue
            strings.append({"cat": r[1], "owner": r[2], "key": r[3],
                            "en": r[4], "cy": r[5] or None})
    out["handoff"] = strings

    return out


def main():
    fw = sys.argv[1]
    ho = sys.argv[2] if len(sys.argv) > 2 else None
    data = build(fw, ho)
    dest = CONFIG_DIR / "welsh_lexicon.json"
    dest.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                    encoding="utf-8")
    print(f"welsh lexicon: {dest}")
    print("  audiences:", len(data["audiences"]),
          "| qualifiers:", len(data["qualifiers"]),
          "| answer labels:", len(data["answer_labels"]),
          "| predicates:", len(data["predicates"]),
          "| handoff strings:", len(data["handoff"]),
          "| handoff translated:",
          sum(1 for s in data["handoff"] if s["cy"]))


if __name__ == "__main__":
    main()
