"""
Diversity sweep for the hybrid's MMR re-ranking (app/ml/hybrid_engine.py).

Measures validation-split NDCG@10 and Catalog Coverage@10 for several diversity values on
the behaviour-based ground truth (5 seeds). The test split is never used here.

Selection rule: pick the largest diversity whose mean validation NDCG@10 is within 5%
(relative) of diversity = 0 AND whose mean Coverage@10 beats diversity = 0 by more than one
seed standard deviation; otherwise keep 0. The coverage condition was added after the first
run, which showed MMR lowering coverage (the original accuracy-only rule would have picked
0.5). See docs/evaluation.md section 4.4.
The chosen value is set as DEFAULT_DIVERSITY in app/ml/hybrid_engine.py.

    python evaluate_diversity.py
"""

import numpy as np

import evaluate as ev
from app.database import SessionLocal
from app.ml.hybrid_engine import recommend_hybrid
from app.models.event import Event

DIVERSITY_VALUES = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
SEEDS = [42, 43, 44, 45, 46]
MAX_RELATIVE_NDCG_DROP = 0.05


def main():
    db = SessionLocal()
    try:
        events = db.query(Event).order_by(Event.title, Event.start_time).all()
        ev.use_catalog_reference_date(events)
        ndcg = {d: [] for d in DIVERSITY_VALUES}
        coverage = {d: [] for d in DIVERSITY_VALUES}

        for seed in SEEDS:
            splits = ev.build_behaviour_splits(seed, events)
            train_rsvps = [r for u in splits for r in u["train_rsvps"]]
            candidates = {
                u["user"].username: [e for e in events if str(e.id) not in u["train_event_ids"]]
                for u in splits
            }
            weights = ev.select_best_hybrid_weights(splits, candidates, train_rsvps)

            for d in DIVERSITY_VALUES:
                user_ndcg, rec_lists = [], []
                for u in splits:
                    recs = recommend_hybrid(
                        user=u["user"],
                        user_interests=u["interests"],
                        all_events=candidates[u["user"].username],
                        all_rsvps=train_rsvps,
                        rsvp_events=u["train_events"],
                        top_n=10,
                        reference_date=ev.FIXED_REFERENCE_DATE,
                        custom_weights=weights,
                        diversity=d,
                    )
                    rec_ids = [str(r["event"].id) for r in recs]
                    rec_lists.append(rec_ids)
                    if u["val_relevant"]:
                        user_ndcg.append(ev.ndcg_at_k(rec_ids, u["val_relevant"], 10))
                ndcg[d].append(float(np.mean(user_ndcg)))
                coverage[d].append(ev.catalog_coverage(rec_lists, len(events)))
            print(f"seed {seed} done", flush=True)

        base = float(np.mean(ndcg[0.0]))
        print(f"\nValidation split, behaviour-based ground truth, {len(SEEDS)} seeds")
        print("| Diversity | Validation NDCG@10 | Relative to 0.0 | Coverage@10 |")
        print("| :---: | :---: | :---: | :---: |")
        chosen = 0.0
        # A coverage gain only counts if it exceeds one seed standard deviation at diversity 0
        coverage_bar = float(np.mean(coverage[0.0]) + np.std(coverage[0.0], ddof=1))
        for d in DIVERSITY_VALUES:
            mean = float(np.mean(ndcg[d]))
            rel = mean / base - 1 if base > 0 else 0.0
            print(
                f"| {d:.1f} | {mean:.3f} ± {np.std(ndcg[d], ddof=1):.3f} | {rel:+.1%} | "
                f"{np.mean(coverage[d]):.3f} ± {np.std(coverage[d], ddof=1):.3f} |"
            )
            if rel >= -MAX_RELATIVE_NDCG_DROP and np.mean(coverage[d]) > coverage_bar:
                chosen = d
        print(
            f"\nChosen DEFAULT_DIVERSITY = {chosen} (largest within {MAX_RELATIVE_NDCG_DROP:.0%} "
            f"NDCG@10 of diversity 0 whose coverage beats {coverage_bar:.3f})"
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
