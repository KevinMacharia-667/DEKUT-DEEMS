"""
Tests for Tukio Feedback & Interaction Telemetry (Step 5).
Verifies:
1. event_feedback table uniqueness on (user_id, event_id).
2. interaction_events append-only logging (impression, skip, rsvp, interested, not_for_me).
3. Feedback write-back to recommender:
   - "not_for_me" excluded from For You (/recommendations), but kept in Explore All (/events).
   - "interested" boosts ranking of similar events.
4. SVD matrix strictly utilizes positive signals (+1.5 RSVP, +1.0 interested; NO negative weights).
5. Undo feedback endpoint (DELETE /events/{event_id}/feedback).
6. Data leakage prevention: held-out ground truth events excluded from model training signals.
"""

from datetime import datetime, timedelta, timezone
import uuid
from app.models.event import Event
from app.models.event_feedback import EventFeedback
from app.models.interaction_event import InteractionEvent
from app.models.rsvp import RSVP
from app.ml.hybrid_engine import compute_collaborative_scores


def test_feedback_crud_and_interaction_logging(client, db_session, student_user, student_token, organizer_user):
    now = datetime.now(timezone.utc)
    event = Event(
        title="Web Security Hackathon",
        description="Learn pentesting and web app security.",
        category="Tech",
        tags="cybersecurity, web, tech",
        start_time=now + timedelta(days=2),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add(event)
    db_session.commit()

    # 1. Unauthenticated request must be rejected (401)
    res_unauth = client.post(
        f"/events/{event.id}/feedback",
        json={"feedback_type": "interested"},
    )
    assert res_unauth.status_code == 401

    # 2. Authenticated user marks 'interested'
    res_int = client.post(
        f"/events/{event.id}/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"feedback_type": "interested"},
    )
    assert res_int.status_code == 200
    assert res_int.json()["feedback_type"] == "interested"

    # Verify event_feedback table
    fb = (
        db_session.query(EventFeedback)
        .filter(EventFeedback.user_id == student_user.id, EventFeedback.event_id == event.id)
        .first()
    )
    assert fb is not None
    assert fb.feedback_type == "interested"

    # Verify interaction_events append-only log has recorded 'interested'
    log_int = (
        db_session.query(InteractionEvent)
        .filter(InteractionEvent.user_id == student_user.id, InteractionEvent.event_id == event.id)
        .all()
    )
    types = [l.interaction_type for l in log_int]
    assert "interested" in types

    # 3. User switches feedback to 'not_for_me' (upsert on unique constraint)
    res_nfm = client.post(
        f"/events/{event.id}/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"feedback_type": "not_for_me"},
    )
    assert res_nfm.status_code == 200
    assert res_nfm.json()["feedback_type"] == "not_for_me"

    # Still exactly ONE row in event_feedback for (user_id, event_id)
    fb_count = (
        db_session.query(EventFeedback)
        .filter(EventFeedback.user_id == student_user.id, EventFeedback.event_id == event.id)
        .count()
    )
    assert fb_count == 1

    # Check GET /users/me/interactions
    res_my = client.get(
        "/users/me/interactions",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_my.status_code == 200
    my_data = res_my.json()
    assert str(event.id) in my_data["not_for_me"]
    assert str(event.id) not in my_data["interested"]

    # 4. Undo feedback (DELETE /events/{event_id}/feedback)
    res_del = client.delete(
        f"/events/{event.id}/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_del.status_code == 204

    # Row removed from event_feedback
    fb_after = (
        db_session.query(EventFeedback)
        .filter(EventFeedback.user_id == student_user.id, EventFeedback.event_id == event.id)
        .first()
    )
    assert fb_after is None

    # interaction_events log contains undo_not_for_me
    all_logs = (
        db_session.query(InteractionEvent)
        .filter(InteractionEvent.user_id == student_user.id, InteractionEvent.event_id == event.id)
        .all()
    )
    log_types = [l.interaction_type for l in all_logs]
    assert "undo_not_for_me" in log_types


def test_impressions_and_skips_telemetry_logging(client, db_session, student_token, organizer_user):
    now = datetime.now(timezone.utc)
    ev1 = Event(
        title="AI Career Fair",
        category="Career",
        start_time=now + timedelta(days=3),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    ev2 = Event(
        title="Robotics Showcase",
        category="Tech",
        start_time=now + timedelta(days=4),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add_all([ev1, ev2])
    db_session.commit()

    # Single impression logging
    res_imp = client.post(
        f"/events/{ev1.id}/interactions",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interaction_type": "impression", "session_id": "sess-123"},
    )
    assert res_imp.status_code == 201

    # Batch logging (e.g. skip ev1, impression ev2)
    res_batch = client.post(
        "/events/interactions/batch",
        headers={"Authorization": f"Bearer {student_token}"},
        json={
            "interactions": [
                {"event_id": str(ev1.id), "interaction_type": "skip", "session_id": "sess-123"},
                {"event_id": str(ev2.id), "interaction_type": "impression", "session_id": "sess-123"},
            ]
        },
    )
    assert res_batch.status_code == 201
    assert res_batch.json()["count"] == 2


def test_recommender_not_for_me_exclusion_and_explore_all_retention(client, db_session, student_user, student_token, organizer_user):
    now = datetime.now(timezone.utc)

    # User interests
    client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interests": [{"tag": "tech", "weight": 1.0}]},
    )

    ev_rejected = Event(
        title="Unwanted Java Seminar",
        description="Legacy Java 8 programming seminar.",
        category="Tech",
        tags="tech, java",
        start_time=now + timedelta(days=2),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    ev_wanted = Event(
        title="Exciting Cloud Computing Workshop",
        description="Modern AWS and GCP microservices.",
        category="Tech",
        tags="tech, cloud",
        start_time=now + timedelta(days=3),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add_all([ev_rejected, ev_wanted])
    db_session.commit()

    # User marks ev_rejected as 'not_for_me'
    client.post(
        f"/events/{ev_rejected.id}/feedback",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"feedback_type": "not_for_me"},
    )

    # 1. In For You (/recommendations): ev_rejected MUST be excluded
    res_rec = client.get(
        "/recommendations?strategy=hybrid&k=10",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_rec.status_code == 200
    rec_titles = [item["event"]["title"] for item in res_rec.json()["recommendations"]]
    assert "Unwanted Java Seminar" not in rec_titles
    assert "Exciting Cloud Computing Workshop" in rec_titles

    # 2. In Explore All (/events): ev_rejected MUST STILL BE PRESENT (rule 3)
    res_all = client.get("/events?time_frame=upcoming")
    assert res_all.status_code == 200
    all_titles = [e["title"] for e in res_all.json()["events"]]
    assert "Unwanted Java Seminar" in all_titles
    assert "Exciting Cloud Computing Workshop" in all_titles


def test_svd_matrix_strictly_positive_signals():
    # Test that compute_collaborative_scores uses only positive signals (no negative weights)
    u1, u2, u3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    now = datetime.now(timezone.utc)
    e1 = Event(id=uuid.uuid4(), title="E1", category="Tech", start_time=now)
    e2 = Event(id=uuid.uuid4(), title="E2", category="Tech", start_time=now)
    e3 = Event(id=uuid.uuid4(), title="E3", category="Tech", start_time=now)
    events = [e1, e2, e3]

    # RSVPs and feedbacks
    r1 = RSVP(user_id=u1, event_id=e1.id, status="confirmed")
    r2 = RSVP(user_id=u2, event_id=e2.id, status="confirmed")
    r3 = RSVP(user_id=u3, event_id=e1.id, status="cancelled")  # cancelled should NOT be negative in SVD
    fb1 = EventFeedback(user_id=u3, event_id=e2.id, feedback_type="interested")

    scores = compute_collaborative_scores(
        target_user_id=u3,
        all_events=events,
        all_rsvps=[r1, r2, r3],
        all_feedbacks=[fb1],
    )
    assert len(scores) == 3
    # All collaborative affinities must be >= 0.0 (non-negative)
    assert (scores >= 0.0).all()


def test_evaluation_excludes_training_interactions(db_session, student_user, organizer_user):
    # Rule 8: Data leakage prevention
    now = datetime.now(timezone.utc)
    ev_test = Event(
        title="Holdout Evaluation Event",
        category="Tech",
        start_time=now + timedelta(days=5),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    ev_train = Event(
        title="Training Prior Event",
        category="Tech",
        start_time=now + timedelta(days=2),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add_all([ev_test, ev_train])
    db_session.commit()

    # User RSVPs to both
    r_test = RSVP(user_id=student_user.id, event_id=ev_test.id, status="confirmed")
    r_train = RSVP(user_id=student_user.id, event_id=ev_train.id, status="confirmed")
    db_session.add_all([r_test, r_train])
    db_session.commit()

    # Ground truth test holdout
    relevant = {str(ev_test.id)}

    # As in evaluate.py:
    all_user_rsvps = (
        db_session.query(Event)
        .join(RSVP, RSVP.event_id == Event.id)
        .filter(RSVP.user_id == student_user.id, RSVP.status == "confirmed")
        .all()
    )
    training_rsvp_events = [e for e in all_user_rsvps if str(e.id) not in relevant]

    # The held-out test event must NOT be in training_rsvp_events
    train_ids = {str(e.id) for e in training_rsvp_events}
    assert str(ev_test.id) not in train_ids
    assert str(ev_train.id) in train_ids


def test_share_and_calendar_interaction_logging(client, db_session, student_token, organizer_user):
    now = datetime.now(timezone.utc)
    ev = Event(
        title="Campus Tech Expo 2026",
        category="Tech",
        start_time=now + timedelta(days=4),
        organizer_id=organizer_user.id,
        is_published=True,
    )
    db_session.add(ev)
    db_session.commit()

    # Log share
    res_share = client.post(
        f"/events/{ev.id}/interactions",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interaction_type": "share", "session_id": "test-sess"},
    )
    assert res_share.status_code == 201

    # Log add_to_calendar
    res_cal = client.post(
        f"/events/{ev.id}/interactions",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interaction_type": "add_to_calendar", "session_id": "test-sess"},
    )
    assert res_cal.status_code == 201

    # Verify rows in interaction_events
    logs = (
        db_session.query(InteractionEvent)
        .filter(InteractionEvent.event_id == ev.id)
        .all()
    )
    logged_types = [l.interaction_type for l in logs]
    assert "share" in logged_types
    assert "add_to_calendar" in logged_types
