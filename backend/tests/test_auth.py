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
