# Tukio — DeKUT Campus Event Recommendation App

**Tukio** (Swahili for *Event / Happening*) is a mobile-first, engagement-focused event recommendation app built for Dedan Kimathi University of Technology (DeKUT). It combines a TikTok/Tinder-style swipeable card feed with an intelligent hybrid recommendation engine (TF-IDF content filtering + collaborative signals) for instant campus discovery and one-tap RSVPs.

## Repository Layout
- `/backend`: Python 3.11/3.13 + FastAPI + SQLAlchemy + SQLite (dev) / PostgreSQL (Supabase prod)
- `/frontend`: React 19 + Vite 8 + React Router 7 (configured as mobile-first Tukio PWA)
- `/backend/app/ml`: Recommendation engine (rule-based baseline, TF-IDF content similarity, and multi-factor hybrid engine)

## Project Pivot & Roadmap (Tukio)
1. ✅ **Mobile-first swipeable card feed**: Full-focus event card deck with touch swipe gestures, keyboard navigation, and instant one-tap RSVP.
2. ⏳ **"Why recommended" chip**: Direct explainability chips on each card powered by the ML engine.
3. ⏳ **Quick onboarding cold-start**: 3+ interest categories selection for new users.
4. ⏳ **Time-aware curation**: Happening Today, This Weekend, For You sections.
5. ⏳ **Feedback loop**: "Interested" / "Not for me" write-backs to the recommender.
6. ⏳ **Sharing & Calendar**: WhatsApp direct sharing and `.ics` / Google Calendar integration.
7. ⏳ **Polishing & UI**: Skeleton loaders, smooth transitions, and dark mode.
8. ⏳ **PWA completion**: Web app manifest, service worker, and mobile install prompt.
9. ⏳ **Offline evaluation script**: Precision@K and Recall@K comparison table for academic documentation.

### Evaluating the recommendation engines
From the backend directory (after seeding): `python seed.py` then `python evaluate.py`
prints the baseline-vs-ML precision table used in Chapter 4 of the report.

## Running the Project

### Backend
1. Navigate to the `backend` directory.
2. Create a Python virtual environment:
   ```cmd
   python -m venv venv
   ```
3. Activate the virtual environment:
   ```cmd
   venv\Scripts\activate
   ```
4. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```
5. Run the FastAPI development server:
   ```cmd
   uvicorn main:app --reload
   ```
6. Open your browser and navigate to `http://127.0.0.1:8000/health`.

### Frontend
1. Navigate to the `frontend` directory.
2. Install the node packages:
   ```cmd
   npm install
   ```
3. Run the Vite development server:
   ```cmd
   npm run dev
   ```
4. Open the displayed local server URL (e.g. `http://localhost:5173`) in your browser.
