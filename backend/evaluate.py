"""
Offline evaluation: Rule-Based Baseline vs. TF-IDF Content ML vs. Unified Hybrid Engine.

Uses the ground truth written by seed.py (seed_ground_truth.json).

Metrics:
1. Precision@k: fraction of top-k recommendations that are relevant.
2. MRR (Mean Reciprocal Rank): 1 / rank of the first relevant event recommended.

Run from the backend directory:
    python evaluate.py

The printed table is intended for Chapter 4 of the final project report.
"""

import json
import sys

from app.database import SessionLocal
from app.ml.baseline import recommend_baseline
from app.ml.engine import recommend_with_scores
from app.ml.hybrid_engine import recommend_hybrid
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


def reciprocal_rank(recommended_ids: list[str], relevant_ids: set[str]) -> float:
    for rank, eid in enumerate(recommended_ids, start=1):
        if eid in relevant_ids:
            return 1.0 / rank
    return 0.0


def main() -> None:
    try:
        with open(GROUND_TRUTH_FILE) as f:
            ground_truth: dict[str, list[str]] = json.load(f)
    except FileNotFoundError:
        sys.exit(f"{GROUND_TRUTH_FILE} not found - run `python seed.py` first.")

    db = SessionLocal()
    try:
        all_events = db.query(Event).all()
        all_rsvps = db.query(RSVP).all()

        per_user_rows = []
        totals = {
            "base@5": 0.0, "ml@5": 0.0, "hybrid@5": 0.0,
            "base@10": 0.0, "ml@10": 0.0, "hybrid@10": 0.0,
            "base_mrr": 0.0, "ml_mrr": 0.0, "hybrid_mrr": 0.0,
        }
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

            max_k = 10
            base = recommend_baseline(interests, all_events, top_n=max_k)
            ml = recommend_with_scores(
                interests, all_events, rsvp_events=rsvp_events, top_n=max_k
            )
            hybrid = recommend_hybrid(
                user=user,
                user_interests=interests,
                all_events=all_events,
                all_rsvps=all_rsvps,
                rsvp_events=rsvp_events,
                top_n=max_k,
            )

            base_ids = [str(r["event"].id) for r in base]
            ml_ids = [str(r["event"].id) for r in ml]
            hybrid_ids = [str(r["event"].id) for r in hybrid]

            row = {
                "user": username,
                "relevant": len(relevant),
                "base@5": precision_at_k(base_ids, relevant, 5),
                "ml@5": precision_at_k(ml_ids, relevant, 5),
                "hybrid@5": precision_at_k(hybrid_ids, relevant, 5),
                "base@10": precision_at_k(base_ids, relevant, 10),
                "ml@10": precision_at_k(ml_ids, relevant, 10),
                "hybrid@10": precision_at_k(hybrid_ids, relevant, 10),
                "base_mrr": reciprocal_rank(base_ids, relevant),
                "ml_mrr": reciprocal_rank(ml_ids, relevant),
                "hybrid_mrr": reciprocal_rank(hybrid_ids, relevant),
            }

            for key in totals:
                totals[key] += row[key]

            per_user_rows.append(row)
            evaluated += 1

        if evaluated == 0:
            sys.exit("No ground-truth users found in the database - re-run seed.py.")

        # ── Print Comparative Report ──────────────────────────────────────────
        print()
        print("=" * 88)
        print("  DEKUT EVENT RECOMMENDATION ENGINE: 3-WAY COMPARATIVE ABLATION BENCHMARK")
        print(f"  Users: {evaluated} | Candidate Events: {len(all_events)} | Total RSVPs: {len(all_rsvps)}")
        print("=" * 88)
        print()
        header = f"{'User':<16}{'Rel':>5} | {'Base@5':>7}{'ML@5':>7}{'Hyb@5':>8} | {'Base@10':>8}{'ML@10':>7}{'Hyb@10':>8} | {'Hyb MRR':>8}"
        print(header)
        print("-" * len(header))
        for row in per_user_rows:
            line = (
                f"{row['user']:<16}{row['relevant']:>5} | "
                f"{row['base@5']:>7.2f}{row['ml@5']:>7.2f}{row['hybrid@5']:>8.2f} | "
                f"{row['base@10']:>8.2f}{row['ml@10']:>7.2f}{row['hybrid@10']:>8.2f} | "
                f"{row['hybrid_mrr']:>8.2f}"
            )
            print(line)
        print("-" * len(header))
        summary = (
            f"{'MEAN':<16}{'':>5} | "
            f"{totals['base@5']/evaluated:>7.2f}{totals['ml@5']/evaluated:>7.2f}{totals['hybrid@5']/evaluated:>8.2f} | "
            f"{totals['base@10']/evaluated:>8.2f}{totals['ml@10']/evaluated:>7.2f}{totals['hybrid@10']/evaluated:>8.2f} | "
            f"{totals['hybrid_mrr']/evaluated:>8.2f}"
        )
        print(summary)
        print("=" * len(header))
        print()
        print("Summary Verdicts:")
        print(f"  Precision@5:   Baseline={totals['base@5']/evaluated:.2f} | ML (TF-IDF)={totals['ml@5']/evaluated:.2f} | Hybrid={totals['hybrid@5']/evaluated:.2f}")
        print(f"  Precision@10:  Baseline={totals['base@10']/evaluated:.2f} | ML (TF-IDF)={totals['ml@10']/evaluated:.2f} | Hybrid={totals['hybrid@10']/evaluated:.2f}")
        print(f"  Mean Reciprocal Rank (MRR): Baseline={totals['base_mrr']/evaluated:.2f} | ML={totals['ml_mrr']/evaluated:.2f} | Hybrid={totals['hybrid_mrr']/evaluated:.2f}")
        print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
