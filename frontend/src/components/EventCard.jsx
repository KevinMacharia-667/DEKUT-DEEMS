import { Link } from 'react-router-dom';
import { CalendarDays, MapPin } from 'lucide-react';
import './EventCard.css';
import { campusDateParts, formatCampusDateTime } from '../utils/dates';
import { categoryCover, categoryIcon } from '../utils/icons';
import { describeAttendance } from '../utils/attendance';

function formatDate(dateStr) {
  return formatCampusDateTime(dateStr);
}

export default function EventCard({ event }) {
  const CategoryIcon = categoryIcon(event.category);
  const dateParts = campusDateParts(event.start_time);
  const attendance = describeAttendance(event.rsvp_count, event.max_attendees);

  return (
    <Link to={`/events/${event.id}`} className="glass-card event-card">
      <div
        className="event-card-image"
        style={event.image_url ? undefined : { background: categoryCover(event.category) }}
      >
        {event.image_url ? (
          <img src={event.image_url} alt={event.title} />
        ) : (
          <>
            {dateParts && (
              <span className="event-card-date-block" aria-hidden="true">
                <span className="event-card-date-day">{dateParts.day}</span>
                <span className="event-card-date-month">{dateParts.month}</span>
              </span>
            )}
            <CategoryIcon className="event-card-cover-icon" size={22} strokeWidth={1.75} aria-hidden="true" />
          </>
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
            <CalendarDays className="event-card-meta-icon" size={15} aria-hidden="true" />
            {formatDate(event.start_time)}
          </span>
          {event.location && (
            <span className="event-card-meta-item">
              <MapPin className="event-card-meta-icon" size={15} aria-hidden="true" />
              {event.location}
            </span>
          )}
        </div>
      </div>

      <div className="event-card-footer">
        <span className="event-card-attendees">
          {attendance.text}
          {attendance.status && (
            <span className={`event-card-seats-flag ${attendance.status}`}> · {attendance.statusText}</span>
          )}
        </span>
        <span className="event-card-organizer">
          by {event.organizer?.full_name || event.organizer?.username}
        </span>
      </div>
    </Link>
  );
}
