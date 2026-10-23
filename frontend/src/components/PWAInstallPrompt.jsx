import { WifiOff } from 'lucide-react';
import { useState, useEffect } from 'react';
import { isStandaloneMode, isPromptDismissed, dismissInstallPrompt, isIOS } from '../utils/pwa';
import './PWAInstallPrompt.css';

export default function PWAInstallPrompt() {
  const [deferredPrompt, setDeferredPrompt] = useState(null);
  const [visible, setVisible] = useState(false);
  const [showIOSGuide, setShowIOSGuide] = useState(false);
  const [isOffline, setIsOffline] = useState(
    typeof navigator !== 'undefined' ? !navigator.onLine : false
  );

  useEffect(() => {
    // If running as standalone installed app, do not show prompt
    if (isStandaloneMode()) {
      return;
    }

    // If user previously dismissed the prompt, do not bother them
    if (isPromptDismissed()) {
      return;
    }

    // Capture standard beforeinstallprompt on Chromium / Android / Desktop Chrome / Edge
    function handleBeforeInstallPrompt(e) {
      e.preventDefault();
      setDeferredPrompt(e);
      setVisible(true);
    }

    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);

    // On iOS Safari, beforeinstallprompt is not emitted; show banner if not standalone and not dismissed
    if (isIOS() && !isStandaloneMode() && !isPromptDismissed()) {
      // Small delay so it does not pop up instantly on first paint
      const timer = setTimeout(() => {
        setVisible(true);
      }, 2500);
      return () => {
        clearTimeout(timer);
        window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
      };
    }

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    };
  }, []);

  // Monitor online / offline network state
  useEffect(() => {
    function handleOnline() {
      setIsOffline(false);
    }
    function handleOffline() {
      setIsOffline(true);
    }

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  async function handleInstallClick() {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const choiceResult = await deferredPrompt.userChoice;
      if (choiceResult.outcome === 'accepted') {
        setVisible(false);
      }
      setDeferredPrompt(null);
    } else if (isIOS()) {
      setShowIOSGuide(true);
    }
  }

  function handleDismiss() {
    dismissInstallPrompt();
    setVisible(false);
  }

  return (
    <>
      {/* Offline Status Pill */}
      {isOffline && (
        <div className="tukio-offline-banner animate-fade-in" role="status">
          <span className="tukio-offline-icon" aria-hidden="true"><WifiOff size={16} /></span>
          <span>You&apos;re currently offline. Viewing cached events.</span>
        </div>
      )}

      {/* PWA Floating Install Prompt */}
      {visible && (
        <div className="tukio-pwa-prompt animate-fade-in-up" role="region" aria-label="Install App">
          <div className="tukio-pwa-content">
            <img
              src="/icon-192.png"
              alt="Tukio logo"
              className="tukio-pwa-icon"
              width="44"
              height="44"
            />
            <div className="tukio-pwa-text">
              <span className="tukio-pwa-title">Get Tukio for DeKUT</span>
              <p className="tukio-pwa-sub">
                Install on your home screen for instant access and offline recommendations.
              </p>
            </div>
          </div>

          {showIOSGuide ? (
            <div className="tukio-pwa-ios-guide">
              <p>
                Tap the Share icon <span className="ios-share-glyph">⎋</span> in Safari, then tap{' '}
                <strong>Add to Home Screen ⊞</strong>.
              </p>
              <button
                type="button"
                className="tukio-pwa-dismiss-btn"
                onClick={handleDismiss}
              >
                Got it
              </button>
            </div>
          ) : (
            <div className="tukio-pwa-actions">
              <button
                type="button"
                className="tukio-pwa-dismiss-btn"
                onClick={handleDismiss}
              >
                Not now
              </button>
              <button
                type="button"
                className="tukio-pwa-install-btn"
                onClick={handleInstallClick}
              >
                Install
              </button>
            </div>
          )}
        </div>
      )}
    </>
  );
}
