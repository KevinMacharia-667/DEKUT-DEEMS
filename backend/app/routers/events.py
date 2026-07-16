"""
Events router: CRUD operations for campus events.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.schemas.event import (
    EventCreate,
    EventListResponse,
    EventResponse,
    EventUpdate,
)
from app.schemas.user import UserBrief

router = APIRouter(prefix="/events", tags=["Events"])


# ── Helpers ───────────────────────────────────────────────────────────


def _event_to_response(event: Event) -> EventResponse:
    """Convert an Event ORM instance to an EventResponse schema."""
    rsvp_count = sum(1 for r in event.rsvps if r.status == "confirmed")
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        category=event.category,
        location=event.location,
        start_time=event.start_time,
        end_time=event.end_time,
        max_attendees=event.max_attendees,
        image_url=event.image_url,
        organizer=UserBrief.model_validate(event.organizer),
        is_published=event.is_published,
        rsvp_count=rsvp_count,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new event",
)
def create_event(
    payload: EventCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Create a new campus event. The authenticated user becomes the organizer.
    Requires the user to have an 'organizer' or 'admin' role.
    """
    if current_user.role not in ("organizer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organizers and admins can create events",
        )

    event = Event(
        **payload.model_dump(),
        organizer_id=current_user.id,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return _event_to_response(event)


@router.get(
    "",
    response_model=EventListResponse,
    summary="List events (paginated, filterable)",
)
def list_events(
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in title"),
    published_only: bool = Query(True, description="Show only published events"),
):
    """
    Return a paginated list of events.
    Supports filtering by category and text search on title.
    """
    query = db.query(Event)

    if published_only:
        query = query.filter(Event.is_published.is_(True))
    if category:
        query = query.filter(Event.category == category)
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))

    total = query.count()
    events = (
        query.order_by(Event.start_time.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    return EventListResponse(
        events=[_event_to_response(e) for e in events],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Get event details",
)
def get_event(
    event_id: uuid.UUID,
    db: Annotated[Session, Depends(get_db)],
):
    """Retrieve a single event by ID, including its RSVP count."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    return _event_to_response(event)


@router.patch(
    "/{event_id}",
    response_model=EventResponse,
    summary="Update an event",
)
def update_event(
    event_id: uuid.UUID,
    payload: EventUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Update an existing event. Only the organizer who created the event
    or an admin can modify it.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if event.organizer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to update this event",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return _event_to_response(event)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an event",
)
def delete_event(
    event_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Delete an event. Only the organizer who created it or an admin
    can delete an event. Associated RSVPs are cascade-deleted.
    """
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )

    if event.organizer_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this event",
        )

    db.delete(event)
    db.commit()
