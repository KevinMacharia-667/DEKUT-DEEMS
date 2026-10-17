"""
Events router: CRUD operations for campus events.
"""

from datetime import datetime
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func, or_, and_
from sqlalchemy.orm import Session

from app.services.time_utils import (
    get_nairobi_now,
    get_today_bounds,
    get_weekend_bounds,
)

from app.dependencies import get_current_user, get_db
from app.ml.engine import recommend_events
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
        department=event.department,
        location=event.location,
        start_time=event.start_time,
        end_time=event.end_time,
        max_attendees=event.max_attendees,
        image_url=event.image_url,
        tags=event.tags,
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
    time_frame: Literal["today", "weekend", "upcoming", "all"] | None = Query(
        None, description="Time-aware filter: 'today', 'weekend', 'upcoming', or 'all'"
    ),
    reference_time: datetime | None = Query(
        None, description="Optional reference ISO timestamp for fixed-date queries/tests"
    ),
):
    """
    Return a paginated list of events.
    Supports filtering by category, search text, and time frames in Africa/Nairobi timezone
    ('today', 'weekend', 'upcoming'). Excludes events that have already ended for active feeds.
    """
    now_nairobi = get_nairobi_now(reference_time)
    naive_now = now_nairobi.replace(tzinfo=None)

    query = db.query(Event)

    if published_only:
        query = query.filter(Event.is_published.is_(True))
    if category and category != "All":
        query = query.filter(Event.category == category)
    if search:
        query = query.filter(Event.title.ilike(f"%{search}%"))

    not_ended_filter = or_(
        Event.end_time >= naive_now,
        and_(Event.end_time.is_(None), Event.start_time >= naive_now),
    )

    if time_frame == "today":
        start_bound, end_bound = get_today_bounds(reference_time)
        naive_start = start_bound.replace(tzinfo=None)
        naive_end = end_bound.replace(tzinfo=None)
        query = query.filter(
            Event.start_time >= naive_start,
            Event.start_time <= naive_end,
            not_ended_filter,
        ).order_by(Event.start_time.asc())
    elif time_frame == "weekend":
        start_bound, end_bound = get_weekend_bounds(reference_time)
        naive_start = start_bound.replace(tzinfo=None)
        naive_end = end_bound.replace(tzinfo=None)
        query = query.filter(
            Event.start_time >= naive_start,
            Event.start_time <= naive_end,
            not_ended_filter,
        ).order_by(Event.start_time.asc())
    elif time_frame == "upcoming":
        query = query.filter(not_ended_filter).order_by(Event.start_time.asc())
    else:
        # Default view: chronological upcoming events soonest first
        query = query.order_by(Event.start_time.asc())

    total = query.count()
    events = (
        query.offset((page - 1) * per_page)
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
    "/recommendations",
    response_model=list[EventResponse],
    summary="Get personalized event recommendations",
)
def get_recommendations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    top_n: int = Query(5, ge=1, le=20, description="Number of recommendations to return"),
):
    """
    Get a list of recommended events based on the user's saved interests using TF-IDF and Cosine Similarity.
    """
    # Fetch all published events
    all_events = db.query(Event).filter(Event.is_published.is_(True)).all()

    # Generate recommendations
    recommended = recommend_events(current_user.interests, all_events, top_n=top_n)

    return [_event_to_response(e) for e in recommended]


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
