"""
Users router: profile viewing and updating, plus interest management.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.models.user import User
from app.models.user_interest import UserInterest
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.user_interest import (
    UserInterestResponse,
    UserInterestsUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Return the profile of the currently authenticated user."""
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
def update_my_profile(
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Update the authenticated user's profile.
    Only provided (non-null) fields are updated.
    """
    update_data = payload.model_dump(exclude_unset=True)

    # If email is being changed, check for uniqueness
    if "email" in update_data and update_data["email"] != current_user.email:
        existing = (
            db.query(User)
            .filter(User.email == update_data["email"])
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists",
            )

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


# ── Interest Tags ─────────────────────────────────────────────────────


@router.get(
    "/me/interests",
    response_model=list[UserInterestResponse],
    summary="Get my interest tags",
)
def get_my_interests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Return all interest tags for the currently authenticated user."""
    interests = (
        db.query(UserInterest)
        .filter(UserInterest.user_id == current_user.id)
        .all()
    )
    return interests


@router.put(
    "/me/interests",
    response_model=list[UserInterestResponse],
    summary="Replace my interest tags",
)
def update_my_interests(
    payload: UserInterestsUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """
    Replace the authenticated user's entire interest tag list.
    All existing tags are deleted and replaced with the provided list.
    """
    # Delete existing interests
    db.query(UserInterest).filter(
        UserInterest.user_id == current_user.id
    ).delete()

    # Insert new interests
    new_interests = []
    seen_tags = set()
    for item in payload.interests:
        tag_lower = item.tag.strip().lower()
        if not tag_lower or tag_lower in seen_tags:
            continue  # Skip duplicates and empty tags
        seen_tags.add(tag_lower)
        interest = UserInterest(
            user_id=current_user.id,
            interest_tag=tag_lower,
            weight=item.weight,
        )
        db.add(interest)
        new_interests.append(interest)

    db.commit()

    # Refresh to get server-generated fields (id, created_at)
    for i in new_interests:
        db.refresh(i)

    return new_interests

