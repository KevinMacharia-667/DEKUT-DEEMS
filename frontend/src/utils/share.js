/**
 * WhatsApp share helper for Tukio events.
 * Constructs deep links targeting https://wa.me/?text=...
 * Uses window.location.origin to link to /events/:id
 */

export function formatEventShareDate(dateStr) {
  if (!dateStr) return 'TBA';
  const hasTimezone = String(dateStr).endsWith('Z') || /[+-]\d{2}(:?\d{2})?$/.test(String(dateStr));
  const date = new Date(hasTimezone ? dateStr : `${dateStr}Z`);
  if (isNaN(date.getTime())) return 'TBA';

  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
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
