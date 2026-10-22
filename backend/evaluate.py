"""
Offline Evaluation Benchmark for Tukio / DeKUT Campus Event Recommendation Engine.

Evaluates 5 recommendation strategies across 10 random seeds:
1. Random Baseline                       (reference floor)
2. Popularity Baseline                   (reference floor)
3. Heuristic Rule-Based Baseline         (app/ml/baseline.py)
4. TF-IDF Content-Based Filtering        (app/ml/engine.py)
5. Unified Multi-Factor Hybrid Engine    (app/ml/hybrid_engine.py)

Metrics Computed:
- Precision@5, Precision@10, Recall@5, Recall@10
- NDCG@10 (Normalized Discounted Cumulative Gain at rank 10)
- MRR (Mean Reciprocal Rank averaged across users)
- Catalog Coverage@10 (share of the catalog that appears in at least one user's top 10)

Ground-Truth Sources (each evaluated separately):
1. "behaviour" - Simulated per-user behaviour. Every simulated student has HIDDEN latent
   preferences (category taste, taste-cluster membership, department, global event appeal)
   plus Gaussian noise. The events they RSVP to come from that hidden utility, NOT from the
   tag/category overlap rule the Rule-Based baseline uses. Models only see a noisy set of
   declared interests and the training-split RSVPs; the held-out test split is scored.
2. "tag_overlap" - The original synthetic set in `seed_ground_truth.json`, produced by
   `seed.py` with the same category/tag overlap rule the Rule-Based baseline scores with.
   It is kept for comparison and is biased toward the baseline.

Cohorts:
- Overall (All Users)
- Cold-Start Users (1-2 training interactions)
- Warm Users (60% of interactions used for training)
"""

from datetime import datetime, timezone
import csv
import json
import math
import os
import random
from typing import Sequence
import uuid

import numpy as np

from app.ml.baseline import recommend_baseline
from app.ml.engine import recommend_with_scores
from app.ml.hybrid_engine import recommend_hybrid
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.models.user_interest import UserInterest

# Fixed reference date ensures temporal urgency features remain deterministic.
# The benchmark scripts replace it with catalog_reference_date() so every catalog
# event is still upcoming, as in the live feed (which never shows ended events).
FIXED_REFERENCE_DATE = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)
SEEDS = [42, 43, 44, 45, 46, 47, 48, 49, 50, 51]
GROUND_TRUTH_FILE = "seed_ground_truth.json"
RESULTS_DIR = "results"
DOCS_DIR = os.path.join("..", "docs")

MODELS = ["Random", "Popularity", "Rule-Based", "TF-IDF Content", "Unified Hybrid"]
COHORTS = ["Overall", "Cold-Start", "Warm"]
METRICS = ["precision@5", "precision@10", "recall@5", "recall@10", "ndcg@10", "mrr", "coverage@10"]
GT_SOURCES = {
    "behaviour": "Behaviour-based ground truth (simulated latent preferences)",
    "tag_overlap": "Tag-overlap ground truth (biased toward the baseline)",
}

# ── Behaviour Simulation Parameters ────────────────────────────────────────────

SIM_USERS = 60
SIM_CLUSTERS = 6
SIM_NOISE_STD = 0.6
SIM_POSITIVES_RANGE = (8, 16)
# Weights of the hidden utility components (each component is z-scored first)
SIM_UTILITY_WEIGHTS = {"category": 0.45, "cluster": 0.35, "dept": 0.10, "appeal": 0.10}
# Probability that a declared interest tag is replaced by an unrelated one
SIM_DECLARATION_NOISE = 0.25

# Mirrors seed.py so simulated users declare tags from the same vocabulary
CATEGORY_TAGS = {
    "Academic":   ["research", "lecture", "seminar", "thesis", "study group", "journal club", "science", "mathematics"],
    "Social":     ["networking", "party", "mixer", "community", "games", "bonfire", "picnic", "karaoke"],
    "Sports":     ["football", "basketball", "athletics", "volleyball", "rugby", "fitness", "marathon", "swimming"],
    "Workshop":   ["hands-on", "training", "certification", "bootcamp", "beginner", "advanced", "skills"],
    "Cultural":   ["music", "dance", "art", "film", "theatre", "poetry", "fashion", "heritage"],
    "Tech":       ["python", "javascript", "ai", "data science", "cybersecurity", "web development", "mobile", "cloud", "iot", "blockchain"],
    "Career":     ["internship", "resume", "interview", "entrepreneurship", "startup", "leadership", "mentorship", "freelancing"],
}
CATEGORY_DEPARTMENTS = {
    "Academic":  "School of Science & Applied Tech",
    "Social":    "Student Affairs & Sports",
    "Sports":    "Student Affairs & Sports",
    "Workshop":  "School of Computer Science & IT",
    "Cultural":  "Cultural Society",
    "Tech":      "School of Computer Science & IT",
    "Career":    "School of Business",
}


def catalog_reference_date(events: Sequence[Event]) -> datetime:
    """Midnight UTC on the day the earliest catalog event starts: every event is upcoming."""
    earliest = min(
        e.start_time if e.start_time.tzinfo else e.start_time.replace(tzinfo=timezone.utc)
        for e in events
    )
    return earliest.replace(hour=0, minute=0, second=0, microsecond=0)


def use_catalog_reference_date(events: Sequence[Event]) -> datetime:
    """Point FIXED_REFERENCE_DATE at the catalog's start (called by the benchmark scripts)."""
    global FIXED_REFERENCE_DATE
    FIXED_REFERENCE_DATE = catalog_reference_date(events)
    return FIXED_REFERENCE_DATE


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


def catalog_coverage(rec_lists: Sequence[Sequence[str]], catalog_size: int, k: int = 10) -> float:
    """Catalog Coverage@K: distinct events in any user's top-K divided by catalog size."""
    if catalog_size <= 0:
        return 0.0
    distinct = {eid for recs in rec_lists for eid in recs[:k]}
    return len(distinct) / float(catalog_size)


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


# ── Train / Validation / Test Splitting ────────────────────────────────────────


def split_interactions(
    event_ids: list[str],
    is_cold: bool,
    rng: random.Random,
) -> tuple[list[str], list[str], list[str]]:
    """Shuffle a user's positive events into train / validation / test lists."""
    shuffled = list(event_ids)
    rng.shuffle(shuffled)
    if is_cold:
        # Cold-start student: 1-2 training interactions only
        n_train = min(len(shuffled), rng.randint(1, 2))
    else:
        # Warm student: 60% train
        n_train = max(3, int(len(shuffled) * 0.60))
    train, remaining = shuffled[:n_train], shuffled[n_train:]
    n_val = max(1, int(len(remaining) * 0.40)) if remaining else 0
    return train, remaining[:n_val], remaining[n_val:]


def _make_user_split(user, interests, is_cold, train_ids, val_ids, test_relevant, event_lookup):
    train_rsvps = [
        RSVP(user_id=user.id, event_id=event_lookup[eid].id, status="confirmed")
        for eid in train_ids
    ]
    return {
        "user": user,
        "interests": interests,
        "is_cold": is_cold,
        "train_rsvps": train_rsvps,
        "train_events": [event_lookup[eid] for eid in train_ids],
        "train_event_ids": set(train_ids),
        "val_relevant": set(val_ids),
        "test_relevant": set(test_relevant),
    }


def build_tag_overlap_splits(
    seed: int,
    db,
    all_events: list[Event],
    ground_truth: dict[str, list[str]],
) -> list[dict]:
    """
    Splits for the original seed.py ground truth. Training interactions are the seeded
    RSVPs; test relevance is every tag-overlap-relevant event not used for train/val.
    """
    rng = random.Random(seed)
    event_lookup = {str(e.id): e for e in all_events}

    user_rsvp_map: dict[str, list[str]] = {}
    for r in db.query(RSVP).filter(RSVP.status == "confirmed").all():
        if str(r.event_id) in event_lookup:
            user_rsvp_map.setdefault(str(r.user_id), []).append(str(r.event_id))

    student_users = []
    for username in sorted(ground_truth.keys()):
        user = db.query(User).filter(User.username == username).first()
        if user:
            student_users.append(user)

    shuffled_students = list(student_users)
    rng.shuffle(shuffled_students)
    num_cold = max(4, int(len(shuffled_students) * 0.35))
    cold_usernames = {u.username for u in shuffled_students[:num_cold]}

    splits = []
    for user in student_users:
        is_cold = user.username in cold_usernames
        interests = db.query(UserInterest).filter(UserInterest.user_id == user.id).all()
        train, val, test = split_interactions(user_rsvp_map.get(str(user.id), []), is_cold, rng)

        test_relevant = set(ground_truth.get(user.username, [])) - set(train) - set(val)
        if not test_relevant:
            test_relevant = set(test)
        splits.append(_make_user_split(user, interests, is_cold, train, val, test_relevant, event_lookup))
    return splits


def _zscore(values: np.ndarray) -> np.ndarray:
    std = values.std()
    return (values - values.mean()) / std if std > 0 else np.zeros_like(values)


def _event_tags(event: Event) -> list[str]:
    return [t.strip().lower() for t in (event.tags or "").split(",") if t.strip()]


def simulate_behaviour_users(
    seed: int,
    all_events: list[Event],
    n_users: int = SIM_USERS,
) -> list[dict]:
    """
    Simulate students whose RSVPs come from hidden latent preferences.

    Hidden utility of event e for user u (each term z-scored over the catalog):
        0.45 * category_taste[u][category(e)]       (Dirichlet-drawn, not declared directly)
      + 0.35 * cluster_affinity[cluster(u)][e]       (shared taste cluster: half hidden tag
                                                      weights, half event-specific latent factor)
      + 0.10 * [department(e) == department(u)]
      + 0.10 * appeal[e]                             (hidden campus-wide appeal)
      + N(0, SIM_NOISE_STD)

    The user's positives are the top-n events by that utility. Declared interests (all
    the models get to see) are a noisy, partial view: the category names and one tag of
    the user's 2-3 most liked categories, with each tag replaced by an unrelated one with
    probability SIM_DECLARATION_NOISE.
    """
    np_rng = np.random.default_rng(seed)
    categories = list(CATEGORY_TAGS.keys())
    all_tags = sorted({t for tags in CATEGORY_TAGS.values() for t in tags})
    tag_index = {t: i for i, t in enumerate(all_tags)}
    n_events = len(all_events)

    event_cat_idx = np.array([
        categories.index(e.category) if e.category in categories else 0 for e in all_events
    ])
    event_tag_lists = [[tag_index[t] for t in _event_tags(e) if t in tag_index] for e in all_events]

    appeal = _zscore(np_rng.normal(0.0, 1.0, n_events))
    clusters = []
    for _ in range(SIM_CLUSTERS):
        tag_weights = np_rng.normal(0.0, 1.0, len(all_tags))
        tag_part = np.array([tag_weights[idx].mean() if idx else 0.0 for idx in event_tag_lists])
        latent_part = np_rng.normal(0.0, 1.0, n_events)
        clusters.append({
            "tag_weights": tag_weights,
            "affinity": _zscore(0.5 * _zscore(tag_part) + 0.5 * latent_part),
        })

    w = SIM_UTILITY_WEIGHTS
    users = []
    for i in range(n_users):
        category_taste = np_rng.dirichlet(np.full(len(categories), 0.6))
        cluster = clusters[int(np_rng.integers(SIM_CLUSTERS))]
        top_cat = categories[int(np.argmax(category_taste))]
        department = (
            CATEGORY_DEPARTMENTS[top_cat]
            if np_rng.random() < 0.7
            else str(np_rng.choice(sorted(set(CATEGORY_DEPARTMENTS.values()))))
        )

        dept_match = np.array([1.0 if e.department == department else 0.0 for e in all_events])
        utility = (
            w["category"] * _zscore(category_taste[event_cat_idx])
            + w["cluster"] * cluster["affinity"]
            + w["dept"] * _zscore(dept_match)
            + w["appeal"] * appeal
            + np_rng.normal(0.0, SIM_NOISE_STD, n_events)
        )
        n_pos = int(np_rng.integers(SIM_POSITIVES_RANGE[0], SIM_POSITIVES_RANGE[1] + 1))
        positives = [str(all_events[j].id) for j in np.argsort(-utility)[:n_pos]]

        # Declared interests: noisy, partial view of the hidden category taste
        n_declared_cats = int(np_rng.integers(2, 4))
        declared_cats = np_rng.choice(
            categories, size=n_declared_cats, replace=False, p=category_taste
        )
        declared: list[str] = []
        for cat in declared_cats:
            pool = CATEGORY_TAGS[cat]
            best_tag = max(pool, key=lambda t: cluster["tag_weights"][tag_index[t]])
            declared.extend([cat.lower(), best_tag])
        declared = [
            str(np_rng.choice(all_tags)) if np_rng.random() < SIM_DECLARATION_NOISE else tag
            for tag in declared
        ]

        user = User(
            id=uuid.UUID(int=int(np_rng.integers(0, 2**63)) << 64 | i),
            username=f"sim_{seed}_{i:03d}",
            role="student",
            department=department,
        )
        interests = [
            UserInterest(user_id=user.id, interest_tag=tag, weight=1.0)
            for tag in dict.fromkeys(declared)
        ]
        users.append({"user": user, "interests": interests, "positives": positives})
    return users


def build_behaviour_splits(seed: int, all_events: list[Event]) -> list[dict]:
    """Splits for the behaviour ground truth: test relevance is the held-out RSVPs only."""
    rng = random.Random(seed)
    event_lookup = {str(e.id): e for e in all_events}
    sim_users = simulate_behaviour_users(seed, all_events)

    order = list(range(len(sim_users)))
    rng.shuffle(order)
    cold_idx = set(order[: int(len(sim_users) * 0.35)])

    splits = []
    for i, su in enumerate(sim_users):
        is_cold = i in cold_idx
        train, val, test = split_interactions(su["positives"], is_cold, rng)
        splits.append(_make_user_split(su["user"], su["interests"], is_cold, train, val, test, event_lookup))
    return splits


# ── Model Scoring ──────────────────────────────────────────────────────────────


def evaluate_trial(seed: int, all_events: list[Event], user_splits: list[dict]) -> dict:
    """Score every model on the held-out test split of one seed."""
    rng = random.Random(seed)
    all_train_rsvps = [r for u in user_splits for r in u["train_rsvps"]]

    # Candidate events for each user: all catalog events excluding their training interactions
    candidates_by_user = {
        u["user"].username: [e for e in all_events if str(e.id) not in u["train_event_ids"]]
        for u in user_splits
    }

    best_weights = select_best_hybrid_weights(user_splits, candidates_by_user, all_train_rsvps)

    results = {m: {c: [] for c in COHORTS} for m in MODELS}
    rec_lists = {m: {c: [] for c in COHORTS} for m in MODELS}

    for udata in user_splits:
        user = udata["user"]
        interests = udata["interests"]
        test_rel = udata["test_relevant"]
        user_train_events = udata["train_events"]
        cand_events = candidates_by_user[user.username]
        cohort = "Cold-Start" if udata["is_cold"] else "Warm"

        model_recs = {
            "Random": recommend_random(cand_events, top_n=10, rng=rng),
            "Popularity": recommend_popularity(
                cand_events, train_rsvps=all_train_rsvps, top_n=10, reference_date=FIXED_REFERENCE_DATE
            ),
            "Rule-Based": recommend_baseline(
                interests, cand_events, top_n=10, reference_date=FIXED_REFERENCE_DATE
            ),
            "TF-IDF Content": recommend_with_scores(
                interests, cand_events, rsvp_events=user_train_events, top_n=10
            ),
            "Unified Hybrid": recommend_hybrid(
                user=user,
                user_interests=interests,
                all_events=cand_events,
                all_rsvps=all_train_rsvps,
                rsvp_events=user_train_events,
                top_n=10,
                reference_date=FIXED_REFERENCE_DATE,
                custom_weights=best_weights,
            ),
        }

        for m_name, recs in model_recs.items():
            rec_ids = [str(r["event"].id) for r in recs]
            u_metrics = {
                "precision@5": precision_at_k(rec_ids, test_rel, 5),
                "precision@10": precision_at_k(rec_ids, test_rel, 10),
                "recall@5": recall_at_k(rec_ids, test_rel, 5),
                "recall@10": recall_at_k(rec_ids, test_rel, 10),
                "ndcg@10": ndcg_at_k(rec_ids, test_rel, 10),
                "mrr": reciprocal_rank(rec_ids, test_rel),
            }
            for c in ("Overall", cohort):
                results[m_name][c].append(u_metrics)
                rec_lists[m_name][c].append(rec_ids)

    # Per-seed means; coverage is a list-level metric, so it is computed once per cohort
    seed_means = {}
    for m in MODELS:
        for c in COHORTS:
            u_list = results[m][c]
            if not u_list:
                continue
            means = {k: float(np.mean([u[k] for u in u_list])) for k in u_list[0]}
            means["coverage@10"] = catalog_coverage(rec_lists[m][c], len(all_events))
            seed_means[(c, m)] = means

    return {"seed": seed, "best_weights": best_weights, "seed_means": seed_means}


def aggregate(trials: list[dict]) -> dict:
    """(cohort, model) -> {metric: (mean, std)} across seeds."""
    summary = {}
    for c in COHORTS:
        for m in MODELS:
            per_seed = [t["seed_means"][(c, m)] for t in trials if (c, m) in t["seed_means"]]
            summary[(c, m)] = {
                k: (
                    float(np.mean([s[k] for s in per_seed])) if per_seed else 0.0,
                    float(np.std([s[k] for s in per_seed], ddof=1)) if len(per_seed) > 1 else 0.0,
                )
                for k in METRICS
            }
    return summary


# ── Reporting ──────────────────────────────────────────────────────────────────

TABLE_COLUMNS = [
    ("precision@5", "P@5"),
    ("precision@10", "P@10"),
    ("recall@10", "R@10"),
    ("ndcg@10", "NDCG@10"),
    ("mrr", "MRR"),
    ("coverage@10", "Coverage@10"),
]


def markdown_tables(summaries: dict, meta: dict) -> str:
    lines = [
        "# Tukio Offline Evaluation - Generated Results",
        "",
        "> Generated by `backend/evaluate.py`. Do not edit by hand; re-run the script.",
        f"> Seeds: {len(SEEDS)} ({SEEDS[0]}-{SEEDS[-1]}) | Catalog: {meta['catalog_size']} events | "
        f"Reference date: {FIXED_REFERENCE_DATE.date().isoformat()}",
        "> Cells are mean ± sample standard deviation across seeds. Best mean per column in **bold** "
        "(Random and Popularity are reference floors and are excluded from bolding).",
        "",
    ]
    compared = ["Rule-Based", "TF-IDF Content", "Unified Hybrid"]
    for gt_key, gt_label in GT_SOURCES.items():
        summary = summaries[gt_key]
        lines.append(f"## {gt_label}")
        lines.append("")
        lines.append(f"Users per seed: {meta['users'][gt_key]}")
        lines.append("")
        for cohort in COHORTS:
            lines.append(f"### {cohort}")
            lines.append("")
            lines.append("| Model | " + " | ".join(label for _, label in TABLE_COLUMNS) + " |")
            lines.append("| :--- | " + " | ".join(":---:" for _ in TABLE_COLUMNS) + " |")
            best = {
                k: max(summary[(cohort, m)][k][0] for m in compared) for k, _ in TABLE_COLUMNS
            }
            for m in MODELS:
                cells = []
                for k, _ in TABLE_COLUMNS:
                    mean, std = summary[(cohort, m)][k]
                    cell = f"{mean:.3f} ± {std:.3f}"
                    if m in compared and math.isclose(mean, best[k]):
                        cell = f"**{cell}**"
                    cells.append(cell)
                lines.append(f"| {m} | " + " | ".join(cells) + " |")
            lines.append("")
    return "\n".join(lines)


def save_chart(summaries: dict, path: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    chart_metrics = [("precision@10", "P@10"), ("recall@10", "R@10"), ("ndcg@10", "NDCG@10"),
                     ("mrr", "MRR"), ("coverage@10", "Coverage@10")]
    colors = {
        "Random": "#b8b8b8",
        "Popularity": "#8c8c8c",
        "Rule-Based": "#e07b39",
        "TF-IDF Content": "#3a7dc9",
        "Unified Hybrid": "#2e9e6a",
    }
    fig, axes = plt.subplots(1, 2, figsize=(14, 5), sharey=True)
    width = 0.16
    x = np.arange(len(chart_metrics))
    for ax, (gt_key, gt_label) in zip(axes, GT_SOURCES.items()):
        summary = summaries[gt_key]
        for i, m in enumerate(MODELS):
            means = [summary[("Overall", m)][k][0] for k, _ in chart_metrics]
            stds = [summary[("Overall", m)][k][1] for k, _ in chart_metrics]
            ax.bar(x + (i - 2) * width, means, width, yerr=stds, capsize=2,
                   label=m, color=colors[m], edgecolor="white", linewidth=0.5)
        ax.set_title(gt_label, fontsize=11)
        ax.set_xticks(x, [label for _, label in chart_metrics])
        ax.set_ylim(0, 1.05)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
    axes[0].set_ylabel(f"Score (mean ± std over {len(SEEDS)} seeds, all users)")
    axes[1].legend(loc="upper right", fontsize=9, frameon=False)
    fig.suptitle("Tukio offline benchmark: baselines vs TF-IDF vs hybrid", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def main():
    from app.database import SessionLocal

    if not os.path.exists(GROUND_TRUTH_FILE):
        print(f"Error: {GROUND_TRUTH_FILE} not found. Run python seed.py first.")
        return

    with open(GROUND_TRUTH_FILE) as f:
        ground_truth: dict[str, list[str]] = json.load(f)

    db = SessionLocal()
    try:
        all_events = db.query(Event).order_by(Event.title, Event.start_time).all()
        if not all_events:
            print("Error: No events found in database. Run python seed.py first.")
            return
        use_catalog_reference_date(all_events)

        print("=" * 100)
        print("  TUKIO RECOMMENDATION ENGINE: MULTI-SEED OFFLINE BENCHMARK")
        print(f"  Catalog: {len(all_events)} events | Seeds: {len(SEEDS)} | Reference: {FIXED_REFERENCE_DATE.isoformat()}")
        print("=" * 100)

        summaries, all_trials, users_count = {}, {}, {}
        for gt_key, gt_label in GT_SOURCES.items():
            print(f"\n[{gt_label}]")
            trials = []
            for seed in SEEDS:
                if gt_key == "behaviour":
                    splits = build_behaviour_splits(seed, all_events)
                else:
                    splits = build_tag_overlap_splits(seed, db, all_events, ground_truth)
                users_count[gt_key] = len(splits)
                trial = evaluate_trial(seed, all_events, splits)
                trials.append(trial)
                o = trial["seed_means"]
                print(
                    f"  seed {seed}: NDCG@10 rule={o[('Overall', 'Rule-Based')]['ndcg@10']:.3f} "
                    f"tfidf={o[('Overall', 'TF-IDF Content')]['ndcg@10']:.3f} "
                    f"hybrid={o[('Overall', 'Unified Hybrid')]['ndcg@10']:.3f}"
                )
            summaries[gt_key] = aggregate(trials)
            all_trials[gt_key] = trials

        meta = {"catalog_size": len(all_events), "users": users_count}
        md = markdown_tables(summaries, meta)
        print("\n" + md)

        # ── Save Results to Disk ───────────────────────────────────────────────
        os.makedirs(RESULTS_DIR, exist_ok=True)
        os.makedirs(DOCS_DIR, exist_ok=True)

        with open(os.path.join(RESULTS_DIR, "evaluation.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["ground_truth", "seed", "cohort", "model", *METRICS])
            writer.writeheader()
            for gt_key, trials in all_trials.items():
                for t in trials:
                    for (c, m), vals in t["seed_means"].items():
                        writer.writerow({"ground_truth": gt_key, "seed": t["seed"], "cohort": c, "model": m, **vals})

        json_summary = {
            "metadata": {
                "evaluation_date": FIXED_REFERENCE_DATE.isoformat(),
                "seeds": SEEDS,
                "candidate_events_count": len(all_events),
                "users_count": users_count,
                "ground_truth_sources": GT_SOURCES,
                "behaviour_simulation": {
                    "users": SIM_USERS,
                    "clusters": SIM_CLUSTERS,
                    "noise_std": SIM_NOISE_STD,
                    "positives_range": list(SIM_POSITIVES_RANGE),
                    "utility_weights": SIM_UTILITY_WEIGHTS,
                    "declaration_noise": SIM_DECLARATION_NOISE,
                },
                "selected_hybrid_weights": {
                    gt_key: [t["best_weights"] for t in trials] for gt_key, trials in all_trials.items()
                },
            },
            "summary": {
                gt_key: {
                    f"{c}_{m}": {k: {"mean": round(v[0], 4), "std": round(v[1], 4)} for k, v in vals.items()}
                    for (c, m), vals in summary.items()
                }
                for gt_key, summary in summaries.items()
            },
        }
        with open(os.path.join(RESULTS_DIR, "evaluation.json"), "w", encoding="utf-8") as f:
            json.dump(json_summary, f, indent=2)

        md_path = os.path.join(DOCS_DIR, "evaluation_results.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md + "\n")
        chart_path = os.path.join(DOCS_DIR, "evaluation_chart.png")
        save_chart(summaries, chart_path)

        print("\n[OK] Results saved:")
        for p in (os.path.join(RESULTS_DIR, "evaluation.csv"), os.path.join(RESULTS_DIR, "evaluation.json"), md_path, chart_path):
            print(f"  -> {p}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
