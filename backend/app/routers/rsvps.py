"""
RSVP router: manage event attendance.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.schemas.rsvp import AttendeeResponse, RSVPResponse
from app.schemas.user import UserBrief

router = APIRouter(tags=["RSVPs"])


@router.post(
    "/events/{event_id}/rsvp",
    response_model=RSVPResponse,
    status_code=status.HTTP_201_CREATED,
    summary="RSVP to an event",
)
def create_rsvp(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Register the current user's attendance for an event.
    Returns 409 if already RSVP'd. Returns 400 if the event is full.
    """
    # Verify event exists
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    # Check for existing RSVP
    existing = (
        db.query(RSVP)
        .filter(RSVP.user_id == current_user.id, RSVP.event_id == event_id)
        .first()
    )
    if existing:
        if existing.status == "confirmed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You have already RSVP'd to this event",
            )
        # Re-confirm a previously cancelled RSVP
        existing.status = "confirmed"
        db.commit()
        db.refresh(existing)
        return existing

    # Check capacity
    if event.max_attendees is not None:
        confirmed_count = (
            db.query(RSVP)
            .filter(RSVP.event_id == event_id, RSVP.status == "confirmed")
            .count()
        )
        if confirmed_count >= event.max_attendees:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This event has reached maximum capacity",
            )

    rsvp = RSVP(user_id=current_user.id, event_id=event_id)
    db.add(rsvp)
    db.commit()
    db.refresh(rsvp)
    return rsvp


@router.delete(
    "/events/{event_id}/rsvp",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel RSVP",
)
def cancel_rsvp(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Cancel the current user's RSVP for an event."""
    rsvp = (
        db.query(RSVP)
        .filter(RSVP.user_id == current_user.id, RSVP.event_id == event_id)
        .first()
    )
    if not rsvp or rsvp.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active RSVP found for this event",
        )

    rsvp.status = "cancelled"
    db.commit()


@router.get(
    "/events/{event_id}/attendees",
    response_model=list[AttendeeResponse],
    summary="List event attendees",
)
def list_attendees(
    event_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """Return a list of confirmed attendees for an event."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    rsvps = (
        db.query(RSVP)
        .filter(RSVP.event_id == event_id, RSVP.status == "confirmed")
        .all()
    )

    return [
        AttendeeResponse(
            rsvp_id=r.id,
            user=UserBrief.model_validate(r.user),
            status=r.status,
            rsvp_date=r.created_at,
        )
        for r in rsvps
    ]


@router.get(
    "/users/me/rsvps",
    response_model=list[RSVPResponse],
    summary="List my RSVPs",
)
def list_my_rsvps(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Return all RSVPs for the currently authenticated user."""
    rsvps = (
        db.query(RSVP)
        .filter(RSVP.user_id == current_user.id)
        .order_by(RSVP.created_at.desc())
        .all()
    )
    return rsvps
