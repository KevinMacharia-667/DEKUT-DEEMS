import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  isStandaloneMode,
  isPromptDismissed,
  dismissInstallPrompt,
  resetInstallPromptDismissal,
  isIOS,
} from './pwa.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

test('manifest.json has all required PWA fields and valid icon configurations', () => {
  const manifestPath = path.resolve(__dirname, '../../public/manifest.json');
  assert.ok(fs.existsSync(manifestPath), 'manifest.json must exist in public directory');

  const content = fs.readFileSync(manifestPath, 'utf-8');
  const manifest = JSON.parse(content);

  assert.equal(manifest.name, 'Tukio — DeKUT Campus Events');
  assert.equal(manifest.short_name, 'Tukio');
  assert.equal(manifest.display, 'standalone');
  assert.equal(manifest.start_url, '/');
  assert.equal(manifest.theme_color, '#34B233');
  assert.equal(manifest.background_color, '#0B111A');

  assert.ok(Array.isArray(manifest.icons) && manifest.icons.length >= 2);
  const has192 = manifest.icons.some((i) => i.sizes === '192x192');
  const has512 = manifest.icons.some((i) => i.sizes === '512x512');
  assert.ok(has192, 'manifest must specify a 192x192 icon');
  assert.ok(has512, 'manifest must specify a 512x512 icon');
});

test('isStandaloneMode detects standalone display mode correctly', () => {
  const originalWindow = globalThis.window;

  // 1. In browser tab mode
  globalThis.window = {
    matchMedia: () => ({ matches: false }),
    navigator: { standalone: false },
  };
  assert.equal(isStandaloneMode(), false);

  // 2. In standalone display-mode media query
  globalThis.window = {
    matchMedia: (query) => ({ matches: query.includes('standalone') }),
    navigator: {},
  };
  assert.equal(isStandaloneMode(), true);

  // 3. In iOS standalone mode
  globalThis.window = {
    matchMedia: () => ({ matches: false }),
    navigator: { standalone: true },
  };
  assert.equal(isStandaloneMode(), true);

  globalThis.window = originalWindow;
});

test('isPromptDismissed and dismissInstallPrompt manage localStorage safely', () => {
  let store = {};
  const originalLocalStorage = globalThis.localStorage;

  globalThis.localStorage = {
    getItem: (key) => store[key] || null,
    setItem: (key, val) => {
      store[key] = String(val);
    },
    removeItem: (key) => {
      delete store[key];
    },
  };

  try {
    assert.equal(isPromptDismissed(), false);
    dismissInstallPrompt();
    assert.equal(isPromptDismissed(), true);
    resetInstallPromptDismissal();
    assert.equal(isPromptDismissed(), false);

    // Verify error safety
    globalThis.localStorage.getItem = () => {
      throw new Error('Access Denied');
    };
    assert.doesNotThrow(() => isPromptDismissed());
    assert.equal(isPromptDismissed(), false);
  } finally {
    globalThis.localStorage = originalLocalStorage;
  }
});

test('isIOS detects iOS user agents accurately', () => {
  const iphoneUA = 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15';
  const androidUA = 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36';
  const desktopUA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36';

  assert.equal(isIOS(iphoneUA), true);
  assert.equal(isIOS(androidUA), false);
  assert.equal(isIOS(desktopUA), false);
});
