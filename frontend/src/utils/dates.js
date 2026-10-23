/**
 * Event date helpers.
 *
 * The API stores and returns times in UTC without a timezone suffix
 * (e.g. "2026-10-23T19:22:25"). Read as-is, browsers treat such strings as
 * local time, which showed every event 3 hours early in Kenya. These helpers
 * parse API times as UTC and display them in campus time (Africa/Nairobi),
 * whatever timezone the viewer's device is set to.
 *
 * Nairobi is UTC+3 all year (no daylight saving), so campus wall-clock values
 * can be derived with a fixed offset.
 */

export const CAMPUS_TZ = 'Africa/Nairobi';
const CAMPUS_OFFSET_MS = 3 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

/** Parse an API datetime (naive values are UTC). Returns a Date, or null if missing/invalid. */
export function parseApiDate(value) {
  if (!value) return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  const s = String(value);
  const hasTimezone = s.endsWith('Z') || /[+-]\d{2}(:?\d{2})?$/.test(s);
  const date = new Date(hasTimezone ? s : `${s}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

/** The campus wall-clock time as a Date whose UTC fields hold the Nairobi values. */
function campusClock(date) {
  return new Date(date.getTime() + CAMPUS_OFFSET_MS);
}

/** Whole calendar days from `from` to `to`, counted in campus time (0 = same day). */
export function campusDayDiff(from, to) {
  const a = campusClock(from);
  const b = campusClock(to);
  const dayA = Date.UTC(a.getUTCFullYear(), a.getUTCMonth(), a.getUTCDate());
  const dayB = Date.UTC(b.getUTCFullYear(), b.getUTCMonth(), b.getUTCDate());
  return Math.round((dayB - dayA) / DAY_MS);
}

/** Day of week (0 = Sunday) and hour in campus time. */
export function campusWeekdayAndHour(date) {
  const c = campusClock(date);
  return { weekday: c.getUTCDay(), hour: c.getUTCHours() };
}

const timeFormat = new Intl.DateTimeFormat('en-GB', {
  timeZone: CAMPUS_TZ,
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

function dateParts(date, { long = false, withYear = false } = {}) {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: CAMPUS_TZ,
    weekday: long ? 'long' : 'short',
    day: 'numeric',
    month: long ? 'long' : 'short',
    ...(withYear ? { year: 'numeric' } : {}),
  }).formatToParts(date);
  const get = (type) => parts.find((p) => p.type === type)?.value ?? '';
  return [get('weekday'), get('day'), get('month'), withYear ? get('year') : '']
    .filter(Boolean)
    .join(' ');
}

/** "14:30" in campus time. */
export function formatCampusTime(value) {
  const date = parseApiDate(value);
  return date ? timeFormat.format(date) : '';
}

/** "Mon 27 Oct" (or "Monday 27 October 2026" with long + withYear) in campus time. */
export function formatCampusDate(value, options = {}) {
  const date = parseApiDate(value);
  return date ? dateParts(date, options) : '';
}

/** "Mon 27 Oct · 14:30" in campus time; `fallback` when the value is missing. */
export function formatCampusDateTime(value, { fallback = 'Date TBA', ...options } = {}) {
  const date = parseApiDate(value);
  if (!date) return fallback;
  return `${dateParts(date, options)} · ${timeFormat.format(date)}`;
}

/** API datetime -> "YYYY-MM-DDTHH:mm" for a datetime-local input, in campus time. */
export function toCampusInputValue(value) {
  const date = parseApiDate(value);
  if (!date) return '';
  return campusClock(date).toISOString().slice(0, 16);
}

/** "YYYY-MM-DDTHH:mm" entered as campus time -> UTC ISO string for the API (null if empty). */
export function campusInputToISO(inputValue) {
  if (!inputValue) return null;
  const date = new Date(`${inputValue}:00+03:00`);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}
