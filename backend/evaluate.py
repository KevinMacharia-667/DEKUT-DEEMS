"""
Offline evaluation: rule-based baseline vs TF-IDF content-based engine.

Uses the ground truth written by seed.py (seed_ground_truth.json), which
records the events each synthetic user *should* find relevant based on
how their interest tags were generated.

Metric: precision@k — of the top-k recommendations for a user, what
fraction are in that user's ground-truth relevant set.

Run from the backend directory (after `python seed.py`):

    python evaluate.py

The printed table is intended to be pasted directly into Chapter 4 of
the project report.
"""

import json
import sys

from app.database import SessionLocal
from app.ml.baseline import recommend_baseline
from app.ml.engine import recommend_with_scores
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.models.user_interest import UserInterest

K_VALUES = (5, 10)
GROUND_TRUTH_FILE = "seed_ground_truth.json"


def precision_at_k(recommended_ids: list[str], relevant_ids: set[str], k: int) -> float:
    top_k = recommended_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for eid in top_k if eid in relevant_ids)
    return hits / len(top_k)


def main() -> None:
    try:
        with open(GROUND_TRUTH_FILE) as f:
            ground_truth: dict[str, list[str]] = json.load(f)
    except FileNotFoundError:
        sys.exit(f"{GROUND_TRUTH_FILE} not found - run `python seed.py` first.")

    db = SessionLocal()
    try:
        all_events = db.query(Event).all()

        per_user_rows = []
        totals = {f"baseline@{k}": 0.0 for k in K_VALUES}
        totals.update({f"ml@{k}": 0.0 for k in K_VALUES})
        evaluated = 0

        for username, relevant_list in ground_truth.items():
            user = db.query(User).filter(User.username == username).first()
            if user is None:
                continue
            relevant = set(relevant_list)

            interests = (
                db.query(UserInterest)
                .filter(UserInterest.user_id == user.id)
                .all()
            )
            rsvp_events = (
                db.query(Event)
                .join(RSVP, RSVP.event_id == Event.id)
                .filter(RSVP.user_id == user.id, RSVP.status == "confirmed")
                .all()
            )

            max_k = max(K_VALUES)
            base = recommend_baseline(interests, all_events, top_n=max_k)
            ml = recommend_with_scores(
                interests, all_events, rsvp_events=rsvp_events, top_n=max_k
            )

            base_ids = [str(r["event"].id) for r in base]
            ml_ids = [str(r["event"].id) for r in ml]

            row = {"user": username, "relevant": len(relevant)}
            for k in K_VALUES:
                row[f"baseline@{k}"] = precision_at_k(base_ids, relevant, k)
                row[f"ml@{k}"] = precision_at_k(ml_ids, relevant, k)
                totals[f"baseline@{k}"] += row[f"baseline@{k}"]
                totals[f"ml@{k}"] += row[f"ml@{k}"]
            per_user_rows.append(row)
            evaluated += 1

        if evaluated == 0:
            sys.exit("No ground-truth users found in the database - re-run seed.py.")

        # ── Print report ──────────────────────────────────────────────
        print()
        print("Recommendation Engine Evaluation: Baseline (rules) vs ML (TF-IDF)")
        print(f"Users evaluated: {evaluated} | Candidate events: {len(all_events)}")
        print()
        header = f"{'User':<15}{'Relevant':>9}"
        for k in K_VALUES:
            header += f"{'Base@' + str(k):>10}{'ML@' + str(k):>9}"
        print(header)
        print("-" * len(header))
        for row in per_user_rows:
            line = f"{row['user']:<15}{row['relevant']:>9}"
            for k in K_VALUES:
                line += f"{row[f'baseline@{k}']:>10.2f}{row[f'ml@{k}']:>9.2f}"
            print(line)
        print("-" * len(header))
        summary = f"{'MEAN':<15}{'':>9}"
        for k in K_VALUES:
            summary += (
                f"{totals[f'baseline@{k}'] / evaluated:>10.2f}"
                f"{totals[f'ml@{k}'] / evaluated:>9.2f}"
            )
        print(summary)
        print()
        for k in K_VALUES:
            b = totals[f"baseline@{k}"] / evaluated
            m = totals[f"ml@{k}"] / evaluated
            verdict = "ML wins" if m > b else ("tie" if m == b else "baseline wins")
            print(f"precision@{k}:  baseline={b:.2f}  ml={m:.2f}  -> {verdict}")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
