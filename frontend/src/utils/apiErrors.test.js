import { test } from 'node:test';
import assert from 'node:assert/strict';
import {
  describeApiError,
  describeNetworkFailure,
  SERVER_UNREACHABLE_MESSAGE,
  OFFLINE_MESSAGE,
} from './apiErrors.js';

test('string detail from the API is shown as-is', () => {
  assert.equal(describeApiError(400, { detail: 'Event is full' }), 'Event is full');
});

test('FastAPI validation list becomes "field: message"', () => {
  const data = { detail: [{ loc: ['body', 'email'], msg: 'value is not a valid email address', type: 'value_error' }] };
  assert.equal(describeApiError(422, data), 'email: value is not a valid email address');
});

test('non-JSON or 5xx responses get the friendly server message', () => {
  assert.equal(describeApiError(502, null), SERVER_UNREACHABLE_MESSAGE);
  assert.equal(describeApiError(500, { detail: '' }), SERVER_UNREACHABLE_MESSAGE);
  assert.equal(describeApiError(404, null), SERVER_UNREACHABLE_MESSAGE);
});

test('other client errors without detail get a generic message', () => {
  assert.equal(describeApiError(403, {}), 'Something went wrong. Please try again.');
});

test('network failures distinguish offline from server down', () => {
  assert.equal(describeNetworkFailure(false), OFFLINE_MESSAGE);
  assert.equal(describeNetworkFailure(true), SERVER_UNREACHABLE_MESSAGE);
  assert.equal(describeNetworkFailure(undefined), SERVER_UNREACHABLE_MESSAGE);
});
