/**
 * Theme resolution and storage helpers for Tukio.
 * Pure JS — no JSX or DOM dependencies required for unit testing.
 */

export function getInitialTheme() {
  try {
    const storage = typeof localStorage !== 'undefined'
      ? localStorage
      : (typeof window !== 'undefined' ? window.localStorage : null);
    const stored = storage ? storage.getItem('tukio_theme') : null;
    if (stored === 'dark' || stored === 'light') {
      return stored;
    }
  } catch {
    // Graceful fallback when localStorage is disabled or throws SecurityError
  }

  const mm = typeof window !== 'undefined' && window.matchMedia
    ? window.matchMedia.bind(window)
    : (typeof matchMedia !== 'undefined' ? matchMedia : null);

  if (mm && mm('(prefers-color-scheme: dark)')?.matches) {
    return 'dark';
  }

  return 'light';
}

export function saveThemePreference(theme) {
  try {
    const storage = typeof localStorage !== 'undefined'
      ? localStorage
      : (typeof window !== 'undefined' ? window.localStorage : null);
    if (storage) {
      storage.setItem('tukio_theme', theme);
    }
  } catch {
    // Safe failure when writing to localStorage is blocked
  }
}
