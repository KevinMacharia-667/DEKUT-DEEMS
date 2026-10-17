"""
Database models package.
Import all models here so Alembic and Base.metadata can discover them.
"""

from app.models.user import User
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user_interest import UserInterest
from app.models.event_feedback import EventFeedback
from app.models.interaction_event import InteractionEvent

__all__ = ["User", "Event", "RSVP", "UserInterest", "EventFeedback", "InteractionEvent"]

