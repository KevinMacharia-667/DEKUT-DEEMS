"""
Venues router.

GET /venues?category=Sports   -> campus venues (optionally filtered by event category)

Public (no auth) so the Create/Edit Event forms can populate their Location picker.
"""

from fastapi import APIRouter, Query

from app.venues import VENUES, venues_for

router = APIRouter(prefix="/venues", tags=["Venues"])


@router.get("")
def list_venues(category: str | None = Query(None, description="Filter by event category")):
    if category:
        return venues_for(category, include_online=True)
    return VENUES
