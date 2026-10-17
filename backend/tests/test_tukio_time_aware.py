"""
Tests for Tukio Time-Aware Feeds (Happening Today, This Weekend, For You).
Verifies Africa/Nairobi timezone boundaries, weekend logic with fixed dates,
and exclusion of already-ended events.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from app.models.event import Event
from app.services.time_utils import (
    NAIROBI_TZ,
    get_nairobi_now,
    get_today_bounds,
    get_weekend_bounds,
)


def test_time_utils_fixed_dates():
    # 1. Wednesday 2026-10-21 14:00 EAT -> Upcoming weekend: Fri Oct 23 17:00 to Sun Oct 25 23:59:59
    wed = datetime(2026, 10, 21, 14, 0, 0, tzinfo=NAIROBI_TZ)
    start_w, end_w = get_weekend_bounds(wed)
    assert start_w.year == 2026 and start_w.month == 10 and start_w.day == 23 and start_w.hour == 17
    assert end_w.year == 2026 and end_w.month == 10 and end_w.day == 25 and end_w.hour == 23

    # 2. Friday 2026-10-23 18:30 EAT (after 17:00) -> Current weekend: Fri Oct 23 17:00 to Sun Oct 25 23:59:59
    fri_evening = datetime(2026, 10, 23, 18, 30, 0, tzinfo=NAIROBI_TZ)
    start_f, end_f = get_weekend_bounds(fri_evening)
    assert start_f.day == 23 and start_f.hour == 17
    assert end_f.day == 25 and end_f.hour == 23

    # 3. Saturday 2026-10-24 11:00 EAT -> Current weekend: Fri Oct 23 17:00 to Sun Oct 25 23:59:59
    sat = datetime(2026, 10, 24, 11, 0, 0, tzinfo=NAIROBI_TZ)
    start_s, end_s = get_weekend_bounds(sat)
    assert start_s.day == 23 and start_s.hour == 17
    assert end_s.day == 25 and end_s.hour == 23

    # 4. Sunday 2026-10-25 20:00 EAT -> Current weekend
    sun = datetime(2026, 10, 25, 20, 0, 0, tzinfo=NAIROBI_TZ)
    start_su, end_su = get_weekend_bounds(sun)
    assert start_su.day == 23 and start_su.hour == 17
    assert end_su.day == 25 and end_su.hour == 23

    # 5. Today bounds
    t_start, t_end = get_today_bounds(sat)
    assert t_start.day == 24 and t_start.hour == 0 and t_start.minute == 0
    assert t_end.day == 24 and t_end.hour == 23 and t_end.minute == 59


def test_happening_today_feed_and_exclusion_of_ended_events(client, db_session, organizer_user):
    # Reference date: Saturday 2026-10-24 at 12:00 EAT
    ref_dt = datetime(2026, 10, 24, 12, 0, 0, tzinfo=NAIROBI_TZ)
    ref_iso = ref_dt.isoformat()

    # Event 1: Today, already ended (10:00 - 11:30)
    ended_event = Event(
        title="Morning Campus Cleanup",
        description="Completed morning cleanup.",
        category="Social",
        start_time=datetime(2026, 10, 24, 10, 0, 0),
        end_time=datetime(2026, 10, 24, 11, 30, 0),
        organizer_id=organizer_user.id,
        is_published=True,
    )

    # Event 2: Today, happening now / later (14:00 - 17:00)
    active_today_event = Event(
        title="Robotics Workshop Hands-on",
        description="Afternoon lab session.",
        category="Tech",
        start_time=datetime(2026, 10, 24, 14, 0, 0),
        end_time=datetime(2026, 10, 24, 17, 0, 0),
        organizer_id=organizer_user.id,
        is_published=True,
    )

    # Event 3: Tomorrow (Sunday 2026-10-25)
    tomorrow_event = Event(
        title="Sunday Chess Tournament",
        description="Competitive campus chess.",
        category="Sports",
        start_time=datetime(2026, 10, 25, 10, 0, 0),
        end_time=datetime(2026, 10, 25, 14, 0, 0),
        organizer_id=organizer_user.id,
        is_published=True,
    )

    db_session.add_all([ended_event, active_today_event, tomorrow_event])
    db_session.commit()

    # Query time_frame=today
    res = client.get(
        "/events",
        params={"time_frame": "today", "reference_time": ref_iso},
    )
    assert res.status_code == 200
    data = res.json()
    titles = [e["title"] for e in data["events"]]

    # Active event today must be included
    assert "Robotics Workshop Hands-on" in titles
    # Already ended event today must be excluded
    assert "Morning Campus Cleanup" not in titles
    # Tomorrow event must not be in today feed
    assert "Sunday Chess Tournament" not in titles


def test_weekend_feed_on_saturday(client, db_session, organizer_user):
    # Reference date: Saturday 2026-10-24 at 12:00 EAT
    ref_dt = datetime(2026, 10, 24, 12, 0, 0, tzinfo=NAIROBI_TZ)
    ref_iso = ref_dt.isoformat()

    # Event on Saturday 15:00
    sat_event = Event(
        title="Saturday Hack Night",
        description="Weekend coding sprint.",
        category="Tech",
        start_time=datetime(2026, 10, 24, 15, 0, 0),
        end_time=datetime(2026, 10, 24, 21, 0, 0),
        organizer_id=organizer_user.id,
        is_published=True,
    )

    # Event on Sunday 16:00
    sun_event = Event(
        title="Sunday Acoustic Jam",
        description="Live campus music.",
        category="Cultural",
        start_time=datetime(2026, 10, 25, 16, 0, 0),
        end_time=datetime(2026, 10, 25, 19, 0, 0),
        organizer_id=organizer_user.id,
        is_published=True,
    )

    # Event next Tuesday (weekday, not weekend)
    tue_event = Event(
        title="Tuesday Seminar",
        description="Academic seminar.",
        category="Academic",
        start_time=datetime(2026, 10, 27, 9, 0, 0),
        end_time=datetime(2026, 10, 27, 11, 0, 0),
        organizer_id=organizer_user.id,
        is_published=True,
    )

    db_session.add_all([sat_event, sun_event, tue_event])
    db_session.commit()

    res = client.get(
        "/events",
        params={"time_frame": "weekend", "reference_time": ref_iso},
    )
    assert res.status_code == 200
    titles = [e["title"] for e in res.json()["events"]]

    assert "Saturday Hack Night" in titles
    assert "Sunday Acoustic Jam" in titles
    assert "Tuesday Seminar" not in titles


def test_recommendations_exclude_ended_events(client, db_session, student_user, student_token, organizer_user):
    # Reference date: Saturday 2026-10-24 at 14:00 EAT
    ref_dt = datetime(2026, 10, 24, 14, 0, 0, tzinfo=NAIROBI_TZ)
    ref_iso = ref_dt.isoformat()

    # Set up user interest in Tech
    client.put(
        "/users/me/interests",
        headers={"Authorization": f"Bearer {student_token}"},
        json={"interests": [{"tag": "tech", "weight": 1.0}]},
    )

    # Ended Tech event
    ended_tech = Event(
        title="Past Python Workshop",
        description="Ended intro to python workshop.",
        category="Tech",
        tags="tech, python",
        start_time=datetime(2026, 10, 24, 9, 0, 0),
        end_time=datetime(2026, 10, 24, 12, 0, 0),  # ended at 12:00, ref is 14:00
        organizer_id=organizer_user.id,
        is_published=True,
    )

    # Upcoming Tech event
    upcoming_tech = Event(
        title="Future Python Masterclass",
        description="Deep dive into python frameworks.",
        category="Tech",
        tags="tech, python",
        start_time=datetime(2026, 10, 24, 16, 0, 0),
        end_time=datetime(2026, 10, 24, 19, 0, 0),
        organizer_id=organizer_user.id,
        is_published=True,
    )

    db_session.add_all([ended_tech, upcoming_tech])
    db_session.commit()

    res = client.get(
        "/recommendations",
        params={"strategy": "hybrid", "k": 10, "reference_time": ref_iso},
        headers={"Authorization": f"Bearer {student_token}"},
    )
    assert res.status_code == 200
    rec_titles = [item["event"]["title"] for item in res.json()["recommendations"]]

    assert "Future Python Masterclass" in rec_titles
    assert "Past Python Workshop" not in rec_titles
