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
    strategy: Literal["ml", "baseline"] = Query(
        "ml", description="Ranking strategy: 'ml' (TF-IDF) or 'baseline' (rules)"
    ),
    k: int = Query(10, ge=1, le=50, description="Number of recommendations"),
):
    """
    Rank upcoming published events for the current user based on their
    interest tags (and, for the ML strategy, their RSVP history).
    """
    now = datetime.now(timezone.utc)

    # Candidate pool: upcoming, published events only.
    # (SQLite stores naive datetimes, so compare with a naive UTC value.)
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

    if strategy == "baseline":
        ranked = recommend_baseline(interests, candidates, top_n=k)
    else:
        rsvp_events = (
            db.query(Event)
            .join(RSVP, RSVP.event_id == Event.id)
            .filter(RSVP.user_id == current_user.id, RSVP.status == "confirmed")
            .all()
        )
        ranked = recommend_with_scores(
            interests, candidates, rsvp_events=rsvp_events, top_n=k
        )

    items = [
        RecommendationItem(
            event=_event_to_response(r["event"]),
            score=r["score"],
            explanation=r["explanation"],
        )
        for r in ranked
    ]

    return RecommendationListResponse(
        strategy=strategy, count=len(items), recommendations=items
    )
