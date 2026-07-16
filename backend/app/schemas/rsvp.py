"""
Pydantic schemas for RSVP request/response validation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserBrief


class RSVPResponse(BaseModel):
    """RSVP record returned by the API."""

    id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AttendeeResponse(BaseModel):
    """An attendee entry for listing event attendees."""

    rsvp_id: uuid.UUID
    user: UserBrief
    status: str
    rsvp_date: datetime

    model_config = {"from_attributes": True}
