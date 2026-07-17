"""
Rule-Based Baseline Recommender.

A deliberately simple, non-ML scorer used as the comparison baseline for
the TF-IDF engine (see engine.py). Scoring rules:

    +3  if the event's category matches one of the user's interest tags
    +2  for every event tag that overlaps a user interest tag
    +1  if the event starts within the next 14 days (recency bonus)

Events with a score of 0 are never recommended.
"""

from datetime import datetime, timedelta, timezone
from typing import Sequence

from app.models.event import Event
from app.models.user_interest import UserInterest

CATEGORY_MATCH_POINTS = 3
TAG_OVERLAP_POINTS = 2
RECENCY_BONUS_POINTS = 1
RECENCY_WINDOW_DAYS = 14


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    """SQLite returns naive datetimes; treat naive values as UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _event_tag_set(event: Event) -> set[str]:
    if not event.tags:
        return set()
    return {t.strip().lower() for t in event.tags.split(",") if t.strip()}


def score_event(user_tags: set[str], event: Event) -> tuple[float, str]:
    """Return (score, human-readable explanation) for one event."""
    score = 0.0
    reasons: list[str] = []

    category = (event.category or "").strip().lower()
    if category and category in user_tags:
        score += CATEGORY_MATCH_POINTS
        reasons.append(f"category match: {event.category}")

    overlap = sorted(user_tags & _event_tag_set(event))
    if overlap:
        score += TAG_OVERLAP_POINTS * len(overlap)
        reasons.append("shared tags: " + ", ".join(overlap[:3]))

    starts = _as_utc(event.start_time)
    if _now_utc() <= starts <= _now_utc() + timedelta(days=RECENCY_WINDOW_DAYS):
        score += RECENCY_BONUS_POINTS
        reasons.append("happening soon")

    return score, "; ".join(reasons)


def recommend_baseline(
    user_interests: Sequence[UserInterest],
    all_events: Sequence[Event],
    top_n: int = 10,
) -> list[dict]:
    """
    Rank events for a user using the rule-based scorer.

    Returns a list of dicts: {"event": Event, "score": float,
    "explanation": str}, highest score first. Ties are broken by the
    sooner start time so imminent events surface first.
    """
    user_tags = {ui.interest_tag.strip().lower() for ui in user_interests}
    if not user_tags:
        return []

    scored = []
    for event in all_events:
        score, explanation = score_event(user_tags, event)
        if score > 0:
            scored.append({"event": event, "score": score, "explanation": explanation})

    scored.sort(key=lambda r: (-r["score"], _as_utc(r["event"].start_time)))
    return scored[:top_n]
