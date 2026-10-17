"""
Recommendations router.

GET /recommendations?strategy=ml|baseline&k=10

Returns a personalised ranking of upcoming, published events for the
authenticated user. Two interchangeable strategies are exposed so the
project evaluation (and the live demo) can compare them:

    baseline — rule-based scoring (category match + tag overlap + recency)
    ml       — content-based filtering with TF-IDF + cosine similarity
"""

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.services.time_utils import get_nairobi_now

from app.dependencies import get_current_user, get_db
from app.ml.baseline import recommend_baseline
from app.ml.engine import recommend_with_scores
from app.ml.hybrid_engine import recommend_hybrid
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.models.user_interest import UserInterest
from app.routers.events import _event_to_response
from app.schemas.recommendation import (
    RecommendationItem,
    RecommendationListResponse,
)

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get(
    "",
    response_model=RecommendationListResponse,
    summary="Get personalised event recommendations",
)
def get_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    strategy: Literal["hybrid", "ml", "baseline"] = Query(
        "hybrid",
        description="Ranking strategy: 'hybrid' (Multi-Factor), 'ml' (TF-IDF), or 'baseline' (rules)",
    ),
    k: int = Query(10, ge=1, le=50, description="Number of recommendations"),
    reference_time: datetime | None = Query(
        None, description="Optional reference datetime in ISO format (for tests or fixed-date evaluation)"
    ),
):
    """
    Rank upcoming published events for the current user using the selected strategy.
    Default is 'hybrid' which combines Content-Based Filtering, SVD Collaborative Filtering,
    and Contextual Ranking (Urgency, Popularity, and Faculty alignment).
    Excludes events that have already ended.
    """
    ref_dt = get_nairobi_now(reference_time)
    naive_ref = ref_dt.replace(tzinfo=None)

    not_ended_filter = or_(
        Event.end_time >= naive_ref,
        and_(Event.end_time.is_(None), Event.start_time >= naive_ref),
    )

    from app.models.event_feedback import EventFeedback

    # Query user's feedbacks
    user_feedbacks = (
        db.query(EventFeedback)
        .filter(EventFeedback.user_id == current_user.id)
        .all()
    )
    not_for_me_ids = {f.event_id for f in user_feedbacks if f.feedback_type == "not_for_me"}
    interested_ids = {f.event_id for f in user_feedbacks if f.feedback_type == "interested"}

    # Candidate pool: upcoming, published events that haven't ended yet
    # Exclude events the user explicitly marked "not_for_me" (applies to For You recommendations)
    cand_query = (
        db.query(Event)
        .filter(Event.is_published.is_(True))
        .filter(not_ended_filter)
    )
    if not_for_me_ids:
        cand_query = cand_query.filter(~Event.id.in_(not_for_me_ids))

    candidates = cand_query.all()

    interests = (
        db.query(UserInterest)
        .filter(UserInterest.user_id == current_user.id)
        .all()
    )

    user_rsvps = (
        db.query(Event)
        .join(RSVP, RSVP.event_id == Event.id)
        .filter(RSVP.user_id == current_user.id, RSVP.status == "confirmed")
        .all()
    )

    interested_events = (
        db.query(Event).filter(Event.id.in_(interested_ids)).all()
        if interested_ids
        else []
    )
    not_for_me_events = (
        db.query(Event).filter(Event.id.in_(not_for_me_ids)).all()
        if not_for_me_ids
        else []
    )
    all_feedbacks = (
        db.query(EventFeedback)
        .filter(EventFeedback.feedback_type == "interested")
        .all()
    )

    if strategy == "baseline":
        ranked = recommend_baseline(interests, candidates, top_n=k)
        items = [
            RecommendationItem(
                event=_event_to_response(r["event"]),
                score=r["score"],
                explanation=r["explanation"],
                badge="📌 Rule Match",
                reasons=[r["explanation"]] if r["explanation"] else ["Rule-based heuristic match"],
                content_score=0.0,
                collab_score=0.0,
                urgency_score=0.0,
                dept_score=0.0,
            )
            for r in ranked
        ]
    elif strategy == "ml":
        ranked = recommend_with_scores(
            interests,
            candidates,
            rsvp_events=list(user_rsvps) + list(interested_events),
            top_n=k,
        )
        items = [
            RecommendationItem(
                event=_event_to_response(r["event"]),
                score=r["score"],
                explanation=r["explanation"],
                badge="✨ For You" if idx < 2 else "⭐ Content Match",
                reasons=[r["explanation"]] if r["explanation"] else ["TF-IDF semantic match"],
                content_score=r["score"],
                collab_score=0.0,
                urgency_score=0.0,
                dept_score=0.0,
            )
            for idx, r in enumerate(ranked)
        ]
    else:
        # Default: Unified Multi-Factor Hybrid Engine
        all_rsvps = db.query(RSVP).all()
        ranked = recommend_hybrid(
            user=current_user,
            user_interests=interests,
            all_events=candidates,
            all_rsvps=all_rsvps,
            rsvp_events=user_rsvps,
            interested_events=interested_events,
            not_for_me_events=not_for_me_events,
            all_feedbacks=all_feedbacks,
            top_n=k,
        )
        items = [
            RecommendationItem(
                event=_event_to_response(r["event"]),
                score=r["score"],
                explanation=r["explanation"],
                badge=r.get("badge", "✨ For You"),
                reasons=r.get("reasons", []),
                content_score=r.get("content_score", 0.0),
                collab_score=r.get("collab_score", 0.0),
                urgency_score=r.get("urgency_score", 0.0),
                dept_score=r.get("dept_score", 0.0),
            )
            for r in ranked
        ]

    return RecommendationListResponse(
        strategy=strategy, count=len(items), recommendations=items
    )
