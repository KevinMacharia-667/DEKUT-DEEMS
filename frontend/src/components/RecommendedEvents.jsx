import { useState, useEffect } from 'react';
import { getRecommendations } from '../api';
import EventCard from './EventCard';
import { splitBadge } from '../utils/icons';
import './RecommendedEvents.css';

/** Engine badge ("🔥 Trending on Campus") shown as an icon plus text. */
function RecBadge({ text }) {
  const { Icon, label } = splitBadge(text);
  return (
    <span className="rec-highlight-badge">
      <Icon size={13} aria-hidden="true" /> {label}
    </span>
  );
}

/**
 * "Recommended for you" section.
 *
 * Displays personalized events using the Unified Multi-Factor Hybrid Engine
 * (combining Content TF-IDF, SVD Collaborative Filtering, and Contextual Ranking).
 * A 3-way strategy toggle allows live comparison against pure Content ML and Baseline.
 */
export default function RecommendedEvents({ k = 6, refreshTrigger = 0 }) {
  const [strategy, setStrategy] = useState('hybrid');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function fetchRecs() {
      setLoading(true);
      setError('');
      try {
        const data = await getRecommendations({ strategy, k });
        if (!cancelled) setItems(data.recommendations || []);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Could not load recommendations');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchRecs();
    return () => {
      cancelled = true;
    };
  }, [strategy, k, refreshTrigger]);

  return (
    <section className="recommended-section">
      <div className="recommended-header">
        <div className="recommended-title-group">
          <h2>Recommended for you</h2>
          <span className="strategy-indicator">
            {strategy === 'hybrid' && 'Multi-factor hybrid (content + collaborative + context)'}
            {strategy === 'ml' && 'Content-based filtering (TF-IDF)'}
            {strategy === 'baseline' && 'Rule-based scoring (baseline)'}
          </span>
        </div>
        <div className="strategy-toggle" role="group" aria-label="Recommendation strategy">
          <button
            className={strategy === 'hybrid' ? 'active' : ''}
            onClick={() => setStrategy('hybrid')}
            title="Unified Multi-Factor Hybrid (Content + SVD + Context)"
          >
            Hybrid
          </button>
          <button
            className={strategy === 'ml' ? 'active' : ''}
            onClick={() => setStrategy('ml')}
            title="TF-IDF Content Matching only"
          >
            Content ML
          </button>
          <button
            className={strategy === 'baseline' ? 'active' : ''}
            onClick={() => setStrategy('baseline')}
            title="Rule-based heuristic scoring"
          >
            Baseline
          </button>
        </div>
      </div>

      {loading && <p className="recommended-status">Finding personalised events for you…</p>}
      {error && <p className="recommended-status error">{error}</p>}

      {!loading && !error && items.length === 0 && (
        <p className="recommended-status">
          No recommendations yet — pick your interest tags and RSVP to a few events
          so the engine can learn your preferences.
        </p>
      )}

      <div className="recommended-grid">
        {items.map(({ event, score, badge, reasons }) => (
          <div className="recommended-item" key={event.id}>
            <div className="recommended-card-wrapper">
              {badge && <RecBadge text={badge} />}
              <EventCard event={event} />
            </div>
            <div className="recommended-why">
              <span className="score-badge">
                {Math.round(Number(score) * 100)}% match
              </span>
              {reasons && reasons.length > 0 ? (
                <div className="reasons-list">
                  {reasons.slice(0, 2).map((reason, idx) => (
                    <span className="reason-pill" key={idx}>{reason}</span>
                  ))}
                </div>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
