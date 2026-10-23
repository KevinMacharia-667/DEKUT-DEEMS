"""
Real-student ground truth from the Google Form survey (docs/tukio_survey_form_template.pdf).

Reads the CSV that Google Forms / Sheets exports, turns each consenting respondent into a
simulated app user (department + interest tags), and evaluates the recommenders on the
16 surveyed events:

  - Each respondent rated 16 seeded events Definitely / Maybe / No ("would you attend?").
  - Per seed, half of a respondent's rated events are training: their "Definitely" answers
    become RSVPs (profile + collaborative signal). The other half are held out.
  - Each model ranks the held-out events; "Definitely" is relevant, Maybe/No are not.
    Only rated events are ranked, because unrated catalog events have no label.

The habit questions (free times, what makes you go, other-school events) are summarised
as evidence for or against the timing, popularity and department assumptions that
docs/evaluation.md section 4.3 found the hybrid's lead depends on.

Keep the raw CSV out of git: put it in backend/data/survey/ (ignored).

    python survey_import.py data/survey/responses.csv
    python survey_import.py data/survey/responses.csv --seeds 10 --out results/survey_evaluation.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

import evaluate as ev
from app.ml.baseline import recommend_baseline
from app.ml.engine import recommend_with_scores
from app.ml.hybrid_engine import recommend_hybrid
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.models.user_interest import UserInterest

# Question titles as written in the form template (matched by prefix, case-insensitive)
Q_CONSENT = "do you agree to take part"
Q_SCHOOL = "which school are you in"
Q_YEAR = "year of study"
Q_CATEGORIES = "which kinds of campus events interest you"
Q_TOPICS = "pick up to 5 specific topics"
Q_FREQUENCY = "about how many campus events"
Q_FREE = "when are you usually free"
Q_MOTIVATION = "what usually makes you decide"
Q_OTHER_SCHOOL = "would you attend an event organised by a different school"
Q_GRID = "would you attend these events"

REACTIONS = {"definitely": "definitely", "maybe": "maybe", "no": "no"}

# Form wording -> app vocabulary (UserInterest tags, Event.category)
CATEGORY_MAP = {
    "tech": "tech", "academic": "academic", "career": "career", "social": "social",
    "sports": "sports", "workshops": "workshop", "workshop": "workshop", "cultural": "cultural",
}
TOPIC_MAP = {
    "python": "python", "ai": "ai", "data science": "data science", "cybersecurity": "cybersecurity",
    "web development": "web development", "mobile apps": "mobile", "research": "research",
    "seminars": "seminar", "mathematics": "mathematics", "internships": "internship",
    "entrepreneurship": "entrepreneurship", "startups": "startup", "mentorship": "mentorship",
    "football": "football", "fitness": "fitness", "basketball": "basketball", "music": "music",
    "dance": "dance", "film": "film", "theatre": "theatre", "networking": "networking",
    "games": "games", "hands-on training": "hands-on", "certifications": "certification",
}
SCHOOLS = {
    "school of computer science & it", "school of engineering", "school of business",
    "school of science & applied tech", "health sciences",
}

TRAIN_SHARE = 0.5
SEEDS = list(range(42, 52))


def normalise(text: str) -> str:
    """Lower-case, straight apostrophes, single spaces: for matching titles and options."""
    return " ".join(str(text).replace("’", "'").replace("‘", "'").lower().split())


def split_multi(value: str) -> list[str]:
    """Google Forms joins checkbox answers with ', '."""
    return [part.strip() for part in str(value or "").split(", ") if part.strip()]


@dataclass
class Respondent:
    respondent_id: str
    school: str | None
    year: str | None
    categories: list[str]
    topics: list[str]
    frequency: str | None
    free_times: dict[str, list[str]]
    motivations: list[str]
    other_school: str | None
    reactions: dict[str, str] = field(default_factory=dict)  # normalised event title -> label

    @property
    def interest_tags(self) -> list[str]:
        tags = [CATEGORY_MAP[normalise(c)] for c in self.categories if normalise(c) in CATEGORY_MAP]
        tags += [TOPIC_MAP[normalise(t)] for t in self.topics if normalise(t) in TOPIC_MAP]
        return list(dict.fromkeys(tags))


def _find(headers: Sequence[str], prefix: str) -> str | None:
    for h in headers:
        if normalise(h).startswith(prefix):
            return h
    return None


def _grid_columns(headers: Sequence[str], prefix: str) -> dict[str, str]:
    """'Question [Row text]' columns -> {row text: header}."""
    out = {}
    for h in headers:
        m = re.match(r"^(.*)\[(.*)\]\s*$", h)
        if m and normalise(m.group(1)).startswith(prefix):
            out[m.group(2).strip()] = h
    return out


def event_title_from_row(row_text: str) -> str:
    """'DeKUT Hackathon 2026 · Sat 09:00 · Innovation Hub' -> normalised 'dekut hackathon 2026'."""
    return normalise(re.split(r"\s+[··|]\s+", row_text)[0])


def parse_responses(csv_path: str) -> tuple[list[Respondent], dict]:
    """Parse a Google Forms CSV export. Returns (consenting respondents, parse report)."""
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)

    cols = {
        "consent": _find(headers, Q_CONSENT), "school": _find(headers, Q_SCHOOL),
        "year": _find(headers, Q_YEAR), "categories": _find(headers, Q_CATEGORIES),
        "topics": _find(headers, Q_TOPICS), "frequency": _find(headers, Q_FREQUENCY),
        "motivation": _find(headers, Q_MOTIVATION), "other_school": _find(headers, Q_OTHER_SCHOOL),
    }
    free_cols = _grid_columns(headers, Q_FREE)
    event_cols = _grid_columns(headers, Q_GRID)
    missing = [k for k, v in cols.items() if v is None]
    if cols["consent"] is None or not event_cols:
        raise ValueError(f"Not a Tukio survey export: missing consent or event-grid columns ({missing})")

    respondents, dropped_no_consent, unknown_labels = [], 0, Counter()
    for i, row in enumerate(rows, 1):
        if not str(row.get(cols["consent"]) or "").strip():
            dropped_no_consent += 1
            continue
        reactions = {}
        for row_text, header in event_cols.items():
            label = REACTIONS.get(normalise(row.get(header) or ""))
            if label:
                reactions[event_title_from_row(row_text)] = label
            elif (row.get(header) or "").strip():
                unknown_labels[row.get(header).strip()] += 1
        get = lambda key: (row.get(cols[key]) or "").strip() or None if cols[key] else None  # noqa: E731
        respondents.append(Respondent(
            respondent_id=f"r{i:03d}",
            school=get("school"),
            year=get("year"),
            categories=split_multi(get("categories")),
            topics=split_multi(get("topics")),
            frequency=get("frequency"),
            free_times={r: split_multi(row.get(h)) for r, h in free_cols.items()},
            motivations=split_multi(get("motivation")),
            other_school=get("other_school"),
            reactions=reactions,
        ))

    report = {
        "rows": len(rows),
        "consenting": len(respondents),
        "dropped_no_consent": dropped_no_consent,
        "event_columns": len(event_cols),
        "missing_optional_columns": [k for k in missing if k != "consent"],
        "unrecognised_grid_answers": dict(unknown_labels),
    }
    return respondents, report


def match_events(respondents: Sequence[Respondent], catalog: Sequence[Event]) -> tuple[dict[str, Event], list[str]]:
    """Normalised survey title -> catalog Event (first by title order). Returns (matches, unmatched titles)."""
    by_title: dict[str, Event] = {}
    for e in sorted(catalog, key=lambda e: (e.title, str(e.start_time))):
        by_title.setdefault(normalise(e.title), e)
    titles = sorted({t for r in respondents for t in r.reactions})
    matched = {t: by_title[t] for t in titles if t in by_title}
    return matched, [t for t in titles if t not in by_title]


def summarise_habits(respondents: Sequence[Respondent]) -> dict:
    """Counts for the assumption-check questions."""
    n = len(respondents) or 1
    motivation = Counter(normalise(m) for r in respondents for m in r.motivations)
    other_school = Counter(normalise(r.other_school) for r in respondents if r.other_school)
    free = Counter(f"{row}: {normalise(slot)}" for r in respondents for row, slots in r.free_times.items() for slot in slots)
    labels = Counter(label for r in respondents for label in r.reactions.values())
    return {
        "respondents": len(respondents),
        "share_popularity_or_friends": round(
            sum(1 for r in respondents if {"friends are going", "it's popular / lots of people going"}
                & {normalise(m) for m in r.motivations}) / n, 3),
        "share_close_to_classes": round(motivation.get("it's close to my classes", 0) / n, 3),
        "other_school_events": dict(other_school),
        "motivations": dict(motivation.most_common()),
        "free_times": dict(free.most_common()),
        "reaction_labels": dict(labels),
        "schools": dict(Counter(r.school or "unknown" for r in respondents)),
        "frequency": dict(Counter(r.frequency or "unknown" for r in respondents)),
    }


def build_survey_users(respondents: Sequence[Respondent], seed: int) -> list[dict]:
    """In-memory User + UserInterest objects for each respondent (nothing is written to the database)."""
    rng = random.Random(seed)
    users = []
    for r in respondents:
        dept = r.school if r.school and normalise(r.school) in SCHOOLS else None
        user = User(id=uuid.UUID(int=rng.getrandbits(128)), username=f"survey_{r.respondent_id}",
                    role="student", department=dept)
        interests = [UserInterest(user_id=user.id, interest_tag=t, weight=1.0) for t in r.interest_tags]
        users.append({"respondent": r, "user": user, "interests": interests})
    return users


def split_survey(users: list[dict], events: dict[str, Event], seed: int) -> list[dict]:
    """Per respondent: rated events -> train half (Definitely = RSVP) and held-out half."""
    rng = random.Random(seed)
    splits = []
    for u in users:
        rated = [t for t in sorted(u["respondent"].reactions) if t in events]
        rng.shuffle(rated)
        n_train = int(round(len(rated) * TRAIN_SHARE))
        train, test = rated[:n_train], rated[n_train:]
        labels = u["respondent"].reactions
        train_pos = [t for t in train if labels[t] == "definitely"]
        splits.append({
            **u,
            "train_titles": set(train),
            "test_titles": test,
            "train_events": [events[t] for t in train_pos],
            "train_rsvps": [RSVP(user_id=u["user"].id, event_id=events[t].id, status="confirmed") for t in train_pos],
            "test_relevant": {str(events[t].id) for t in test if labels[t] == "definitely"},
            "is_cold": len(train_pos) <= 2,
        })
    return splits


def evaluate_survey(respondents: Sequence[Respondent], events: dict[str, Event], seeds: Sequence[int]) -> dict:
    """Mean ± std across seeds of P@3, NDCG@5 and MRR over each respondent's held-out events."""
    models = ["Random", "Popularity", "Rule-Based", "TF-IDF Content", "Unified Hybrid"]
    metrics = ["precision@3", "ndcg@5", "mrr"]
    per_seed = {m: {k: [] for k in metrics} for m in models}
    users_scored = []

    for seed in seeds:
        rng = random.Random(seed)
        splits = split_survey(build_survey_users(respondents, seed), events, seed)
        all_train_rsvps = [r for s in splits for r in s["train_rsvps"]]
        scores = {m: {k: [] for k in metrics} for m in models}
        scored = 0
        for s in splits:
            if not s["test_relevant"]:
                continue  # nothing this respondent would "definitely" attend among the held-out events
            cands = [events[t] for t in s["test_titles"]]
            n = len(cands)
            recs = {
                "Random": ev.recommend_random(cands, top_n=n, rng=rng),
                "Popularity": ev.recommend_popularity(cands, all_train_rsvps, top_n=n),
                "Rule-Based": recommend_baseline(s["interests"], cands, top_n=n,
                                                 reference_date=ev.FIXED_REFERENCE_DATE),
                "TF-IDF Content": recommend_with_scores(s["interests"], cands, rsvp_events=s["train_events"], top_n=n),
                "Unified Hybrid": recommend_hybrid(user=s["user"], user_interests=s["interests"], all_events=cands,
                                                   all_rsvps=all_train_rsvps, rsvp_events=s["train_events"], top_n=n,
                                                   reference_date=ev.FIXED_REFERENCE_DATE),
            }
            scored += 1
            for m, ranked in recs.items():
                ids = [str(r["event"].id) for r in ranked]
                # Models may drop zero-score events; append the rest in title order so every list ranks all candidates
                ids += [str(e.id) for e in sorted(cands, key=lambda e: e.title) if str(e.id) not in ids]
                scores[m]["precision@3"].append(ev.precision_at_k(ids, s["test_relevant"], 3))
                scores[m]["ndcg@5"].append(ev.ndcg_at_k(ids, s["test_relevant"], 5))
                scores[m]["mrr"].append(ev.reciprocal_rank(ids, s["test_relevant"]))
        users_scored.append(scored)
        for m in models:
            for k in metrics:
                if scores[m][k]:
                    per_seed[m][k].append(float(np.mean(scores[m][k])))

    summary = {
        m: {k: {"mean": round(float(np.mean(v)), 4) if v else None,
                "std": round(float(np.std(v, ddof=1)), 4) if len(v) > 1 else None}
            for k, v in per_seed[m].items()}
        for m in models
    }
    return {"seeds": list(seeds), "respondents_scored_per_seed": users_scored, "summary": summary}


def markdown_table(result: dict) -> str:
    lines = ["| Model | P@3 | NDCG@5 | MRR |", "| :--- | :---: | :---: | :---: |"]
    for m, vals in result["summary"].items():
        cells = []
        for k in ["precision@3", "ndcg@5", "mrr"]:
            v = vals[k]
            cells.append("n/a" if v["mean"] is None else f"{v['mean']:.3f} ± {v['std'] or 0:.3f}")
        lines.append(f"| {m} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("csv_path", help="Google Forms CSV export")
    parser.add_argument("--seeds", type=int, default=len(SEEDS), help="number of random splits (default 10)")
    parser.add_argument("--out", default=os.path.join("results", "survey_evaluation.json"))
    args = parser.parse_args()

    from app.database import SessionLocal

    respondents, report = parse_responses(args.csv_path)
    print(f"Rows: {report['rows']} | consenting: {report['consenting']} | "
          f"dropped (no consent): {report['dropped_no_consent']} | event columns: {report['event_columns']}")
    if report["missing_optional_columns"]:
        print("  Missing optional columns:", ", ".join(report["missing_optional_columns"]))
    if report["unrecognised_grid_answers"]:
        print("  Unrecognised grid answers (ignored):", report["unrecognised_grid_answers"])

    db = SessionLocal()
    try:
        catalog = db.query(Event).all()
        ev.use_catalog_reference_date(catalog)
        events, unmatched = match_events(respondents, catalog)
    finally:
        db.close()
    if unmatched:
        print("  Survey events not in the catalog (ignored):", unmatched)
    print(f"Matched {len(events)} surveyed events to the catalog.")

    habits = summarise_habits(respondents)
    result = evaluate_survey(respondents, events, SEEDS[: args.seeds])
    print("\nAssumption checks:")
    print(f"  Popularity / friends influence decisions: {habits['share_popularity_or_friends']:.0%} of respondents")
    print(f"  'Close to my classes' influences decisions: {habits['share_close_to_classes']:.0%}")
    print(f"  Attend other schools' events: {habits['other_school_events']}")
    print(f"\nRanking held-out survey events ({len(result['seeds'])} seeds, "
          f"respondents scored per seed: {result['respondents_scored_per_seed']}):\n")
    print(markdown_table(result))

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump({"parse_report": report, "unmatched_events": unmatched, "habits": habits, **result}, f, indent=2)
    print(f"\nSaved {args.out}")


if __name__ == "__main__":
    main()
