import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  parseApiDate,
  campusDayDiff,
  campusWeekdayAndHour,
  formatCampusTime,
  formatCampusDate,
  formatCampusDateTime,
  toCampusInputValue,
  campusInputToISO,
} from './dates.js';

test('naive API times are read as UTC', () => {
  assert.equal(parseApiDate('2026-10-23T19:22:25').toISOString(), '2026-10-23T19:22:25.000Z');
  assert.equal(parseApiDate('2026-10-23T19:22:25Z').toISOString(), '2026-10-23T19:22:25.000Z');
  assert.equal(parseApiDate('2026-10-23T22:22:25+03:00').toISOString(), '2026-10-23T19:22:25.000Z');
  assert.equal(parseApiDate(null), null);
  assert.equal(parseApiDate('not a date'), null);
});

test('display is campus time (UTC+3), 24-hour, British order', () => {
  // 19:22 UTC is 22:22 in Nairobi: the bug showed this as 7:22 PM
  assert.equal(formatCampusTime('2026-10-23T19:22:25'), '22:22');
  assert.equal(formatCampusDateTime('2026-10-27T11:30:00'), 'Tue 27 Oct · 14:30');
  assert.equal(formatCampusDate('2026-10-27T11:30:00'), 'Tue 27 Oct');
  assert.equal(
    formatCampusDate('2026-10-27T11:30:00', { long: true, withYear: true }),
    'Tuesday 27 October 2026'
  );
  assert.equal(formatCampusDateTime(null), 'Date TBA');
  assert.equal(formatCampusDateTime('', { fallback: '—' }), '—');
});

test('late-evening UTC times roll over to the next campus day', () => {
  // 22:00 UTC Monday is 01:00 Tuesday in Nairobi
  assert.equal(formatCampusDateTime('2026-10-26T22:00:00'), 'Tue 27 Oct · 01:00');
  const { weekday, hour } = campusWeekdayAndHour(parseApiDate('2026-10-26T22:00:00'));
  assert.equal(weekday, 2);
  assert.equal(hour, 1);
});

test('campusDayDiff counts calendar days in campus time', () => {
  const now = parseApiDate('2026-10-23T20:30:00'); // 23:30 Fri in Nairobi
  assert.equal(campusDayDiff(now, parseApiDate('2026-10-23T20:45:00')), 0); // 23:45 same day
  assert.equal(campusDayDiff(now, parseApiDate('2026-10-23T21:30:00')), 1); // 00:30 Sat
  assert.equal(campusDayDiff(now, parseApiDate('2026-10-20T08:00:00')), -3);
});

test('datetime-local round trip keeps the same instant', () => {
  const api = '2026-10-23T19:22:00';
  const input = toCampusInputValue(api);
  assert.equal(input, '2026-10-23T22:22');
  assert.equal(campusInputToISO(input), '2026-10-23T19:22:00.000Z');
  assert.equal(campusInputToISO(''), null);
  assert.equal(toCampusInputValue(null), '');
});
