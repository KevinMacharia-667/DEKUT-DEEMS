"""
Pydantic schemas for JWT token responses.
"""

import uuid

from pydantic import BaseModel


class Token(BaseModel):
    """JWT token pair returned on successful authentication."""

    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Payload extracted from a decoded JWT."""

    user_id: uuid.UUID
