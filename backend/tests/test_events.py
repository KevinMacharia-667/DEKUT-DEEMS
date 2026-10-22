"""
Event CRUD operations and role-based permissions test suite.
"""

import uuid
from datetime import datetime, timedelta, timezone


def test_student_cannot_create_event(client, student_token):
    payload = {
        "title": "Student Organized Hackathon",
        "start_time": "2026-11-01T09:00:00Z",
    }
    response = client.post(
        "/events",
        headers={"Authorization": f"Bearer {student_token}"},
        json=payload,
    )
    assert response.status_code == 403
    assert "Only organizers and admins can create events" in response.json()["detail"]


def test_organizer_can_create_event(client, organizer_token):
    payload = {
        "title": "Annual DeKUT Tech Expo",
        "description": "Showcasing student engineering innovations.",
        "category": "Tech",
        "location": "Academic Block ICT Labs",
        "start_time": "2026-11-15T09:00:00Z",
        "is_published": True,
    }
    response = client.post(
        "/events",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Annual DeKUT Tech Expo"
    assert data["category"] == "Tech"
    assert data["location"] == "Academic Block ICT Labs"
    assert data["organizer"]["username"] == "organizer_test"


def test_admin_can_create_event(client, admin_token):
    payload = {
        "title": "Vice Chancellor's Address",
        "description": "University address to freshmen.",
        "category": "Academic",
        "location": "DeKUT Freedom Hall",
        "start_time": "2026-11-20T10:00:00Z",
        "is_published": True,
    }
    response = client.post(
        "/events",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Vice Chancellor's Address"
    assert data["organizer"]["username"] == "admin_test"


def test_get_event_by_id_and_not_found(client, organizer_token):
    create_res = client.post(
        "/events",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json={
            "title": "Inter-Faculty Debate",
            "category": "Cultural",
            "start_time": "2026-12-05T14:00:00Z",
            "is_published": True,
        },
    )
    event_id = create_res.json()["id"]

    # Public GET
    res = client.get(f"/events/{event_id}")
    assert res.status_code == 200
    assert res.json()["title"] == "Inter-Faculty Debate"

    # Non-existent event
    random_id = uuid.uuid4()
    res404 = client.get(f"/events/{random_id}")
    assert res404.status_code == 404
    assert "Event not found" in res404.json()["detail"]


def test_event_update_permissions(
    client, organizer_token, second_organizer_token, student_token, admin_token
):
    # 1. Organizer 1 creates an event
    create_res = client.post(
        "/events",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json={
            "title": "Orig Title",
            "category": "Tech",
            "start_time": "2026-12-01T10:00:00Z",
            "is_published": True,
        },
    )
    event_id = create_res.json()["id"]

    # 2. Student cannot update -> 403
    res_student = client.patch(
        f"/events/{event_id}",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"title": "Hacked Title"},
    )
    assert res_student.status_code == 403
    assert "permission to update" in res_student.json()["detail"]

    # 3. Second organizer (non-owner) cannot update -> 403
    res_org2 = client.patch(
        f"/events/{event_id}",
        headers={"Authorization": f"Bearer {second_organizer_token}"},
        json={"title": "Other Org Title"},
    )
    assert res_org2.status_code == 403
    assert "permission to update" in res_org2.json()["detail"]

    # 4. Creator organizer CAN update -> 200
    res_owner = client.patch(
        f"/events/{event_id}",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json={"title": "Updated by Creator"},
    )
    assert res_owner.status_code == 200
    assert res_owner.json()["title"] == "Updated by Creator"

    # 5. Admin CAN update any event -> 200
    res_admin = client.patch(
        f"/events/{event_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"title": "Overridden by Admin"},
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["title"] == "Overridden by Admin"


def test_event_delete_permissions(
    client, organizer_token, second_organizer_token, student_token, admin_token
):
    # Helper to create event
    def make_event(title: str) -> str:
        res = client.post(
            "/events",
            headers={"Authorization": f"Bearer {organizer_token}"},
            json={
                "title": title,
                "category": "Workshop",
                "start_time": "2026-12-10T14:00:00Z",
                "is_published": True,
            },
        )
        return res.json()["id"]

    ev1 = make_event("Delete Test 1")

    # 1. Student cannot delete -> 403
    res_student = client.delete(
        f"/events/{ev1}",
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res_student.status_code == 403

    # 2. Second organizer cannot delete -> 403
    res_org2 = client.delete(
        f"/events/{ev1}",
        headers={"Authorization": f"Bearer {second_organizer_token}"},
    )
    assert res_org2.status_code == 403

    # 3. Creator organizer CAN delete -> 204
    res_owner = client.delete(
        f"/events/{ev1}",
        headers={"Authorization": f"Bearer {organizer_token}"},
    )
    assert res_owner.status_code == 204
    assert client.get(f"/events/{ev1}").status_code == 404

    # 4. Admin CAN delete any event -> 204
    ev2 = make_event("Delete Test 2 (Admin Target)")
    res_admin = client.delete(
        f"/events/{ev2}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_admin.status_code == 204
    assert client.get(f"/events/{ev2}").status_code == 404

    # 5. Non-existent event delete -> 404
    res_404 = client.delete(
        f"/events/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert res_404.status_code == 404
