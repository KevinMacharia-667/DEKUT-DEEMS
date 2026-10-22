# DeKUT Event Management System (Tukio) — Project Status

> **Date:** 22 October 2026  
> **Status:** Stage 5: Pre-Defense Hardening & Polish (Feature Complete & Tested)  
> **Test Suite Counts:** **25/25 passing backend tests** (`pytest`) | **13/13 passing frontend tests** (`node --test`)

---

## 1. What's Built & Verified

### Backend (Python 3.13 + FastAPI + SQLAlchemy + SQLite dev DB)

| Layer | Files | Status & Evidence |
|---|---|---|
| **Models** | `user.py`, `event.py`, `rsvp.py`, `user_interest.py`, `event_feedback.py`, `interaction_event.py` | ✅ Complete — Verified via `tests/test_auth.py`, `tests/test_events.py`, `tests/test_tukio_rsvp.py` |
| **Schemas** | `user.py`, `event.py`, `rsvp.py`, `token.py`, `user_interest.py`, `recommendation.py`, `interaction.py` | ✅ Complete — Pydantic v2 validation models across all endpoints |
| **Routers** | `auth.py`, `events.py`, `rsvps.py`, `users.py`, `recommendations.py`, `interactions.py`, `venues.py` | ✅ Complete — Full CRUD, feedback logging, time-aware filtering, venues API (`pytest` 25 passed) |
| **Auth & Security** | `services/auth.py`, `dependencies.py`, `config.py` | ✅ Complete — JWT + bcrypt, role guards, trusted CORS whitelist, production secret validator |
| **Venues Module** | `venues.py`, `routers/venues.py` | ✅ Complete — Official DeKUT campus spaces with source tags; tested in `tests/test_venues.py` |
| **Recommender** | `ml/baseline.py`, `ml/engine.py`, `ml/hybrid_engine.py` | ✅ Complete — Heuristic rule baseline, TF-IDF content model, and multi-factor hybrid engine |
| **Evaluation** | `evaluate.py`, `seed_ground_truth.json`, `results/` | 🟡 Partial — Multi-seed benchmark runs (P@K, R@K, NDCG@10, MRR). Awaiting coverage & docs chart in Step 4 |

### Frontend (React 19 + Vite 8 + React Router 7 + Plain CSS)

| Area | Key Files | Status & Evidence |
|---|---|---|
| **Auth Flow** | `LoginPage.jsx`, `RegisterPage.jsx`, `AuthContext.jsx` | ✅ Complete — Login, registration, token persistence in localStorage |
| **Swipe Feed (Tukio)** | `EventsPage.jsx`, `TukioCard.jsx`, `TukioCard.css` | ✅ Complete — Touch gestures, card flight, time-aware tabs (`Today`, `Weekend`, `For You`, `All`) |
| **Event Detail & Edit** | `EventDetailPage.jsx`, `EditEventPage.jsx`, `CreateEventPage.jsx` | ✅ Complete — Detail view, full organizer edit/create with venue `<datalist>` picker |
| **Onboarding** | `OnboardingPage.jsx`, `user_interest.py` | ✅ Complete — Cold-start category picker (3+ required), tested in `test_tukio_onboarding.py` |
| **Calendar & Share** | `utils/calendar.js`, `TukioCard.jsx` | ✅ Complete — RFC 5545 `.ics` generator and WhatsApp deep link; tested in `src/utils/calendar.test.js` |
| **Theme & Transitions** | `context/ThemeContext.jsx`, `utils/theme.js`, `index.css` | ✅ Complete — Dark/light mode with anti-flash script; tested in `src/utils/theme.test.js` |
| **PWA Infrastructure** | `public/manifest.json`, `public/sw.js`, `components/PWAInstallPrompt.jsx` | 🟡 Partial — Manifest and SW installed; full offline app-shell for hashed Vite chunks scheduled for Step 3 |
| **API Client** | `api.js` | ✅ Complete — Unified client covering events, feedback, interactions, telemetry, venues, and auth |

---

## 2. Tukio Roadmap Verification Matrix (9 Priorities)

1. ✅ **Mobile-first swipeable card feed**  
   *Evidence:* `frontend/src/pages/EventsPage.jsx`, `frontend/src/components/TukioCard.jsx` (touch swipe, keyboard navigation, and feed state locking).
2. ✅ **"Why recommended" explainability chip**  
   *Evidence:* `frontend/src/components/TukioCard.jsx:253`, `backend/app/ml/hybrid_engine.py:244` (verified in `tests/test_recommendations.py`).
3. ✅ **Cold-start onboarding (3+ interests)**  
   *Evidence:* `frontend/src/pages/OnboardingPage.jsx`, `backend/app/routers/users.py:65` (verified in `tests/test_tukio_onboarding.py`).
4. ✅ **Time-aware curation (Today / This Weekend / For You / All)**  
   *Evidence:* `backend/app/services/time_utils.py`, `backend/app/routers/events.py:107` (verified in `tests/test_tukio_time_aware.py`).
5. ✅ **Feedback loop ("Interested" / "Not for me")**  
   *Evidence:* `backend/app/routers/interactions.py`, `backend/app/models/event_feedback.py` (verified in `tests/test_tukio_feedback.py`).
6. ✅ **WhatsApp share & .ics calendar download**  
   *Evidence:* `frontend/src/utils/calendar.js`, `frontend/src/components/TukioCard.jsx:340` (verified in `frontend/src/utils/calendar.test.js`).
7. ✅ **Skeleton loaders, smooth transitions & dark mode**  
   *Evidence:* `frontend/src/components/TukioCard.css`, `frontend/src/context/ThemeContext.jsx` (verified in `frontend/src/utils/theme.test.js`).
8. 🟡 **PWA setup (manifest, service worker, install prompt)**  
   *Evidence:* `frontend/public/manifest.json`, `frontend/public/sw.js` (verified in `frontend/src/utils/pwa.test.js`; marked partial pending hashed chunk precaching in Step 3).
9. 🟡 **Offline evaluation script (Precision@K, Recall@K, NDCG@K, MRR)**  
   *Evidence:* `backend/evaluate.py`, `backend/results/evaluation.json` (verified in `tests/test_tukio_evaluation.py`; marked partial pending catalog coverage and docs chart in Step 4).

---

## 3. Venues Module Documentation

* **Backend Source of Truth:** [`backend/app/venues.py`](file:///c:/Users/ADMIN/Documents/SEM%204.1/PROJECT/antigravity%20iteration/backend/app/venues.py)  
  Defines verified DeKUT campus facilities categorized by suitability (`Academic`, `Tech`, `Sports`, `Workshop`, `Cultural`, `Career`, `Social`).
* **Source Tags:** Every venue entry carries an audit source tag:
  * `"official"`: Verified via official university documentation (`dkut.ac.ke`, University Profile PDF, Library portal).
  * `"secondary"`: Sourced from institutional secondary publications (e.g., Academic Block descriptions).
  * `"unverified"`: Plausible physical room that requires confirmation.
* **API Endpoint:** `GET /venues?category={category}` in [`backend/app/routers/venues.py`](file:///c:/Users/ADMIN/Documents/SEM%204.1/PROJECT/antigravity%20iteration/backend/app/routers/venues.py).
* **Location Picker:** Integrated into [`CreateEventPage.jsx`](file:///c:/Users/ADMIN/Documents/SEM%204.1/PROJECT/antigravity%20iteration/frontend/src/pages/CreateEventPage.jsx) and [`EditEventPage.jsx`](file:///c:/Users/ADMIN/Documents/SEM%204.1/PROJECT/antigravity%20iteration/frontend/src/pages/EditEventPage.jsx) via `<datalist id="venue-options">`, dynamically filtered by the event's selected category while permitting free-form custom input.

---

## 4. Known Limitations & Defense Considerations

1. **Synthetic Ground Truth Bias:**  
   In `seed.py`, `seed_ground_truth.json` was generated by evaluating whether an event's category or tags matched a student's declared tags. The heuristic **Rule-Based Baseline** therefore has a structural advantage on this benchmark. Online A/B telemetry (CTR, RSVP retention) is required for unbiased production assessment.
2. **DeKUT Venue Room Granularity:**  
   Specific room subdivisions and individual capacities within the Resource Centre (RC) phases and Wildlife Conservancy conference wings are not published online by the university and require physical verification on site.
3. **Database Configuration:**  
   Currently running on a seeded local SQLite database (`dekut_events.db`). PostgreSQL / Supabase migration configuration is present in `config.py` for cloud deployment.
