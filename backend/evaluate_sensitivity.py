"""
Sensitivity check for the behaviour-based ground truth in evaluate.py.

Re-runs the behaviour benchmark (5 seeds) with alternative hidden-utility weightings, to check
whether the hybrid's lead depends on the department and event-appeal signals that the
simulator includes and the hybrid has features for. Results are reported in docs/evaluation.md.

    python evaluate_sensitivity.py
"""

import evaluate as ev
from app.database import SessionLocal
from app.models.event import Event

SCENARIOS = {
    "category_only": {"category": 1.0, "cluster": 0.0, "dept": 0.0, "appeal": 0.0},
    "no_dept_no_appeal": {"category": 0.55, "cluster": 0.45, "dept": 0.0, "appeal": 0.0},
}
SEEDS = [42, 43, 44, 45, 46]
COLUMNS = ["precision@10", "recall@10", "ndcg@10", "mrr", "coverage@10"]


def main():
    db = SessionLocal()
    try:
        events = db.query(Event).order_by(Event.title, Event.start_time).all()
        for name, weights in SCENARIOS.items():
            ev.SIM_UTILITY_WEIGHTS = weights
            trials = [ev.evaluate_trial(s, events, ev.build_behaviour_splits(s, events)) for s in SEEDS]
            summary = ev.aggregate(trials)
            print(f"\n## {name} {weights} ({len(SEEDS)} seeds, Overall)")
            print("| Model | P@10 | R@10 | NDCG@10 | MRR | Coverage@10 |")
            for m in ev.MODELS:
                s = summary[("Overall", m)]
                print(f"| {m} | " + " | ".join(f"{s[k][0]:.3f} ± {s[k][1]:.3f}" for k in COLUMNS) + " |", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    main()
