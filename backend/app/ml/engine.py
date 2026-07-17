"""
Machine Learning Recommendation Engine (Content-Based Filtering).

Uses TF-IDF term weighting (Salton & Buckley, 1988) and cosine
similarity to rank upcoming events against a per-user profile built
from the user's declared interest tags and the titles of events they
have RSVP'd to. This implements the content-based filtering approach
justified in Chapter 2 of the project proposal (Pazzani & Billsus,
2007), chosen because it works from day one with no interaction
history (no cold-start problem).
"""

from typing import Sequence

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.models.event import Event
from app.models.user_interest import UserInterest


def build_event_document(event: Event) -> str:
    """
    One text document per event: title + description + category + tags.
    Tags and category are repeated to weight them above free description
    text, since they are curated signals.
    """
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
    return " ".join(parts)


def build_user_profile(
    user_interests: Sequence[UserInterest],
    rsvp_events: Sequence[Event] = (),
) -> str:
    """
    One text document per user: declared interest tags (repeated by
    weight) plus the titles of events they RSVP'd to (engagement
    signal). This is the "user profile" of classic content-based
    filtering.
    """
    words: list[str] = []
    for ui in user_interests:
        repeats = max(1, int(round(ui.weight)))
        words.extend([ui.interest_tag.lower().strip()] * repeats)
    for event in rsvp_events:
        if event.title:
            words.append(event.title.lower())
    return " ".join(words)


def recommend_with_scores(
    user_interests: Sequence[UserInterest],
    all_events: Sequence[Event],
    rsvp_events: Sequence[Event] = (),
    top_n: int = 10,
) -> list[dict]:
    """
    Rank events by cosine similarity between the TF-IDF vector of the
    user profile and each event document.

    Returns a list of dicts: {"event": Event, "score": float,
    "explanation": str} sorted by similarity (highest first). The
    explanation lists the top three vocabulary terms shared between the
    user profile and the event, which is what makes the model's
    behaviour inspectable during the project demonstration.
    """
    if not all_events:
        return []

    user_doc = build_user_profile(user_interests, rsvp_events)
    if not user_doc.strip():
        return []

    event_docs = [build_event_document(e) for e in all_events]
    corpus = [user_doc] + event_docs

    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        tfidf_matrix = vectorizer.fit_transform(corpus)
    except ValueError:
        # Corpus was empty after stop-word removal
        return []

    user_vec = tfidf_matrix[0]
    event_vecs = tfidf_matrix[1:]
    sim_scores = cosine_similarity(user_vec, event_vecs).flatten()

    feature_names = vectorizer.get_feature_names_out()
    user_arr = user_vec.toarray().flatten()

    results: list[dict] = []
    for idx in sim_scores.argsort()[::-1]:
        score = float(sim_scores[idx])
        if score <= 0:
            break
        event_arr = event_vecs[idx].toarray().flatten()
        # Terms present in BOTH the user profile and this event,
        # ranked by their combined TF-IDF contribution.
        shared = user_arr * event_arr
        top_term_idx = shared.argsort()[::-1][:3]
        terms = [feature_names[i] for i in top_term_idx if shared[i] > 0]
        explanation = "matched terms: " + ", ".join(terms) if terms else ""
        results.append(
            {"event": all_events[idx], "score": round(score, 4), "explanation": explanation}
        )
        if len(results) == top_n:
            break

    return results


def recommend_events(
    user_interests: Sequence[UserInterest],
    all_events: Sequence[Event],
    top_n: int = 5,
) -> list[Event]:
    """Backward-compatible wrapper returning plain Event objects."""
    ranked = recommend_with_scores(user_interests, all_events, top_n=top_n)
    return [r["event"] for r in ranked]
