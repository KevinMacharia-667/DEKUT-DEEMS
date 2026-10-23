/**
 * WhatsApp share helper for Tukio events.
 * Constructs deep links targeting https://wa.me/?text=...
 * Uses window.location.origin to link to /events/:id
 */
import { formatCampusDateTime } from './dates.js';

export function formatEventShareDate(dateStr) {
  // Campus time (EAT), e.g. "Mon 27 Oct · 14:30"
  return formatCampusDateTime(dateStr, { fallback: 'TBA' });
}

export function buildWhatsAppShareUrl(event, origin = '') {
  const baseOrigin = origin || (typeof window !== 'undefined' ? window.location.origin : '');
  const eventUrl = event.id ? `${baseOrigin}/events/${event.id}` : '';
  const dateFormatted = formatEventShareDate(event.start_time);

  const lines = [
    'Check out this event on Tukio! 🎉',
    '',
    `📌 *${event.title || 'Campus Event'}*`,
    `📅 ${dateFormatted}`,
    `📍 ${event.location || 'DeKUT Campus'}`,
  ];

  if (eventUrl) {
    lines.push('');
    lines.push(`🔗 ${eventUrl}`);
  }

  const message = lines.join('\n');
  return `https://wa.me/?text=${encodeURIComponent(message)}`;
}

export function openWhatsAppShare(event, origin = '') {
  const url = buildWhatsAppShareUrl(event, origin);
  window.open(url, '_blank', 'noopener,noreferrer');
}
