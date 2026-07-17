import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getEvents, getMyRsvps, getEvent, getMyInterests, updateMyInterests } from '../api';
import RecommendedEvents from '../components/RecommendedEvents';
import './DashboardPage.css';

/**
 * Predefined interest tags matching the event categories and common
 * sub-topics. Users can also add free-text tags beyond these.
 */
const INTEREST_OPTIONS = [
  'academic', 'social', 'sports', 'workshop', 'cultural', 'tech', 'career',
  'entrepreneurship', 'python', 'javascript', 'ai', 'data science',
  'cybersecurity', 'networking', 'design', 'music', 'film', 'debate',
  'research', 'volunteering', 'leadership', 'health', 'fitness',
];

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [myEvents, setMyEvents] = useState([]);
  const [myRsvps, setMyRsvps] = useState([]);
  const [rsvpEvents, setRsvpEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  // Interest tags state
  const [selectedTags, setSelectedTags] = useState(new Set());
  const [customTag, setCustomTag] = useState('');
  const [savingInterests, setSavingInterests] = useState(false);
  const [interestsSaved, setInterestsSaved] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        // Fetch events created by current user (use search with published_only=false)
        const eventsData = await getEvents({ per_page: 100, published_only: false });
        const owned = eventsData.events.filter(
          (e) => e.organizer?.id === user?.id
        );
        setMyEvents(owned);

        // Fetch RSVPs
        const rsvps = await getMyRsvps();
        setMyRsvps(rsvps);

        // Fetch event details for each RSVP
        const eventDetails = await Promise.all(
          rsvps.map((r) => getEvent(r.event_id).catch(() => null))
        );
        setRsvpEvents(eventDetails.filter(Boolean));

        // Fetch existing interests
        const interests = await getMyInterests();
        setSelectedTags(new Set(interests.map((i) => i.interest_tag)));
      } catch {
        // Silently handle errors
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [user]);

  // Save interests to backend
  const saveInterests = useCallback(async (tags) => {
    setSavingInterests(true);
    setInterestsSaved(false);
    try {
      const interests = [...tags].map((tag) => ({ tag, weight: 1.0 }));
      await updateMyInterests(interests);
      setInterestsSaved(true);
      setTimeout(() => setInterestsSaved(false), 2000);
    } catch {
      // Silently handle
    } finally {
      setSavingInterests(false);
    }
  }, []);

  function toggleTag(tag) {
    setSelectedTags((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) {
        next.delete(tag);
      } else {
        next.add(tag);
      }
      saveInterests(next);
      return next;
    });
  }

  function addCustomTag(e) {
    e.preventDefault();
    const tag = customTag.trim().toLowerCase();
    if (!tag) return;
    setSelectedTags((prev) => {
      const next = new Set(prev);
      next.add(tag);
      saveInterests(next);
      return next;
    });
    setCustomTag('');
  }

  if (loading) {
    return <div className="page"><div className="loading-page"><div className="spinner" /></div></div>;
  }

  const confirmedRsvps = myRsvps.filter((r) => r.status === 'confirmed');

  return (
    <div className="page">
      <div className="container">
        <div className="page-header animate-fade-in">
          <h1>Dashboard</h1>
          <p>Your events and activity at a glance</p>
        </div>

        <RecommendedEvents k={5} />

        <div className="dashboard-grid animate-fade-in">
          {/* Profile sidebar */}
          <div>
            <div className="glass-card profile-card">
              <div className="profile-avatar">
                {user?.full_name?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || '?'}
              </div>
              <div className="profile-name">
                {user?.full_name || user?.username}
              </div>
              <div className="profile-email">{user?.email}</div>
              <span className="badge badge-accent profile-role">{user?.role}</span>

              <div className="profile-stats">
                <div>
                  <div className="profile-stat-value">{myEvents.length}</div>
                  <div className="profile-stat-label">Events</div>
                </div>
                <div>
                  <div className="profile-stat-value">{confirmedRsvps.length}</div>
                  <div className="profile-stat-label">Attending</div>
                </div>
              </div>
            </div>

            {/* My Interests */}
            <div className="glass-card interests-card">
              <div className="interests-header">
                <h3>My Interests</h3>
                {savingInterests && <span className="spinner interests-spinner" />}
                {interestsSaved && <span className="interests-saved">✓ Saved</span>}
              </div>
              <p className="interests-hint">
                Select topics you&apos;re interested in. We&apos;ll recommend matching events.
              </p>

              <div className="interests-chips">
                {INTEREST_OPTIONS.map((tag) => (
                  <button
                    key={tag}
                    className={`interest-chip${selectedTags.has(tag) ? ' active' : ''}`}
                    onClick={() => toggleTag(tag)}
                    type="button"
                  >
                    {tag}
                  </button>
                ))}
                {/* Show custom tags not in the predefined list */}
                {[...selectedTags]
                  .filter((t) => !INTEREST_OPTIONS.includes(t))
                  .map((tag) => (
                    <button
                      key={tag}
                      className="interest-chip active custom"
                      onClick={() => toggleTag(tag)}
                      type="button"
                    >
                      {tag} ×
                    </button>
                  ))}
              </div>

              <form className="interests-add" onSubmit={addCustomTag}>
                <input
                  className="form-input"
                  type="text"
                  placeholder="Add custom tag…"
                  value={customTag}
                  onChange={(e) => setCustomTag(e.target.value)}
                  maxLength={50}
                />
                <button type="submit" className="btn btn-secondary btn-sm">Add</button>
              </form>
            </div>
          </div>

          {/* Main content */}
          <div>
            {/* My Events */}
            <div className="dashboard-section">
              <div className="dashboard-section-header">
                <h2>My Events</h2>
                {(user?.role === 'organizer' || user?.role === 'admin') && (
                  <Link to="/events/new" className="btn btn-primary btn-sm">+ New Event</Link>
                )}
              </div>

              {myEvents.length === 0 ? (
                <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    {user?.role === 'student'
                      ? "Students can attend events. Contact an admin to become an organizer!"
                      : "You haven't created any events yet."}
                  </p>
                </div>
              ) : (
                <div className="dashboard-list">
                  {myEvents.map((event) => (
                    <Link
                      key={event.id}
                      to={`/events/${event.id}`}
                      className="glass-card dashboard-item"
                    >
                      <div className="dashboard-item-icon">📅</div>
                      <div className="dashboard-item-body">
                        <div className="dashboard-item-title">{event.title}</div>
                        <div className="dashboard-item-meta">
                          {formatDate(event.start_time)} · {event.rsvp_count} attendees
                          {!event.is_published && ' · Draft'}
                        </div>
                      </div>
                      {event.category && (
                        <span className="badge badge-muted">{event.category}</span>
                      )}
                    </Link>
                  ))}
                </div>
              )}
            </div>

            {/* My RSVPs */}
            <div className="dashboard-section">
              <div className="dashboard-section-header">
                <h2>Events I&apos;m Attending</h2>
              </div>

              {rsvpEvents.length === 0 ? (
                <div className="glass-card" style={{ padding: '24px', textAlign: 'center' }}>
                  <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                    You haven&apos;t RSVP&apos;d to any events yet.{' '}
                    <Link to="/events">Browse events</Link>
                  </p>
                </div>
              ) : (
                <div className="dashboard-list">
                  {rsvpEvents.map((event) => (
                    <Link
                      key={event.id}
                      to={`/events/${event.id}`}
                      className="glass-card dashboard-item"
                    >
                      <div className="dashboard-item-icon" style={{ background: 'var(--gold-bg)' }}>
                        🎟️
                      </div>
                      <div className="dashboard-item-body">
                        <div className="dashboard-item-title">{event.title}</div>
                        <div className="dashboard-item-meta">
                          {formatDate(event.start_time)}
                          {event.location && ` · ${event.location}`}
                        </div>
                      </div>
                      <span className="badge badge-accent">Attending</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
