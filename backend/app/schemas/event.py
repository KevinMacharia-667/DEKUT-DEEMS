"""
Pydantic schemas for Event request/response validation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserBrief


# ── Request Schemas ───────────────────────────────────────────────────


class EventCreate(BaseModel):
    """Schema for creating a new event."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=200)
    start_time: datetime
    end_time: datetime | None = None
    max_attendees: int | None = Field(None, ge=1)
    image_url: str | None = Field(None, max_length=500)
    tags: str | None = Field(None, max_length=500, description="Comma-separated tags")


class EventUpdate(BaseModel):
    """Schema for updating an existing event. All fields are optional."""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = Field(None, max_length=50)
    location: str | None = Field(None, max_length=200)
    start_time: datetime | None = None
    end_time: datetime | None = None
    max_attendees: int | None = Field(None, ge=1)
    image_url: str | None = Field(None, max_length=500)
    tags: str | None = Field(None, max_length=500, description="Comma-separated tags")
    is_published: bool | None = None


# ── Response Schemas ──────────────────────────────────────────────────


class EventResponse(BaseModel):
    """Full event representation returned by the API."""

    id: uuid.UUID
    title: str
    description: str | None
    category: str | None
    location: str | None
    start_time: datetime
    end_time: datetime | None
    max_attendees: int | None
    image_url: str | None
    tags: str | None
    organizer: UserBrief
    is_published: bool
    rsvp_count: int = 0
    created_at: datetime
    updated_at: datetime | None

    model_config = {"from_attributes": True}


class EventListResponse(BaseModel):
    """Paginated list of events."""

    events: list[EventResponse]
    total: int
    page: int
    per_page: int
