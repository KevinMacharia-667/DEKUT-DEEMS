"""
Authentication and Authorization / Roles test suite.
"""

def test_register_and_login_flow(client, db_session):
    # 1. Register a new user
    register_payload = {
        "email": "newuser@test.com",
        "username": "newuser",
        "password": "securepassword",
        "full_name": "New User"
    }
    
    response = client.post("/auth/register", json=register_payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["role"] == "student"  # default role
    
    # 2. Login with the new user
    login_payload = {
        "email": "newuser@test.com",
        "password": "securepassword"
    }
    
    response = client.post("/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    
    # 3. Verify token works (get me)
    token = data["access_token"]
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "newuser@test.com"


def test_register_role_escalation_prevented(client, db_session):
    """Attempting to inject role='admin' in registration payload must not grant admin."""
    payload = {
        "email": "hacker@test.com",
        "username": "hacker_user",
        "password": "securepassword123",
        "role": "admin",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "student"


def test_register_duplicate_email_fails(client, student_user):
    """Registration with an existing email returns 409 Conflict."""
    payload = {
        "email": student_user.email,
        "username": "unique_username_99",
        "password": "securepassword123",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_duplicate_username_fails(client, student_user):
    """Registration with an existing username returns 409 Conflict."""
    payload = {
        "email": "different_email@test.com",
        "username": student_user.username,
        "password": "securepassword123",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_login_invalid_password_fails(client, student_user):
    """Login with wrong password returns 401 Unauthorized."""
    response = client.post(
        "/auth/login",
        json={"email": student_user.email, "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_login_nonexistent_user_fails(client):
    """Login with un-registered email returns 401 Unauthorized."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@test.com", "password": "anypassword"}
    )
    assert response.status_code == 401


def test_unauthenticated_request_fails(client):
    """Accessing protected routes without token returns 401."""
    response = client.get("/users/me")
    assert response.status_code == 401

    response = client.get("/recommendations")
    assert response.status_code == 401


def test_invalid_token_fails(client):
    """Accessing protected route with corrupted token returns 401."""
    response = client.get(
        "/users/me",
        headers={"Authorization": "Bearer invalid.corrupted.token"}
    )
    assert response.status_code == 401


def test_auth_login_rate_limiting_blocks_sixth_attempt(client, student_user):
    """
    Five rapid failed/successful login attempts from the same IP are permitted;
    the 6th attempt is blocked with 429 Too Many Requests.
    """
    from app.services.rate_limiter import reset_auth_limiter

    reset_auth_limiter()

    # Attempts 1 through 5
    for i in range(5):
        res = client.post(
            "/auth/login",
            json={"email": student_user.email, "password": "wrongpassword"}
        )
        assert res.status_code == 401

    # 6th attempt must be blocked by rate limiter
    res_6th = client.post(
        "/auth/login",
        json={"email": student_user.email, "password": "password123"}
    )
    assert res_6th.status_code == 429
    data = res_6th.json()
    assert "Too many attempts" in data["detail"]
    assert "Retry-After" in res_6th.headers

    # Resetting the limiter restores normal login flow immediately
    reset_auth_limiter()
    res_after_reset = client.post(
        "/auth/login",
        json={"email": student_user.email, "password": "password123"}
    )
    assert res_after_reset.status_code == 200
    assert "access_token" in res_after_reset.json()


def test_auth_register_rate_limiting_blocks_sixth_attempt(client):
    """
    Five rapid register attempts from the same IP are permitted;
    the 6th attempt is blocked with 429 Too Many Requests.
    """
    from app.services.rate_limiter import reset_auth_limiter

    reset_auth_limiter()

    for i in range(5):
        res = client.post(
            "/auth/register",
            json={
                "email": f"ratelimit_user_{i}@test.com",
                "username": f"ratelimit_user_{i}",
                "password": "password123",
            }
        )
        assert res.status_code == 201

    # 6th attempt
    res_6th = client.post(
        "/auth/register",
        json={
            "email": "ratelimit_user_blocked@test.com",
            "username": "ratelimit_blocked",
            "password": "password123",
        }
    )
    assert res_6th.status_code == 429
    assert "Too many attempts" in res_6th.json()["detail"]


def test_jwt_guard_fails_safe_without_explicit_development_mode():
    """
    Settings must refuse to instantiate if the default JWT secret is used
    and APP_ENV is anything other than 'development' (e.g. production, staging, or unset).
    """
    import pytest
    from app.config import Settings

    # 1. Default APP_ENV='production' with default secret -> Must raise ValueError
    with pytest.raises(ValueError, match="Default JWT_SECRET cannot be used unless APP_ENV=development"):
        Settings(
            APP_ENV="production",
            JWT_SECRET="your_super_secret_jwt_key_here_change_in_production"
        )

    # 2. Staging without custom secret -> Must raise ValueError
    with pytest.raises(ValueError, match="Default JWT_SECRET cannot be used unless APP_ENV=development"):
        Settings(
            APP_ENV="staging",
            JWT_SECRET="your_super_secret_jwt_key_here_change_in_production"
        )

    # 3. Explicit APP_ENV='development' with default secret -> Allowed
    dev_settings = Settings(
        APP_ENV="development",
        JWT_SECRET="your_super_secret_jwt_key_here_change_in_production"
    )
    assert dev_settings.APP_ENV == "development"

    # 4. APP_ENV='production' with strong custom secret -> Allowed
    prod_settings = Settings(
        APP_ENV="production",
        JWT_SECRET="super_strong_cryptographic_random_key_9876543210_ok"
    )
    assert prod_settings.JWT_SECRET == "super_strong_cryptographic_random_key_9876543210_ok"
