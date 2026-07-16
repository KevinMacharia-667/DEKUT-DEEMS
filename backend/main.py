"""
DeKUT Event Management System - FastAPI Application Entry Point.

Registers all API routers and configures middleware.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import auth, events, rsvps, users

# Create all tables on startup (for dev; use Alembic in production)
# Import models so Base.metadata knows about them
import app.models  # noqa: F401

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="DeKUT Event Management System API",
    description="Backend API for the DeKUT Event Management Platform with Recommendation Engine",
    version="1.0.0",
)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development; refine in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ──────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(rsvps.router)


# ── System Endpoints ──────────────────────────────────────────────────


@app.get("/health", tags=["System"])
def health_check():
    """
    Health check endpoint to verify backend operational status.
    """
    return {"status": "ok"}
