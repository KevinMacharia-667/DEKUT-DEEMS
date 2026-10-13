"""
Unified Multi-Factor Hybrid Recommendation Engine.

Combines:
1. Content-Based Filtering (TF-IDF on titles, descriptions, categories, tags, and department)
2. Collaborative Filtering via Matrix Factorization (TruncatedSVD on the User-Event interaction matrix)
3. Context-Aware Ranking (Academic department match, exponential time-decay urgency, and RSVP capacity velocity)

Dynamically adapts weights for cold-start students (zero RSVPs) to guarantee
graceful, highly relevant recommendations from day one.
"""

from datetime import datetime, timezone
import math
from typing import Sequence
import uuid

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.event import Event
from app.models.rsvp import RSVP
from app.models.user import User
from app.models.user_interest import UserInterest


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def build_event_document(event: Event) -> str:
    """Construct a text representation of an event with weighted curated signals."""
    parts: list[str] = []
    if event.title:
        parts.append(event.title.lower())
    if event.description:
        parts.append(event.description.lower())
    if event.category:
        parts.extend([event.category.lower()] * 2)
    if event.tags:
        tags_clean = event.tags.replace(",", " ").lower()
        parts.extend([tags_clean] * 2)
    if event.department:
        parts.extend([event.department.lower()] * 2)
    return " ".join(parts)


def build_user_profile(
    user_interests: Sequence[UserInterest],
    rsvp_events: Sequence[Event] = (),
    department: str | None = None,
) -> str:
    """Build the user text document from declared interests, RSVPs, and department."""
    words: list[str] = []
    for ui in user_interests:
        repeats = max(1, int(round(ui.weight)))
        words.extend([ui.interest_tag.lower().strip()] * repeats)
    for event in rsvp_events:
        if event.title:
            words.append(event.title.lower())
        if event.category:
            words.append(event.category.lower())
    if department:
        words.extend([department.lower().strip()] * 2)
    return " ".join(words)


def compute_content_scores(
    user_doc: str,
    all_events: Sequence[Event],
) -> tuple[np.ndarray, list[list[str]]]:
    """Compute TF-IDF cosine similarities and shared top matching terms."""
    n_events = len(all_events)
    if not user_doc.strip() or n_events == 0:
        return np.zeros(n_events), [[] for _ in range(n_events)]

    event_docs = [build_event_document(e) for e in all_events]
    corpus = [user_doc] + event_docs

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        return np.zeros(n_events), [[] for _ in range(n_events)]

    user_vec = tfidf_matrix[0]
    event_vecs = tfidf_matrix[1:]
    sim_scores = cosine_similarity(user_vec, event_vecs).flatten()

    feature_names = vectorizer.get_feature_names_out()
    user_arr = user_vec.toarray().flatten()

    explanations: list[list[str]] = []
    for idx in range(n_events):
        event_arr = event_vecs[idx].toarray().flatten()
        shared = user_arr * event_arr
        top_indices = shared.argsort()[::-1][:3]
        terms = [feature_names[i] for i in top_indices if shared[i] > 0]
        explanations.append(terms)

    return np.clip(sim_scores, 0.0, 1.0), explanations


def compute_collaborative_scores(
    target_user_id: uuid.UUID,
    all_events: Sequence[Event],
    all_rsvps: Sequence[RSVP],
) -> np.ndarray:
    """
    Compute collaborative latent factor affinities via TruncatedSVD
    on the User x Event interaction matrix.
    """
    n_events = len(all_events)
    if n_events == 0 or not all_rsvps:
        return np.zeros(n_events)

    event_id_to_idx = {e.id: i for i, e in enumerate(all_events)}
    unique_users = list({r.user_id for r in all_rsvps})

    if target_user_id not in unique_users:
        return np.zeros(n_events)

    user_id_to_idx = {u: i for i, u in enumerate(unique_users)}
    target_idx = user_id_to_idx[target_user_id]

    n_users = len(unique_users)
    if n_users < 3 or n_events < 3:
        scores = np.zeros(n_events)
        for r in all_rsvps:
            if r.user_id == target_user_id and r.event_id in event_id_to_idx:
                scores[event_id_to_idx[r.event_id]] = 0.5
        return scores

    R = np.zeros((n_users, n_events), dtype=np.float32)
    for r in all_rsvps:
        if r.user_id in user_id_to_idx and r.event_id in event_id_to_idx:
            u_i = user_id_to_idx[r.user_id]
            e_i = event_id_to_idx[r.event_id]
            R[u_i, e_i] = 1.0 if r.status == "confirmed" else -0.5

    if np.all(R[target_idx] <= 0):
        return np.zeros(n_events)

    n_components = min(8, n_users - 1, n_events - 1)
    if n_components < 1:
        return np.zeros(n_events)

    try:
        svd = TruncatedSVD(n_components=n_components, random_state=42)
        latent_users = svd.fit_transform(R)
        reconstructed = svd.inverse_transform(latent_users)
        user_pred = reconstructed[target_idx]

        min_p, max_p = np.min(user_pred), np.max(user_pred)
        if max_p > min_p:
            norm_scores = (user_pred - min_p) / (max_p - min_p)
        else:
            norm_scores = np.zeros(n_events)
        return np.clip(norm_scores, 0.0, 1.0)
    except Exception:
        return np.zeros(n_events)


def compute_context_scores(
    all_events: Sequence[Event],
    user_department: str | None,
    all_rsvps: Sequence[RSVP],
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute contextual feature vectors for all candidate events:
    1. Department match (1.0 if department matches, 0.0 otherwise)
    2. Time-urgency decay (higher score for upcoming events within 2-14 days)
    3. Popularity velocity (ratio of confirmed RSVPs relative to capacity)
    """
    now = _now_utc()
    n_events = len(all_events)

    dept_scores = np.zeros(n_events)
    urgency_scores = np.zeros(n_events)
    pop_scores = np.zeros(n_events)

    rsvp_counts: dict[uuid.UUID, int] = {}
    for r in all_rsvps:
        if r.status == "confirmed":
            rsvp_counts[r.event_id] = rsvp_counts.get(r.event_id, 0) + 1

    clean_user_dept = user_department.strip().lower() if user_department else None

    for i, event in enumerate(all_events):
        if clean_user_dept and event.department:
            clean_ev_dept = event.department.strip().lower()
            if clean_user_dept == clean_ev_dept or clean_ev_dept in clean_user_dept:
                dept_scores[i] = 1.0

        event_start = _as_utc(event.start_time)
        delta_days = max(0.0, (event_start - now).total_seconds() / 86400.0)
        urgency_scores[i] = math.exp(-delta_days / 12.0)

        conf_count = rsvp_counts.get(event.id, 0)
        capacity = event.max_attendees if (event.max_attendees and event.max_attendees > 0) else 50
        pop_scores[i] = min(1.0, conf_count / float(capacity))

    return dept_scores, urgency_scores, pop_scores


def assign_badge_and_reasons(
    content_score: float,
    collab_score: float,
    dept_score: float,
    urgency_score: float,
    pop_score: float,
    matched_terms: list[str],
    event: Event,
    rank: int,
) -> tuple[str, list[str]]:
    """Determine dynamic badge tag and human-readable explanation pills."""
    reasons: list[str] = []

    if matched_terms:
        reasons.append("Matches interests: " + ", ".join(matched_terms[:3]))
    elif content_score > 0.2:
        reasons.append(f"Category: {event.category}")

    if collab_score > 0.4:
        reasons.append("Popular with students in your courses")

    if dept_score > 0.5:
        reasons.append(f"Department: {event.department or 'Campus-wide'}")

    now = _now_utc()
    delta_days = (_as_utc(event.start_time) - now).total_seconds() / 86400.0
    if 0 <= delta_days <= 4:
        reasons.append(f"Happening in {max(1, int(round(delta_days)))} days")
    elif urgency_score > 0.6:
        reasons.append("Happening soon")

    if pop_score >= 0.5:
        reasons.append("Trending on campus")

    # Select primary highlight badge (using unicode escape literals)
    if rank <= 2 and (content_score >= 0.35 or collab_score >= 0.5):
        badge = "\u2728 For You"
    elif pop_score >= 0.5:
        badge = "\U0001F525 Trending on Campus"
    elif 0 <= delta_days <= 4:
        badge = "\u26a1 Happening Soon"
    elif dept_score > 0.5:
        badge = "\U0001F393 Faculty Pick"
    elif content_score >= 0.3:
        badge = "\u2b50 Recommended"
    else:
        badge = "\U0001F4CC Explore"

    return badge, reasons


def recommend_hybrid(
    user: User,
    user_interests: Sequence[UserInterest],
    all_events: Sequence[Event],
    all_rsvps: Sequence[RSVP] = (),
    rsvp_events: Sequence[Event] = (),
    top_n: int = 10,
) -> list[dict]:
    """
    Unified Multi-Factor Hybrid Recommender:
    Simultaneously blends Content, Collaborative SVD, and Contextual Ranking.
    """
    n_events = len(all_events)
    if n_events == 0:
        return []

    user_doc = build_user_profile(
        user_interests, rsvp_events=rsvp_events, department=user.department
    )

    content_scores, explanations = compute_content_scores(user_doc, all_events)
    collab_scores = compute_collaborative_scores(user.id, all_events, all_rsvps)
    dept_scores, urgency_scores, pop_scores = compute_context_scores(
        all_events, user.department, all_rsvps
    )

    has_user_rsvps = len(rsvp_events) > 0
    has_interests = len(user_interests) > 0

    if has_user_rsvps:
        w_content = 0.42
        w_collab = 0.28
        w_dept = 0.12
        w_urgency = 0.10
        w_pop = 0.08
    elif has_interests:
        w_content = 0.62
        w_collab = 0.00
        w_dept = 0.16
        w_urgency = 0.12
        w_pop = 0.10
    else:
        w_content = 0.00
        w_collab = 0.00
        w_dept = 0.35
        w_urgency = 0.35
        w_pop = 0.30

    composite_scores = (
        w_content * content_scores
        + w_collab * collab_scores
        + w_dept * dept_scores
        + w_urgency * urgency_scores
        + w_pop * pop_scores
    )

    ranked_indices = composite_scores.argsort()[::-1]

    results: list[dict] = []
    for rank, idx in enumerate(ranked_indices[:top_n], start=1):
        score_val = float(composite_scores[idx])
        if score_val <= 0.0 and len(results) >= 5:
            break

        event = all_events[idx]
        badge, reasons = assign_badge_and_reasons(
            content_score=float(content_scores[idx]),
            collab_score=float(collab_scores[idx]),
            dept_score=float(dept_scores[idx]),
            urgency_score=float(urgency_scores[idx]),
            pop_score=float(pop_scores[idx]),
            matched_terms=explanations[idx],
            event=event,
            rank=rank,
        )

        explanation_str = "; ".join(reasons) if reasons else "Recommended campus event"

        results.append({
            "event": event,
            "score": round(score_val, 4),
            "explanation": explanation_str,
            "badge": badge,
            "reasons": reasons,
            "content_score": round(float(content_scores[idx]), 4),
            "collab_score": round(float(collab_scores[idx]), 4),
            "urgency_score": round(float(urgency_scores[idx]), 4),
            "dept_score": round(float(dept_scores[idx]), 4),
        })

    return results
