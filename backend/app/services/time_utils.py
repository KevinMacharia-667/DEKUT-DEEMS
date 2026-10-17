"""
Timezone and date range utilities for Africa/Nairobi (EAT, UTC+3).
Used for time-aware event feeds: Happening Today, This Weekend, and For You.
"""

from datetime import datetime, time, timedelta, timezone
from typing import Tuple

try:
    from zoneinfo import ZoneInfo
    NAIROBI_TZ = ZoneInfo("Africa/Nairobi")
except Exception:
    # Resilient fallback if tzdata is missing on older environments
    NAIROBI_TZ = timezone(timedelta(hours=3))


def get_nairobi_now(ref_dt: datetime | None = None) -> datetime:
    """Return the current datetime in Africa/Nairobi timezone or convert reference dt."""
    if ref_dt is not None:
        if ref_dt.tzinfo is None:
            # Assume UTC if naive, then convert to Nairobi
            ref_dt = ref_dt.replace(tzinfo=timezone.utc)
        return ref_dt.astimezone(NAIROBI_TZ)
    return datetime.now(NAIROBI_TZ)


def get_today_bounds(ref_dt: datetime | None = None) -> Tuple[datetime, datetime]:
    """
    Return the (start, end) datetimes for 'Today' in Africa/Nairobi.
    start: 00:00:00.000000
    end:   23:59:59.999999
    """
    now = get_nairobi_now(ref_dt)
    d = now.date()
    today_start = datetime(d.year, d.month, d.day, 0, 0, 0, 0, tzinfo=NAIROBI_TZ)
    today_end = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=NAIROBI_TZ)
    return today_start, today_end


def get_weekend_bounds(ref_dt: datetime | None = None) -> Tuple[datetime, datetime]:
    """
    Return the (start, end) datetimes for 'This Weekend' in Africa/Nairobi.
    
    Rule:
    - If today is Friday after 17:00, Saturday (weekday=5) or Sunday (weekday=6),
      'This Weekend' means the current weekend (Friday 17:00 to Sunday 23:59:59).
    - Otherwise (Monday-Thursday, or Friday before 17:00),
      'This Weekend' means the upcoming weekend.
    """
    now = get_nairobi_now(ref_dt)
    wd = now.weekday()  # Monday is 0, Sunday is 6

    # Friday after 17:00, Saturday, or Sunday
    if (wd == 4 and now.hour >= 17) or wd == 5 or wd == 6:
        days_back = wd - 4
        fri_date = now.date() - timedelta(days=days_back)
    else:
        days_ahead = (4 - wd) % 7
        fri_date = now.date() + timedelta(days=days_ahead)

    weekend_start = datetime(
        fri_date.year, fri_date.month, fri_date.day, 17, 0, 0, 0, tzinfo=NAIROBI_TZ
    )
    sun_date = fri_date + timedelta(days=2)
    weekend_end = datetime(
        sun_date.year, sun_date.month, sun_date.day, 23, 59, 59, 999999, tzinfo=NAIROBI_TZ
    )
    return weekend_start, weekend_end
