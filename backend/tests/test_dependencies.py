"""
Tests for FastAPI dependencies: get_db, get_current_user, get_optional_current_user, require_role.
"""

import uuid
import pytest
from fastapi import HTTPException

from app.dependencies import (
    get_db,
    get_current_user,
    get_optional_current_user,
    require_role,
)
from app.models.user import User
from app.services.auth import create_access_token, hash_password


def test_get_db_yields_session():
    """Verify get_db session generator yields a session and properly closes."""
    gen = get_db()
    session = next(gen)
    assert session is not None
    try:
        next(gen)
    except StopIteration:
        pass


def test_get_current_user_valid(db_session, student_user):
    token = create_access_token(data={"sub": str(student_user.id)})
    user = get_current_user(token=token, db=db_session)
    assert user.id == student_user.id
    assert user.email == student_user.email


def test_get_current_user_invalid_token(db_session):
    with pytest.raises(HTTPException) as exc:
        get_current_user(token="invalid.bearer.token", db=db_session)
    assert exc.value.status_code == 401


def test_get_current_user_missing_sub(db_session):
    # Token without 'sub' claim
    token = create_access_token(data={"role": "admin"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


def test_get_current_user_invalid_uuid(db_session):
    token = create_access_token(data={"sub": "not-a-valid-uuid"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


def test_get_current_user_inactive(db_session):
    inactive_user = User(
        email="inactive@test.com",
        username="inactive_user",
        hashed_password=hash_password("pw"),
        is_active=False,
    )
    db_session.add(inactive_user)
    db_session.commit()
    db_session.refresh(inactive_user)

    token = create_access_token(data={"sub": str(inactive_user.id)})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token, db=db_session)
    assert exc.value.status_code == 401


def test_get_optional_current_user(db_session, student_user):
    # 1. No token
    assert get_optional_current_user(token=None, db=db_session) is None
    assert get_optional_current_user(token="", db=db_session) is None

    # 2. Corrupt token
    assert get_optional_current_user(token="garbage.token", db=db_session) is None

    # 3. Missing sub
    token_no_sub = create_access_token(data={"role": "student"})
    assert get_optional_current_user(token=token_no_sub, db=db_session) is None

    # 4. Invalid UUID
    token_bad_uuid = create_access_token(data={"sub": "invalid-uuid"})
    assert get_optional_current_user(token=token_bad_uuid, db=db_session) is None

    # 5. Valid token
    valid_token = create_access_token(data={"sub": str(student_user.id)})
    user = get_optional_current_user(token=valid_token, db=db_session)
    assert user is not None
    assert user.id == student_user.id


def test_require_role_dependency(student_user, organizer_user, admin_user):
    # Require organizer or admin
    checker = require_role("organizer", "admin")

    # Organizer succeeds
    assert checker(organizer_user).id == organizer_user.id
    # Admin succeeds
    assert checker(admin_user).id == admin_user.id

    # Student forbidden
    with pytest.raises(HTTPException) as exc:
        checker(student_user)
    assert exc.value.status_code == 403
    assert exc.value.detail == "Insufficient permissions"
