"""Shared configuration, label maps and parsing helpers.

School Sport Survey 2026 - Interactive Learning Report prototype pipeline.
All processing happens at build time; nothing in this package runs in the
browser.
"""
from __future__ import annotations

import re as _re

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import yaml

PIPELINE_VERSION = "0.1.0"
SCHEMA_VERSION = "0.1"
REPORT_VERSION = "2026-prototype-001"

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
# v6 (pipeline 0.28.0, V5.0 real-school round): one build tree per school.
# SSS_GENERATED_DIR names the output directory of THIS build (report
# package, evidence, bundle); unset, it is the prototype's generated/.
import os as _os
GENERATED_DIR = Path(_os.environ["SSS_GENERATED_DIR"]).resolve() \
    if _os.environ.get("SSS_GENERATED_DIR") else ROOT / "generated"
# The school profile the build reads (SSS_SCHOOL_PROFILE); unset, the
# prototype school (config/school_profile.json). Every per-school value —
# name, authority, years, scope groups, accepted statuses — comes from it.
SCHOOL_PROFILE_PATH = Path(_os.environ["SSS_SCHOOL_PROFILE"]).resolve() \
    if _os.environ.get("SSS_SCHOOL_PROFILE") else CONFIG_DIR / "school_profile.json"

RE_MATRIX_CELL = re.compile(r"\{[^{}]*\}")

# --------------------------------------------------------------------------
# Fixed code -> display label maps (codes are stable identifiers used in the
# report package; labels are the English display strings).
# --------------------------------------------------------------------------
LABELS = {
    "freq": {
        "less_weekly": "Less than once a week",
        "once_week": "1 time a week",
        "twice_week": "2 times a week",
        "three_plus": "Three or more times a week",
        "dont_know": "I don’t know",
    },
    "settings": {
        "pe_lessons": "In PE or lesson time",
        "school_club": "In a school club",
        "community_club": "In a club outside of school",
        "somewhere_else": "Somewhere else",
    },
    "join_in": {
        "always": "Yes, always",
        "sometimes": "Yes, sometimes",
        "not_often": "No, not often",
        "never": "Never",
    },
    "listened": {
        "always": "Always",
        "sometimes": "Sometimes",
        "not_often": "Not often",
        "never": "Never",
    },
    "welsh": {
        "very_well": "I can speak Welsh very well",
        "fair_amount": "I can speak a fair amount of Welsh",
        "a_little": "I can speak a little Welsh",
        "few_words": "I can say just a few words in Welsh",
        "none": "I do not speak Welsh",
    },
    "yes_no": {"yes": "Yes", "no": "No"},
    "enjoy": {
        "a_lot": "A lot",
        "a_little": "A little",
        "not_much": "Not much",
        "not_at_all": "Not at all",
        "not_sure": "Not sure",
    },
    "confidence": {
        "very": "Very",
        "quite": "Quite",
        "not_very": "Not very",
        "not_at_all": "Not at all",
    },
    "disability": {
        "yes": "Yes",
        "no": "No",
        "not_sure": "Not sure",
        "prefer_not_to_say": "Prefer not to say",
    },
    "take_part": {
        "standing": "Standing",
        "seated": "Seated",
        "communication_aids": "With communication aids",
        "not_sure": "I’m not sure",
        "prefer_not_to_say": "Prefer not to say",
        "other": "Other",
    },
    "more_if": {
        "more_sports_liked": "There were more sports I liked",
        "more_confident": "I felt more confident",
        "easier_to_take_part": "It was easier to take part",
        "more_motivated": "I felt more motivated",
        "more_comfortable": "It felt more comfortable for me",
        "equipment_or_cost": "I had what I need or it cost less",
        "other": "Other",
        "none_of_these": "None of these",
    },
    "important": {
        "having_fun": "Having fun",
        "friends": "Being with friends",
        "improving_skills": "Improving my skills",
        "feeling_confident": "Feeling confident",
        "winning": "Winning",
        "coach_or_teacher": "Liking my coach or teacher",
        "feeling_safe": "Feeling safe",
        "equipment_facilities": "Access to good equipment and facilities",
        "other": "Other",
        "none_of_these": "None of these",
    },
    "years": {f"y{n}": f"Year {n}" for n in range(3, 12)},
    "gender_display": {"boy": "Boys", "girl": "Girls",
                       "nonbinary": "Non-binary",
                       "not_stated": "Prefer not to say"},
    "organised_freq": {
        "none_reported": "No club sport reported",
        "less_weekly": "Less than once a week",
        "once_week": "1 time a week",
        "twice_week": "2 times a week",
        "three_plus": "Three or more times a week",
        "dont_know": "I don’t know",
    },
    "overall_freq": {
        # v2.2: accumulated weekly occasions on the 0-to-7-plus scale
        # (meeting decision P02); true zero kept distinct from positive
        # but less-than-weekly participation (decision D08)
        "none_reported": "No sport reported",
        "less_weekly_only": "Less than once a week",
        "w1": "1 time a week",
        "w2": "2 times a week",
        "w3": "3 times a week",
        "w4": "4 times a week",
        "w5": "5 times a week",
        "w6": "6 times a week",
        "w7": "7 or more times a week",
    },
    "club_freq_estimate": {
        # v5 (build 012): flat square-root method restricted to the two
        # club settings - replaces the highest-frequency calculation
        "none_reported": "No club sport reported",
        "dont_know_only": "Don\u2019t know",
        "less_weekly_only": "Less than once a week",
        "e1": "1", "e2": "2", "e3": "3", "e4": "4",
        "e5": "5", "e6": "6", "e7": "7", "e8": "8", "e9plus": "9+",
    },
    "freq_estimate": {
        # v3 (build 010): agreed estimated average weekly frequency
        "none_reported": "No sport reported",
        "dont_know_only": "Don\u2019t know",
        "less_weekly_only": "Less than once a week",
        "e1": "1", "e2": "2", "e3": "3", "e4": "4",
        "e5": "5", "e6": "6", "e7": "7", "e8": "8", "e9plus": "9+",
    },
    "setting_acc": {
        "less_weekly_only": "Less than once a week",
        "w1": "1 time a week",
        "w2": "2 times a week",
        "w3": "3 times a week",
        "w4": "4 times a week",
        "w5": "5 times a week",
        "w6": "6 times a week",
        "w7": "7 or more times a week",
    },
    "ethnicity": {
        "white": "White",
        "mixed": "Mixed or multiple ethnic groups",
        "asian": "Asian, Asian Welsh or Asian British",
        "other_grouped": "Other ethnic groups",
        "not_sure": "I’m not sure",
        "prefer_not_to_say": "Prefer not to say",
    },
}

# raw answer label -> code, for the fixed single-choice questions
RAW_TO_CODE = {
    "gender": {"a boy": "boy", "a girl": "girl", "non-binary": "nonbinary",
               "I'd prefer not to say": "not_stated"},
    "join_in": {v: k for k, v in LABELS["join_in"].items()},
    "listened": {v: k for k, v in LABELS["listened"].items()},
    "welsh": {v: k for k, v in LABELS["welsh"].items()},
    "yes_no": {"Yes": "yes", "No": "no"},
    "disability": {v: k for k, v in LABELS["disability"].items()},
    "enjoy_col": {v: k for k, v in LABELS["enjoy"].items()},
    "confidence_col": {v: k for k, v in LABELS["confidence"].items()},
    "freq_col": {v: k for k, v in LABELS["freq"].items()},
    "settings_col": {
        "In PE or Lesson Time": "pe_lessons",
        "In a school club": "school_club",
        "In a club outside of school": "community_club",
        "Somewhere else": "somewhere_else",
    },
    "take_part": {
        "Standing": "standing",
        "Seated": "seated",
        "With communication aids": "communication_aids",
        "I’m not sure": "not_sure",
        "Prefer not to say": "prefer_not_to_say",
    },
    "more_if": {v: k for k, v in LABELS["more_if"].items() if k not in ("other",)},
    "important": {v: k for k, v in LABELS["important"].items() if k not in ("other",)},
    "enjoy_row": {
        "PE lessons": "pe_lessons",
        "School sports clubs": "school_clubs",
        "Sports clubs outside of school": "community_clubs",
        "Other settings, like in the park or garden": "other_settings",
    },
    "confidence_row": {
        "Try a new sport?": "try_new",
        "Learn a new skill?": "learn_skill",
        "Try again when sport is hard?": "try_again",
        "Try sport in a new place?": "new_place",
    },
    "pe_feel_row": {
        "Healthy?": "healthy",
        "Confident?": "confident",
        "Ready to learn?": "ready_to_learn",
    },
}

FREQ_ORDER = {"three_plus": 4, "twice_week": 3, "once_week": 2, "less_weekly": 1, "dont_know": 0}

NON_SPORT_LABELS = {"None of these", "My sport isn’t here"}

# ---------------------------------------------------------------------------
# v2.3 (build 008): provisional Tier 1 / Tier 2 classification, derived from
# the survey instrument: Tier 2 sports are those offered in the routed
# "(Other category)" questions reached via "My sport isn't here".
# Classification awaiting formal Sport Wales confirmation.
# ---------------------------------------------------------------------------
TIER2_SPORTS = {
    "gym_fitness_training", "obstacle_course_racing",
    "handball", "american_football", "gaelic_games", "floorball",
    "ultimate_frisbee", "bench_ball",
    "diving", "wakeboarding", "scuba_diving", "underwater_hockey_octopush",
    "snorkelling", "jet_skiing",
    "darts", "ten_pin_bowling", "billiards", "croquet",
    "airsoft_target_shooting",
    "ballet", "aerial", "majorettes", "baton_twirling", "circus_skills",
    "breakdancing", "street_dance", "morris_dancing",
    "padel", "pickleball",
    "scootering", "orienteering", "parachuting", "ropes_courses", "gliding",
    "hiking_mountain_walking",
    "taekwondo", "kickboxing", "mixed_martial_arts_mma",
    "jiu_jitsu_including_brazilian_jiu_jitsu", "muay_thai", "kung_fu",
    "krav_maga", "figure_skating",
    # short-form codes as they appear in the export's setting grids
    "jiu_jitsu", "mixed_martial_arts", "underwater_hockey",
}
TIER2_COMPOSITE_CODE = "other_sports"
TIER2_COMPOSITE_LABEL = "Other sports (composite)"



def norm_text(s: str) -> str:
    """Normalise whitespace in an answer label."""
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", str(s))).strip()


def slugify(label: str) -> str:
    """Stable option code from a display label."""
    s = norm_text(label).lower()
    s = re.sub(r"\(.*?\)", "", s)           # drop parentheticals
    s = s.replace("’", "'")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def parse_matrix(cell_value) -> list[tuple[str, str]]:
    """Parse a SmartSurvey matrix cell: '{json}; {json}; ...'.

    Returns [(row_title, column_title), ...] with whitespace normalised.
    """
    out = []
    if cell_value is None:
        return out
    for m in RE_MATRIX_CELL.finditer(str(cell_value)):
        try:
            o = json.loads(m.group(0))
        except json.JSONDecodeError:
            continue
        row = norm_text(o.get("row_title", ""))
        col = norm_text(o.get("column_title", ""))
        if row and col:
            out.append((row, col))
    return out


def split_multi(cell_value) -> list[str]:
    """Split a '; '-separated multi-select answer into normalised labels."""
    if cell_value is None:
        return []
    return [norm_text(p) for p in str(cell_value).split(";") if norm_text(p)]


def load_config():
    profile = json.loads(SCHOOL_PROFILE_PATH.read_text(encoding="utf-8"))
    mapping = yaml.safe_load((CONFIG_DIR / "column_mapping.yml").read_text(encoding="utf-8"))
    metrics = yaml.safe_load((CONFIG_DIR / "metrics.yml").read_text(encoding="utf-8"))
    narratives = yaml.safe_load((CONFIG_DIR / "narratives.yml").read_text(encoding="utf-8"))
    return profile, mapping, metrics, narratives


def load_held_cohorts() -> dict:
    """v6 (0.28.0): cohorts HELD from the filter offering because the
    Framework carries no Welsh for the qualifier they need (D44: a missing
    Welsh entry is never composed in code). config/held_cohorts.json maps
    cohort key -> {reason, needs}. The chart bar stays, with its count,
    as a non-selectable bar (the client's existing 'cannot be selected as
    a filter' behaviour); the validation summary and the flags register
    name the hold. Absent file: nothing held."""
    p = CONFIG_DIR / "held_cohorts.json"
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def file_checksum(path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def anon_id(raw_id, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{raw_id}".encode()).hexdigest()[:12]


def plural(n: int, singular: str, plural_form: str | None = None) -> str:
    return singular if n == 1 else (plural_form or singular + "s")

def latest_framework(config_dir=None):
    """The newest Welsh Generation Framework workbook in config/, by VERSION
    NUMBER (v2.10 after v2.9 — a lexicographic sort would put it before
    v2.2). V4.17 (0.29.1): every consumer that used to take the last entry
    of a sorted glob goes through here."""
    d = Path(config_dir) if config_dir else CONFIG_DIR
    cands = []
    for f in d.glob("*Framework*v[0-9]*.xlsx"):
        m = _re.search(r"v(\d+)\.(\d+)", f.name)
        if m:
            cands.append(((int(m.group(1)), int(m.group(2))), f))
    return max(cands)[1] if cands else None
