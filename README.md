# DeKUT Event Management System

A campus event management platform with a recommendation engine built as a final-year project.

## Repository Layout
- `/backend`: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL (Supabase)
- `/frontend`: React 18 + Vite + Tailwind CSS + react-router (configured as a PWA)
- `/ml`: Recommendation engine module using `scikit-learn` for TF-IDF & cosine similarity

## Current Stage
**STAGE 5 COMPLETE: Recommendation Engine (baseline + ML).**
- Stages 1-4 done: auth (JWT + roles), events CRUD, RSVPs, full React frontend.
- Stage 5 Part A done: event category/tags, user_interests model + /me/interests endpoints, seed script with ground truth.
- Stage 5 Parts B & C done: rule-based baseline (app/ml/baseline.py), TF-IDF engine with explanations (app/ml/engine.py), GET /recommendations?strategy=ml|baseline endpoint, "Recommended for you" section with strategy toggle on the Dashboard, and evaluate.py (precision@5/@10 comparison for the report).
- Next: search/filter UI polish, edit-event page, tests, then Stage 6 (PWA) and Stage 7 (deploy + Supabase).

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
