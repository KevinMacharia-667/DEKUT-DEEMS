import { useState } from 'react';
import { Link } from 'react-router-dom';
import './TukioCard.css';
import {
  parseApiDate,
  campusDayDiff,
  campusWeekdayAndHour,
  formatCampusTime,
  formatCampusDate,
} from '../utils/dates';

const CATEGORY_STYLES = {
  Academic: {
    gradient: 'linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%)',
    emoji: '📚',
  },
  Tech: {
    gradient: 'linear-gradient(135deg, #064e3b 0%, #10b981 100%)',
    emoji: '💻',
  },
  Social: {
    gradient: 'linear-gradient(135deg, #78350f 0%, #f59e0b 100%)',
    emoji: '🎉',
  },
  Sports: {
    gradient: 'linear-gradient(135deg, #7f1d1d 0%, #ef4444 100%)',
    emoji: '⚽',
  },
  Workshop: {
    gradient: 'linear-gradient(135deg, #4c1d95 0%, #8b5cf6 100%)',
    emoji: '🔧',
  },
  Cultural: {
    gradient: 'linear-gradient(135deg, #701a75 0%, #ec4899 100%)',
    emoji: '🎭',
  },
  Career: {
    gradient: 'linear-gradient(135deg, #134e4a 0%, #14b8a6 100%)',
    emoji: '💼',
  },
};

function formatEventTime(dateStr) {
  const eventDate = parseApiDate(dateStr);
  if (!eventDate) return { formatted: 'Date TBA', statusBadge: null, deltaDays: null };

  const now = new Date();
  // Calendar days in campus time (Africa/Nairobi), whatever the device timezone
  const dayDiff = campusDayDiff(now, eventDate);
  const isToday = dayDiff === 0;
  const isTomorrow = dayDiff === 1;

  const timeString = formatCampusTime(eventDate);

  const deltaDays = Math.ceil((eventDate - now) / (1000 * 60 * 60 * 24));
  const { weekday: dayOfWeek, hour } = campusWeekdayAndHour(eventDate); // 0: Sun, 5: Fri, 6: Sat
  const isWeekend =
    (dayOfWeek === 6 || dayOfWeek === 0 || (dayOfWeek === 5 && hour >= 17)) &&
    deltaDays >= 0 &&
    deltaDays <= 6;

  if (isToday) {
    return {
      formatted: `Today · ${timeString}`,
      statusBadge: 'Today',
      isToday: true,
      isWeekend,
      deltaDays,
    };
  }

  if (isTomorrow) {
    return {
      formatted: `Tomorrow · ${timeString}`,
      statusBadge: isWeekend ? 'Tomorrow (Weekend)' : 'Tomorrow',
      isToday: false,
      isWeekend,
      deltaDays,
    };
  }

  if (isWeekend) {
    const dayName = formatCampusDate(eventDate).split(' ')[0];
    return {
      formatted: `This Weekend (${dayName}) · ${timeString}`,
      statusBadge: `🌴 Weekend • ${dayName}`,
      isToday: false,
      isWeekend: true,
      deltaDays,
    };
  }

  const dateString = formatCampusDate(eventDate);

  return {
    formatted: `${dateString} · ${timeString}`,
    statusBadge: dateString,
    isToday: false,
    isWeekend: false,
    deltaDays,
  };
}

export function TukioSkeletonCard() {
  return (
    <div className="tukio-card tukio-skeleton-card">
      <div className="tukio-skeleton-box tukio-skeleton-img" />
      <div className="tukio-card-body">
        <div className="tukio-skeleton-box tukio-skeleton-title" />
        <div className="tukio-skeleton-box tukio-skeleton-meta" />
        <div className="tukio-skeleton-box tukio-skeleton-text" />
        <div className="tukio-skeleton-box tukio-skeleton-text" style={{ width: '65%' }} />
      </div>
      <div className="tukio-card-footer">
        <div className="tukio-skeleton-box tukio-skeleton-btn" />
      </div>
    </div>
  );
}

/**
 * "Up next" list shown beside the card on wide screens: the next few events in
 * the deck, each jumping straight to its card when clicked.
 */
export function TukioUpNext({ events, currentIndex, onSelect, limit = 5 }) {
  const upcoming = events
    .map((event, index) => ({ event, index }))
    .slice(currentIndex + 1, currentIndex + 1 + limit);
  if (upcoming.length === 0) return null;

  return (
    <aside className="tukio-up-next" aria-label="Up next">
      <h3 className="tukio-up-next-title">Up next</h3>
      <ul className="tukio-up-next-list">
        {upcoming.map(({ event, index }) => {
          const style = CATEGORY_STYLES[event.category] || { emoji: '📌' };
          return (
            <li key={event.id}>
              <button type="button" className="tukio-up-next-item" onClick={() => onSelect(index)}>
                <span className="tukio-up-next-emoji" aria-hidden="true">{style.emoji}</span>
                <span className="tukio-up-next-text">
                  <span className="tukio-up-next-name">{event.title}</span>
                  <span className="tukio-up-next-when">{formatEventTime(event.start_time).formatted}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
      {events.length > currentIndex + 1 + limit && (
        <p className="tukio-up-next-more">+{events.length - currentIndex - 1 - limit} more in this feed</p>
      )}
    </aside>
  );
}

export default function TukioCard({
  event,
  recommendation = null,
  isAttending = false,
  isInterested = false,
  onRsvpToggle,
  onFeedback,
  feedbackLoading = false,
  onShare,
  onAddToCalendar,
  isAuthenticated = false,
  rsvpLoading = false,
  isDragging = false,
  dragOffset = { x: 0, y: 0 },
  transitionClass = '',
}) {
  const [descExpanded, setDescExpanded] = useState(false);
  const [showWhyModal, setShowWhyModal] = useState(false);
  const [imgLoaded, setImgLoaded] = useState(false);

  if (!event) return null;

  const catStyle = CATEGORY_STYLES[event.category] || {
    gradient: 'linear-gradient(135deg, #1f2937 0%, #4b5563 100%)',
    emoji: '📅',
  };

  const { formatted: formattedDate, statusBadge, isToday, isWeekend, deltaDays } = formatEventTime(event.start_time);

  // Dynamic drag transform
  const cardStyle = isDragging
    ? {
        transform: `translate3d(${dragOffset.x}px, ${dragOffset.y}px, 0) rotate(${dragOffset.x * 0.04}deg)`,
      }
    : undefined;

  const attendeeCount = event.rsvp_count ?? 0;
  const organizerName =
    event.organizer?.full_name || event.organizer?.username || 'Campus Organizer';

  // Recommendation signals resolution
  const hasEngineSignal = Boolean(recommendation);
  const matchScore = recommendation?.score ? Math.min(99, Math.round(Number(recommendation.score) * 100)) : null;

  let whyBadge = recommendation?.badge;
  let whyReasons = recommendation?.reasons || [];

  if (!hasEngineSignal) {
    if (attendeeCount >= 5) {
      whyBadge = '🔥 Trending on Campus';
      whyReasons = [
        `${attendeeCount} students attending`,
        'Popular with students this week',
      ];
    } else if (deltaDays !== null && deltaDays >= 0 && deltaDays <= 3) {
      whyBadge = '⚡ Happening Soon';
      whyReasons = [
        `Starts in ${deltaDays === 0 ? 'a few hours' : `${deltaDays} days`}`,
        'Open to all DeKUT students',
      ];
    } else {
      whyBadge = '📌 Recommended';
      whyReasons = [
        `Campus event in ${event.category || 'General'}`,
        'Discover activities happening at DeKUT',
      ];
    }
  }

  return (
    <div
      className={`tukio-card ${isDragging ? 'dragging' : ''} ${transitionClass}`.trim()}
      style={cardStyle}
    >
      {/* ── Top Media / Image Header ────────────────────────────── */}
      <div className="tukio-card-media">
        {event.image_url ? (
          <>
            {!imgLoaded && <div className="tukio-card-img-placeholder" />}
            <img
              src={event.image_url}
              alt={event.title}
              className={`tukio-card-img ${imgLoaded ? 'loaded' : ''}`}
              loading="lazy"
              onLoad={() => setImgLoaded(true)}
            />
          </>
        ) : (
          <div
            className="tukio-card-fallback-media"
            style={{ background: catStyle.gradient }}
          >
            <span className="tukio-card-fallback-emoji" role="img" aria-label={event.category}>
              {catStyle.emoji}
            </span>
          </div>
        )}

        <div className="tukio-card-gradient-overlay" />

        <div className="tukio-card-top-badges">
          <span className="tukio-badge-category">
            {event.category || 'Event'}
          </span>
          {statusBadge && (
            <span
              className={`tukio-badge-time-status ${
                isToday ? 'today' : isWeekend ? 'weekend' : ''
              }`}
            >
              {statusBadge}
            </span>
          )}
        </div>
      </div>

      {/* ── Card Main Body ──────────────────────────────────────── */}
      <div className="tukio-card-body">
        <div className="tukio-card-title-row">
          <h2 className="tukio-card-title">{event.title}</h2>
          <span className="tukio-card-organizer">by {organizerName}</span>
        </div>

        {/* ── Why Recommended Chip ──────────────────────────────── */}
        <div className="tukio-why-chip-container">
          <button
            type="button"
            className="tukio-why-chip"
            onClick={() => setShowWhyModal(true)}
            aria-label="Why this event is recommended"
          >
            <span className="tukio-why-chip-icon">✨</span>
            <span className="tukio-why-chip-badge">{whyBadge}</span>
            {matchScore !== null && matchScore > 0 && (
              <span className="tukio-why-chip-score">{matchScore}%</span>
            )}
            <span className="tukio-why-chip-info">ⓘ</span>
          </button>
        </div>

        {/* Date, Venue & Attendee Meta Box */}
        <div className="tukio-card-meta">
          <div className="tukio-meta-item">
            <span className="tukio-meta-icon">📅</span>
            <span className="tukio-meta-text">{formattedDate}</span>
          </div>
          {event.location && (
            <div className="tukio-meta-item">
              <span className="tukio-meta-icon">📍</span>
              <span className="tukio-meta-text">{event.location}</span>
            </div>
          )}
          <div className="tukio-meta-item">
            <span className="tukio-meta-icon">👥</span>
            <span className="tukio-meta-text">
              {attendeeCount} {attendeeCount === 1 ? 'attendee' : 'attendees'}
              {event.max_attendees ? ` • limit ${event.max_attendees}` : ''}
            </span>
          </div>
        </div>

        {/* Description snippet */}
        {event.description && (
          <div className="tukio-card-desc-wrap">
            <p className={`tukio-card-description ${descExpanded ? '' : 'clamped'}`}>
              {event.description}
            </p>
            {event.description.length > 100 && (
              <button
                type="button"
                className="tukio-expand-desc-btn"
                onClick={() => setDescExpanded(!descExpanded)}
              >
                {descExpanded ? 'Show less' : 'Read more'}
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Sticky Action Footer ────────────────────────────────── */}
      <div className="tukio-card-footer">
        {/* Quick Feedback Row (Interested / Not for me) — Hidden for guests */}
        {isAuthenticated && (
          <div className="tukio-feedback-row">
            {!isAttending && (
              <button
                type="button"
                className={`tukio-feedback-btn interested ${isInterested ? 'active' : ''}`}
                onClick={() => onFeedback?.(event, 'interested')}
                disabled={feedbackLoading}
                aria-pressed={isInterested}
                title={isInterested ? 'Remove from Interested' : 'Mark as Interested'}
              >
                <span className="tukio-feedback-icon">{isInterested ? '⭐' : '👍'}</span>
                <span>{isInterested ? 'Interested' : 'Interested'}</span>
              </button>
            )}

            <button
              type="button"
              className="tukio-feedback-btn not-for-me"
              onClick={() => onFeedback?.(event, 'not_for_me')}
              disabled={feedbackLoading}
              title="Not for me (dismiss event)"
              aria-label="Not for me"
            >
              <span className="tukio-feedback-icon">👎</span>
              <span>Not for me</span>
            </button>
          </div>
        )}

        {/* Compact Share & Calendar Utility Row */}
        <div className="tukio-card-utility-row">
          <button
            type="button"
            className="tukio-utility-btn whatsapp"
            onClick={(e) => {
              e.stopPropagation();
              onShare?.(event);
            }}
            title="Share via WhatsApp"
            aria-label="Share via WhatsApp"
          >
            <span className="tukio-utility-icon" role="img" aria-label="WhatsApp">💬</span>
            <span>WhatsApp</span>
          </button>

          <button
            type="button"
            className="tukio-utility-btn calendar"
            onClick={(e) => {
              e.stopPropagation();
              onAddToCalendar?.(event);
            }}
            title="Add to Calendar (.ics)"
            aria-label="Add to Calendar"
          >
            <span className="tukio-utility-icon" role="img" aria-label="Calendar">📅</span>
            <span>Calendar</span>
          </button>
        </div>

        <div className="tukio-card-cta-row">
          <button
            type="button"
            className={`tukio-rsvp-btn ${isAttending ? 'attending' : ''}`}
            onClick={() => onRsvpToggle?.(event)}
            disabled={rsvpLoading}
            aria-label={isAttending ? 'Cancel RSVP' : 'One tap RSVP'}
          >
            {rsvpLoading ? (
              <span className="tukio-micro-spinner" />
            ) : isAttending ? (
              <>
                <span>✓</span> Attending
              </>
            ) : (
              <>
                <span>✨</span> RSVP Now
              </>
            )}
          </button>

          <Link
            to={`/events/${event.id}`}
            className="tukio-details-link-btn"
            title="View Full Event Details"
          >
            Details ↗
          </Link>
        </div>
      </div>

      {/* ── Why Recommended Explanation Sheet / Modal ────────────── */}
      {showWhyModal && (
        <div className="tukio-why-overlay" onClick={() => setShowWhyModal(false)}>
          <div className="tukio-why-sheet" onClick={(e) => e.stopPropagation()}>
            <div className="tukio-why-sheet-header">
              <span className="tukio-why-sheet-title">
                <span>✨</span> Why Recommended
              </span>
              <button
                type="button"
                className="tukio-why-sheet-close"
                onClick={() => setShowWhyModal(false)}
                aria-label="Close"
              >
                ✕
              </button>
            </div>

            {/* Match score bar */}
            {matchScore !== null && matchScore > 0 ? (
              <div className="tukio-why-meter-row">
                <div className="tukio-why-meter-top">
                  <span className="tukio-why-meter-label">Recommender Match</span>
                  <span className="tukio-why-meter-percent">{matchScore}%</span>
                </div>
                <div className="tukio-why-bar-bg">
                  <div
                    className="tukio-why-bar-fill"
                    style={{ width: `${matchScore}%` }}
                  />
                </div>
              </div>
            ) : (
              <p className="tukio-why-guest-prompt">
                Based on campus popularity, faculty schedule, and category engagement.
              </p>
            )}

            {/* Signals breakdown */}
            <div className="tukio-why-reasons-wrap">
              <span className="tukio-why-reasons-title">Signals Detected</span>
              <ul className="tukio-why-reasons-list">
                {whyReasons.map((reason, idx) => (
                  <li key={idx} className="tukio-why-reason-item">
                    <span className="tukio-why-reason-bullet">✓</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
