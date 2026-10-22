"""
Unit tests for hybrid engine internals: context urgency and MMR diversity re-ranking.
"""

from datetime import datetime, timedelta, timezone
import math
import uuid

import numpy as np

from app.ml.hybrid_engine import compute_context_scores, mmr_rerank, recommend_hybrid
from app.models.event import Event
from app.models.user import User
from app.models.user_interest import UserInterest

NOW = datetime(2026, 10, 17, 12, 0, 0, tzinfo=timezone.utc)


def _event(title, start_offset_days, duration_hours=2, category="Tech", tags="ai, python", has_end=True):
    start = NOW + timedelta(days=start_offset_days)
    return Event(
        id=uuid.uuid4(),
        title=title,
        description=f"{title} description",
        category=category,
        tags=tags,
        department="School of Computer Science & IT",
        start_time=start,
        end_time=start + timedelta(hours=duration_hours) if has_end else None,
    )


def test_urgency_is_zero_for_ended_events_and_full_for_in_progress():
    ended = _event("Ended", -3)
    ended_no_end_time = _event("Ended no end", -1, has_end=False)
    in_progress = _event("Live now", 0, duration_hours=4)
    in_progress.start_time = NOW - timedelta(hours=1)
    in_progress.end_time = NOW + timedelta(hours=2)
    upcoming = _event("In 12 days", 12)

    _, urgency, _ = compute_context_scores(
        [ended, ended_no_end_time, in_progress, upcoming], None, [], reference_date=NOW
    )
    assert urgency[0] == 0.0
    assert urgency[1] == 0.0
    assert urgency[2] == 1.0
    assert math.isclose(urgency[3], math.exp(-1.0), rel_tol=1e-9)


def test_mmr_zero_diversity_is_plain_relevance_order():
    relevance = np.array([0.2, 0.9, 0.5, 0.7])
    similarity = np.eye(4)
    assert mmr_rerank(relevance, similarity, top_n=3, diversity=0.0) == [1, 3, 2]


def test_mmr_skips_near_duplicate_of_already_picked_item():
    # Items 0 and 1 are near-duplicates; item 2 is different but slightly less relevant
    relevance = np.array([1.0, 0.95, 0.9])
    similarity = np.array([
        [1.0, 0.98, 0.1],
        [0.98, 1.0, 0.1],
        [0.1, 0.1, 1.0],
    ])
    assert mmr_rerank(relevance, similarity, top_n=2, diversity=0.0) == [0, 1]
    assert mmr_rerank(relevance, similarity, top_n=2, diversity=0.5) == [0, 2]


def test_recommend_hybrid_diversity_avoids_near_duplicates():
    user = User(id=uuid.uuid4(), username="mmr_user", department="School of Computer Science & IT")
    interests = [UserInterest(user_id=user.id, interest_tag="ai", weight=1.0)]
    events = [
        _event("AI Hackathon", 2, tags="ai, hackathon"),
        _event("AI Hackathon Day Two", 3, tags="ai, hackathon"),
        _event("Python Data Science Bootcamp", 4, tags="python, data science"),
        _event("Football Final", 5, category="Sports", tags="football"),
    ]

    plain = recommend_hybrid(user, interests, events, top_n=3, reference_date=NOW, diversity=0.0)
    default = recommend_hybrid(user, interests, events, top_n=3, reference_date=NOW)
    diverse = recommend_hybrid(user, interests, events, top_n=3, reference_date=NOW, diversity=0.9)

    # DEFAULT_DIVERSITY is 0, so the default call matches plain relevance ranking
    assert [r["event"].id for r in default] == [r["event"].id for r in plain]
    assert len(diverse) == 3
    # Heavy diversity keeps the top event but stops the near-duplicate taking second place
    assert diverse[0]["event"].id == plain[0]["event"].id
    titles = [r["event"].title for r in diverse[:2]]
    assert not ("AI Hackathon" in titles and "AI Hackathon Day Two" in titles)
