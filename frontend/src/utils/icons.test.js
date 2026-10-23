import { test } from 'node:test';
import assert from 'node:assert/strict';
import { CalendarDays, Flame, GraduationCap, Laptop, Pin, Sparkles, Zap } from 'lucide-react';
import { categoryIcon, splitBadge } from './icons.js';

test('categories map to icons, unknown falls back to a calendar', () => {
  assert.equal(categoryIcon('Tech'), Laptop);
  assert.equal(categoryIcon('Nonsense'), CalendarDays);
  assert.equal(categoryIcon(undefined), CalendarDays);
});

test('backend badges lose their emoji and get a matching icon', () => {
  assert.deepEqual(splitBadge('\u{1F525} Trending on Campus'), { Icon: Flame, label: 'Trending on Campus' });
  assert.deepEqual(splitBadge('\u26a1 Happening Soon'), { Icon: Zap, label: 'Happening Soon' });
  assert.deepEqual(splitBadge('\u{1F393} Faculty Pick'), { Icon: GraduationCap, label: 'Faculty Pick' });
  assert.deepEqual(splitBadge('\u2728 For You'), { Icon: Sparkles, label: 'For You' });
  assert.deepEqual(splitBadge('Something new'), { Icon: Pin, label: 'Something new' });
  assert.deepEqual(splitBadge(null), { Icon: Pin, label: '' });
});
