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
from sqlalchemy.orm import Session

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
):
    """
    Rank upcoming published events for the current user using the selected strategy.
    Default is 'hybrid' which combines Content-Based Filtering, SVD Collaborative Filtering,
    and Contextual Ranking (Urgency, Popularity, and Faculty alignment).
    """
    now = datetime.now(timezone.utc)

    # Candidate pool: upcoming, published events only.
    candidates = (
        db.query(Event)
        .filter(Event.is_published.is_(True))
        .filter(Event.start_time >= now.replace(tzinfo=None))
        .all()
    )

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
            interests, candidates, rsvp_events=user_rsvps, top_n=k
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
