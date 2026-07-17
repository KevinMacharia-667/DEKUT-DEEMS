"""
Event database model.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Event(Base):
    """Represents a campus event created by an organizer."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(
        String(200), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(
        String(50)  # Academic, Social, Sports, Workshop, Cultural, etc.
    )
    location: Mapped[str | None] = mapped_column(String(200))
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_attendees: Mapped[int | None] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(500))
    tags: Mapped[str | None] = mapped_column(
        String(500)  # Comma-separated tags, e.g. "python,hackathon,beginner"
    )
    organizer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────
    organizer = relationship("User", back_populates="events_created")
    rsvps = relationship(
        "RSVP",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Event {self.title!r}>"
