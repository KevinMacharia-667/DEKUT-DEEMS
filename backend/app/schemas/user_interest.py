"""
Pydantic schemas for UserInterest request/response validation.
"""

import uuid

from pydantic import BaseModel, Field


class InterestTag(BaseModel):
    """A single interest tag with optional weight."""

    tag: str = Field(..., min_length=1, max_length=50)
    weight: float = Field(1.0, ge=0.0, le=10.0)


class UserInterestsUpdate(BaseModel):
    """Replace all of a user's interest tags at once."""

    interests: list[InterestTag]


class UserInterestResponse(BaseModel):
    """Single interest tag in API responses."""

    id: uuid.UUID
    interest_tag: str
    weight: float

    model_config = {"from_attributes": True}
