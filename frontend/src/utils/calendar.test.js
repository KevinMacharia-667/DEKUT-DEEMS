import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  formatICSDateUTC,
  escapeICS,
  getEventDates,
  buildICSContent,
} from './calendar.js';

test('formatICSDateUTC formats UTC date correctly into YYYYMMDDTHHMMSSZ', () => {
  const dt = new Date(Date.UTC(2026, 9, 24, 14, 30, 45)); // Oct 24, 2026
  const formatted = formatICSDateUTC(dt);
  assert.equal(formatted, '20261024T143045Z');
});

test('escapeICS properly escapes commas, semicolons, backslashes and newlines', () => {
  const raw = 'DeKUT, Nyeri; Kenya \\ East Africa\nLine 2\r\nLine 3';
  const escaped = escapeICS(raw);
  assert.equal(escaped, 'DeKUT\\, Nyeri\\; Kenya \\\\ East Africa\\nLine 2\\nLine 3');
});

test('getEventDates uses default 2-hour duration when end_time is null/missing', () => {
  const event = {
    start_time: '2026-10-24T14:00:00',
    end_time: null,
  };
  const { startDate, endDate } = getEventDates(event);
  assert.equal(startDate.toISOString(), '2026-10-24T14:00:00.000Z');
  assert.equal(endDate.toISOString(), '2026-10-24T16:00:00.000Z');
  const durationHours = (endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60);
  assert.equal(durationHours, 2);
});

test('buildICSContent generates valid RFC 5545 .ics with CRLF line endings and fixed dates', () => {
  const event = {
    id: '123e4567-e89b-12d3-a456-426614174000',
    title: 'AI & Robotics, DeKUT; Lab',
    description: 'Autonomous robotics workshop.\nBring laptops.',
    location: 'Computer Lab 3, DeKUT',
    start_time: '2026-10-24T10:00:00',
    end_time: '2026-10-24T13:00:00',
  };

  const ics = buildICSContent(event, 'http://localhost:5173');

  // Strict CRLF line endings
  assert.ok(ics.includes('\r\n'));
  assert.ok(!ics.replace(/\r\n/g, '').includes('\n')); // No naked \n

  // Required RFC 5545 headers
  assert.ok(ics.includes('BEGIN:VCALENDAR\r\n'));
  assert.ok(ics.includes('VERSION:2.0\r\n'));
  assert.ok(ics.includes('PRODID:-//DeKUT Tukio//Event Recommender//EN\r\n'));
  assert.ok(ics.includes('BEGIN:VEVENT\r\n'));
  assert.ok(ics.includes('UID:tukio-123e4567-e89b-12d3-a456-426614174000@dekut.ac.ke\r\n'));
  assert.ok(ics.includes('DTSTAMP:'));
  assert.ok(ics.includes('DTSTART:20261024T100000Z\r\n'));
  assert.ok(ics.includes('DTEND:20261024T130000Z\r\n'));

  // Escaping verification
  assert.ok(ics.includes('SUMMARY:AI & Robotics\\, DeKUT\\; Lab\r\n'));
  assert.ok(ics.includes('DESCRIPTION:Autonomous robotics workshop.\\nBring laptops.\r\n'));
  assert.ok(ics.includes('LOCATION:Computer Lab 3\\, DeKUT\r\n'));
  assert.ok(ics.includes('URL:http://localhost:5173/events/123e4567-e89b-12d3-a456-426614174000\r\n'));
  assert.ok(ics.includes('STATUS:CONFIRMED\r\n'));
  assert.ok(ics.includes('END:VEVENT\r\n'));
  assert.ok(ics.includes('END:VCALENDAR\r\n'));
});
