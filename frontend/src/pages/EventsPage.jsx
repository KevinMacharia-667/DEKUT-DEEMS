import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  getEvents,
  getMyRsvps,
  rsvpToEvent,
  cancelRsvp,
  getRecommendations,
  getMyInterests,
  submitEventFeedback,
  deleteEventFeedback,
  getMyInteractions,
  logEventInteraction,
} from '../api';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import TukioCard, { TukioSkeletonCard, TukioUpNext } from '../components/TukioCard';
import { openWhatsAppShare } from '../utils/share';
import { downloadEventICS } from '../utils/calendar';
import { useScrollFade, scrollSelectedIntoView } from '../utils/useScrollFade';
import './EventsPage.css';

const SECTIONS = [
  { id: 'today', label: 'Happening Today', icon: '⚡' },
  { id: 'weekend', label: 'This Weekend', icon: '🌴' },
  { id: 'for-you', label: 'For You', icon: '✨' },
  { id: 'all', label: 'All Events', icon: '📅' },
];

const CATEGORIES = [
  'All',
  'Tech',
  'Social',
  'Academic',
  'Workshop',
  'Cultural',
  'Sports',
  'Career',
];

export default function EventsPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const toast = useToast();

  const [activeSection, setActiveSection] = useState('for-you');
  const [todayCount, setTodayCount] = useState(0);
  const [activeCategory, setActiveCategory] = useState('All');
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState(null);
  const [currentIndex, setCurrentIndex] = useState(0);

  // Set of event IDs the current logged-in user has RSVP'd to
  const [myRsvps, setMyRsvps] = useState(new Set());
  const [rsvpLoadingId, setRsvpLoadingId] = useState(null);

  // Set of event IDs the current logged-in user has marked as 'interested'
  const [interestedSet, setInterestedSet] = useState(new Set());
  const [feedbackLoadingId, setFeedbackLoadingId] = useState(null);

  // Map of eventId -> recommendation item from hybrid ML engine
  const [recommendationsMap, setRecommendationsMap] = useState({});
  const [hasInterests, setHasInterests] = useState(true);

  // Touch drag state for swipe gestures
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const touchStartRef = useRef({ x: 0, y: 0, time: 0 });

  // Card flight transition state & navigation lock
  const [transitionClass, setTransitionClass] = useState('');
  const isTransitioningRef = useRef(false);

  // Edge fades on the horizontally scrolling tab and chip rows
  const [tabsRef, tabsFadeClass] = useScrollFade();
  const [chipsRef, chipsFadeClass] = useScrollFade();

  // Keep the active tab / chip visible when it changes (e.g. feed opens on "Today")
  useEffect(() => {
    scrollSelectedIntoView(tabsRef.current, '[aria-selected="true"]');
  }, [activeSection, tabsRef]);

  useEffect(() => {
    scrollSelectedIntoView(chipsRef.current, '.tukio-chip.active');
  }, [activeCategory, chipsRef]);

  // ── Fetch User RSVPs ──────────────────────────────────────────────
  const loadUserRsvps = useCallback(async () => {
    if (!isAuthenticated) {
      setMyRsvps(new Set());
      return;
    }
    try {
      const rsvpList = await getMyRsvps();
      const activeIds = new Set(
        rsvpList
          .filter((r) => r.status === 'confirmed')
          .map((r) => r.event_id)
      );
      setMyRsvps(activeIds);
    } catch {
      setMyRsvps(new Set());
    }
  }, [isAuthenticated]);

  // ── Fetch User Active Feedbacks (Interested & Not for me) ──────────
  const loadUserInteractions = useCallback(async () => {
    if (!isAuthenticated) {
      setInterestedSet(new Set());
      return;
    }
    try {
      const data = await getMyInteractions();
      setInterestedSet(new Set(data.interested || []));
    } catch {
      setInterestedSet(new Set());
    }
  }, [isAuthenticated]);

  // ── Fetch Recommendation Signals ──────────────────────────────────
  const loadRecommendations = useCallback(async () => {
    if (!isAuthenticated) {
      setRecommendationsMap({});
      setHasInterests(true);
      return;
    }
    try {
      const [recData, interests] = await Promise.all([
        getRecommendations({ strategy: 'hybrid', k: 50 }),
        getMyInterests().catch(() => []),
      ]);
      setHasInterests(Array.isArray(interests) && interests.length > 0);

      const map = {};
      if (recData && recData.recommendations) {
        recData.recommendations.forEach((item) => {
          map[item.event.id] = {
            score: item.score,
            badge: item.badge,
            reasons: item.reasons || [],
            explanation: item.explanation,
            content_score: item.content_score,
            collab_score: item.collab_score,
            urgency_score: item.urgency_score,
            dept_score: item.dept_score,
          };
        });
      }
      setRecommendationsMap(map);
    } catch {
      setRecommendationsMap({});
    }
  }, [isAuthenticated]);

  useEffect(() => {
    loadUserRsvps();
    loadRecommendations();
    loadUserInteractions();
  }, [loadUserRsvps, loadRecommendations, loadUserInteractions]);

  // ── Section-Aware Event Fetcher ───────────────────────────────────
  const loadEventsForSection = useCallback(
    async (section, category) => {
      setLoading(true);
      setApiError(null);
      setCurrentIndex(0);
      try {
        const catParam = category !== 'All' ? category : undefined;

        if (section === 'today') {
          const data = await getEvents({
            time_frame: 'today',
            category: catParam,
            per_page: 50,
            published_only: true,
          });
          const list = data.events || [];
          setEvents(list);
          if (category === 'All') {
            setTodayCount(list.length);
          }
        } else if (section === 'weekend') {
          const data = await getEvents({
            time_frame: 'weekend',
            category: catParam,
            per_page: 50,
            published_only: true,
          });
          setEvents(data.events || []);
        } else if (section === 'for-you') {
          if (isAuthenticated) {
            const recData = await getRecommendations({ strategy: 'hybrid', k: 50 });
            let recEvents = (recData.recommendations || []).map((r) => r.event);
            if (catParam) {
              recEvents = recEvents.filter((ev) => ev.category === catParam);
            }
            setEvents(recEvents);
          } else {
            // Guest fallback
            const data = await getEvents({
              time_frame: 'upcoming',
              category: catParam,
              per_page: 50,
              published_only: true,
            });
            setEvents(data.events || []);
          }
        } else {
          // 'all' section (Explore All) — displays all upcoming events without not_for_me exclusion
          const data = await getEvents({
            time_frame: 'upcoming',
            category: catParam,
            per_page: 50,
            published_only: true,
          });
          setEvents(data.events || []);
        }
      } catch (err) {
        setApiError(
          err.message || 'Unable to connect to Tukio servers. Please check your backend.'
        );
        setEvents([]);
      } finally {
        setLoading(false);
      }
    },
    [isAuthenticated]
  );

  // ── Initial Feed Bootstrap: Open on Happening Today if it has events, else For You ──
  useEffect(() => {
    let isMounted = true;
    async function initFeed() {
      setLoading(true);
      setApiError(null);
      try {
        const todayData = await getEvents({
          time_frame: 'today',
          per_page: 50,
          published_only: true,
        });
        const todayList = todayData.events || [];
        if (!isMounted) return;
        setTodayCount(todayList.length);

        if (todayList.length > 0) {
          // Priority 1: Open on Happening Today if it has events
          setActiveSection('today');
          setEvents(todayList);
        } else {
          // Priority 2: Fall back to For You
          setActiveSection('for-you');
          if (isAuthenticated) {
            const recData = await getRecommendations({ strategy: 'hybrid', k: 50 });
            if (!isMounted) return;
            const recEvents = (recData.recommendations || []).map((r) => r.event);
            setEvents(recEvents);
          } else {
            const allData = await getEvents({
              time_frame: 'upcoming',
              per_page: 50,
              published_only: true,
            });
            if (!isMounted) return;
            setEvents(allData.events || []);
          }
        }
      } catch (err) {
        if (!isMounted) return;
        setApiError(
          err.message || 'Unable to connect to Tukio servers. Please check your backend.'
        );
        setEvents([]);
      } finally {
        if (isMounted) setLoading(false);
      }
    }
    initFeed();
    return () => {
      isMounted = false;
    };
  }, [isAuthenticated]);

  // ── Section & Category Tab Handlers ───────────────────────────────
  function handleSectionChange(newSection) {
    if (activeSection === newSection) return;
    setActiveSection(newSection);
    loadEventsForSection(newSection, activeCategory);
  }

  function handleCategoryClick(cat) {
    if (activeCategory === cat) return;
    setActiveCategory(cat);
    loadEventsForSection(activeSection, cat);
  }

  const currentEvent = events[currentIndex];
  const isEndOfDeck = events.length > 0 && currentIndex >= events.length;

  // ── Telemetry: Log Impression when active card changes ────────────
  useEffect(() => {
    if (currentEvent && currentEvent.id) {
      logEventInteraction(currentEvent.id, 'impression').catch(() => {});
    }
  }, [currentEvent]);

  // ── Navigation in Deck (with telemetry skip logging) ───────────────
  // ── Navigation in Deck (with telemetry skip logging & animation lock) ───────────────
  const goNext = useCallback(() => {
    if (isTransitioningRef.current) return;
    if (currentIndex >= events.length) return;

    if (currentEvent && currentEvent.id) {
      const isAttending = myRsvps.has(currentEvent.id);
      const isInterested = interestedSet.has(currentEvent.id);
      if (!isAttending && !isInterested) {
        logEventInteraction(currentEvent.id, 'skip').catch(() => {});
      }
    }

    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reducedMotion) {
      setCurrentIndex((prev) => Math.min(prev + 1, events.length));
      return;
    }

    isTransitioningRef.current = true;
    setTransitionClass('slide-out-left');

    setTimeout(() => {
      setCurrentIndex((prev) => Math.min(prev + 1, events.length));
      setDragOffset({ x: 0, y: 0 });
      setTransitionClass('card-entering');

      setTimeout(() => {
        setTransitionClass('');
        isTransitioningRef.current = false;
      }, 200);
    }, 180);
  }, [currentIndex, currentEvent, events.length, myRsvps, interestedSet]);

  const goPrev = useCallback(() => {
    if (isTransitioningRef.current) return;
    if (currentIndex <= 0) return;

    const reducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (reducedMotion) {
      setCurrentIndex((prev) => Math.max(prev - 1, 0));
      return;
    }

    isTransitioningRef.current = true;
    setTransitionClass('slide-out-right');

    setTimeout(() => {
      setCurrentIndex((prev) => Math.max(prev - 1, 0));
      setDragOffset({ x: 0, y: 0 });
      setTransitionClass('card-entering');

      setTimeout(() => {
        setTransitionClass('');
        isTransitioningRef.current = false;
      }, 200);
    }, 180);
  }, [currentIndex]);

  // Keyboard navigation (Arrow keys & Space)
  useEffect(() => {
    function handleKeyDown(e) {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return;

      if (e.key === 'ArrowRight' || e.key === 'ArrowDown' || e.key === ' ') {
        e.preventDefault();
        goNext();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        goPrev();
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [goNext, goPrev]);

  // ── Touch Gesture Handlers ────────────────────────────────────────
  function handleTouchStart(e) {
    if (isTransitioningRef.current) return;
    const touch = e.touches[0];
    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
    };
    setIsDragging(true);
  }

  function handleTouchMove(e) {
    if (!isDragging || isTransitioningRef.current) return;
    const touch = e.touches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;
    setDragOffset({ x: deltaX, y: deltaY * 0.2 });
  }

  function handleTouchEnd() {
    if (!isDragging) return;
    setIsDragging(false);
    if (isTransitioningRef.current) return;

    const deltaX = dragOffset.x;
    const elapsed = Date.now() - touchStartRef.current.time;
    const velocity = Math.abs(deltaX) / (elapsed || 1);

    if (deltaX < -60 || (deltaX < -25 && velocity > 0.35)) {
      goNext();
    } else if (deltaX > 60 || (deltaX > 25 && velocity > 0.35)) {
      goPrev();
    } else {
      setDragOffset({ x: 0, y: 0 });
    }
  }

  // ── Feedback Handler (Interested / Not for me with Undo) ───────────
  async function handleFeedback(event, type) {
    if (!isAuthenticated) {
      toast.info('Please sign in to personalize your recommendations');
      navigate('/login');
      return;
    }

    const eventId = event.id;
    setFeedbackLoadingId(eventId);

    if (type === 'interested') {
      const wasInterested = interestedSet.has(eventId);

      // Optimistic update
      setInterestedSet((prev) => {
        const next = new Set(prev);
        if (wasInterested) {
          next.delete(eventId);
        } else {
          next.add(eventId);
        }
        return next;
      });

      try {
        if (wasInterested) {
          await deleteEventFeedback(eventId);
          toast.info(`Removed "${event.title}" from your interested list`);
        } else {
          await submitEventFeedback(eventId, 'interested');
          toast.success(`Marked as Interested! We'll recommend more events like this.`);
        }
      } catch (err) {
        setInterestedSet((prev) => {
          const next = new Set(prev);
          if (wasInterested) next.add(eventId);
          else next.delete(eventId);
          return next;
        });
        toast.error(err.message || 'Failed to update feedback. Please try again.');
      } finally {
        setFeedbackLoadingId(null);
      }
    } else if (type === 'not_for_me') {
      // Save event and deck index for Undo
      const dismissedEvent = event;
      const dismissedIndex = currentIndex;

      // Optimistically remove from current deck
      setEvents((prev) => prev.filter((e) => e.id !== eventId));

      try {
        await submitEventFeedback(eventId, 'not_for_me');
        toast.action(
          `Marked "${event.title}" as Not for me`,
          {
            label: 'Undo',
            onClick: async () => {
              try {
                await deleteEventFeedback(dismissedEvent.id);
                setEvents((prev) => {
                  const updated = [...prev];
                  updated.splice(Math.min(dismissedIndex, updated.length), 0, dismissedEvent);
                  return updated;
                });
                toast.info(`Restored "${dismissedEvent.title}" to your feed`);
              } catch {
                toast.error('Failed to undo dismissal');
              }
            },
          },
          'info',
          7000
        );
      } catch (err) {
        // Rollback
        setEvents((prev) => {
          const updated = [...prev];
          updated.splice(Math.min(dismissedIndex, updated.length), 0, dismissedEvent);
          return updated;
        });
        toast.error(err.message || 'Failed to dismiss event.');
      } finally {
        setFeedbackLoadingId(null);
      }
    }
  }

  // ── One-Tap RSVP Handler ──────────────────────────────────────────
  async function handleRsvpToggle(event) {
    if (!isAuthenticated) {
      toast.info('Please sign in to RSVP to campus events');
      navigate('/login');
      return;
    }

    const eventId = event.id;
    const isCurrentlyAttending = myRsvps.has(eventId);
    setRsvpLoadingId(eventId);

    setMyRsvps((prev) => {
      const updated = new Set(prev);
      if (isCurrentlyAttending) {
        updated.delete(eventId);
      } else {
        updated.add(eventId);
      }
      return updated;
    });

    setEvents((prev) =>
      prev.map((ev) => {
        if (ev.id === eventId) {
          const delta = isCurrentlyAttending ? -1 : 1;
          return {
            ...ev,
            rsvp_count: Math.max(0, (ev.rsvp_count || 0) + delta),
          };
        }
        return ev;
      })
    );

    try {
      if (isCurrentlyAttending) {
        await cancelRsvp(eventId);
        toast.info(`RSVP cancelled for ${event.title}`);
      } else {
        await rsvpToEvent(eventId);
        toast.success(`You're attending ${event.title}!`);
      }
    } catch (err) {
      setMyRsvps((prev) => {
        const rollback = new Set(prev);
        if (isCurrentlyAttending) {
          rollback.add(eventId);
        } else {
          rollback.delete(eventId);
        }
        return rollback;
      });

      setEvents((prev) =>
        prev.map((ev) => {
          if (ev.id === eventId) {
            const rollbackDelta = isCurrentlyAttending ? 1 : -1;
            return {
              ...ev,
              rsvp_count: Math.max(0, (ev.rsvp_count || 0) + rollbackDelta),
            };
          }
          return ev;
        })
      );
      toast.error(err.message || 'Failed to update RSVP. Please try again.');
    } finally {
      setRsvpLoadingId(null);
    }
  }

  // ── Share & Calendar Handlers ─────────────────────────────────────
  function handleShare(event) {
    if (!event) return;
    openWhatsAppShare(event);
    logEventInteraction(event.id, 'share').catch(() => {});
  }

  function handleAddToCalendar(event) {
    if (!event) return;
    downloadEventICS(event, window.location.origin);
    toast.success(`Calendar event downloaded for "${event.title}"`);
    logEventInteraction(event.id, 'add_to_calendar').catch(() => {});
  }

  return (
    <div className="tukio-feed-page">
      <div className="tukio-feed-container">
        {/* ── Brand Header ─────────────────────────────────────────── */}
        <header className="tukio-feed-header animate-fade-in">
          <h1 className="tukio-feed-brand-title">Tukio</h1>
          <p className="tukio-feed-brand-sub">Discover & Attend Campus Events</p>
        </header>

        {/* ── Cold-Start Personalization Banner ─────────────────────── */}
        {isAuthenticated && !hasInterests && (
          <div className="tukio-cold-start-banner animate-fade-in">
            <span>🎯 Personalize your feed — pick your interests for custom AI recommendations</span>
            <Link to="/onboarding" className="tukio-cold-start-link">
              Pick Interests →
            </Link>
          </div>
        )}

        {/* ── Time-Aware Section Tabs ──────────────────────────────── */}
        <div
          ref={tabsRef}
          className={`tukio-section-tabs-wrapper ${tabsFadeClass}`.trim()}
          role="tablist"
          aria-label="Event Feeds"
        >
          {SECTIONS.map((sec) => (
            <button
              key={sec.id}
              type="button"
              role="tab"
              aria-selected={activeSection === sec.id}
              className={`tukio-section-tab ${activeSection === sec.id ? 'active' : ''}`}
              onClick={() => handleSectionChange(sec.id)}
            >
              <span className="tukio-section-tab-icon">{sec.icon}</span>
              <span className="tukio-section-tab-label">{sec.label}</span>
              {sec.id === 'today' && todayCount > 0 && (
                <span className="tukio-section-tab-count" title={`${todayCount} events today`}>
                  {todayCount}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── Horizontal Category Chips Bar ────────────────────────── */}
        <div ref={chipsRef} className={`tukio-category-bar-wrapper ${chipsFadeClass}`.trim()}>
          <div className="tukio-category-chips">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                type="button"
                className={`tukio-chip ${activeCategory === cat ? 'active' : ''}`}
                onClick={() => handleCategoryClick(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        <div className="tukio-feed-body">
          <div className="tukio-feed-main">
            {/* ── Main Deck Stage ──────────────────────────────────────── */}
            <div className="tukio-deck-stage">
              {loading ? (
                <div className="tukio-card-wrapper animate-fade-in">
                  <TukioSkeletonCard />
                </div>
              ) : apiError ? (
                <div className="tukio-error-state animate-fade-in">
                  <span className="tukio-error-icon" role="img" aria-label="Warning">
                    ⚠️
                  </span>
                  <h3 className="tukio-error-title">Unable to Load Feed</h3>
                  <p className="tukio-error-msg">{apiError}</p>
                  <button
                    type="button"
                    className="tukio-retry-btn"
                    onClick={() => loadEventsForSection(activeSection, activeCategory)}
                  >
                    Retry
                  </button>
                </div>
              ) : events.length === 0 ? (
                <div className="tukio-caught-up-card animate-fade-in">
                  <span className="tukio-caught-up-icon" role="img" aria-label="Calendar">
                    📭
                  </span>
                  <h3 className="tukio-caught-up-title">
                    {activeSection === 'today'
                      ? 'No Events Happening Today'
                      : activeSection === 'weekend'
                      ? 'No Events This Weekend'
                      : `No Events in ${activeCategory}`}
                  </h3>
                  <p className="tukio-caught-up-desc">
                    {activeSection === 'today'
                      ? 'There are no events scheduled for today. Check out what is happening this weekend or browse your recommendations.'
                      : activeSection === 'weekend'
                      ? 'There are no events scheduled for this weekend yet. Explore all upcoming events or check your recommendations.'
                      : `There are no upcoming events listed under ${activeCategory} right now.`}
                  </p>
                  <div className="tukio-caught-up-actions">
                    {activeSection === 'today' && (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => handleSectionChange('weekend')}
                      >
                        View This Weekend 🌴
                      </button>
                    )}
                    {activeSection === 'weekend' && (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => handleSectionChange('for-you')}
                      >
                        View For You ✨
                      </button>
                    )}
                    {activeCategory !== 'All' && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleCategoryClick('All')}
                      >
                        Show All Categories
                      </button>
                    )}
                  </div>
                </div>
              ) : isEndOfDeck ? (
                <div className="tukio-caught-up-card animate-fade-in">
                  <span className="tukio-caught-up-icon" role="img" aria-label="Party">
                    🎉
                  </span>
                  <h3 className="tukio-caught-up-title">You&apos;re All Caught Up!</h3>
                  <p className="tukio-caught-up-desc">
                    You&apos;ve checked out all events in{' '}
                    {activeSection === 'today'
                      ? 'Happening Today'
                      : activeSection === 'weekend'
                      ? 'This Weekend'
                      : activeCategory === 'All'
                      ? 'this feed'
                      : activeCategory}
                    .
                  </p>
                  <div className="tukio-caught-up-actions">
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={() => setCurrentIndex(0)}
                    >
                      Start Over
                    </button>
                    {activeSection !== 'all' && (
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleSectionChange('all')}
                      >
                        Explore All Events 📅
                      </button>
                    )}
                  </div>
                </div>
              ) : (
                <div
                  className="tukio-card-wrapper"
                  onTouchStart={handleTouchStart}
                  onTouchMove={handleTouchMove}
                  onTouchEnd={handleTouchEnd}
                >
                  <TukioCard
                    event={currentEvent}
                    recommendation={recommendationsMap[currentEvent.id] || null}
                    isAttending={myRsvps.has(currentEvent.id)}
                    isInterested={interestedSet.has(currentEvent.id)}
                    onRsvpToggle={handleRsvpToggle}
                    onFeedback={handleFeedback}
                    feedbackLoading={feedbackLoadingId === currentEvent.id}
                    onShare={handleShare}
                    onAddToCalendar={handleAddToCalendar}
                    isAuthenticated={isAuthenticated}
                    rsvpLoading={rsvpLoadingId === currentEvent.id}
                    isDragging={isDragging}
                    dragOffset={dragOffset}
                    transitionClass={transitionClass}
                  />
                </div>
              )}
            </div>

            {/* ── Navigation Controls & Progress Pill ──────────────────── */}
            {!loading && !apiError && events.length > 0 && (
              <>
                <div className="tukio-nav-controls">
                  <button
                    type="button"
                    className="tukio-nav-btn"
                    onClick={goPrev}
                    disabled={currentIndex === 0 || Boolean(transitionClass)}
                    aria-label="Previous event card"
                    title="Previous (Arrow Left)"
                  >
                    ←
                  </button>

                  <div className="tukio-progress-pill">
                    <span>
                      {Math.min(currentIndex + 1, events.length)} of {events.length}
                    </span>
                    <div className="tukio-progress-dots">
                      {events.slice(0, 7).map((ev, idx) => (
                        <span
                          key={ev.id}
                          className={`tukio-dot ${
                            idx === (currentIndex % 7) ? 'active' : ''
                          }`}
                        />
                      ))}
                    </div>
                  </div>

                  <button
                    type="button"
                    className="tukio-nav-btn"
                    onClick={goNext}
                    disabled={isEndOfDeck || Boolean(transitionClass)}
                    aria-label="Next event card"
                    title="Next (Arrow Right)"
                  >
                    →
                  </button>
                </div>

                <span className="tukio-swipe-hint">
                  <span>👈</span> Swipe or use arrow keys <span>👉</span>
                </span>
              </>
            )}
          </div>

          {/* ── "Up next" panel (wide screens only, hidden by CSS below 1024px) ── */}
          {!loading && !apiError && !isEndOfDeck && (
            <div className="tukio-feed-side">
              <TukioUpNext events={events} currentIndex={currentIndex} onSelect={setCurrentIndex} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
