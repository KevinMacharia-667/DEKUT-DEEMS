"""
Tests for the DeKUT campus venues API (/venues).
"""


def test_get_venues_all(client):
    response = client.get("/venues")
    assert response.status_code == 200
    venues = response.json()
    assert isinstance(venues, list)
    assert len(venues) > 0

    sample = venues[0]
    for key in ("name", "area", "kind", "categories", "source", "note"):
        assert key in sample


def test_get_venues_filter_sports(client):
    response = client.get("/venues?category=Sports")
    assert response.status_code == 200
    venues = response.json()
    assert isinstance(venues, list)
    assert len(venues) > 0

    # All returned venues must explicitly support Sports
    for v in venues:
        assert "Sports" in v["categories"]

    # Sports must not return libraries or labs
    kinds = {v["kind"] for v in venues}
    assert "library" not in kinds, "Sports venues must not return libraries"
    assert "lab" not in kinds, "Sports venues must not return laboratories"

    # Verify expected sports facilities exist
    venue_names = [v["name"] for v in venues]
    assert any("Pitch" in name or "Court" in name or "Grounds" in name for name in venue_names)
