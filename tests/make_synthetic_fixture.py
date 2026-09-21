"""Build the synthetic edge-case workbook (brief section 23).

The real school export is never altered; deliberately engineered cases live
in this separate fixture:
  - a unique leading answer (Year 7 sports)
  - a two-way tie (Year 7: Football vs Netball)
  - a three-way tie (demand in Year 7)
  - a year group below the threshold (Year 4: 3 respondents)
  - a gender subgroup of zero alongside a small visible one (Year 8: 5 boys,
    0 girls -> complementary suppression)
  - exactly five respondents (Year 10 girls)
  - a question not asked through routing (take-part: nobody routed in Y7)
  - a multi-select question and an answer-derived cohort
  - missing answers / partial response rows
  - an invalid year code and an unknown gender code (validation warnings)

Usage: python -m tests.make_synthetic_fixture [out.xlsx]
"""
import json
import sys
from pathlib import Path

import pandas as pd

QIDS = {
    "screen": 26871527, "gender": 26871497, "year": 26871554,
    "ethnicity": 26871498,
    "disability": 26871504, "learning": 26871505, "welsh": 26871567,
    "welsh_sport": 26871590, "join_in": 26871565, "listened": 26871566,
    "more_if": 26871588, "important": 26871589, "demand": 26871551,
    "enjoy": 26871552, "confidence": 26871586, "pe_feel": 26871587,
    "take_part": 26871506,
}
SPORT_QIDS = [26871507, 26871508, 26871509, 26871510, 26871511,
              26871512, 26871513, 26871514, 26871515, 26871516]
SETTINGS_QIDS = [26871517, 26871518, 26871519, 26871520, 26871521,
                 26871522, 26871523, 26871524, 26871525, 26871526]
FREQ_QIDS = list(range(26871531, 26871541)) + list(range(26871541, 26871551)) + \
            list(range(26871568, 26871578)) + list(range(26871591, 26871601))


def mx(rows):
    """Encode matrix cells the way SmartSurvey exports them."""
    return "; ".join(json.dumps({"id": 1, "type": "matrix_row", "row_title": r,
                                 "column_title": c}) for r, c in rows)


def make_row(rid, year, gender, sports="Football", demand="Swimming",
             join_in="Yes, always", enjoy_pe="A lot", disability="No",
             take_part=None, community=None, status="Complete", screen="Yes",
             listened="Sometimes", more_if="I felt more confident",
             important="Having fun", welsh="I do not speak Welsh"):
    r = {"Response_ID": rid, "Completion_Status": status,
         "School_Name": "Synthetic School", "School_ID": "0000000",
         "Local_Authority": "Testshire"}
    if status != "Complete":
        return r
    q = lambda k: f"Q_{QIDS[k]}_x"
    r[q("screen")] = screen
    r[q("year")] = year
    r[q("gender")] = gender
    r[q("disability")] = disability
    r[q("learning")] = "No"
    r[q("welsh")] = welsh
    r[q("join_in")] = join_in
    r[q("listened")] = listened
    r[q("more_if")] = more_if
    r[q("important")] = important
    r[q("demand")] = demand
    r[f"Q_{SPORT_QIDS[1]}_x"] = sports        # team sports category
    r[q("enjoy")] = mx([("PE lessons", enjoy_pe), ("School sports clubs", "A little"),
                        ("Sports clubs outside of school", "Not sure"),
                        ("Other settings, like in the park or garden", "A lot")])
    r[q("confidence")] = mx([("Try a new sport?", "Very"), ("Learn a new skill?", "Quite"),
                             ("Try again when sport is hard?", "Quite"),
                             ("Try sport in a new place?", "Not very")])
    r[q("pe_feel")] = mx([("Healthy?", "Very"), ("Confident?", "Quite"),
                          ("Ready to learn?", "Quite")])
    r[f"Q_{SETTINGS_QIDS[1]}_x"] = mx([(s.strip(), "In PE or Lesson Time") for s in sports.split(";")
                                       if s.strip() not in ("None of these",)])
    if community:
        r[f"Q_{SETTINGS_QIDS[1]}_x"] = mx([(sports.split(";")[0].strip(), "In a club outside of school")])
        r["Q_26871542_x"] = mx([(sports.split(";")[0].strip(), community)])
    if take_part:
        r[q("take_part")] = take_part
    return r


def build(out_path):
    rows, n = [], [0]

    def add(**kw):
        n[0] += 1
        rows.append(make_row(f"S{n[0]:04d}", **kw))

    # Year 7: 10 boys + 10 girls; Football/Netball two-way tie; demand 3-way tie
    for i in range(10):
        add(year="Year 7", gender="a boy", sports="Football",
            demand="Swimming; Tennis; Golf" if i < 6 else "Dodgeball",
            join_in="Yes, always" if i < 6 else "Yes, sometimes",
            enjoy_pe="A lot" if i < 7 else "A little",
            community="1 time a week" if i < 6 else None)
    for i in range(10):
        add(year="Year 7", gender="a girl", sports="Netball",
            demand="Tennis; Golf" if i < 6 else "Golf; Swimming",
            join_in="Yes, sometimes" if i < 5 else "No, not often",
            enjoy_pe="A lot" if i < 5 else "Not much",
            community="Three or more times a week" if i < 5 else None)
    # Year 3: 6 respondents (visible); Year 4: 3 (below threshold)
    for i in range(6):
        add(year="Year 3", gender="a boy" if i % 2 else "a girl", sports="Rounders",
            demand="Dodgeball", enjoy_pe="A lot", join_in="Yes, always",
            community="2 times a week" if i < 5 else None)
    for i in range(3):
        add(year="Year 4", gender="a girl", sports="Cricket", demand="Cricket")
    # Year 8: 5 boys, 0 girls -> complementary gender suppression
    for i in range(5):
        add(year="Year 8", gender="a boy", sports="Basketball", demand="Basketball",
            enjoy_pe="A little", join_in="Yes, sometimes")
    # Year 10: exactly 5 girls, incl routed take-part answers
    for i in range(5):
        add(year="Year 10", gender="a girl", sports="Hockey", demand="Hockey",
            disability="Yes" if i < 2 else "No",
            take_part="Standing" if i < 2 else None,
            enjoy_pe="Not much", join_in="Yes, always")
    # invalid year + unknown gender codes -> excluded / warned
    add(year="Year 99", gender="a boy")
    bad = make_row("S9998", year="Year 9", gender="a dragon")
    rows.append(bad)
    # partial with no answers -> excluded
    rows.append(make_row("S9999", year=None, gender=None, status="Partial"))

    # ensure every required column exists even if empty
    all_cols = (["Response_ID", "Completion_Status", "School_Name", "School_ID",
                 "Local_Authority"] +
                [f"Q_{q}_x" for q in QIDS.values()] +
                [f"Q_{q}_x" for q in SPORT_QIDS + SETTINGS_QIDS + FREQ_QIDS])
    df = pd.DataFrame(rows)
    for c in all_cols:
        if c not in df.columns:
            df[c] = None
    df = df[[c for c in all_cols if c in df.columns] +
            [c for c in df.columns if c not in all_cols]]
    df.to_excel(out_path, sheet_name="Responses wide", index=False)
    print(f"synthetic fixture: {out_path} ({len(df)} rows)")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("tests/fixtures/synthetic.xlsx")
    out.parent.mkdir(parents=True, exist_ok=True)
    build(out)
