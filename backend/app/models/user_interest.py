"""
UserInterest database model.

Tracks a user's interest tags used by the recommendation engine to
compute personalised event rankings.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserInterest(Base):
    """A single interest tag belonging to a user."""

    __tablename__ = "user_interests"
    __table_args__ = (
        UniqueConstraint("user_id", "interest_tag", name="uq_user_interest_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    interest_tag: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    weight: Mapped[float] = mapped_column(
        Float, default=1.0  # Allow future fine-tuning of tag importance
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # ── Relationships ─────────────────────────────────────────────────
    user = relationship("User", back_populates="interests")

    def __repr__(self) -> str:
        return f"<UserInterest user={self.user_id} tag={self.interest_tag!r}>"
