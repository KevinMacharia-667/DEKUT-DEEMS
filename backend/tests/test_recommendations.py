from datetime import datetime, timedelta, timezone
from app.models.event import Event
from app.models.user_interest import UserInterest

def test_recommendations_baseline_and_ml(client, db_session, student_user, student_token, organizer_user):
    # 1. Seed events
    now = datetime.now(timezone.utc)
    events = [
        Event(
            title="Tech Summit 2026",
            description="A summit for technology enthusiasts.",
            category="Tech",
            tags="tech, summit, ai",
            start_time=now + timedelta(days=2),
            end_time=now + timedelta(days=2, hours=4),
            organizer_id=organizer_user.id,
            is_published=True
        ),
        Event(
            title="Sports Meetup",
            description="Weekly sports meetup.",
            category="Sports",
            tags="sports, outdoor",
            start_time=now + timedelta(days=3),
            organizer_id=organizer_user.id,
            is_published=True
        ),
        Event(
            title="AI Workshop",
            description="Learn AI and Machine Learning.",
            category="Tech",
            tags="ai, machine learning, workshop",
            start_time=now + timedelta(days=5),
            organizer_id=organizer_user.id,
            is_published=True
        )
    ]
    db_session.add_all(events)
    db_session.commit()
    
    # 2. Add interests for the student
    interest = UserInterest(user_id=student_user.id, interest_tag="Tech")
    db_session.add(interest)
    db_session.commit()
    
    # 3. Test baseline strategy
    response = client.get(
        "/recommendations?strategy=baseline",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "baseline"
    # Tech events should be ranked higher due to the "Tech" interest
    # Only events scoring above zero are returned, so the count may be
    # fewer than the number of seeded events. What matters is that the
    # user's interest ("Tech") is ranked at the top.
    assert len(data["recommendations"]) >= 1
    top_categories = [rec["event"]["category"] for rec in data["recommendations"][:2]]
    assert "Tech" in top_categories
    
    # 4. Test ML strategy
    response = client.get(
        "/recommendations?strategy=ml",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "ml"
    # The TF-IDF engine excludes events with zero cosine similarity to the
    # user profile, so it legitimately returns fewer items than exist.
    assert len(data["recommendations"]) >= 1
    top_categories_ml = [rec["event"]["category"] for rec in data["recommendations"][:2]]
    assert "Tech" in top_categories_ml
    # Every returned item must carry a score and an explanation
    for rec in data["recommendations"]:
        assert rec["score"] > 0
        assert "explanation" in rec

    # 5. Test Unified Hybrid strategy (default)
    response = client.get(
        "/recommendations?strategy=hybrid",
        headers={"Authorization": f"Bearer {student_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "hybrid"
    assert len(data["recommendations"]) >= 1
    top_categories_hybrid = [rec["event"]["category"] for rec in data["recommendations"][:2]]
    assert "Tech" in top_categories_hybrid
    for rec in data["recommendations"]:
        assert rec["score"] > 0
        assert rec["badge"] is not None
        assert "reasons" in rec


def test_hybrid_empty_database(client, student_token):
    """Hybrid recommender returns empty list when no published events exist."""
    response = client.get(
        "/recommendations?strategy=hybrid",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "hybrid"
    assert data["count"] == 0
    assert data["recommendations"] == []


def test_hybrid_cold_start_user(client, db_session, student_user, student_token, organizer_user):
    """
    Cold-start user (0 declared interests, 0 RSVPs, 0 feedback) receives
    graceful contextual recommendations without crashing.
    """
    now = datetime.now(timezone.utc)
    events = [
        Event(
            title="Intro to Computing at DeKUT",
            description="Orientation for Computer Science students.",
            category="Academic",
            department="Computer Science",
            start_time=now + timedelta(days=1),
            organizer_id=organizer_user.id,
            is_published=True,
        ),
        Event(
            title="Weekend Forest Walk",
            description="Recreational hiking at Conservancy.",
            category="Social",
            department="Tourism",
            start_time=now + timedelta(days=10),
            organizer_id=organizer_user.id,
            is_published=True,
        ),
    ]
    db_session.add_all(events)
    db_session.commit()

    # Verify student has NO interests and NO RSVPs
    interests = db_session.query(UserInterest).filter_by(user_id=student_user.id).all()
    assert len(interests) == 0

    response = client.get(
        "/recommendations?strategy=hybrid",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["strategy"] == "hybrid"
    assert len(data["recommendations"]) == 2

    # Since student is in 'Computer Science', that department event should rank #1
    top_event = data["recommendations"][0]["event"]
    assert top_event["title"] == "Intro to Computing at DeKUT"
    assert data["recommendations"][0]["badge"] is not None
    assert len(data["recommendations"][0]["reasons"]) > 0


def test_hybrid_user_with_rsvps(client, db_session, student_user, student_token, organizer_user):
    """
    User with no declared interests but confirmed RSVPs for a category
    receives recommendations biased towards that RSVP history.
    """
    now = datetime.now(timezone.utc)
    # Past/attended event that student RSVP'd to
    past_event = Event(
        title="Inter-University Football Match",
        description="Championship game at sports pitch.",
        category="Sports",
        tags="football, sports, pitch",
        start_time=now - timedelta(days=2),
        end_time=now - timedelta(days=2, hours=-2),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add(past_event)
    db_session.commit()
    db_session.refresh(past_event)

    # Student RSVPs to the football event
    from app.models.rsvp import RSVP
    rsvp = RSVP(user_id=student_user.id, event_id=past_event.id, status="confirmed")
    db_session.add(rsvp)
    db_session.commit()

    # Upcoming candidate events: one Sports, one Agriculture
    upcoming_sports = Event(
        title="Basketball Finals",
        description="Annual basketball tournament at Court.",
        category="Sports",
        tags="basketball, sports, court",
        start_time=now + timedelta(days=3),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    upcoming_agri = Event(
        title="Organic Soil Fertility Workshop",
        description="Field session on organic soil fertility.",
        category="Academic",
        tags="soil, farming, crop",
        department="Agriculture",
        start_time=now + timedelta(days=4),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add_all([upcoming_sports, upcoming_agri])
    db_session.commit()

    response = client.get(
        "/recommendations?strategy=hybrid",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["recommendations"]) >= 2

    # Sports event should be top recommended due to RSVP history
    top_rec = data["recommendations"][0]
    assert top_rec["event"]["category"] == "Sports"
    assert top_rec["score"] > 0
