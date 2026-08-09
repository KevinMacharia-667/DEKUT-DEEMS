import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.dependencies import get_db
from main import app
from app.models.user import User
from app.services.auth import get_password_hash

# Use a temporary file-based SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_temp.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables and remove db file
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("./test_temp.db"):
        os.remove("./test_temp.db")

@pytest.fixture
def db_session():
    """Returns an sqlalchemy session, and after the test tears down everything properly."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

@pytest.fixture
def student_user(db_session):
    user = User(
        email="student@test.com",
        username="student_test",
        hashed_password=get_password_hash("password123"),
        full_name="Test Student",
        role="student"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def organizer_user(db_session):
    user = User(
        email="organizer@test.com",
        username="organizer_test",
        hashed_password=get_password_hash("password123"),
        full_name="Test Organizer",
        role="organizer"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def student_token(client, student_user):
    response = client.post(
        "/auth/login",
        json={"email": student_user.email, "password": "password123"}
    )
    return response.json()["access_token"]

@pytest.fixture
def organizer_token(client, organizer_user):
    response = client.post(
        "/auth/login",
        json={"email": organizer_user.email, "password": "password123"}
    )
    return response.json()["access_token"]
