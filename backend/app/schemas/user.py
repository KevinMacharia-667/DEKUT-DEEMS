"""
Pydantic schemas for User request/response validation.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ── Request Schemas ───────────────────────────────────────────────────


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str = Field(
        ..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$"
    )
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)


class UserUpdate(BaseModel):
    """Schema for updating the current user's profile."""

    full_name: str | None = Field(None, max_length=100)
    email: EmailStr | None = None
    department: str | None = Field(None, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


# ── Response Schemas ──────────────────────────────────────────────────


class UserResponse(BaseModel):
    """Public user representation returned by the API."""

    id: uuid.UUID
    email: str
    username: str
    full_name: str | None
    role: str
    department: str | None = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserBrief(BaseModel):
    """Minimal user info for embedding in other responses (e.g., event organizer)."""

    id: uuid.UUID
    username: str
    full_name: str | None

    model_config = {"from_attributes": True}
