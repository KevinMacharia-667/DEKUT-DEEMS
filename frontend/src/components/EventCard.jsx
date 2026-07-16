import { Link } from 'react-router-dom';
import './EventCard.css';

const CATEGORY_EMOJI = {
  Academic: '📚',
  Social: '🎉',
  Sports: '⚽',
  Workshop: '🔧',
  Cultural: '🎭',
  Tech: '💻',
  Career: '💼',
};

function formatDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function EventCard({ event }) {
  const emoji = CATEGORY_EMOJI[event.category] || '📅';

  return (
    <Link to={`/events/${event.id}`} className="glass-card event-card">
      <div className="event-card-image">
        {event.image_url ? (
          <img src={event.image_url} alt={event.title} />
        ) : (
          <span>{emoji}</span>
        )}
        {event.category && (
          <span className="badge badge-accent event-card-category">
            {event.category}
          </span>
        )}
      </div>

      <div className="event-card-body">
        <h3 className="event-card-title">{event.title}</h3>

        <div className="event-card-meta">
          <span className="event-card-meta-item">
            <span className="event-card-meta-icon">📅</span>
            {formatDate(event.start_time)}
          </span>
          {event.location && (
            <span className="event-card-meta-item">
              <span className="event-card-meta-icon">📍</span>
              {event.location}
            </span>
          )}
        </div>
      </div>

      <div className="event-card-footer">
        <span className="event-card-attendees">
          {event.rsvp_count} {event.rsvp_count === 1 ? 'attendee' : 'attendees'}
        </span>
        <span className="event-card-organizer">
          by {event.organizer?.full_name || event.organizer?.username}
        </span>
      </div>
    </Link>
  );
}
