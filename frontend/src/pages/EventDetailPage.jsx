import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getEvent, getAttendees, rsvpToEvent, cancelRsvp, deleteEvent } from '../api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import './EventDetailPage.css';

const CATEGORY_EMOJI = {
  Academic: '📚', Social: '🎉', Sports: '⚽', Workshop: '🔧',
  Cultural: '🎭', Tech: '💻', Career: '💼',
};

function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export default function EventDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, isAuthenticated } = useAuth();
  const toast = useToast();

  const [event, setEvent] = useState(null);
  const [attendees, setAttendees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [rsvpLoading, setRsvpLoading] = useState(false);

  const isOwner = user && event?.organizer?.id === user.id;
  const isAdmin = user?.role === 'admin';
  const hasRsvpd = attendees.some((a) => a.user?.id === user?.id);

  useEffect(() => {
    Promise.all([getEvent(id), getAttendees(id)])
      .then(([eventData, attendeesData]) => {
        setEvent(eventData);
        setAttendees(attendeesData);
      })
      .catch(() => {
        toast.error('Event not found');
        navigate('/events');
      })
      .finally(() => setLoading(false));
  }, [id]);

  async function handleRsvp() {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    setRsvpLoading(true);
    try {
      await rsvpToEvent(id);
      toast.success("You're attending this event!");
      // Refresh attendees
      const updated = await getAttendees(id);
      setAttendees(updated);
      setEvent((prev) => ({ ...prev, rsvp_count: updated.length }));
    } catch (err) {
      toast.error(err.message || 'Failed to RSVP');
    } finally {
      setRsvpLoading(false);
    }
  }

  async function handleCancelRsvp() {
    setRsvpLoading(true);
    try {
      await cancelRsvp(id);
      toast.info('RSVP cancelled');
      const updated = await getAttendees(id);
      setAttendees(updated);
      setEvent((prev) => ({ ...prev, rsvp_count: updated.length }));
    } catch (err) {
      toast.error(err.message || 'Failed to cancel RSVP');
    } finally {
      setRsvpLoading(false);
    }
  }

  async function handleDelete() {
    if (!window.confirm('Are you sure you want to delete this event?')) return;
    try {
      await deleteEvent(id);
      toast.success('Event deleted');
      navigate('/events');
    } catch (err) {
      toast.error(err.message || 'Failed to delete event');
    }
  }

  if (loading) {
    return <div className="page"><div className="loading-page"><div className="spinner" /></div></div>;
  }

  if (!event) return null;

  const emoji = CATEGORY_EMOJI[event.category] || '📅';

  return (
    <div className="page">
      <div className="container event-detail">
        {/* Hero */}
        <div className="event-detail-hero glass-card">
          {event.image_url ? (
            <img src={event.image_url} alt={event.title} />
          ) : (
            <span>{emoji}</span>
          )}
        </div>

        {/* Header */}
        <div className="event-detail-header">
          <div className="event-detail-badges">
            {event.category && <span className="badge badge-accent">{event.category}</span>}
            {!event.is_published && <span className="badge badge-gold">Draft</span>}
            {event.tags && event.tags.split(',').map((tag) => (
              <span key={tag.trim()} className="badge badge-muted">{tag.trim()}</span>
            ))}
          </div>
          <h1>{event.title}</h1>
          <p className="event-detail-organizer">
            Organized by <strong>{event.organizer?.full_name || event.organizer?.username}</strong>
          </p>
        </div>

        {/* Meta cards */}
        <div className="event-detail-meta">
          <div className="glass-card event-meta-card">
            <div className="event-meta-icon">📅</div>
            <div className="event-meta-info">
              <h4>Starts</h4>
              <p>{formatDateTime(event.start_time)}</p>
            </div>
          </div>
          {event.end_time && (
            <div className="glass-card event-meta-card">
              <div className="event-meta-icon">🏁</div>
              <div className="event-meta-info">
                <h4>Ends</h4>
                <p>{formatDateTime(event.end_time)}</p>
              </div>
            </div>
          )}
          {event.location && (
            <div className="glass-card event-meta-card">
              <div className="event-meta-icon">📍</div>
              <div className="event-meta-info">
                <h4>Location</h4>
                <p>{event.location}</p>
              </div>
            </div>
          )}
          <div className="glass-card event-meta-card">
            <div className="event-meta-icon">👥</div>
            <div className="event-meta-info">
              <h4>Attendees</h4>
              <p>
                {event.rsvp_count}
                {event.max_attendees ? ` / ${event.max_attendees}` : ''}
              </p>
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="event-detail-actions">
          {hasRsvpd ? (
            <button
              className="btn btn-secondary btn-lg"
              onClick={handleCancelRsvp}
              disabled={rsvpLoading}
            >
              {rsvpLoading ? <span className="spinner" /> : '✓ Attending — Cancel'}
            </button>
          ) : (
            <button
              className="btn btn-primary btn-lg"
              onClick={handleRsvp}
              disabled={rsvpLoading}
            >
              {rsvpLoading ? <span className="spinner" /> : 'RSVP to this event'}
            </button>
          )}
          {(isOwner || isAdmin) && (
            <button className="btn btn-danger" onClick={handleDelete}>
              Delete Event
            </button>
          )}
        </div>

        {/* Description */}
        {event.description && (
          <div className="event-detail-description">
            <h2>About this event</h2>
            <p>{event.description}</p>
          </div>
        )}

        {/* Attendees */}
        <div className="event-detail-attendees">
          <h2>Attendees ({attendees.length})</h2>
          {attendees.length === 0 ? (
            <p style={{ fontSize: '0.9rem', marginTop: '8px' }}>No one has RSVP&apos;d yet. Be the first!</p>
          ) : (
            <div className="attendees-list">
              {attendees.map((a) => (
                <span key={a.rsvp_id} className="attendee-chip">
                  <span className="attendee-chip-avatar">
                    {a.user?.full_name?.[0]?.toUpperCase() || a.user?.username?.[0]?.toUpperCase()}
                  </span>
                  {a.user?.full_name || a.user?.username}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
