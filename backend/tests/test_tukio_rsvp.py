"""
Tests for Tukio Event Feed & One-Tap RSVP flows.
"""

def test_tukio_category_filtering(client, organizer_token):
    # Create events in Tech and Social categories
    e1 = client.post(
        "/events",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json={
            "title": "AI Symposium 2026",
            "category": "Tech",
            "start_time": "2026-11-01T10:00:00Z",
            "is_published": True,
        },
    )
    assert e1.status_code == 201

    e2 = client.post(
        "/events",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json={
            "title": "Campus Cultural Night",
            "category": "Cultural",
            "start_time": "2026-11-02T18:00:00Z",
            "is_published": True,
        },
    )
    assert e2.status_code == 201

    # Query 'Tech' category
    tech_res = client.get("/events?category=Tech")
    assert tech_res.status_code == 200
    tech_events = tech_res.json()["events"]
    assert all(e["category"] == "Tech" for e in tech_events)
    assert any(e["title"] == "AI Symposium 2026" for e in tech_events)

    # Query 'Social' category (empty in this fixture)
    social_res = client.get("/events?category=Social")
    assert social_res.status_code == 200
    assert all(e["category"] == "Social" for e in social_res.json()["events"])


def test_tukio_one_tap_rsvp_and_cancel_persistence(client, student_token, organizer_token):
    # 1. Organizer creates event
    create_res = client.post(
        "/events",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json={
            "title": "Robotics Workshop",
            "category": "Tech",
            "start_time": "2026-12-01T14:00:00Z",
            "is_published": True,
        },
    )
    assert create_res.status_code == 201
    event_id = create_res.json()["id"]

    # 2. Student taps RSVP (POST /events/{id}/rsvp)
    rsvp_res = client.post(
        f"/events/{event_id}/rsvp",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert rsvp_res.status_code == 201
    assert rsvp_res.json()["status"] == "confirmed"

    # 3. Simulate page refresh / sync: fetch /users/me/rsvps
    my_rsvps = client.get(
        "/users/me/rsvps",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert my_rsvps.status_code == 200
    active_ids = [r["event_id"] for r in my_rsvps.json() if r["status"] == "confirmed"]
    assert event_id in active_ids

    # Also verify attendee count updated on the event
    event_data = client.get(f"/events/{event_id}").json()
    assert event_data["rsvp_count"] == 1

    # 4. Student taps cancel RSVP (DELETE /events/{id}/rsvp)
    cancel_res = client.delete(
        f"/events/{event_id}/rsvp",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert cancel_res.status_code == 204

    # 5. Confirm cancellation persisted after refresh
    my_rsvps_after = client.get(
        "/users/me/rsvps",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert my_rsvps_after.status_code == 200
    active_ids_after = [r["event_id"] for r in my_rsvps_after.json() if r["status"] == "confirmed"]
    assert event_id not in active_ids_after

    # 6. Re-RSVP should succeed and re-confirm
    re_rsvp_res = client.post(
        f"/events/{event_id}/rsvp",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert re_rsvp_res.status_code in (200, 201)
    assert re_rsvp_res.json()["status"] == "confirmed"
