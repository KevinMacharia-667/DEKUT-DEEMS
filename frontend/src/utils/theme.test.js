import { test } from 'node:test';
import assert from 'node:assert/strict';
import { getInitialTheme, saveThemePreference } from './theme.js';

test('getInitialTheme returns stored theme from localStorage if valid', () => {
  const originalLocalStorage = globalThis.localStorage;
  globalThis.localStorage = {
    getItem: (key) => (key === 'tukio_theme' ? 'dark' : null),
  };

  try {
    const theme = getInitialTheme();
    assert.equal(theme, 'dark');
  } finally {
    globalThis.localStorage = originalLocalStorage;
  }
});

test('getInitialTheme falls back gracefully when localStorage throws', () => {
  const originalLocalStorage = globalThis.localStorage;
  globalThis.localStorage = {
    getItem: () => {
      throw new Error('SecurityError: Access Denied');
    },
  };

  try {
    const theme = getInitialTheme();
    assert.ok(theme === 'light' || theme === 'dark');
  } finally {
    globalThis.localStorage = originalLocalStorage;
  }
});

test('getInitialTheme checks prefers-color-scheme when no storage entry exists', () => {
  const originalLocalStorage = globalThis.localStorage;
  const originalWindow = globalThis.window;

  globalThis.localStorage = {
    getItem: () => null,
  };
  globalThis.window = {
    matchMedia: (query) => ({
      matches: query.includes('dark'),
    }),
  };

  try {
    const theme = getInitialTheme();
    assert.equal(theme, 'dark');
  } finally {
    globalThis.localStorage = originalLocalStorage;
    globalThis.window = originalWindow;
  }
});

test('saveThemePreference handles storage successfully and handles errors gracefully', () => {
  let storedVal = null;
  const originalLocalStorage = globalThis.localStorage;

  globalThis.localStorage = {
    setItem: (key, val) => {
      storedVal = val;
    },
  };

  try {
    saveThemePreference('dark');
    assert.equal(storedVal, 'dark');

    // Simulate error throw
    globalThis.localStorage.setItem = () => {
      throw new Error('QuotaExceededError');
    };
    assert.doesNotThrow(() => saveThemePreference('light'));
  } finally {
    globalThis.localStorage = originalLocalStorage;
  }
});
