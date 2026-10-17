"""
Tests for Tukio Onboarding & Interest-Driven Cold Start Personalization.
"""

from datetime import datetime, timedelta, timezone
from app.models.event import Event


def test_onboarding_interest_validation(client, student_token):
    # 1. Empty list should be rejected (422 by Pydantic min_length or 400)
    res_empty = client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interests": []},
    )
    assert res_empty.status_code in (400, 422)

    # 2. Oversized list (> 50) should be rejected
    oversized = [{"tag": f"tag-{i}", "weight": 1.0} for i in range(55)]
    res_oversized = client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interests": oversized},
    )
    assert res_oversized.status_code in (400, 422)

    # 3. Invalid strings only (symbols) should be rejected after sanitization
    res_symbols = client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interests": [{"tag": "!@#$%^", "weight": 1.0}]},
    )
    assert res_symbols.status_code == 400
    assert "No valid interest tags" in res_symbols.json()["detail"]


def test_onboarding_interest_sanitization_and_persistence(client, student_token):
    # Valid submission with dirty inputs (whitespace, capitals, duplicates)
    payload = {
        "interests": [
            {"tag": "  PYTHON  ", "weight": 1.0},
            {"tag": "Web Development", "weight": 1.0},
            {"tag": "python", "weight": 1.0},  # duplicate, should be deduplicated
            {"tag": "AI & Machine Learning", "weight": 1.0},  # symbol & should be sanitized
        ]
    }
    res = client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json=payload,
    )
    assert res.status_code == 200
    tags = [item["interest_tag"] for item in res.json()]
    assert "python" in tags
    assert "web development" in tags
    assert len(tags) == len(set(tags))  # No duplicates


def test_onboarding_cold_start_ranking_shift(client, db_session, student_user, student_token, organizer_user):
    now = datetime.now(timezone.utc)
    
    # Create two competing candidate events in DB
    tech_event = Event(
        title="DeKUT AI Hackathon",
        description="Build machine learning and python apps.",
        category="Tech",
        tags="python, ai, web development",
        start_time=now + timedelta(days=3),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    sports_event = Event(
        title="Inter-Faculty Football Cup",
        description="Annual campus soccer tournament.",
        category="Sports",
        tags="sports, football, athletics, fitness",
        start_time=now + timedelta(days=3),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add_all([tech_event, sports_event])
    db_session.commit()

    # Step 1: User completes onboarding choosing Tech interests
    onboarding_tech = {
        "interests": [
            {"tag": "tech", "weight": 1.0},
            {"tag": "python", "weight": 1.0},
            {"tag": "ai", "weight": 1.0},
        ]
    }
    client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json=onboarding_tech,
    )

    # Fetch recommendations: Tech event should rank above Sports event
    recs_tech = client.get(
        "/recommendations?strategy=hybrid&k=10",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()["recommendations"]

    rec_titles_tech = [r["event"]["title"] for r in recs_tech]
    assert "DeKUT AI Hackathon" in rec_titles_tech
    tech_rank = rec_titles_tech.index("DeKUT AI Hackathon")
    sports_rank = rec_titles_tech.index("Inter-Faculty Football Cup") if "Inter-Faculty Football Cup" in rec_titles_tech else 999
    assert tech_rank < sports_rank

    # Step 2: User changes their preferences to Sports
    onboarding_sports = {
        "interests": [
            {"tag": "sports", "weight": 1.0},
            {"tag": "football", "weight": 1.0},
            {"tag": "athletics", "weight": 1.0},
        ]
    }
    client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json=onboarding_sports,
    )

    # Fetch recommendations: Sports event should now rank above Tech event
    recs_sports = client.get(
        "/recommendations?strategy=hybrid&k=10",
        headers={"Authorization": f"Bearer {student_token}"},
    ).json()["recommendations"]

    rec_titles_sports = [r["event"]["title"] for r in recs_sports]
    assert "Inter-Faculty Football Cup" in rec_titles_sports
    new_sports_rank = rec_titles_sports.index("Inter-Faculty Football Cup")
    new_tech_rank = rec_titles_sports.index("DeKUT AI Hackathon") if "DeKUT AI Hackathon" in rec_titles_sports else 999
    assert new_sports_rank < new_tech_rank
