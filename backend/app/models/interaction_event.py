"""
InteractionEvent model: Append-only telemetry log.
Tracks user interactions (impression, skip, rsvp, interested, not_for_me)
without unique constraints for analytical telemetry and recommender feedback.
"""

from datetime import datetime, timezone
import uuid

from sqlalchemy import Column, DateTime, ForeignKey, String
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


class InteractionEvent(Base):
    __tablename__ = "interaction_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_id = Column(GUID(), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True)
    interaction_type = Column(String(50), nullable=False, index=True)  # impression, skip, rsvp, interested, not_for_me
    session_id = Column(String(100), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user = relationship("User", backref="interaction_logs")
    event = relationship("Event", backref="interaction_logs")

    def __repr__(self):
        return f"<InteractionEvent user={self.user_id} event={self.event_id} type={self.interaction_type}>"
