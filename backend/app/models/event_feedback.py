"""
EventFeedback model: Stores current feedback status per user and event.
Enforces unique constraint on (user_id, event_id).
Feedback types: 'interested' or 'not_for_me'.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import CHAR, TypeDecorator

from app.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type."""
    impl = CHAR(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


class EventFeedback(Base):
    __tablename__ = "event_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_user_event_feedback"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(GUID(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type = Column(String(30), nullable=False)  # 'interested' or 'not_for_me'

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", backref="feedbacks")
    event = relationship("Event", backref="feedbacks")

    def __repr__(self):
        return f"<EventFeedback user={self.user_id} event={self.event_id} type={self.feedback_type}>"
