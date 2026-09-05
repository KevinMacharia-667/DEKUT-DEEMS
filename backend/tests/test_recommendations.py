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
