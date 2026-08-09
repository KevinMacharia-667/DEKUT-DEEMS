def test_student_cannot_create_event(client, student_token):
    payload = {
        "title": "Hackathon 2026",
        "start_time": "2026-08-01T09:00:00Z"
    }
    response = client.post(
        "/events",
        headers={"Authorization": f"Bearer {student_token}"},
        json=payload
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Only organizers and admins can create events"

def test_organizer_can_create_event(client, organizer_token):
    payload = {
        "title": "Hackathon 2026",
        "description": "Annual tech hackathon",
        "category": "Tech",
        "start_time": "2026-08-01T09:00:00Z",
        "is_published": True
    }
    response = client.post(
        "/events",
        headers={"Authorization": f"Bearer {organizer_token}"},
        json=payload
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Hackathon 2026"
    assert data["category"] == "Tech"
    assert data["organizer"]["username"] == "organizer_test"
