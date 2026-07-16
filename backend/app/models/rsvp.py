"""
RSVP database model.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class RSVP(Base):
    """Tracks a user's attendance registration for an event."""

    __tablename__ = "rsvps"
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_user_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("events.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default="confirmed"  # confirmed | cancelled
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────
    user = relationship("User", back_populates="rsvps")
    event = relationship("Event", back_populates="rsvps")

    def __repr__(self) -> str:
        return f"<RSVP user={self.user_id} event={self.event_id} status={self.status}>"
