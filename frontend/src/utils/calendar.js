/**
 * iCalendar (.ics) generator utility for Tukio.
 * RFC 5545 compliant:
 * - VERSION:2.0, PRODID, UID, DTSTAMP
 * - Strict \r\n (CRLF) line endings
 * - Escaped characters (commas, semicolons, backslashes, newlines)
 * - UTC timestamps ending in 'Z'
 * - Default 2-hour duration if end_time is null/missing
 */

export function parseEventDate(dateStr) {
  if (!dateStr) return null;
  if (dateStr instanceof Date) return dateStr;
  const s = String(dateStr);
  const hasTimezone = s.endsWith('Z') || /[+-]\d{2}(:?\d{2})?$/.test(s);
  return new Date(hasTimezone ? s : `${s}Z`);
}

export function formatICSDateUTC(date) {
  const pad = (n) => String(n).padStart(2, '0');
  const year = date.getUTCFullYear();
  const month = pad(date.getUTCMonth() + 1);
  const day = pad(date.getUTCDate());
  const hours = pad(date.getUTCHours());
  const mins = pad(date.getUTCMinutes());
  const secs = pad(date.getUTCSeconds());
  return `${year}${month}${day}T${hours}${mins}${secs}Z`;
}

export function escapeICS(str) {
  if (!str) return '';
  return String(str)
    .replace(/\\/g, '\\\\')
    .replace(/;/g, '\\;')
    .replace(/,/g, '\\,')
    .replace(/\r\n|\n|\r/g, '\\n');
}

export function getEventDates(event) {
  const startDate = parseEventDate(event.start_time) || new Date();
  let endDate = parseEventDate(event.end_time);
  if (!endDate || isNaN(endDate.getTime()) || endDate <= startDate) {
    // Default duration: 2 hours if end_time is missing or invalid
    endDate = new Date(startDate.getTime() + 2 * 60 * 60 * 1000);
  }
  return { startDate, endDate };
}

export function buildICSContent(event, origin = '') {
  const { startDate, endDate } = getEventDates(event);
  const dtstamp = formatICSDateUTC(new Date());
  const dtstart = formatICSDateUTC(startDate);
  const dtend = formatICSDateUTC(endDate);

  const uid = `tukio-${event.id || 'event'}@dekut.ac.ke`;
  const summary = escapeICS(event.title || 'Campus Event');
  const description = escapeICS(event.description || '');
  const location = escapeICS(event.location || 'DeKUT Campus');
  const eventUrl = origin && event.id ? `${origin}/events/${event.id}` : '';

  const lines = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//DeKUT Tukio//Event Recommender//EN',
    'CALSCALE:GREGORIAN',
    'METHOD:PUBLISH',
    'BEGIN:VEVENT',
    `UID:${uid}`,
    `DTSTAMP:${dtstamp}`,
    `DTSTART:${dtstart}`,
    `DTEND:${dtend}`,
    `SUMMARY:${summary}`,
    `DESCRIPTION:${description}`,
    `LOCATION:${location}`,
  ];

  if (eventUrl) {
    lines.push(`URL:${eventUrl}`);
  }

  lines.push('STATUS:CONFIRMED');
  lines.push('END:VEVENT');
  lines.push('END:VCALENDAR');

  return lines.join('\r\n') + '\r\n';
}

export function downloadEventICS(event, origin = '') {
  const icsContent = buildICSContent(event, origin);
  const blob = new Blob([icsContent], { type: 'text/calendar;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  const filename = (event.title || 'tukio-event')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  link.download = `${filename || 'event'}.ics`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
