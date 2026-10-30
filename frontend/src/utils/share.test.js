import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildWhatsAppShareUrl } from './share.js';

const event = { id: 'abc', title: 'AI & Ethics Panel', start_time: '2026-10-27T11:30:00', location: 'Library Auditorium' };

test('share link goes to api.whatsapp.com, not the wa.me redirect that breaks emoji', () => {
  const url = new URL(buildWhatsAppShareUrl(event, 'https://tukio.example.com'));
  assert.equal(url.origin, 'https://api.whatsapp.com');
  assert.equal(url.pathname, '/send');
});

test('message keeps emoji, campus time and the event link intact', () => {
  const text = new URL(buildWhatsAppShareUrl(event, 'https://tukio.example.com')).searchParams.get('text');
  assert.ok(!text.includes('\uFFFD'), 'no replacement characters');
  assert.ok(text.includes('🎉') && text.includes('📌') && text.includes('🔗'));
  assert.ok(text.includes('*AI & Ethics Panel*'));
  assert.ok(text.includes('Tue 27 Oct · 14:30'));
  assert.ok(text.includes('https://tukio.example.com/events/abc'));
});
