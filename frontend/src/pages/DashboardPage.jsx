import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import { getEvents, getMyRsvps, getEvent, getMyInterests, updateMyInterests, updateMe, cancelRsvp } from '../api';
import RecommendedEvents from '../components/RecommendedEvents';
import './DashboardPage.css';

const DEPARTMENTS = [
  'School of Computer Science & IT',
  'School of Engineering',
  'School of Business',
  'School of Science & Applied Tech',
  'Health Sciences',
  'Student Affairs & Sports',
  'Cultural Society',
];

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
  const { user, refreshUser } = useAuth();
  const toast = useToast();
  const [myEvents, setMyEvents] = useState([]);
  const [myRsvps, setMyRsvps] = useState([]);
  const [rsvpEvents, setRsvpEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  // Recommendations & dashboard live refresh counter
  const [refreshKey, setRefreshKey] = useState(0);

  // Profile edit state
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    email: '',
    department: '',
  });
  const [savingProfile, setSavingProfile] = useState(false);

  // Interest tags state
  const [selectedTags, setSelectedTags] = useState(new Set());
  const [customTag, setCustomTag] = useState('');
  const [savingInterests, setSavingInterests] = useState(false);
  const [interestsSaved, setInterestsSaved] = useState(false);

  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.full_name || '',
        email: user.email || '',
        department: user.department || 'School of Computer Science & IT',
      });
    }
  }, [user]);

  // Fetch initial interests once user is loaded
  useEffect(() => {
    async function loadInterests() {
      try {
        const interests = await getMyInterests();
        setSelectedTags(new Set(interests.map((i) => i.interest_tag)));
      } catch {
        // Silently handle
      }
    }
    if (user) {
      loadInterests();
    }
  }, [user]);

  // Fetch events and RSVPs whenever user or refreshKey changes
  const fetchDashboardData = useCallback(async () => {
    try {
      // Fetch events created by current user
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
    } catch {
      // Silently handle
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    fetchDashboardData();
  }, [fetchDashboardData, refreshKey]);

  // Automatically refresh in real time when window gets focus (e.g. user returns from another tab/event page)
  useEffect(() => {
    function handleFocus() {
      fetchDashboardData();
      setRefreshKey((k) => k + 1);
    }
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [fetchDashboardData]);

  // Save interests to backend
  const saveInterests = useCallback(async (tags) => {
    setSavingInterests(true);
    setInterestsSaved(false);
    try {
      const interests = [...tags].map((tag) => ({ tag, weight: 1.0 }));
      await updateMyInterests(interests);
      setInterestsSaved(true);
      // Trigger instant real-time recommendation & dashboard refresh
      setRefreshKey((k) => k + 1);
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

  async function handleProfileSubmit(e) {
    e.preventDefault();
    setSavingProfile(true);
    try {
      await updateMe(profileForm);
      await refreshUser();
      setIsEditingProfile(false);
      // Real-time refresh recommendation feed since department or details changed
      setRefreshKey((k) => k + 1);
      toast.success('Profile updated successfully!');
    } catch (err) {
      toast.error(err.message || 'Failed to update profile');
    } finally {
      setSavingProfile(false);
    }
  }

  // Quick cancel RSVP from dashboard with immediate real-time refresh
  async function handleCancelRsvp(eventId, e) {
    e.preventDefault();
    e.stopPropagation();
    try {
      await cancelRsvp(eventId);
      toast.info('RSVP cancelled');
      // Increment refreshKey: re-fetches dashboard RSVPs and updates Hybrid recommendations
      setRefreshKey((k) => k + 1);
    } catch (err) {
      toast.error(err.message || 'Failed to cancel RSVP');
    }
  }

  if (loading) {
    return <div className="page"><div className="loading-page"><div className="spinner" /></div></div>;
  }

  const confirmedRsvps = myRsvps.filter((r) => r.status === 'confirmed');

  return (
    <div className="page">
      <div className="container">
        <div className="page-header animate-fade-in" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h1>Dashboard</h1>
            <p>Your events and activity at a glance</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              fetchDashboardData();
              setRefreshKey((k) => k + 1);
              toast.info('Dashboard refreshed!');
            }}
            title="Refresh dashboard and recommendations in real time"
          >
            🔄 Refresh Live
          </button>
        </div>

        <RecommendedEvents k={6} refreshTrigger={refreshKey} />

        <div className="dashboard-grid animate-fade-in">
          {/* Profile sidebar */}
          <div>
            <div className="glass-card profile-card">
              <div className="profile-avatar">
                {user?.full_name?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || '?'}
              </div>

              {!isEditingProfile ? (
                <>
                  <div className="profile-name">
                    {user?.full_name || user?.username}
                  </div>
                  <div className="profile-username">@{user?.username}</div>
                  <div className="profile-email">{user?.email}</div>

                  {user?.department && (
                    <div className="profile-department-badge" title="Academic Department">
                      🎓 {user.department}
                    </div>
                  )}

                  <span className="badge badge-accent profile-role">{user?.role}</span>

                  <div style={{ margin: 'var(--space-md) 0' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setIsEditingProfile(true)}
                    >
                      ✏️ Edit Profile
                    </button>
                  </div>
                </>
              ) : (
                <form className="profile-edit-form" onSubmit={handleProfileSubmit}>
                  <div className="form-group">
                    <label className="form-label" htmlFor="edit-full-name">Full Name</label>
                    <input
                      id="edit-full-name"
                      type="text"
                      className="form-input"
                      value={profileForm.full_name}
                      onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                      placeholder="e.g. Jane Doe"
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="edit-email">Email</label>
                    <input
                      id="edit-email"
                      type="email"
                      className="form-input"
                      value={profileForm.email}
                      onChange={(e) => setProfileForm({ ...profileForm, email: e.target.value })}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="edit-department">Academic School / Dept</label>
                    <select
                      id="edit-department"
                      className="form-input"
                      value={profileForm.department}
                      onChange={(e) => setProfileForm({ ...profileForm, department: e.target.value })}
                    >
                      {DEPARTMENTS.map((dept) => (
                        <option key={dept} value={dept}>
                          {dept}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="profile-edit-actions">
                    <button
                      type="submit"
                      className="btn btn-primary btn-sm"
                      disabled={savingProfile}
                    >
                      {savingProfile ? 'Saving…' : 'Save Changes'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setIsEditingProfile(false)}
                      disabled={savingProfile}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              )}

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
                    <div key={event.id} className="glass-card dashboard-item-row" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingRight: '12px' }}>
                      <Link
                        to={`/events/${event.id}`}
                        className="dashboard-item"
                        style={{ flex: 1, border: 'none', background: 'transparent' }}
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
                      <button
                        type="button"
                        className="btn btn-secondary btn-xs"
                        style={{ fontSize: '0.75rem', padding: '4px 8px', flexShrink: 0 }}
                        onClick={(e) => handleCancelRsvp(event.id, e)}
                        title="Cancel attendance for this event"
                      >
                        Cancel
                      </button>
                    </div>
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
