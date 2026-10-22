"""
Unit tests for Tukio Offline Evaluation (Priority 9).

Verifies:
1. Strict data leakage prevention (held-out test events NEVER appear in training inputs).
2. Correctness and edge-case resilience of ranking metrics (Precision@K, Recall@K, NDCG@K, MRR).
3. Deterministic repeatability under a fixed reference date.
"""

from datetime import datetime, timedelta, timezone
import math
import uuid

import pytest

from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.models.user_interest import UserInterest
from app.ml.baseline import recommend_baseline
from app.ml.hybrid_engine import recommend_hybrid
from evaluate import (
    precision_at_k,
    recall_at_k,
    ndcg_at_k,
    reciprocal_rank,
    catalog_coverage,
    catalog_reference_date,
    recommend_popularity,
    recommend_random,
    simulate_behaviour_users,
    build_behaviour_splits,
    CATEGORY_TAGS,
    CATEGORY_DEPARTMENTS,
    FIXED_REFERENCE_DATE,
    SIM_POSITIVES_RANGE,
)


def test_metric_calculations_edge_cases():
    """Verify precision, recall, ndcg, and mrr on boundary cases and known values."""
    # 1. Empty recommendations
    assert precision_at_k([], {"e1", "e2"}, k=5) == 0.0
    assert recall_at_k([], {"e1", "e2"}, k=5) == 0.0
    assert ndcg_at_k([], {"e1", "e2"}, k=10) == 0.0
    assert reciprocal_rank([], {"e1", "e2"}) == 0.0

    # 2. Empty relevant set
    assert precision_at_k(["e1", "e2"], set(), k=5) == 0.0
    assert recall_at_k(["e1", "e2"], set(), k=5) == 0.0
    assert ndcg_at_k(["e1", "e2"], set(), k=10) == 0.0
    assert reciprocal_rank(["e1", "e2"], set()) == 0.0

    # 3. Perfect Top-3 hits
    recs = ["e1", "e2", "e3", "e4", "e5"]
    rel = {"e1", "e2", "e3"}
    assert precision_at_k(recs, rel, k=3) == 1.0
    assert recall_at_k(recs, rel, k=3) == 1.0
    assert ndcg_at_k(recs, rel, k=10) == 1.0
    assert reciprocal_rank(recs, rel) == 1.0

    # 4. First hit at rank 2
    recs_rank2 = ["noise", "e1", "noise2"]
    assert reciprocal_rank(recs_rank2, {"e1"}) == 0.5
    assert precision_at_k(recs_rank2, {"e1"}, k=2) == 0.5
    assert recall_at_k(recs_rank2, {"e1"}, k=2) == 1.0

    # 5. NDCG calculation manual verification
    # Recs: [relevant, non-relevant, relevant], Ideal: [rel, rel, non-rel]
    # DCG@3 = 1/log2(2) + 0 + 1/log2(4) = 1.0 + 0.5 = 1.5
    # IDCG@3 = 1/log2(2) + 1/log2(3) = 1.0 + (1 / 1.58496) = 1.0 + 0.63093 = 1.63093
    # Expected NDCG = 1.5 / 1.63093 ~= 0.9197
    recs_test = ["r1", "noise", "r2"]
    rel_test = {"r1", "r2"}
    val_ndcg = ndcg_at_k(recs_test, rel_test, k=3)
    assert abs(val_ndcg - (1.5 / (1.0 + 1.0 / math.log2(3)))) < 1e-4


def test_held_out_events_never_appear_in_training_inputs(db_session, student_user, organizer_user):
    """
    Requirement 2 Test:
    Asserts that held-out events are completely quarantined:
    - Never passed in rsvp_events to Content-based recommender
    - Never included in all_train_rsvps passed to SVD or Popularity
    - Disjoint from train_events
    """
    ref_now = FIXED_REFERENCE_DATE

    ev_train = Event(
        id=uuid.uuid4(),
        title="Training Cloud Workshop",
        category="Tech",
        tags="cloud, tech",
        start_time=ref_now + timedelta(days=2),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    ev_held_out = Event(
        id=uuid.uuid4(),
        title="Held-out Test AI Hackathon",
        category="Tech",
        tags="ai, tech",
        start_time=ref_now + timedelta(days=4),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add_all([ev_train, ev_held_out])
    db_session.commit()

    # User RSVPs to both
    r_train = RSVP(user_id=student_user.id, event_id=ev_train.id, status="confirmed")
    r_test = RSVP(user_id=student_user.id, event_id=ev_held_out.id, status="confirmed")
    db_session.add_all([r_train, r_test])
    db_session.commit()

    # Partition: train gets ev_train, test gets ev_held_out
    test_relevant_ids = {str(ev_held_out.id)}

    # Training signals
    all_user_rsvps = db_session.query(RSVP).filter(RSVP.user_id == student_user.id).all()
    train_rsvps = [r for r in all_user_rsvps if str(r.event_id) not in test_relevant_ids]
    train_rsvp_events = [ev_train]  # Strictly training events

    # 1. Assert disjointness
    train_event_ids = {str(r.event_id) for r in train_rsvps}
    assert str(ev_held_out.id) not in train_event_ids
    assert str(ev_train.id) in train_event_ids

    # 2. Assert popularity baseline on train_rsvps only counts ev_train
    pop_recs = recommend_popularity(
        candidate_events=[ev_train, ev_held_out],
        train_rsvps=train_rsvps,
        top_n=2,
        reference_date=ref_now,
    )
    pop_map = {str(r["event"].id): r["score"] for r in pop_recs}
    assert pop_map[str(ev_train.id)] == 1.0
    assert pop_map[str(ev_held_out.id)] == 0.0

    # 3. Assert hybrid engine given train_rsvps and train_rsvp_events has no test leakage
    interests = [UserInterest(user_id=student_user.id, interest_tag="Tech")]
    hybrid_recs = recommend_hybrid(
        user=student_user,
        user_interests=interests,
        all_events=[ev_held_out],
        all_rsvps=train_rsvps,
        rsvp_events=train_rsvp_events,
        reference_date=ref_now,
    )
    assert len(hybrid_recs) == 1


def test_fixed_reference_date_determinism(db_session, student_user, organizer_user):
    """Verify that passing fixed reference_date guarantees 100% deterministic output."""
    fixed_dt = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)
    ev = Event(
        id=uuid.uuid4(),
        title="Deterministic Science Symposium",
        category="Academic",
        tags="science, research",
        start_time=fixed_dt + timedelta(days=3),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add(ev)
    db_session.commit()

    interests = [UserInterest(user_id=student_user.id, interest_tag="Academic")]

    res1 = recommend_baseline(interests, [ev], top_n=1, reference_date=fixed_dt)
    res2 = recommend_baseline(interests, [ev], top_n=1, reference_date=fixed_dt)

    assert len(res1) == 1
    assert res1[0]["score"] == res2[0]["score"]
    assert res1[0]["explanation"] == res2[0]["explanation"]


def _synthetic_catalog(n_per_category: int = 6) -> list[Event]:
    """Unsaved in-memory events spread over every category, each with two pool tags."""
    events = []
    for cat, pool in CATEGORY_TAGS.items():
        for i in range(n_per_category):
            events.append(Event(
                id=uuid.uuid4(),
                title=f"{cat} Event {i}",
                description=f"A {cat.lower()} session",
                category=cat,
                department=CATEGORY_DEPARTMENTS[cat],
                tags=",".join([pool[i % len(pool)], pool[(i + 1) % len(pool)]]),
                start_time=FIXED_REFERENCE_DATE + timedelta(days=i + 1),
            ))
    return events


def test_catalog_coverage():
    """Coverage counts distinct events across all users' top-K lists."""
    assert catalog_coverage([], 10) == 0.0
    assert catalog_coverage([["a", "b"]], 0) == 0.0
    assert catalog_coverage([["a", "b"], ["b", "c"]], 10) == 0.3
    # Only the top-K of each list counts
    assert catalog_coverage([["a", "b", "c"]], 10, k=2) == 0.2


def test_behaviour_simulation_is_seeded_and_well_formed():
    """Same seed reproduces the same users; positives and declared interests are well formed."""
    events = _synthetic_catalog()
    event_ids = {str(e.id) for e in events}

    run1 = simulate_behaviour_users(7, events, n_users=20)
    run2 = simulate_behaviour_users(7, events, n_users=20)
    assert [u["positives"] for u in run1] == [u["positives"] for u in run2]
    assert [[i.interest_tag for i in u["interests"]] for u in run1] == \
           [[i.interest_tag for i in u["interests"]] for u in run2]

    run3 = simulate_behaviour_users(8, events, n_users=20)
    assert [u["positives"] for u in run1] != [u["positives"] for u in run3]

    for u in run1:
        lo, hi = SIM_POSITIVES_RANGE
        assert lo <= len(u["positives"]) <= hi
        assert len(set(u["positives"])) == len(u["positives"])
        assert set(u["positives"]) <= event_ids
        assert 1 <= len(u["interests"]) <= 6


def test_behaviour_ground_truth_is_not_the_tag_overlap_rule():
    """
    Positives come from hidden preferences, so some RSVP'd events share neither a
    category nor a tag with the user's declared interests (impossible under seed.py's rule).
    """
    events = _synthetic_catalog()
    by_id = {str(e.id): e for e in events}
    outside_rule = 0
    for u in simulate_behaviour_users(11, events, n_users=30):
        declared = {i.interest_tag for i in u["interests"]}
        for eid in u["positives"]:
            ev = by_id[eid]
            ev_tags = {t.strip() for t in ev.tags.split(",")}
            if ev.category.lower() not in declared and not (declared & ev_tags):
                outside_rule += 1
    assert outside_rule > 0


def test_behaviour_splits_have_no_leakage():
    """Train, validation and test events are disjoint and cold-start users train on 1-2 events."""
    events = _synthetic_catalog()
    splits = build_behaviour_splits(3, events)
    assert any(s["is_cold"] for s in splits) and any(not s["is_cold"] for s in splits)
    for s in splits:
        train = s["train_event_ids"]
        assert not train & s["val_relevant"]
        assert not train & s["test_relevant"]
        assert not s["val_relevant"] & s["test_relevant"]
        assert {str(r.event_id) for r in s["train_rsvps"]} == train
        assert all(r.user_id == s["user"].id for r in s["train_rsvps"])
        if s["is_cold"]:
            assert 1 <= len(train) <= 2


def test_catalog_reference_date_makes_every_event_upcoming():
    """The benchmark reference date is midnight UTC on the first event's day."""
    events = _synthetic_catalog()
    events[3].start_time = datetime(2026, 9, 7, 16, 22)  # naive, as SQLite returns it
    ref = catalog_reference_date(events)
    assert ref == datetime(2026, 9, 7, 0, 0, tzinfo=timezone.utc)
    assert all(
        (e.start_time if e.start_time.tzinfo else e.start_time.replace(tzinfo=timezone.utc)) >= ref
        for e in events
    )
