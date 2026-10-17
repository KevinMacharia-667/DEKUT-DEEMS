"""
Interaction service: Helper for writing append-only telemetry events
(impressions, skips, rsvps, interested, not_for_me) to interaction_events.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session

from app.models.interaction_event import InteractionEvent


def log_interaction(
    db: Session,
    event_id: uuid.UUID,
    interaction_type: str,
    user_id: uuid.UUID | None = None,
    session_id: str | None = None,
    commit: bool = True,
) -> InteractionEvent:
    """
    Append an interaction event to interaction_events.
    Can be called for authenticated users (user_id from JWT) or guest sessions.
    """
    interaction = InteractionEvent(
        user_id=user_id,
        event_id=event_id,
        interaction_type=interaction_type,
        session_id=session_id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(interaction)
    if commit:
        db.commit()
        db.refresh(interaction)
    return interaction
