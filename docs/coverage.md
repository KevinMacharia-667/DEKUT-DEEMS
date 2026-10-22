# Backend Code Coverage Report

> **Date:** 23 October 2026  
> **Platform:** Windows, Python 3.13.6  
> **Test Framework:** `pytest` 9.1.1 + `pytest-cov` 7.1.0  
> **Test Results:** **57 passed, 1 warning (deprecation notice from starlette testclient)**  
> **Total Project Statements:** 1254  
> **Total Line Coverage:** **93%**  

---

## 1. Summary

All modules in `backend/app/` meet the defense-readiness criteria.
* **Files below 70% coverage threshold:** **None** (all files $\ge$ 76%).
* **100% Coverage:** `app/config.py`, `app/database.py`, `app/dependencies.py`, `app/venues.py`, `app/routers/recommendations.py`, `app/routers/venues.py`, and all Pydantic v2 schemas.

---

## 2. Per-File Coverage Table

| Module | Statements | Missed | Coverage | Uncovered Lines |
|---|---|---|---|---|
| `app/__init__.py` | 0 | 0 | **100%** | None |
| `app/config.py` | 28 | 0 | **100%** | None |
| `app/database.py` | 11 | 0 | **100%** | None |
| `app/dependencies.py` | 51 | 0 | **100%** | None |
| `app/ml/baseline.py` | 46 | 3 | **93%** | 34, 39, 86 |
| `app/ml/engine.py` | 63 | 9 | **86%** | 58-59, 80, 84, 92-94, 119, 130-131 |
| `app/ml/hybrid_engine.py` | 237 | 31 | **87%** | 36, 74-79, 92, 100-101, 148, 158, 160-161, 181, 185, 197, 199-200, 263, 266, 279, 285, 289, 291, 354-358, 392 |
| `app/models/__init__.py` | 7 | 0 | **100%** | None |
| `app/models/event.py` | 26 | 1 | **96%** | 61 |
| `app/models/event_feedback.py` | 37 | 5 | **86%** | 25, 30, 35, 37, 68 |
| `app/models/interaction_event.py` | 36 | 5 | **86%** | 25, 30, 35, 37, 61 |
| `app/models/rsvp.py` | 17 | 1 | **94%** | 43 |
| `app/models/user.py` | 22 | 1 | **95%** | 57 |
| `app/models/user_interest.py` | 16 | 1 | **94%** | 45 |
| `app/routers/__init__.py` | 0 | 0 | **100%** | None |
| `app/routers/auth.py` | 31 | 1 | **97%** | 96 |
| `app/routers/events.py` | 88 | 5 | **94%** | 129, 189-194, 233 |
| `app/routers/interactions.py` | 58 | 3 | **95%** | 54, 120, 179 |
| `app/routers/recommendations.py` | 45 | 0 | **100%** | None |
| `app/routers/rsvps.py` | 55 | 7 | **87%** | 52, 103, 123-136 |
| `app/routers/users.py` | 59 | 14 | **76%** | 49-69, 85-90, 108, 114 |
| `app/routers/venues.py` | 8 | 0 | **100%** | None |
| `app/schemas/__init__.py` | 0 | 0 | **100%** | None |
| `app/schemas/event.py` | 51 | 0 | **100%** | None |
| `app/schemas/interaction.py` | 26 | 0 | **100%** | None |
| `app/schemas/recommendation.py` | 16 | 0 | **100%** | None |
| `app/schemas/rsvp.py` | 17 | 0 | **100%** | None |
| `app/schemas/token.py` | 7 | 0 | **100%** | None |
| `app/schemas/user.py` | 31 | 0 | **100%** | None |
| `app/schemas/user_interest.py` | 12 | 0 | **100%** | None |
| `app/services/__init__.py` | 0 | 0 | **100%** | None |
| `app/services/auth.py` | 20 | 0 | **100%** | None |
| `app/services/interaction_service.py` | 11 | 0 | **100%** | None |
| `app/services/rate_limiter.py` | 69 | 4 | **94%** | 92, 103, 129, 141 |
| `app/services/time_utils.py` | 31 | 3 | **90%** | 12-14, 22 |
| `app/venues.py` | 22 | 0 | **100%** | None |
| **TOTAL** | **1254** | **94** | **93%** | |

---

## 3. Key Security & Recommender Test Coverage

1. **Authentication & Rate Limiting (`test_auth.py`):**
   * Default role assignment on registration (`student`).
   * Privilege escalation prevention against body injection.
   * In-memory sliding-window rate limiter blocking the 6th failed login attempt with `HTTP 429`.
   * Successful logins never consume failure budget.
   * `X-Forwarded-For` proxy resolution when `AUTH_TRUST_PROXY=true`; ignored when `false`.
   * Fail-safe refusal to start with default secret unless `APP_ENV=development`.

2. **Role-Based CRUD Operations (`test_events.py`):**
   * Creation: student denied (403), organizer/admin allowed (201).
   * Modification/Deletion: non-owners denied (403), event owner organizer allowed (200/204), admin override allowed (200/204).

3. **Event RSVP Capacity Controls (`test_tukio_rsvp.py`):**
   * Capacity rejection at threshold (`400 Bad Request`).
   * Seat replenishment upon cancellation.
   * Re-confirmation guard preventing reservation if capacity filled while cancelled.

4. **Multi-Factor Recommender Verification (`test_recommendations.py`):**
   * Cold-start users (0 interests, 0 RSVPs) gracefully receive popularity/department/urgency recommendations without errors.
   * Attendee history dynamically boosts collaborative and content scoring.
   * Graceful zero-event response when database is empty (`count: 0`).
