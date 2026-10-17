"""
Interactions & Feedback router.

Endpoints:
- POST /events/{event_id}/feedback : Set feedback ('interested' or 'not_for_me')
- DELETE /events/{event_id}/feedback : Remove feedback (undo)
- GET /users/me/interactions : List current user's active feedbacks
- POST /events/{event_id}/interactions : Append telemetry interaction (impression, skip)
- POST /events/interactions/batch : Batch append telemetry interactions
"""

from datetime import datetime, timezone
from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db, get_optional_current_user
from app.models.event import Event
from app.models.event_feedback import EventFeedback
from app.models.user import User
from app.schemas.interaction import (
    BatchInteractionLogCreate,
    FeedbackCreate,
    FeedbackResponse,
    InteractionLogCreate,
    UserInteractionsResponse,
)
from app.services.interaction_service import log_interaction

router = APIRouter(tags=["Interactions & Feedback"])


@router.post(
    "/events/{event_id}/feedback",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit event feedback (interested / not_for_me)",
)
def submit_event_feedback(
    event_id: uuid.UUID,
    payload: FeedbackCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Record or update user feedback for an event.
    user_id is extracted strictly from the JWT authentication token.
    Writes to event_feedback (upsert) and interaction_events (append-only log).
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Upsert in event_feedback
    feedback = (
        db.query(EventFeedback)
        .filter(
            EventFeedback.user_id == current_user.id,
            EventFeedback.event_id == event_id,
        )
        .first()
    )

    now = datetime.now(timezone.utc)
    if feedback:
        feedback.feedback_type = payload.feedback_type
        feedback.updated_at = now
    else:
        feedback = EventFeedback(
            user_id=current_user.id,
            event_id=event_id,
            feedback_type=payload.feedback_type,
            created_at=now,
            updated_at=now,
        )
        db.add(feedback)

    db.commit()
    db.refresh(feedback)

    # Append to interaction_events telemetry stream
    log_interaction(
        db=db,
        event_id=event_id,
        interaction_type=payload.feedback_type,
        user_id=current_user.id,
    )

    return feedback


@router.delete(
    "/events/{event_id}/feedback",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove event feedback (Undo)",
)
def delete_event_feedback(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Delete an event feedback record for the current user.
    Appends an 'undo_feedback' event to the telemetry stream.
    """
    feedback = (
        db.query(EventFeedback)
        .filter(
            EventFeedback.user_id == current_user.id,
            EventFeedback.event_id == event_id,
        )
        .first()
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No feedback found for this event",
        )

    prev_type = feedback.feedback_type
    db.delete(feedback)
    db.commit()

    log_interaction(
        db=db,
        event_id=event_id,
        interaction_type=f"undo_{prev_type}",
        user_id=current_user.id,
    )


@router.get(
    "/users/me/interactions",
    response_model=UserInteractionsResponse,
    summary="Get current user's active feedbacks",
)
def get_my_interactions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Retrieve lists of event IDs the current user has marked as 'interested' or 'not_for_me'.
    Used by the frontend to pre-populate button states.
    """
    feedbacks = (
        db.query(EventFeedback)
        .filter(EventFeedback.user_id == current_user.id)
        .all()
    )

    interested = [f.event_id for f in feedbacks if f.feedback_type == "interested"]
    not_for_me = [f.event_id for f in feedbacks if f.feedback_type == "not_for_me"]

    return UserInteractionsResponse(interested=interested, not_for_me=not_for_me)


@router.post(
    "/events/{event_id}/interactions",
    status_code=status.HTTP_201_CREATED,
    summary="Log a single interaction event (impression / skip)",
)
def create_interaction(
    event_id: uuid.UUID,
    payload: InteractionLogCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
):
    """
    Append an impression or skip to interaction_events.
    Can be called by authenticated users or guests.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    user_id = current_user.id if current_user else None
    log_interaction(
        db=db,
        event_id=event_id,
        interaction_type=payload.interaction_type,
        user_id=user_id,
        session_id=payload.session_id,
    )
    return {"status": "recorded", "event_id": str(event_id), "type": payload.interaction_type}


@router.post(
    "/events/interactions/batch",
    status_code=status.HTTP_201_CREATED,
    summary="Log a batch of interaction events (impressions / skips)",
)
def create_batch_interactions(
    payload: BatchInteractionLogCreate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User | None, Depends(get_optional_current_user)] = None,
):
    """
    Append multiple telemetry interactions (e.g. deck impressions, skips) in a single request.
    """
    user_id = current_user.id if current_user else None
    for item in payload.interactions:
        log_interaction(
            db=db,
            event_id=item.event_id,
            interaction_type=item.interaction_type,
            user_id=user_id,
            session_id=item.session_id,
            commit=False,
        )
    db.commit()
    return {"status": "recorded", "count": len(payload.interactions)}
