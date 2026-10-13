/**
 * Centralized API client for the DeKUT Event Management System.
 * All requests go through the Vite proxy (/api → FastAPI backend).
 */

const API_BASE = '/api';

/**
 * Get the stored JWT token.
 */
function getToken() {
  return localStorage.getItem('dekut_token');
}

/**
 * Core fetch wrapper with auth header injection and error handling.
 */
async function request(endpoint, options = {}) {
  const token = getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Handle no-content responses (e.g., DELETE 204)
  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (!response.ok) {
    const error = new Error(data.detail || 'Something went wrong');
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return data;
}

// ── Auth ──────────────────────────────────────────────────────────────

export async function registerUser({ email, username, password, full_name, department }) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, username, password, full_name, department }),
  });
}

export async function loginUser({ email, password }) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
}

export async function getMe() {
  return request('/users/me');
}

export async function updateMe(data) {
  return request('/users/me', {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

// ── Events ───────────────────────────────────────────────────────────

export async function getEvents({ page = 1, per_page = 20, category, search, published_only = true } = {}) {
  const params = new URLSearchParams({ page, per_page, published_only });
  if (category) params.append('category', category);
  if (search) params.append('search', search);
  return request(`/events?${params}`);
}

export async function getEvent(eventId) {
  return request(`/events/${eventId}`);
}

export async function createEvent(data) {
  return request('/events', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateEvent(eventId, data) {
  return request(`/events/${eventId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  });
}

export async function deleteEvent(eventId) {
  return request(`/events/${eventId}`, {
    method: 'DELETE',
  });
}

// ── RSVPs ────────────────────────────────────────────────────────────

export async function rsvpToEvent(eventId) {
  return request(`/events/${eventId}/rsvp`, {
    method: 'POST',
  });
}

export async function cancelRsvp(eventId) {
  return request(`/events/${eventId}/rsvp`, {
    method: 'DELETE',
  });
}

export async function getAttendees(eventId) {
  return request(`/events/${eventId}/attendees`);
}

export async function getMyRsvps() {
  return request('/users/me/rsvps');
}

// ── Interests ─────────────────────────────────────────────────────────

export async function getMyInterests() {
  return request('/users/me/interests');
}

export async function updateMyInterests(interests) {
  return request('/users/me/interests', {
    method: 'PUT',
    body: JSON.stringify({ interests }),
  });
}

// ── Recommendations ───────────────────────────────────────────────────

/**
 * Get personalised event recommendations for the logged-in user.
 * strategy: 'ml' (TF-IDF) or 'baseline' (rule-based) — the toggle exists
 * so the two engines can be compared live during the project demo.
 */
export async function getRecommendations({ strategy = 'ml', k = 5 } = {}) {
  return request(`/recommendations?strategy=${strategy}&k=${k}`);
}
