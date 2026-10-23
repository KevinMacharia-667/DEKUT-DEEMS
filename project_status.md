# DeKUT Event Management System (Tukio) — Project Status

> **Date:** 22 October 2026  
> **Status:** Stage 5: Pre-Defense Hardening & Polish (Feature Complete & Tested)  
> **Test Suite Counts:** **72/72 passing backend tests** (`pytest`, **93% code coverage**, see `docs/coverage.md`) | **31/31 passing frontend tests** (`node --test`)

---

## 1. What's Built & Verified

### Backend (Python 3.13 + FastAPI + SQLAlchemy + SQLite dev DB)

| Layer | Files | Status & Evidence |
|---|---|---|
| **Models** | `user.py`, `event.py`, `rsvp.py`, `user_interest.py`, `event_feedback.py`, `interaction_event.py` | ✅ Complete — Verified via `tests/test_auth.py`, `tests/test_events.py`, `tests/test_tukio_rsvp.py` |
| **Schemas** | `user.py`, `event.py`, `rsvp.py`, `token.py`, `user_interest.py`, `recommendation.py`, `interaction.py` | ✅ Complete — Pydantic v2 validation models across all endpoints |
| **Routers** | `auth.py`, `events.py`, `rsvps.py`, `users.py`, `recommendations.py`, `interactions.py`, `venues.py` | ✅ Complete — Full CRUD, feedback logging, time-aware filtering, venues API (`pytest` 66 passed, 93% coverage) |
| **Auth & Security** | `services/auth.py`, `dependencies.py`, `config.py` | ✅ Complete — JWT + bcrypt, role guards, trusted CORS whitelist, production secret validator |
| **Venues Module** | `venues.py`, `routers/venues.py` | ✅ Complete — Official DeKUT campus spaces with source tags; tested in `tests/test_venues.py` |
| **Recommender** | `ml/baseline.py`, `ml/engine.py`, `ml/hybrid_engine.py` | ✅ Complete — Heuristic rule baseline, TF-IDF content model, and multi-factor hybrid engine |
| **Evaluation** | `evaluate.py`, `evaluate_sensitivity.py`, `seed_ground_truth.json`, `results/` | ✅ Complete — Behaviour-based + tag-overlap ground truth, 10 seeds, P@5/P@10/R@10/NDCG@10/MRR/Coverage@10; write-up in `docs/evaluation.md` |

### Frontend (React 19 + Vite 8 + React Router 7 + Plain CSS)

| Area | Key Files | Status & Evidence |
|---|---|---|
| **Auth Flow** | `LoginPage.jsx`, `RegisterPage.jsx`, `AuthContext.jsx` | ✅ Complete — Login, registration, token persistence in localStorage |
| **Swipe Feed (Tukio)** | `EventsPage.jsx`, `TukioCard.jsx`, `TukioCard.css` | ✅ Complete — Touch gestures, card flight, time-aware tabs (`Today`, `Weekend`, `For You`, `All`) |
| **Event Detail & Edit** | `EventDetailPage.jsx`, `EditEventPage.jsx`, `CreateEventPage.jsx` | ✅ Complete — Detail view, full organizer edit/create with venue `<datalist>` picker |
| **Onboarding** | `OnboardingPage.jsx`, `user_interest.py` | ✅ Complete — Cold-start category picker (3+ required), tested in `test_tukio_onboarding.py` |
| **Calendar & Share** | `utils/calendar.js`, `TukioCard.jsx` | ✅ Complete — RFC 5545 `.ics` generator and WhatsApp deep link; tested in `src/utils/calendar.test.js` |
| **Theme & Transitions** | `context/ThemeContext.jsx`, `utils/theme.js`, `index.css` | ✅ Complete — Dark/light mode with anti-flash script; tested in `src/utils/theme.test.js` |
| **PWA Infrastructure** | `public/manifest.json`, `dist/sw.js`, `vite.config.js`, `components/PWAInstallPrompt.jsx` | ✅ Complete — Manifest, precached hashed Vite chunks, offline app shell fallback, and install prompt (tested in `src/utils/pwa.test.js`) |
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
8. ✅ **PWA setup (manifest, service worker, install prompt)**  
   *Evidence:* `frontend/public/manifest.json`, `frontend/dist/sw.js`, `frontend/vite.config.js` (verified in `frontend/src/utils/pwa.test.js`; precaches hashed chunks, offline navigation fallback).
9. ✅ **Offline evaluation benchmark (Precision@K, Recall@K, NDCG@K, MRR, Catalog Coverage)**  
   *Evidence:* `backend/evaluate.py`, `docs/evaluation.md`, `docs/evaluation_results.md`, `docs/evaluation_chart.png`, `docs/iterations.md` (rule-based → TF-IDF → hybrid history) (verified in `tests/test_tukio_evaluation.py`). On behaviour-based ground truth the hybrid leads (NDCG@10 0.187 vs 0.138 TF-IDF vs 0.119 rule-based); on tag-overlap ground truth the rule-based baseline wins (0.825 vs 0.722).

---

## 2b. Latest Work (23 Oct 2026)

* **UI pass:** event times shown in campus time (EAT); the edit form no longer shifts events; one lucide-react icon set; category date-block covers and "42 / 60 going" seat labels; keyboard focus, 44px touch targets and WCAG AA contrast in both themes; sticky RSVP bar on the event page; feed search and venue filter; one colour token set.
* **Fixes:** service worker registers only in production builds; npm audit clean (Vite 8.3.5, react-router 7.18.4).
* **Real-student data:** survey template (`docs/tukio_survey_form_template.pdf`) and importer (`backend/survey_import.py`, tested with Google-Forms-format CSVs). Waiting on responses.
* **Deployment prepared:** `render.yaml` (Render frontend + backend) and `docs/deployment.md` (Neon PostgreSQL); rehearsed locally with a production build calling a production-mode backend across origins.
* **Next:** create the Neon and Render services, then run the survey and the importer.

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

1. **Synthetic Ground Truth:**  
   `seed_ground_truth.json` uses the Rule-Based baseline's own tag/category rule, so the baseline wins on it. The primary benchmark uses simulated per-user behaviour with hidden preferences, where the hybrid leads. But when the simulator's department and popularity signals are removed, the hybrid only ties TF-IDF on NDCG@10 and loses on MRR (`docs/evaluation.md` §4.3). The hybrid also has the lowest catalog coverage of the three main models, and MMR diversity re-ranking made that worse (§4.4). Online A/B telemetry (CTR, RSVP retention) is required for unbiased production assessment.
2. **DeKUT Venue Room Granularity:**  
   Specific room subdivisions and individual capacities within the Resource Centre (RC) phases and Wildlife Conservancy conference wings are not published online by the university and require physical verification on site.
3. **Database Configuration:**  
   Currently running on a seeded local SQLite database (`dekut_events.db`). PostgreSQL / Supabase migration configuration is present in `config.py` for cloud deployment.
