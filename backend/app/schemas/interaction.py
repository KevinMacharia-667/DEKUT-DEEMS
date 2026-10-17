"""
Interaction and Feedback schemas.
"""

from datetime import datetime
from typing import Literal
import uuid
from pydantic import BaseModel, ConfigDict


class FeedbackCreate(BaseModel):
    feedback_type: Literal["interested", "not_for_me"]


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    event_id: uuid.UUID
    feedback_type: str
    created_at: datetime
    updated_at: datetime


class UserInteractionsResponse(BaseModel):
    interested: list[uuid.UUID]
    not_for_me: list[uuid.UUID]


class InteractionLogCreate(BaseModel):
    interaction_type: Literal[
        "impression", "skip", "rsvp", "interested", "not_for_me", "share", "add_to_calendar"
    ]
    session_id: str | None = None


class BatchInteractionItem(BaseModel):
    event_id: uuid.UUID
    interaction_type: Literal[
        "impression", "skip", "rsvp", "interested", "not_for_me", "share", "add_to_calendar"
    ]
    session_id: str | None = None


class BatchInteractionLogCreate(BaseModel):
    interactions: list[BatchInteractionItem]
