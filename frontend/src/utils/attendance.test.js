import { test } from 'node:test';
import assert from 'node:assert/strict';
import { describeAttendance } from './attendance.js';
import { campusDateParts } from './dates.js';

test('no capacity shows a plain count', () => {
  assert.deepEqual(describeAttendance(7, null), { text: '7 going', status: null });
  assert.deepEqual(describeAttendance(undefined, 0), { text: '0 going', status: null });
});

test('capacity shows going / capacity', () => {
  assert.deepEqual(describeAttendance(42, 60), { text: '42 / 60 going', status: null });
});

test('"Few seats left" only when under 10% of seats remain', () => {
  // 60 seats: 10% is 6 seats
  assert.equal(describeAttendance(54, 60).status, null); // 6 left: exactly 10%, not under
  assert.deepEqual(describeAttendance(55, 60), {
    text: '55 / 60 going',
    status: 'few',
    statusText: 'Few seats left',
  }); // 5 left
});

test('full when no seats remain', () => {
  assert.deepEqual(describeAttendance(30, 30), { text: '30 / 30 going', status: 'full', statusText: 'Full' });
  assert.equal(describeAttendance(31, 30).status, 'full');
});

test('date parts for the card date block are campus time', () => {
  // 22:00 UTC on the 26th is the 27th in Nairobi
  assert.deepEqual(campusDateParts('2026-10-26T22:00:00'), { day: '27', month: 'Oct' });
  assert.equal(campusDateParts(null), null);
});
