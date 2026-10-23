"""
Tests for the Google Form survey importer (survey_import.py), using CSVs in the exact shape
Google Forms exports: a Timestamp column, one column per question, checkbox answers joined
with ", ", and grid questions as one "Question [Row]" column per row.
"""

import csv
from datetime import timedelta
import uuid

import pytest

from evaluate import FIXED_REFERENCE_DATE
from app.models.event import Event
from survey_import import (
    evaluate_survey,
    match_events,
    parse_responses,
    split_survey,
    build_survey_users,
    summarise_habits,
)

GRID1 = "Would you attend these events? (part 1 of 2)"
GRID2 = "Would you attend these events? (part 2 of 2)"

# (row text in the form, category, tags) for the 16 surveyed events
EVENTS = [
    ("DeKUT Hackathon 2026 · Sat 09:00 · Innovation Hub", "Tech", "hackathon,ai,python", GRID1),
    ("AI & Ethics Panel · Wed 16:00 · Library Auditorium", "Tech", "ai,ethics", GRID1),
    ("Python for Beginners · Tue 14:00 · Computer Lab 3", "Workshop", "python,beginner", GRID1),
    ("Cybersecurity Essentials · Thu 17:00 · Online (Zoom)", "Workshop", "cybersecurity,training", GRID1),
    ("Research Methods Seminar · Mon 10:00 · Lecture Theatre 1", "Academic", "research,seminar", GRID1),
    ("Journal Club: AI in Medicine · Fri 18:00 · Science Lab", "Academic", "journal club,ai", GRID1),
    ("Mock Interview Day · Wed 09:00 · Business Incubator", "Career", "interview,career", GRID1),
    ("Tech Internship Fair · Thu 11:00 · Main Hall", "Career", "internship,tech", GRID1),
    ("Entrepreneurship Bootcamp · Sat 10:00 · Business Incubator", "Career", "entrepreneurship,startup", GRID2),
    ("Inter-Faculty Football Tournament · Sat 14:00 · Open Grounds", "Sports", "football", GRID2),
    ("Campus Marathon 2026 · Sun 07:00 · Sports Complex", "Sports", "marathon,fitness", GRID2),
    ("DeKUT Music Fest · Fri 19:00 · Open Grounds", "Cultural", "music,dance", GRID2),
    ("Poetry Slam Night · Thu 18:30 · Arts Studio", "Cultural", "poetry,art", GRID2),
    ("Freshers’ Welcome Mixer · Fri 17:00 · Student Centre", "Social", "mixer,networking", GRID2),
    ("Board Games Afternoon · Sun 15:00 · Cafeteria Courtyard", "Social", "games,community", GRID2),
    ("Web Development Bootcamp · Sat 13:00 · Computer Lab 3", "Workshop", "web development,bootcamp", GRID2),
]
TECHY = {"Tech", "Workshop"}
SPORTY = {"Sports", "Social"}

HEADERS = [
    "Timestamp",
    "Do you agree to take part?",
    "Which school are you in?",
    "Year of study",
    "Which kinds of campus events interest you?",
    "Pick up to 5 specific topics you care about most",
    "About how many campus events do you attend in a month?",
    "When are you usually free for events? [Weekdays]",
    "When are you usually free for events? [Weekends]",
    "What usually makes you decide to go to an event?",
    "Would you attend an event organised by a different school or faculty?",
    *[f"{grid} [{row}]" for row, _, _, grid in EVENTS],
    f"{GRID2} [Mystery Event · Fri 20:00 · Nowhere]",
    "An event you wish existed on campus (optional)",
]
CONSENT = "I agree that my anonymous answers may be used for a DeKUT final-year project on campus event recommendations."


def catalog():
    """In-memory Events whose titles match the form rows (seed titles use a straight apostrophe)."""
    out = []
    for i, (row, cat, tags, _) in enumerate(EVENTS):
        title = row.split(" · ")[0].replace("’", "'")
        out.append(Event(
            id=uuid.uuid4(), title=title, description=f"{title} on campus", category=cat, tags=tags,
            department="School of Computer Science & IT" if cat in TECHY else "Student Affairs & Sports",
            start_time=FIXED_REFERENCE_DATE + timedelta(days=i + 1),
        ))
    return out


def respondent_row(consent, school, categories, topics, likes, motivations="The topic itself", other="Sometimes"):
    row = {
        "Timestamp": "2026/11/02 10:15:00 AM GMT+3",
        "Do you agree to take part?": CONSENT if consent else "",
        "Which school are you in?": school,
        "Year of study": "3rd year",
        "Which kinds of campus events interest you?": ", ".join(categories),
        "Pick up to 5 specific topics you care about most": ", ".join(topics),
        "About how many campus events do you attend in a month?": "1–2",
        "When are you usually free for events? [Weekdays]": "Evening",
        "When are you usually free for events? [Weekends]": "Morning, Afternoon",
        "What usually makes you decide to go to an event?": motivations,
        "Would you attend an event organised by a different school or faculty?": other,
        f"{GRID2} [Mystery Event · Fri 20:00 · Nowhere]": "Maybe",
        "An event you wish existed on campus (optional)": "",
    }
    for event_row, cat, _, grid in EVENTS:
        row[f"{grid} [{event_row}]"] = "Definitely" if cat in likes else "No"
    return row


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return str(path)


@pytest.fixture
def survey_csv(tmp_path):
    rows = []
    for _ in range(4):
        rows.append(respondent_row(True, "School of Computer Science & IT", ["Tech", "Workshops", "Career"],
                                   ["Python", "AI", "Web development", "Mobile apps"], TECHY,
                                   motivations="The topic itself, Career or CV benefit"))
        rows.append(respondent_row(True, "School of Business", ["Sports", "Social", "Cultural"],
                                   ["Football", "Fitness", "Games", "Networking"], SPORTY,
                                   motivations="Friends are going, It’s popular / lots of people going",
                                   other="Often"))
    rows.append(respondent_row(False, "School of Engineering", ["Tech", "Academic", "Career"], ["AI"], TECHY))
    bad = respondent_row(True, "Other", ["Academic", "Career", "Tech"], ["Research", "Hands-on training"], {"Academic"})
    bad[f"{GRID1} [{EVENTS[0][0]}]"] = "Probably"  # not a valid grid answer
    rows.append(bad)
    return write_csv(tmp_path / "responses.csv", rows)


def test_parse_drops_non_consenting_and_maps_vocabulary(survey_csv):
    respondents, report = parse_responses(survey_csv)
    assert report["rows"] == 10
    assert report["consenting"] == 9
    assert report["dropped_no_consent"] == 1
    assert report["event_columns"] == 17
    assert report["unrecognised_grid_answers"] == {"Probably": 1}

    techy = respondents[0]
    assert techy.categories == ["Tech", "Workshops", "Career"]
    # Form wording mapped to the app's tag vocabulary
    assert techy.interest_tags == ["tech", "workshop", "career", "python", "ai", "web development", "mobile"]
    assert techy.free_times == {"Weekdays": ["Evening"], "Weekends": ["Morning", "Afternoon"]}
    # Curly apostrophe in the form row is normalised for matching
    assert "freshers' welcome mixer" in techy.reactions
    assert techy.reactions["dekut hackathon 2026"] == "definitely"

    last = respondents[-1]
    assert "hands-on" in last.interest_tags
    assert "dekut hackathon 2026" not in last.reactions  # "Probably" was ignored


def test_rejects_a_csv_that_is_not_the_survey(tmp_path):
    path = tmp_path / "other.csv"
    path.write_text("Timestamp,Name\n2026,Alice\n", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_responses(str(path))


def test_events_match_catalog_and_unknown_rows_are_reported(survey_csv):
    respondents, _ = parse_responses(survey_csv)
    events, unmatched = match_events(respondents, catalog())
    assert len(events) == 16
    assert unmatched == ["mystery event"]


def test_split_has_no_leakage(survey_csv):
    respondents, _ = parse_responses(survey_csv)
    events, _ = match_events(respondents, catalog())
    splits = split_survey(build_survey_users(respondents, 7), events, 7)
    for s in splits:
        assert not s["train_titles"] & set(s["test_titles"])
        test_ids = {str(events[t].id) for t in s["test_titles"]}
        assert s["test_relevant"] <= test_ids
        assert all(s["respondent"].reactions[t] == "definitely" for t in s["train_titles"]
                   if events[t] in s["train_events"])
        assert {str(r.event_id) for r in s["train_rsvps"]} == {str(e.id) for e in s["train_events"]}
    # Respondent with school "Other" gets no department
    assert splits[-1]["user"].department is None
    assert splits[0]["user"].department == "School of Computer Science & IT"


def test_content_models_beat_random_on_consistent_respondents(survey_csv):
    respondents, _ = parse_responses(survey_csv)
    events, _ = match_events(respondents, catalog())
    result = evaluate_survey(respondents, events, seeds=[42, 43, 44])
    summary = result["summary"]
    for model, vals in summary.items():
        for metric in vals.values():
            assert metric["mean"] is None or 0.0 <= metric["mean"] <= 1.0
    # Respondents' answers follow their declared interests, so interest-based models should win
    assert summary["Rule-Based"]["ndcg@5"]["mean"] > summary["Random"]["ndcg@5"]["mean"]
    assert summary["TF-IDF Content"]["ndcg@5"]["mean"] > summary["Random"]["ndcg@5"]["mean"]


def test_habit_summary(survey_csv):
    respondents, _ = parse_responses(survey_csv)
    habits = summarise_habits(respondents)
    assert habits["respondents"] == 9
    assert habits["share_popularity_or_friends"] == round(4 / 9, 3)
    assert habits["other_school_events"] == {"sometimes": 5, "often": 4}
    assert habits["reaction_labels"]["definitely"] > 0
