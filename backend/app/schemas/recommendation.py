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


class RecommendationListResponse(BaseModel):
    """Response for GET /recommendations."""

    strategy: str
    count: int
    recommendations: list[RecommendationItem]
