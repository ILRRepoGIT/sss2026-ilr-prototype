# -*- coding: utf-8 -*-
"""Welsh grammar engine for the SSS2026 bilingual report.

Implements the rule sheets of the Welsh Generation Framework v1.5:
mutations (06/07), cardinals (08), ordinals (09), the article (10),
conjunctions and list construction (11), noun morphology (13, lexical
lookup only), and the exceptions register (25). Every rule here is
transcribed from the framework; sources are cited in the workbook.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from .common import CONFIG_DIR

_LEX = None


def lexicon():
    global _LEX
    if _LEX is None:
        _LEX = json.loads((CONFIG_DIR / "welsh_lexicon.json")
                          .read_text(encoding="utf-8"))
    return _LEX


# ---------------------------------------------------------------- mutations
# Sheet 06. Consonants not listed are immutable.
SOFT_MAP = {"p": "b", "t": "d", "c": "g", "b": "f", "d": "dd",
            "g": "", "ll": "l", "m": "f", "rh": "r"}
NASAL_MAP = {"p": "mh", "t": "nh", "c": "ngh", "b": "m", "d": "n", "g": "ng"}
ASP_MAP = {"p": "ph", "t": "th", "c": "ch"}

VOWELS = "aeiouwyâêîôûŵŷáéíóúàèìòù"

# EX-01..04: lexical exceptions that never mutate
IMMUTABLE_WORDS = {"gêm", "golff", "gamblo", "garej", "gêr", "gerbocs",
                   "gliw", "miliwn", "biliwn"}

_IMMUTABLE_HEADS = None          # (id of the lexicon it was built from, set)
_TRAIL = ",.;:!?)’'\"”"


def _core(word):
    """The word as a dictionary key: case-folded, trailing punctuation
    dropped — 'golff,' and 'Parkour' look up as golff and parkour."""
    return str(word or "").lower().rstrip(_TRAIL)


def immutable_heads():
    """The words that never mutate on ANY path: the exceptions register
    (EX-01..04, IMMUTABLE_WORDS) plus the first word of every answer label
    the translator marked 'Mutable? NO' on sheet 23 — the unadapted loans
    (PR-05 / EX-04: Parkour, Badminton, Boccia, BMX, Padel, Pickleball,
    Triathlon, Taekwondo, Muay Thai, Majorettes …) and the recent g-
    borrowings (EX-01..03: golff, gymnasteg) — case-folded.

    V6.0 (production pilot review, 23 Sep 2026, finding A03): label_after_soft
    honoured the flag, but a label that had been joined into a list or a
    counted phrase reached soft_phrase / aspirate_phrase / conj_and as plain
    text and was mutated by its initial — 'a Pharkour', 'mwy o Barkour',
    'am Fadminton', 'am ymnasteg', 'a Thriathlon', 'mwy o FMX', 'am olff,'
    (the trailing comma defeated the IMMUTABLE_WORDS lookup). The flag is the
    translator's data, read from the lexicon here; nothing is listed in code."""
    global _IMMUTABLE_HEADS
    lex = lexicon()
    if _IMMUTABLE_HEADS is None or _IMMUTABLE_HEADS[0] != id(lex):
        heads = set(IMMUTABLE_WORDS)
        for lab in (lex.get("answer_labels") or {}).values():
            if not isinstance(lab, dict) or lab.get("mutable", True):
                continue
            for form in (lab.get("cy"), lab.get("prose")):
                head = _core(str(form or "").split(" ", 1)[0])
                if head and head[:1].isalpha():
                    heads.add(head)
        _IMMUTABLE_HEADS = (id(lex), heads)
    return _IMMUTABLE_HEADS[1]


def _initial(word):
    """(digraph-aware initial, rest). Case-insensitive initial."""
    w = word
    low = w.lower()
    for dg in ("ll", "rh", "ch", "th", "ph", "ff", "ng"):
        if low.startswith(dg):
            return dg, w[2:]
    return (low[:1], w[1:]) if w else ("", "")


def is_vowel_initial(word):
    return bool(word) and word.lower().lstrip("‘’'\"“”")[:1] in VOWELS


def _apply_map(word, mapping, exempt_ll_rh=False):
    if not word:
        return word
    if _core(word) in immutable_heads():
        return word
    ini, rest = _initial(word)
    if ini in ("ll", "rh") and exempt_ll_rh:
        return word
    if ini not in mapping:
        return word
    repl = mapping[ini]
    # case preservation: keep an initial capital
    if word[:1].isupper():
        if repl == "":
            return rest[:1].upper() + rest[1:] if rest else rest
        return repl[:1].upper() + repl[1:] + rest
    return repl + rest


def soft(word, exempt_ll_rh=False, mutable=True):
    """Soft mutation (treiglad meddal)."""
    if not mutable:
        return word
    return _apply_map(word, SOFT_MAP, exempt_ll_rh=exempt_ll_rh)


def nasal(word, mutable=True):
    if not mutable:
        return word
    return _apply_map(word, NASAL_MAP)


def aspirate(word, mutable=True):
    if not mutable:
        return word
    return _apply_map(word, ASP_MAP)


def soft_phrase(phrase, mutable=True):
    """Soft-mutate the first word of a phrase (labels are phrases)."""
    if not phrase or not mutable:
        return phrase
    parts = phrase.split(" ", 1)
    head = soft(parts[0])
    return head + (" " + parts[1] if len(parts) > 1 else "")


def aspirate_phrase(phrase, mutable=True):
    if not phrase or not mutable:
        return phrase
    parts = phrase.split(" ", 1)
    head = aspirate(parts[0])
    return head + (" " + parts[1] if len(parts) > 1 else "")


# ---------------------------------------------------------------- numerals
# Sheet 08. First-word vigesimal reading, used for a/ac and y/yr before a
# figure (CONJ-06) — only the initial sound matters.
_UNIT_FIRST = {0: "sero", 1: "un", 2: "dau", 3: "tri", 4: "pedwar",
               5: "pum", 6: "chwe", 7: "saith", 8: "wyth", 9: "naw"}
_TEEN_FIRST = {10: "deg", 11: "un", 12: "deuddeg", 13: "tri", 14: "pedwar",
               15: "pymtheg", 16: "un", 17: "dau", 18: "deunaw", 19: "pedwar"}
_TENS_FIRST = {20: "ugain", 30: "deg", 40: "deugain", 50: "hanner",
               60: "trigain", 70: "deg", 80: "pedwar", 90: "deg"}


def reading_first_word(n):
    """The first word of the vigesimal reading of n (for CONJ-06/ART).
    Corrected v4.5: 21-39 read as ⟪1-19⟫ ar hugain, so 36 leads with
    'un' (un ar bymtheg ar hugain), not with its unit digit."""
    n = int(n)
    if n >= 200:
        return reading_first_word(n // 100)
    if n >= 100:
        return "cant"
    if n == 80:
        return "pedwar"
    if n > 80:
        return reading_first_word(n - 80)
    if n == 60:
        return "trigain"
    if n > 60:
        return reading_first_word(n - 60)
    if n == 40:
        return "deugain"
    if n > 40:
        return reading_first_word(n - 40)
    if n == 20:
        return "ugain"
    if n > 20:
        return reading_first_word(n - 20)
    if n >= 10:
        return _TEEN_FIRST[n]
    return _UNIT_FIRST[n]


def decimal_first_word(n):
    """The first word of the DECIMAL reading of n (un deg un, dau ddeg,
    cant, mil …) — the alternative CONJ-06 reading the translator named
    (sheet 4 rule 15, 21 Sep 2026)."""
    n = int(n)
    if n >= 1000:
        return "mil" if n < 2000 else _UNIT_FIRST[n // 1000]
    if n >= 100:
        return "cant" if n < 200 else _UNIT_FIRST[n // 100]
    if n >= 20:
        return _UNIT_FIRST[n // 10]
    if n >= 11:
        return "un"
    if n == 10:
        return "deg"
    return _UNIT_FIRST[n]


def conj06_mode():
    """CONJ-06 (sheet 11): how a FIGURE is read for a/ac and y/yr —
    'figure' (translator's ruling, 21 Sep 2026: figures are symbols and
    take 'a' / 'y' without sandhi), 'decimal' or 'vigesimal' (the v1.5–
    v2.6 rule). Read from the workbook; absent in a pre-v2.7 workbook
    means vigesimal."""
    return lexicon().get("conj06_mode", "vigesimal")


def figure_lead(n):
    """The word whose initial decides a/ac and y/yr before figure n under
    the configured CONJ-06 mode; None when figures are symbols."""
    mode = conj06_mode()
    if mode == "figure":
        return None
    if mode == "decimal":
        return decimal_first_word(n)
    if mode == "vigesimal":
        return reading_first_word(n)
    raise SystemExit(f"sheet 11 CONJ-06: unknown MODE {mode!r} — refusing to guess")


NUM_WORD_M = {1: "un", 2: "dau", 3: "tri", 4: "pedwar", 5: "pum",
              6: "chwe", 7: "saith", 8: "wyth", 9: "naw", 10: "deg"}
NUM_WORD_F = {1: "un", 2: "dwy", 3: "tair", 4: "pedair", 5: "pum",
              6: "chwe", 7: "saith", 8: "wyth", 9: "naw", 10: "deg"}


def num_with_noun(n, noun_sg, gender, mutable=True, as_word=True):
    """Counted noun phrase: noun SINGULAR after the numeral, with the
    numeral's own mutation (sheet 08). Words for 1-10 when as_word."""
    n = int(n)
    g = (gender or "m").lower()[:1]
    if n > 10 or not as_word:
        return f"{n} {noun_sg}"
    word = (NUM_WORD_F if g in ("f", "b") else NUM_WORD_M)[n]
    noun = noun_sg
    if n == 1:
        if g in ("f", "b"):
            noun = soft(noun_sg, exempt_ll_rh=True, mutable=mutable)
    elif n == 2:
        noun = soft(noun_sg, mutable=mutable)
    elif n == 3 and g not in ("f", "b"):
        noun = aspirate(noun_sg, mutable=mutable)
    elif n == 6:
        noun = aspirate(noun_sg, mutable=mutable)
    return f"{word} {noun}"


def partitive(n, noun_pl, mutable=True):
    """'N o ⟪soft plural⟫' — the statistical partitive (digits, D19)."""
    return f"{int(n)} o {soft_phrase(noun_pl, mutable=mutable)}"


def pct(n):
    return f"{n}%"


# ---------------------------------------------------------------- ordinals
# Sheet 09 — vigesimal only; distinct feminine stems for 3rd/4th.
_ORD_M = {1: "cyntaf", 2: "ail", 3: "trydydd", 4: "pedwerydd", 5: "pumed",
          6: "chweched", 7: "seithfed", 8: "wythfed", 9: "nawfed",
          10: "degfed", 11: "unfed ar ddeg", 12: "deuddegfed",
          13: "trydydd ar ddeg", 14: "pedwerydd ar ddeg", 15: "pymthegfed",
          16: "unfed ar bymtheg", 17: "ail ar bymtheg", 18: "deunawfed",
          19: "pedwerydd ar bymtheg", 20: "ugeinfed"}
_ORD_F = {1: "gyntaf", 2: "ail", 3: "drydedd", 4: "bedwaredd", 5: "bumed",
          6: "chweched", 7: "seithfed", 8: "wythfed", 9: "nawfed",
          10: "ddegfed", 11: "unfed ar ddeg", 12: "ddeuddegfed",
          13: "drydedd ar ddeg", 14: "bedwaredd ar ddeg", 15: "bymthegfed",
          16: "unfed ar bymtheg", 17: "ail ar bymtheg", 18: "ddeunawfed",
          19: "bedwaredd ar bymtheg", 20: "ugeinfed"}


def ordinal(n, gender="m", with_article=True):
    n = int(n)
    g = (gender or "m").lower()[:1]
    table = _ORD_F if g in ("f", "b") else _ORD_M
    word = table.get(n, f"{n}fed")
    if not with_article:
        return word
    art = "yr" if is_vowel_initial(word) else "y"
    return f"{art} {word}"


# ----------------------------------------------------------------- article
def article(next_word, prev_word=None):
    """Sheet 10: 'r after a vowel-final word; yr before a vowel or h-;
    else y. Digits use their vigesimal reading."""
    if prev_word and prev_word[-1:].lower() in VOWELS:
        return "'r"
    probe = next_word
    m = re.match(r"\d+", str(next_word))
    if m:
        lead = figure_lead(int(m.group(0)))
        if lead is None:          # CONJ-06 MODE=figure: a symbol takes y
            return "y"
        probe = lead
    p = str(probe).lstrip("‘’'\"“”")
    if p[:1].lower() in VOWELS or p[:1].lower() == "h":
        return "yr"
    return "y"


def with_article(noun, gender="m", plural=False, mutable=True):
    """Article + noun with ART-06 (feminine singular soft, not ll-/rh-)."""
    n = noun
    if gender and gender.lower()[:1] in ("f", "b") and not plural:
        n = soft(noun, exempt_ll_rh=True, mutable=mutable)
    return f"{article(n)} {n}"


# -------------------------------------------------------------- conjunction
def _ac_fnwords():
    """CONJ-03 function-word list — CONFIGURATION from sheet 11 (D67/PR-13),
    never hard-coded. Normalised to straight apostrophes for matching."""
    return {w.replace("’", "'").lower() for w in lexicon()["ac_fnwords"]}


def conj_and(next_item, mutate=True):
    """The ONE conjunction service (D67): correct 'and' + the (possibly
    aspirated) item on every boundary (CONJ-01..06).
    PR-04 (data value from sheet 39): the form before the negative
    particles ni / nid. PR-13: 'ac' before the CONJ-03 function words,
    read from sheet 11."""
    item = str(next_item)
    probe = item.lstrip("‘’'\"“”")
    if re.match(r"(?:ni|nid)\b", probe, re.I):
        return pr("PR-04", "ac"), item
    m = re.match(r"\d+", probe)
    if m:
        lead = figure_lead(int(m.group(0)))
        if lead is None:
            # CONJ-06 MODE=figure (sheet 11, translator's ruling of
            # 21 Sep 2026): a figure written in digits is a symbol — it
            # takes 'a' and never mutates ('ac 36' → 'a 36', 'ac 11' →
            # 'a 11'); words keep CONJ-01..04.
            return "a", item
        probe = lead
    first = re.split(r"\s", probe.replace("’", "'"), 1)[0].lower()
    p0 = probe[:1].lower()
    if first in _ac_fnwords():
        # PR-13: the operative value is the sheet-11 list itself, consumed
        # via _ac_fnwords(); the conjunction before a list member is 'ac'.
        return "ac", item
    if p0 == "h":
        return "a", item
    if p0 in VOWELS:
        return "ac", item
    # quoted labels are citation forms and do not mutate (EX-29)
    if item[:1] in "‘'\"“":
        return "a", item
    return "a", (aspirate_phrase(item) if mutate else item)


def join_list(items, mutate_last=True):
    """CONJ-10 list construction: commas, final pair joined by a/ac with
    the aspirate on the final item."""
    items = [str(i) for i in items if i]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    conj, last = conj_and(items[-1], mutate=mutate_last)
    head = ", ".join(items[:-1])
    return f"{head} {conj} {last}"


def conj_neu(item, mutable=True):
    """'neu' + soft mutation on nouns/verb-nouns/adjectives (CONJ-09)."""
    return f"neu {soft_phrase(str(item), mutable=mutable)}"


# ------------------------------------------------------------- year phrases
def year_loc(year_label):
    """'Year 8' -> 'ym Mlwyddyn 8' (nasal after locative yn)."""
    m = re.search(r"(\d+)", str(year_label))
    n = m.group(1) if m else str(year_label)
    return f"ym Mlwyddyn {n}"


def year_cite(year_label):
    m = re.search(r"(\d+)", str(year_label))
    n = m.group(1) if m else str(year_label)
    return f"Blwyddyn {n}"


# ----------------------------------------------------------- label services
def label_cy(en_label, form="cy"):
    """Welsh form of an answer label from framework sheet 23.
    form: cy (table form) | prose. Falls back to the English label and
    records the miss so builds fail loudly."""
    lab = lexicon()["answer_labels"].get(str(en_label))
    if lab is None:
        _MISSES.add(("label", str(en_label)))
        return str(en_label)
    return lab.get("prose") if form == "prose" and lab.get("prose") else lab["cy"]


def label_entry(en_label):
    return lexicon()["answer_labels"].get(str(en_label))


def term(en_noun):
    """The Welsh of a core noun from framework sheet 17 (v2.7: the term
    for 'long-term condition' lives there, never in a renderer literal).
    A missing row is a recorded miss — the build fails, never a guess."""
    row = lexicon()["core_nouns"].get(str(en_noun))
    if row is None or not row.get("cy"):
        _MISSES.add(("core_noun", str(en_noun)))
        return str(en_noun)
    return row["cy"]


def label_after_soft(en_label, quoted=False):
    """A label in a soft-mutation environment (after o/am/i/gan or as the
    object of an inflected verb). Quoted citation forms do not mutate
    (EX-29); unadapted names do not mutate (EX-04) — per the framework's
    golden tests T-032/T-033 a label whose Welsh form is identical to the
    English is treated as unadapted (Tennis, BMX, Boccia), while adapted
    Welsh forms mutate (a ddewisodd Bêl Droed, T-035)."""
    e = label_entry(en_label)
    if quoted:
        return label_cy(en_label)              # citation form, no mutation
    # D21 / PR-10: running prose uses the prose form, case-folded BEFORE
    # mutation; unadapted names (PR-05) and quoted citations stay put.
    cy = label_cy(en_label, "prose")
    if e is None or not e.get("mutable"):
        return cy
    if cy.strip().lower() == str(en_label).strip().lower():
        return cy
    return soft_phrase(cy)


_MISSES = set()


def misses():
    return sorted(_MISSES)


# --------------------------------------------------------------- audiences
_SCOPE_EN = {"whole": "across the whole school",
             "primary": "in the primary phase",
             "secondary": "in the secondary phase"}


def audience_en_name(scope, gender):
    head = {"all": "pupils", "boy": "boys", "girl": "girls"}[gender]
    if scope.startswith("y") and scope[1:].isdigit():
        yr = scope[1:]
        return f"Year {yr} {head}"
    return f"{head} {_SCOPE_EN[scope]}"


def audience(scope, gender, form):
    """One of the six contextual forms from framework sheet 21.
    form: bare | def_sg | after_o | after_or | ymhlith | def_pl | holl"""
    name = audience_en_name(scope, gender)
    a = lexicon()["audiences"].get(name)
    if a is None:
        _MISSES.add(("audience", name))
        return name
    return a[form]


# --------------------------------------------------------------- qualifiers
_QUAL_INDEX = None
_NORM = lambda s: re.sub(r"[’‘]", "'", re.sub(r"\s+", " ", s or "")).strip().lower()


def _qual_index():
    global _QUAL_INDEX
    if _QUAL_INDEX is None:
        _QUAL_INDEX = {}
        for q in lexicon()["qualifiers"]:
            _QUAL_INDEX[(q["family"], _NORM(q["en"]))] = q["cy"]
    return _QUAL_INDEX


def qualifier_cy(family, en_phrase, answer_label=None):
    """The Welsh relative clause for a cohort qualifier (sheet 22).
    Parameterised families substitute the answer label with the mutation
    the frame specifies."""
    idx = _qual_index()
    key = (family, _NORM(en_phrase))
    if key in idx:
        return idx[key]
    # parameterised rows: find the family's slot row
    for q in lexicon()["qualifiers"]:
        if q["family"] != family or "⟪" not in q["en"]:
            continue
        pat = re.escape(_NORM(q["en"]))
        pat = pat.replace(re.escape("⟪answer⟫"), "(.+)")
        pat = pat.replace(re.escape("'⟪answer⟫'"), "'(.+)'")
        m = re.fullmatch(pat, _NORM(en_phrase))
        if m:
            en_ans = answer_label or m.group(1)
            cy = q["cy"]
            if "⟪ANSWER:OBJ⟫" in cy:
                return cy.replace("⟪ANSWER:OBJ⟫", label_after_soft(en_ans))
            if "⟪ANSWER:AFTER_O⟫" in cy:
                return cy.replace("⟪ANSWER:AFTER_O⟫", label_after_soft(en_ans))
            if "⟪ANSWER:PRED⟫" in cy:
                return cy.replace("⟪ANSWER:PRED⟫",
                                  soft_phrase(label_cy(en_ans, "prose")))
            if "‘⟪ANSWER⟫’" in cy:
                # D46: the frame owns this quote pair — insert the bare
                # citation form, never a second pair
                return cy.replace("‘⟪ANSWER⟫’", f"‘{label_cy(en_ans)}’"
                                  ).replace("‘‘", "‘").replace("’’", "’")
            if "⟪ANSWER⟫" in cy:
                # unquoted slot: the citation renderer adds exactly one pair
                return cy.replace("⟪ANSWER⟫", f"‘{label_cy(en_ans)}’")
    _MISSES.add(("qualifier", family, en_phrase))
    return None


# ======================================================== D40 — ONE REALISER
# Framework v1.6, decision D40: the numeral form, the noun's number, the
# mutation and the partitive are chosen TOGETHER by one function receiving
# value, gender, definiteness and syntactic role. No caller formats a
# number itself. Rules: D03 (words 1-10 before a noun, digits 11+ and in
# mixed-magnitude series), D19 (three counting branches), sheet 08
# (numeral-triggered mutations), sheet 10 (article; y ddau / y ddwy only).
#
# Two engineering constraints, both recorded for the linguist:
#  * the corpus figure-parity checker's Welsh number vocabulary lacks the
#    soft form 'dri' and the aspirate 'phump'; the realiser therefore
#    prefers constructions that never need them (aspirating 'gyda' frames
#    over 'gan' agents for small counts; absolute 'pump' only before 'o').
#  * zero is NEVER realised: Welsh has no positive nil count (FT-01 N=0,
#    NUM-N0-NEG). Passing n=0 raises, forcing the template's negative
#    branch — a deliberate D44 fail-loud.

_ABS = {5: "pump", 6: "chwech"}          # absolute forms away from a noun


class ZeroCount(ValueError):
    """n=0 reached a positive-count realisation (must use NUM-N0-NEG)."""


def _num_word_g(n, gender):
    g = (gender or "m").lower()[:1]
    return (NUM_WORD_F if g in ("f", "b") else NUM_WORD_M)[int(n)]


def _noun_after_num(n, noun_sg, gender, mutable=True):
    """The mutation the numeral itself causes on its SINGULAR noun (08)."""
    n = int(n)
    g = (gender or "m").lower()[:1]
    fem = g in ("f", "b")
    if n == 1:
        return soft(noun_sg, exempt_ll_rh=True, mutable=mutable) if fem else noun_sg
    if n == 2:
        return soft(noun_sg, mutable=mutable)
    if n == 3 and not fem:
        return aspirate(noun_sg, mutable=mutable)
    if n == 6:
        if noun_sg.lower().startswith(("blynedd", "blwydd")):
            return noun_sg
        return aspirate(noun_sg, mutable=mutable)
    return noun_sg


def num_noun(n, noun_sg, gender="m", mutable=True):
    """Indefinite counted unit: 'tair camp', 'chwe champ', '12 disgybl'."""
    n = int(n)
    if n == 0:
        raise ZeroCount(noun_sg)
    if n > 10:
        return f"{n} {noun_sg}"
    return f"{_num_word_g(n, gender)} {_noun_after_num(n, noun_sg, gender, mutable)}"


def def_num_noun(n, noun_sg, gender="m", mutable=True):
    """After the article ('the N pupils'): only dau/dwy mutate after y
    (sheet 08 notes: y ddau / y ddwy; tair does not mutate; y pedair
    lenition is optional and not taken). Returns WITHOUT the article."""
    n = int(n)
    if n == 0:
        raise ZeroCount(noun_sg)
    if n > 10:
        return f"{n} {noun_sg}"
    w = _num_word_g(n, gender)
    if n == 2:
        w = "ddau" if w == "dau" else "ddwy"
    return f"{w} {_noun_after_num(n, noun_sg, gender, mutable)}"


def gyda_num(n, noun_sg, noun_pl, gender="m", mutable=True):
    """'gyda' + counted unit: gydag un o'r disgyblion / gyda phum disgybl /
    gyda 225 o ddisgyblion. gyda aspirates; every aspirated word form
    (thri, thair, phedwar, phedair, phum) is parity-safe. n=1 takes the
    'un o'r ⟪plural⟫' partitive (D48/G9b: 'un ⟪singular noun⟫' inside a
    paragraph that also carries a plural cohort qualifier reads as an
    agreement clash to the acceptance gate)."""
    n = int(n)
    if n == 0:
        raise ZeroCount(noun_sg)
    if n == 1:
        return f"gydag un o’r {noun_pl}"
    if n > 10:
        return f"gyda {n} o {soft_phrase(noun_pl, mutable=mutable)}"
    w = _num_word_g(n, gender)
    w = {"tri": "thri", "tair": "thair", "pedwar": "phedwar",
         "pedair": "phedair", "pum": "phum"}.get(w, w)
    return f"gyda {w} {_noun_after_num(n, noun_sg, gender, mutable)}"


def count_partitive(n, noun_sg, noun_pl, gender="m", mutable=True):
    """D19 counting construction: n=1 -> 'un' + singular (no partitive);
    2..10 -> word (absolute form) + o + soft plural; 11+ -> digits + o +
    soft plural."""
    n = int(n)
    if n == 0:
        raise ZeroCount(noun_sg)
    if n == 1:
        return f"un {_noun_after_num(1, noun_sg, gender, mutable)}"
    if n > 10:
        return f"{n} o {soft_phrase(noun_pl, mutable=mutable)}"
    w = _ABS.get(n, _num_word_g(n, gender))
    return f"{w} o {soft_phrase(noun_pl, mutable=mutable)}"


def of_base(base, phrase, gender="m", mutable=True):
    """\"o'r ⟪BASE⟫ ⟪noun-phrase⟫\": the definite base of a partitive.
    phrase is the audience noun phrase whose FIRST word is the counted
    noun ('disgybl yn yr ysgol gyfan'). Words for 1-10 (D03), the
    definite-numeral mutation of def_num_noun, digits above ten."""
    base = int(base)
    head, _, rest = phrase.partition(" ")
    if base == 0:
        raise ZeroCount(head)
    if base == 1:
        # D48/G9b (v1.7): 'yr unig ⟪noun⟫' — the only pupil — reads as
        # what it is, and keeps the singular head visibly singular even
        # when the sentence also carries a plural cohort clause
        unit = f"unig {soft(head, mutable=mutable)}"
    else:
        unit = def_num_noun(base, head, gender, mutable)
    return f"o’r {unit} {rest}".rstrip() if rest else f"o’r {unit}"


def numerator(n, gender="m", prep=None):
    """A bare count with no noun of its own ('… dywedodd N o'r …').
    v1.7 (G8a/G8b): words for 1-10 — the V4.3 figure-before-worded-base
    juxtaposition ('9 o'r naw') was the defect the old gate missed.
    Absolute forms away from a noun (pump, chwech); soft after gan."""
    n = int(n)
    if n == 0:
        raise ZeroCount("numerator")
    if n > 10:
        return str(n)
    w = _ABS.get(n, _num_word_g(n, gender))
    if prep == "gan":
        w = {"dau": "ddau", "dwy": "ddwy", "tri": "dri", "tair": "dair",
             "pedwar": "bedwar", "pedair": "bedair", "pump": "bump",
             "deg": "ddeg"}.get(w, w)
    return w


def gan_count(n, noun_sg, noun_pl, gender="m", mutable=True):
    """'gan' + agent count: gan un ⟪sg⟫ / gan ⟪soft word⟫ o ⟪soft pl⟫ /
    gan ⟪digits⟫ o ⟪soft pl⟫ (D19 + gan-triggered soft mutation)."""
    n = int(n)
    if n == 0:
        raise ZeroCount(noun_sg)
    if n == 1:
        return f"gan un o’r {noun_pl}"
    if n > 10:
        return f"gan {n} o {soft_phrase(noun_pl, mutable=mutable)}"
    return (f"gan {numerator(n, gender, 'gan')} o "
            f"{soft_phrase(noun_pl, mutable=mutable)}")


def sg_qual(qual, gender=None):
    """D62: the N = 1 realisation of a qualifier frame. Sheet 44 gives the
    singleton form of every family that carries a plural feature, in three
    gendered columns — known boy (m), known girl (f), and unknown sex,
    which under PR-14 agrees with the grammatical gender of the antecedent
    noun (disgybl, masculine). Possession roles are REALISED
    (ganddo / ganddi), NEVER deleted: the possessor is a role on the fact
    record, and deleting it also orphans the mutation it licensed."""
    if not qual:
        return qual
    col = "f" if gender == "girl" else ("m" if gender == "boy" else "u")
    girl = col == "f"
    out = qual
    # 1. Whole-clause frames from sheet 44, longest first, e7 predicate
    #    rows excluded (they are templates consumed by the renderer).
    frames = [r for r in lexicon().get("singleton_frames", [])
              if r["family"] != "e7" and r["pl"] and "⟪" not in r["pl"]]
    for r in sorted(frames, key=lambda r: -len(r["pl"])):
        if r["pl"] in out:
            out = out.replace(r["pl"], r[col])
    # 2. Generic 3sg verb agreement for clauses sheet 44 does not list
    #    (no plural possession inside them).
    for a, b in [("yr hoffent", "yr hoffai"), ("nad ydynt", "nad yw"),
                 ("a ydynt", "a yw"), ("y maent", "y mae"),
                 ("nad oeddent", "nad oedd"), ("a oeddent", "a oedd"),
                 ("yr oeddent", "yr oedd"), ("y byddent", "y byddai"),
                 ("pe baent", "pe bai’n"), ("gallant", "gall"),
                 # identity clauses recast pronoun-free (PR-03): the set is
                 # defined by the answer, so 'sy'n' carries it singularly
                 ("a nododd eu bod yn", "sy’n"),
                 ("a ddywedodd eu bod fel arfer yn", "sydd fel arfer yn"),
                 ("a ddywedodd eu bod yn", "sy’n")]:
        out = out.replace(a, b)
    # 3. Realised 3sg possession and prepositions for the residue —
    #    the same rule sheet 44 applies, with PR-14 for unknown sex.
    out = out.replace("ganddynt", "ganddi" if girl else "ganddo")
    out = out.replace("iddynt", "iddi" if girl else "iddo")
    out = out.replace("eu bod", "ei bod" if girl else "ei fod")
    # 4. Residual 'eu <noun>' possessives: ei + h-prothesis (f) / ei (m).
    #    Object-pronoun uses ('eu dweud' after gall) are left alone.
    _VOW = "aeiouwyâêîôûŵŷ"

    def _ei(m):
        h, w = m.group(1), m.group(2)
        base = w if (h and w[:1] in _VOW) else h + w   # undo h-prothesis
        if base in ("dweud", "gwneud", "cael", "dewis", "gweld", "hoffi",
                    "mwynhau", "chwarae", "cynnwys", "nodi", "trin",
                    "adrodd", "hadrodd"):
            return m.group(0)          # object pronoun, number of the object
        if girl:                       # ei (f): spirant + h-prothesis
            if base[:1] in _VOW:
                return f"ei h{base}"
            return f"ei {aspirate(base)}"
        return f"ei {soft(base)}"      # ei (m): soft mutation
    out = re.sub(r"\beu (h?)(\w+)", _ei, out)
    return out


def pr(pr_id, default=None):
    """D51: the operative value of a provisional ruling, read from the
    framework workbook (sheet 39) — never a literal in code."""
    for row in lexicon().get("provisional_rulings", []):
        if row["id"] == pr_id:
            return row["value"]
    if default is not None:
        return default
    _MISSES.add(("provisional_ruling", pr_id))
    return None


def pr_set():
    """The active provisional-ruling set, for the build metadata stamp."""
    return [{"id": r["id"], "value": r["value"], "ruledBy": r["ruled_by"]}
            for r in lexicon().get("provisional_rulings", [])]
