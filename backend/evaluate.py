"""
Offline Evaluation Benchmark for Tukio / DeKUT Campus Event Recommendation Engine.

Evaluates 5 recommendation strategies across 10 random seeds:
1. Random Baseline
2. Popularity Baseline
3. Heuristic Rule-Based Baseline
4. Content-Based Filtering (TF-IDF Cosine Similarity)
5. Unified Multi-Factor Hybrid Engine (Content + SVD Collaborative + Context + Time Urgency + Popularity)

Metrics Computed:
- Precision@5, Precision@10
- Recall@5, Recall@10
- NDCG@10 (Normalized Discounted Cumulative Gain at rank 10)
- MRR (Mean Reciprocal Rank averaged across users)

Cohorts:
- Overall (All Users)
- Cold-Start Users (few training interactions, <= 2)
- Warm Users (rich interaction history)

Methodological Limitation Notice:
---------------------------------
Because the synthetic ground truth in `seed_ground_truth.json` was generated in `seed.py`
using tag overlap and category matching rules, the heuristic rule-based baseline has an
inherent structural advantage on this benchmark. In production, evaluation should transition
to online A/B testing or implicit feedback logs (CTR, retention, RSVP completion rate).
"""

from datetime import datetime, timezone
import json
import math
import os
import random
from typing import Sequence

import numpy as np

from app.database import SessionLocal
from app.ml.baseline import recommend_baseline
from app.ml.engine import recommend_with_scores
from app.ml.hybrid_engine import recommend_hybrid
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.models.user_interest import UserInterest

# Fixed reference date ensures temporal urgency features remain deterministic
FIXED_REFERENCE_DATE = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)
SEEDS = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]
GROUND_TRUTH_FILE = "seed_ground_truth.json"
RESULTS_DIR = "results"


# ── Metric Formulations ────────────────────────────────────────────────────────


def precision_at_k(recommended_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Precision@K: fraction of top-K recommendations that are in the relevant test set."""
    top_k = recommended_ids[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for eid in top_k if eid in relevant_ids)
    return hits / float(len(top_k))


def recall_at_k(recommended_ids: list[str], relevant_ids: set[str], k: int) -> float:
    """Recall@K: fraction of relevant test items discovered in the top-K recommendations."""
    if not relevant_ids:
        return 0.0
    top_k = recommended_ids[:k]
    hits = sum(1 for eid in top_k if eid in relevant_ids)
    return hits / float(len(relevant_ids))


def ndcg_at_k(recommended_ids: list[str], relevant_ids: set[str], k: int = 10) -> float:
    """Normalized Discounted Cumulative Gain at rank K."""
    if not relevant_ids:
        return 0.0
    top_k = recommended_ids[:k]
    dcg = 0.0
    for i, eid in enumerate(top_k):
        if eid in relevant_ids:
            dcg += 1.0 / math.log2(i + 2)  # i+2 maps 0-index to rank 1 (log2(2)=1.0)

    ideal_hits = min(k, len(relevant_ids))
    if ideal_hits == 0:
        return 0.0
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg


def reciprocal_rank(recommended_ids: list[str], relevant_ids: set[str]) -> float:
    """Reciprocal rank of the first relevant item in the recommended list (0.0 if none)."""
    for rank, eid in enumerate(recommended_ids, start=1):
        if eid in relevant_ids:
            return 1.0 / float(rank)
    return 0.0


# ── Baselines ──────────────────────────────────────────────────────────────────


def recommend_random(
    candidate_events: Sequence[Event],
    top_n: int = 10,
    rng: random.Random | None = None,
) -> list[dict]:
    """Random baseline: uniform random selection of candidate events."""
    shuffled = list(candidate_events)
    if rng is not None:
        rng.shuffle(shuffled)
    else:
        random.shuffle(shuffled)
    return [{"event": e, "score": 1.0 / (i + 1)} for i, e in enumerate(shuffled[:top_n])]


def recommend_popularity(
    candidate_events: Sequence[Event],
    train_rsvps: Sequence[RSVP],
    top_n: int = 10,
    reference_date: datetime = FIXED_REFERENCE_DATE,
) -> list[dict]:
    """
    Popularity baseline: rank events by RSVP count in the training split only.
    Ties broken by earliest start date.
    """
    counts: dict[str, int] = {}
    for r in train_rsvps:
        if r.status == "confirmed":
            key = str(r.event_id)
            counts[key] = counts.get(key, 0) + 1

    def sort_key(ev: Event):
        c = counts.get(str(ev.id), 0)
        st = ev.start_time
        if st.tzinfo is None:
            st = st.replace(tzinfo=timezone.utc)
        return (-c, st)

    sorted_events = sorted(candidate_events, key=sort_key)
    return [{"event": e, "score": float(counts.get(str(e.id), 0))} for e in sorted_events[:top_n]]


# ── Validation Split Weight Selector ───────────────────────────────────────────


WEIGHT_CANDIDATES = [
    {"name": "production_balanced", "weights": {"content": 0.42, "collab": 0.28, "dept": 0.12, "urgency": 0.10, "pop": 0.08}},
    {"name": "high_content", "weights": {"content": 0.58, "collab": 0.18, "dept": 0.12, "urgency": 0.08, "pop": 0.04}},
    {"name": "high_collab", "weights": {"content": 0.30, "collab": 0.42, "dept": 0.12, "urgency": 0.10, "pop": 0.06}},
]


def select_best_hybrid_weights(
    validation_users: list[dict],
    candidate_events_by_user: dict[str, list[Event]],
    train_rsvps: list[RSVP],
) -> dict[str, float]:
    """Select hybrid weights maximizing NDCG@10 on the validation split."""
    best_weights = WEIGHT_CANDIDATES[0]["weights"]
    best_score = -1.0

    for cand in WEIGHT_CANDIDATES:
        scores = []
        for udata in validation_users:
            u = udata["user"]
            val_rel = udata["val_relevant"]
            if not val_rel:
                continue
            cand_events = candidate_events_by_user[u.username]
            user_train_events = udata["train_events"]
            recs = recommend_hybrid(
                user=u,
                user_interests=udata["interests"],
                all_events=cand_events,
                all_rsvps=train_rsvps,
                rsvp_events=user_train_events,
                top_n=10,
                reference_date=FIXED_REFERENCE_DATE,
                custom_weights=cand["weights"],
            )
            rec_ids = [str(r["event"].id) for r in recs]
            scores.append(ndcg_at_k(rec_ids, val_rel, k=10))

        mean_ndcg = float(np.mean(scores)) if scores else 0.0
        if mean_ndcg > best_score:
            best_score = mean_ndcg
            best_weights = cand["weights"]

    return best_weights


# ── Main Multi-Seed Evaluation ─────────────────────────────────────────────────


def evaluate_trial(
    seed: int,
    db,
    all_events: list[Event],
    ground_truth: dict[str, list[str]],
) -> dict:
    """Run one evaluation trial under a specific random seed."""
    rng = random.Random(seed)
    event_lookup = {str(e.id): e for e in all_events}

    all_db_rsvps = db.query(RSVP).filter(RSVP.status == "confirmed").all()
    user_rsvp_map: dict[str, list[RSVP]] = {}
    for r in all_db_rsvps:
        uid = str(r.user_id)
        user_rsvp_map.setdefault(uid, []).append(r)

    # 1. Partition users into Cold-Start (few interactions, <= 2) and Warm cohorts
    student_users = []
    for username in sorted(ground_truth.keys()):
        user = db.query(User).filter(User.username == username).first()
        if user:
            student_users.append(user)

    # Deterministically shuffle users for cohort assignment
    shuffled_students = list(student_users)
    rng.shuffle(shuffled_students)
    num_cold = max(4, int(len(shuffled_students) * 0.35))
    cold_usernames = {u.username for u in shuffled_students[:num_cold]}

    # 2. Split interactions per user into Train, Validation, and Test
    user_splits = []
    all_train_rsvps = []

    for user in student_users:
        user_id_str = str(user.id)
        user_rsvps = user_rsvp_map.get(user_id_str, [])
        is_cold = user.username in cold_usernames

        interests = (
            db.query(UserInterest)
            .filter(UserInterest.user_id == user.id)
            .all()
        )

        all_gt_relevant = set(ground_truth.get(user.username, []))

        # Split user RSVPs into train / val / test
        shuffled_rsvps = list(user_rsvps)
        rng.shuffle(shuffled_rsvps)

        if is_cold:
            # Cold-start student: 1-2 training RSVPs only
            n_train = min(len(shuffled_rsvps), rng.randint(1, 2))
            train_rsvps_u = shuffled_rsvps[:n_train]
            remaining = shuffled_rsvps[n_train:]
        else:
            # Warm student: 60% train
            n_train = max(3, int(len(shuffled_rsvps) * 0.60))
            train_rsvps_u = shuffled_rsvps[:n_train]
            remaining = shuffled_rsvps[n_train:]

        n_val = max(1, int(len(remaining) * 0.40)) if remaining else 0
        val_rsvps_u = remaining[:n_val]
        test_rsvps_u = remaining[n_val:]

        train_event_ids = {str(r.event_id) for r in train_rsvps_u}
        val_event_ids = {str(r.event_id) for r in val_rsvps_u}
        test_event_ids = {str(r.event_id) for r in test_rsvps_u}

        # Held-out test relevant items: ground truth events excluding train and val
        test_relevant = (all_gt_relevant - train_event_ids - val_event_ids)
        if not test_relevant:
            # Fallback if ground truth was small
            test_relevant = test_event_ids

        val_relevant = val_event_ids

        all_train_rsvps.extend(train_rsvps_u)

        user_splits.append({
            "user": user,
            "interests": interests,
            "is_cold": is_cold,
            "train_rsvps": train_rsvps_u,
            "train_events": [event_lookup[eid] for eid in train_event_ids if eid in event_lookup],
            "train_event_ids": train_event_ids,
            "val_relevant": val_relevant,
            "test_relevant": test_relevant,
        })

    # Candidate events for each user: all catalog events excluding their training interactions
    candidates_by_user = {}
    for udata in user_splits:
        tr_ids = udata["train_event_ids"]
        candidates_by_user[udata["user"].username] = [
            e for e in all_events if str(e.id) not in tr_ids
        ]

    # Select optimal hybrid weights on validation split
    best_weights = select_best_hybrid_weights(user_splits, candidates_by_user, all_train_rsvps)

    # 3. Evaluate each model on test split
    models = ["Random", "Popularity", "Rule-Based", "Content-Based ML", "Unified Hybrid"]
    results = {
        m: {"Overall": [], "Cold-Start": [], "Warm": []}
        for m in models
    }

    for udata in user_splits:
        user = udata["user"]
        interests = udata["interests"]
        test_rel = udata["test_relevant"]
        user_train_events = udata["train_events"]
        cand_events = candidates_by_user[user.username]
        cohort = "Cold-Start" if udata["is_cold"] else "Warm"

        # Model recommendations
        rec_random = recommend_random(cand_events, top_n=10, rng=rng)
        rec_pop = recommend_popularity(
            cand_events,
            train_rsvps=all_train_rsvps,
            top_n=10,
            reference_date=FIXED_REFERENCE_DATE,
        )
        rec_base = recommend_baseline(
            interests,
            cand_events,
            top_n=10,
            reference_date=FIXED_REFERENCE_DATE,
        )
        rec_ml = recommend_with_scores(
            interests,
            cand_events,
            rsvp_events=user_train_events,
            top_n=10,
        )
        rec_hyb = recommend_hybrid(
            user=user,
            user_interests=interests,
            all_events=cand_events,
            all_rsvps=all_train_rsvps,
            rsvp_events=user_train_events,
            top_n=10,
            reference_date=FIXED_REFERENCE_DATE,
            custom_weights=best_weights,
        )

        model_recs = {
            "Random": [str(r["event"].id) for r in rec_random],
            "Popularity": [str(r["event"].id) for r in rec_pop],
            "Rule-Based": [str(r["event"].id) for r in rec_base],
            "Content-Based ML": [str(r["event"].id) for r in rec_ml],
            "Unified Hybrid": [str(r["event"].id) for r in rec_hyb],
        }

        for m_name, rec_ids in model_recs.items():
            u_metrics = {
                "precision@5": precision_at_k(rec_ids, test_rel, 5),
                "precision@10": precision_at_k(rec_ids, test_rel, 10),
                "recall@5": recall_at_k(rec_ids, test_rel, 5),
                "recall@10": recall_at_k(rec_ids, test_rel, 10),
                "ndcg@10": ndcg_at_k(rec_ids, test_rel, 10),
                "mrr": reciprocal_rank(rec_ids, test_rel),
            }
            results[m_name]["Overall"].append(u_metrics)
            results[m_name][cohort].append(u_metrics)

    return {
        "seed": seed,
        "best_weights": best_weights,
        "results": results,
    }


def main():
    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"Error: {GROUND_TRUTH_FILE} not found. Run python seed.py first.")
        return

    with open(GROUND_TRUTH_FILE) as f:
        ground_truth: dict[str, list[str]] = json.load(f)

    db = SessionLocal()
    try:
        all_events = db.query(Event).all()
        if not all_events:
            print("Error: No events found in database. Run python seed.py first.")
            return

        print()
        print("=" * 100)
        print("  TUKIO RECOMMENDATION ENGINE: MULTI-SEED OFFLINE BENCHMARK")
        print(f"  Candidate Events: {len(all_events)} | Users: {len(ground_truth)} | Evaluation Seeds: {len(SEEDS)}")
        print(f"  Fixed Reference Date: {FIXED_REFERENCE_DATE.isoformat()}")
        print("=" * 100)
        print()
        print("METHODOLOGICAL LIMITATION NOTICE:")
        print("  The synthetic ground truth was constructed during seeding using category matches")
        print("  and tag overlap. The rule-based baseline therefore has a structural advantage on")
        print("  this dataset. In production, ground truth should stem from real click/RSVP logs.")
        print()

        all_trial_results = []
        for seed in SEEDS:
            trial = evaluate_trial(seed, db, all_events, ground_truth)
            all_trial_results.append(trial)

        # Aggregate across seeds
        models = ["Random", "Popularity", "Rule-Based", "Content-Based ML", "Unified Hybrid"]
        cohorts = ["Overall", "Cold-Start", "Warm"]
        metrics = ["precision@5", "precision@10", "recall@5", "recall@10", "ndcg@10", "mrr"]

        summary = {}  # (cohort, model) -> {metric: (mean, std)}
        csv_rows = []

        for cohort in cohorts:
            for model in models:
                summary[(cohort, model)] = {}
                metric_seed_means = {m: [] for m in metrics}

                for trial in all_trial_results:
                    seed = trial["seed"]
                    u_list = trial["results"][model][cohort]
                    if not u_list:
                        continue
                    seed_vals = {
                        m: float(np.mean([u[m] for u in u_list]))
                        for m in metrics
                    }
                    for m in metrics:
                        metric_seed_means[m].append(seed_vals[m])

                    csv_rows.append({
                        "seed": seed,
                        "cohort": cohort,
                        "model": model,
                        **seed_vals,
                    })

                for m in metrics:
                    vals = metric_seed_means[m]
                    mean_val = float(np.mean(vals)) if vals else 0.0
                    std_val = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
                    summary[(cohort, model)][m] = (mean_val, std_val)

        # ── Output Formatted Tables ────────────────────────────────────────────

        def format_cell_ascii(mean_val, std_val):
            return f"{mean_val:.3f} +/- {std_val:.3f}"

        def format_cell_md(mean_val, std_val):
            return f"{mean_val:.3f} \u00b1 {std_val:.3f}"

        # 1. ASCII Terminal Table
        print("=" * 115)
        print("  OFFLINE ABLATION BENCHMARK (MEAN +/- STD OVER 10 EVALUATION SEEDS)")
        print("=" * 115)

        for cohort in cohorts:
            print(f"\n[Cohort: {cohort.upper()}]")
            header = f"{'Model':<20} | {'P@5':<17} | {'P@10':<17} | {'R@5':<17} | {'R@10':<17} | {'NDCG@10':<17} | {'MRR':<17}"
            print("-" * len(header))
            print(header)
            print("-" * len(header))
            for model in models:
                m_dict = summary[(cohort, model)]
                line = (
                    f"{model:<20} | "
                    f"{format_cell_ascii(*m_dict['precision@5']):<17} | "
                    f"{format_cell_ascii(*m_dict['precision@10']):<17} | "
                    f"{format_cell_ascii(*m_dict['recall@5']):<17} | "
                    f"{format_cell_ascii(*m_dict['recall@10']):<17} | "
                    f"{format_cell_ascii(*m_dict['ndcg@10']):<17} | "
                    f"{format_cell_ascii(*m_dict['mrr']):<17}"
                )
                print(line)
            print("-" * len(header))

        # 2. Markdown Table
        print("\n\n### Markdown Benchmark Table (Ready for Chapter 4 Report)\n")
        md_lines = []
        for cohort in cohorts:
            md_lines.append(f"#### Cohort: {cohort}\n")
            md_lines.append("| Recommendation Model | Precision@5 | Precision@10 | Recall@5 | Recall@10 | NDCG@10 | MRR |")
            md_lines.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
            for model in models:
                m_dict = summary[(cohort, model)]
                p5 = format_cell_md(*m_dict['precision@5'])
                p10 = format_cell_md(*m_dict['precision@10'])
                r5 = format_cell_md(*m_dict['recall@5'])
                r10 = format_cell_md(*m_dict['recall@10'])
                ndcg = format_cell_md(*m_dict['ndcg@10'])
                mrr = format_cell_md(*m_dict['mrr'])
                md_lines.append(f"| **{model}** | {p5} | {p10} | {r5} | {r10} | {ndcg} | {mrr} |")
            md_lines.append("")

        md_output = "\n".join(md_lines)
        print(md_output)

        # ── Save Results to Disk ───────────────────────────────────────────────
        os.makedirs(RESULTS_DIR, exist_ok=True)
        csv_file = os.path.join(RESULTS_DIR, "evaluation.csv")
        json_file = os.path.join(RESULTS_DIR, "evaluation.json")

        # Save CSV
        import csv
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            fieldnames = ["seed", "cohort", "model", "precision@5", "precision@10", "recall@5", "recall@10", "ndcg@10", "mrr"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in csv_rows:
                writer.writerow(r)

        # Save JSON summary
        json_summary = {
            "metadata": {
                "evaluation_date": FIXED_REFERENCE_DATE.isoformat(),
                "seeds": SEEDS,
                "candidate_events_count": len(all_events),
                "users_count": len(ground_truth),
                "limitation": "Synthetic ground truth from seed.py rewards tag/category match.",
            },
            "summary": {
                f"{cohort}_{model}": {
                    k: {"mean": round(v[0], 4), "std": round(v[1], 4)}
                    for k, v in summary[(cohort, model)].items()
                }
                for cohort in cohorts
                for model in models
            },
        }
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(json_summary, f, indent=2)

        print(f"\n[OK] Results saved successfully:")
        print(f"  -> CSV:  {csv_file}")
        print(f"  -> JSON: {json_file}\n")

    finally:
        db.close()


if __name__ == "__main__":
    main()
