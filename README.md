# DeKUT Event Management System

A campus event management platform with a recommendation engine built as a final-year project.

## Repository Layout
- `/backend`: Python 3.11 + FastAPI + SQLAlchemy + PostgreSQL (Supabase)
- `/frontend`: React 18 + Vite + Tailwind CSS + react-router (configured as a PWA)
- `/ml`: Recommendation engine module using `scikit-learn` for TF-IDF & cosine similarity

## Current Stage
We are currently at **STAGE 1: Project Setup**.
- Backend has a `/health` endpoint.
- Frontend has a beautiful placeholder landing page with Tailwind CSS.
- ML directory has a placeholder readme.

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
