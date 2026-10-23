# Tukio — DeKUT Campus Event Recommendation App

> **Current Date:** 22 October 2026  
> **Status:** Stage 5: Pre-Defense Hardening & Polish  
> **Test Suite:** **66/66 passing backend tests** (`pytest`, 93% coverage, see `docs/coverage.md`) | **31/31 passing frontend tests** (`node --test`)

**Tukio** (*Swahili for "Event" / "Happening"*) is a mobile-first campus event recommendation application designed for Dedan Kimathi University of Technology (DeKUT). It pairs a swipeable, engagement-driven card feed with a multi-factor recommendation engine (TF-IDF content filtering, TruncatedSVD collaborative filtering, and contextual urgency) for frictionless campus discovery and one-tap RSVPs.

---

## 1. Technology Stack

* **Backend:** Python 3.13, FastAPI 0.115, SQLAlchemy 2.0, SQLite (development) / PostgreSQL (production config)
* **Machine Learning & Recommenders:** Scikit-learn (TF-IDF Vectorization, TruncatedSVD Matrix Factorization), NumPy
* **Frontend:** React 19, Vite 8, React Router 7, Plain CSS (custom design system with CSS custom properties; no Tailwind)
* **PWA & Offline:** Web App Manifest, Service Worker (`sw.js`), Cache API, RFC 5545 `.ics` generator
* **Testing:** Pytest (Python backend), Node.js native test runner (`node --test` for frontend utilities)

---

## 2. Project Roadmap & Verification Matrix

| # | Priority Feature | Status | Verification & Code Evidence |
|---|---|:---:|---|
| 1 | **Mobile-first swipeable card feed** | ✅ Done | `frontend/src/pages/EventsPage.jsx` & `frontend/src/components/TukioCard.jsx` (touch swipe, card flight, feed lock) |
| 2 | **"Why recommended" explainability chip** | ✅ Done | `frontend/src/components/TukioCard.jsx:253`, `backend/app/ml/hybrid_engine.py:244` (tested in `tests/test_recommendations.py`) |
| 3 | **Cold-start onboarding (3+ interests)** | ✅ Done | `frontend/src/pages/OnboardingPage.jsx`, `backend/app/routers/users.py:65` (tested in `tests/test_tukio_onboarding.py`) |
| 4 | **Time-aware curation (Today / Weekend / For You / All)** | ✅ Done | `backend/app/services/time_utils.py`, `backend/app/routers/events.py:107` (tested in `tests/test_tukio_time_aware.py`) |
| 5 | **Feedback loop ("Interested" / "Not for me")** | ✅ Done | `backend/app/routers/interactions.py`, `backend/app/models/event_feedback.py` (tested in `tests/test_tukio_feedback.py`) |
| 6 | **WhatsApp share & .ics calendar download** | ✅ Done | `frontend/src/utils/calendar.js`, `frontend/src/components/TukioCard.jsx:340` (tested in `frontend/src/utils/calendar.test.js`) |
| 7 | **Skeleton loaders, smooth transitions & dark mode** | ✅ Done | `frontend/src/components/TukioCard.css`, `frontend/src/context/ThemeContext.jsx` (tested in `frontend/src/utils/theme.test.js`) |
| 8 | **PWA setup (manifest, service worker, install prompt)** | ✅ Done | `frontend/dist/sw.js`, `vite.config.js` (precache hashed chunks, offline app shell fallback, tested in `frontend/src/utils/pwa.test.js`) |
| 9 | **Offline evaluation benchmark (ML vs Baselines)** | ✅ Done | `backend/evaluate.py` (behaviour-based + tag-overlap ground truth, 10 seeds, catalog coverage), write-up in `docs/evaluation.md`, version history in `docs/iterations.md`, chart `docs/evaluation_chart.png` (tested in `tests/test_tukio_evaluation.py`) |

---

## 3. DeKUT Venues Module

Campus facilities are formalized in [`backend/app/venues.py`](file:///c:/Users/ADMIN/Documents/SEM%204.1/PROJECT/antigravity%20iteration/backend/app/venues.py) as the single source of truth for event locations.

* **Audited Venue Sources:**
  * `"official"`: Verified against official university publications (`dkut.ac.ke`, University Profile 2021, Library portal).
  * `"secondary"`: Verified via documented campus structures (e.g., Academic Block laboratories and halls).
  * `"unverified"`: Plausible physical room that still requires physical verification.
* **API Access:** `GET /venues` (optionally filtered with `?category=Sports` or `?category=Academic`).
* **UI Location Picker:** Both [`CreateEventPage.jsx`](file:///c:/Users/ADMIN/Documents/SEM%204.1/PROJECT/antigravity%20iteration/frontend/src/pages/CreateEventPage.jsx) and [`EditEventPage.jsx`](file:///c:/Users/ADMIN/Documents/SEM%204.1/PROJECT/antigravity%20iteration/frontend/src/pages/EditEventPage.jsx) provide a `<datalist id="venue-options">` auto-filtered by event category while allowing free text entry.

---

## 4. Known Limitations

* **Synthetic Evaluation Data:**  
  The original `backend/seed_ground_truth.json` uses the same tag/category overlap rule as the Rule-Based baseline, which wins on that set. The primary benchmark now uses simulated per-user behaviour with hidden preferences, where the hybrid leads, but without the simulator's department and popularity signals it only ties TF-IDF. See `docs/evaluation.md`. Real RSVP logs are still needed.
* **Campus Room Granularity:**  
  Individual room numbers and seating capacities within the Resource Centre (RC phases 1–3) and Wildlife Conservancy conference wings are not published online by the university and must be physically confirmed on site.

---

## 5. Security & Fail-Safe Configuration

* **Fail-Safe JWT Secret Guard (`APP_ENV`):**
  * The environment variable `APP_ENV` defaults to `"production"`.
  * If `APP_ENV` is omitted, blank, or set to anything other than `"development"`, the backend **refuses to start** with a `ValueError` if the default development secret is in use.
  * For local testing and development, you must explicitly set `APP_ENV=development` in your `.env` or environment.
  * In production, always set a cryptographically strong, unique `JWT_SECRET` string.
* **Authentication Rate Limiting:**
  * Endpoints `/auth/login` and `/auth/register` are protected against credential stuffing and brute-force attacks via an in-memory sliding-window limiter.
  * Default policy: **5 attempts per 60 seconds per IP**.
  * When exceeded, the API responds with `HTTP 429 Too Many Requests`, a detailed error message, and a `Retry-After` header.
  * Configurable via `.env` (`AUTH_RATE_LIMIT_MAX_ATTEMPTS`, `AUTH_RATE_LIMIT_WINDOW_SECONDS`, `AUTH_RATE_LIMIT_ENABLED`).

---

## 6. Running the Project (Windows Setup)

### Prerequisites
* Python 3.11+ (Python 3.13 recommended)
* Node.js 20+ (Node.js 22 tested)

### Backend Setup & Execution
1. Open PowerShell and navigate to the `backend` folder:
   ```powershell
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
3. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
4. Run the database seed script:
   ```powershell
   python seed.py
   ```
5. Run the backend tests:
   ```powershell
   python -m pytest -q
   ```
6. Start the FastAPI development server:
   ```powershell
   python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   ```
7. Verify operational health at `http://127.0.0.1:8000/health` and Swagger docs at `http://127.0.0.1:8000/docs`.

### Frontend Setup & Execution
1. Open a second PowerShell terminal and navigate to the `frontend` folder:
   ```powershell
   cd frontend
   ```
2. Install Node dependencies:
   ```powershell
   npm install
   ```
3. Run the frontend unit tests:
   ```powershell
   npm test
   ```
4. Verify the production build:
   ```powershell
   npm run build
   ```
5. Launch the Vite development server:
   ```powershell
   npm run dev
   ```
6. Open your browser at `http://localhost:5173`.
