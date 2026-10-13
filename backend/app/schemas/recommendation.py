"""
Pydantic schemas for the recommendation endpoint.
"""

from pydantic import BaseModel

from app.schemas.event import EventResponse


class RecommendationItem(BaseModel):
    """A single recommended event with its score and explanation."""

    event: EventResponse
    score: float
    explanation: str
    badge: str | None = None
    reasons: list[str] = []
    content_score: float = 0.0
    collab_score: float = 0.0
    urgency_score: float = 0.0
    dept_score: float = 0.0


class RecommendationListResponse(BaseModel):
    """Response for GET /recommendations."""

    strategy: str
    count: int
    recommendations: list[RecommendationItem]
