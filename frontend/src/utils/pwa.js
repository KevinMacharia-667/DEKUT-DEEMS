/**
 * Progressive Web App (PWA) utilities for Tukio.
 * Handles service worker registration, standalone display mode detection,
 * and safe localStorage persistence for user install prompt interactions.
 */

export function registerServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return;
  }

  // The worker serves cached files first. On the Vite dev server that means
  // stale, unhashed source modules, so only production builds register it,
  // and dev removes any worker left over from testing a build on this origin.
  if (import.meta.env.DEV) {
    navigator.serviceWorker
      .getRegistrations()
      .then((registrations) => registrations.forEach((r) => r.unregister()))
      .catch(() => {});
    return;
  }

  // When the API is on another origin (production), tell the worker which one,
  // so it treats those requests as API calls (never cached when personalised)
  // and leaves every other cross-origin request alone.
  let swUrl = '/sw.js';
  const apiBase = import.meta.env.VITE_API_BASE_URL;
  if (apiBase) {
    try {
      swUrl += `?api=${encodeURIComponent(new URL(apiBase).origin)}`;
    } catch {
      // Relative or malformed value: keep the same-origin /api behaviour
    }
  }

  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register(swUrl)
      .catch((err) => {
        console.warn('[Tukio PWA] Service Worker registration failed:', err);
      });
  });
}

export function isStandaloneMode() {
  if (typeof window === 'undefined') {
    return false;
  }

  const isStandaloneMedia =
    window.matchMedia && window.matchMedia('(display-mode: standalone)').matches;
  const isIOSStandalone = window.navigator && window.navigator.standalone === true;

  return Boolean(isStandaloneMedia || isIOSStandalone);
}

export function isPromptDismissed() {
  try {
    if (typeof localStorage !== 'undefined') {
      return localStorage.getItem('tukio_pwa_dismissed') === 'true';
    }
  } catch {
    // Graceful fallback when localStorage is blocked
  }
  return false;
}

export function dismissInstallPrompt() {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('tukio_pwa_dismissed', 'true');
    }
  } catch {
    // Ignore storage write errors
  }
}

export function resetInstallPromptDismissal() {
  try {
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('tukio_pwa_dismissed');
    }
  } catch {
    // Ignore storage errors
  }
}

export function isIOS(customUserAgent) {
  const ua =
    customUserAgent ||
    (typeof navigator !== 'undefined' ? navigator.userAgent : '') ||
    '';
  const isMSStream = typeof window !== 'undefined' && Boolean(window.MSStream);
  return /iPad|iPhone|iPod/.test(ua) && !isMSStream;
}
