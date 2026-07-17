import { useState, useEffect } from 'react';
import { getRecommendations } from '../api';
import EventCard from './EventCard';
import './RecommendedEvents.css';

/**
 * "Recommended for you" section.
 *
 * Shows the top-k personalised events for the logged-in user. The
 * strategy toggle switches between the ML engine (TF-IDF + cosine
 * similarity) and the rule-based baseline so the two can be compared
 * live — this toggle exists for the project demonstration.
 */
export default function RecommendedEvents({ k = 5 }) {
  const [strategy, setStrategy] = useState('ml');
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
  }, [strategy, k]);

  return (
    <section className="recommended-section">
      <div className="recommended-header">
        <h2>Recommended for you</h2>
        <div className="strategy-toggle" role="group" aria-label="Recommendation strategy">
          <button
            className={strategy === 'ml' ? 'active' : ''}
            onClick={() => setStrategy('ml')}
            title="TF-IDF + cosine similarity (machine learning)"
          >
            ML
          </button>
          <button
            className={strategy === 'baseline' ? 'active' : ''}
            onClick={() => setStrategy('baseline')}
            title="Rule-based scoring (baseline)"
          >
            Baseline
          </button>
        </div>
      </div>

      {loading && <p className="recommended-status">Finding events for you…</p>}
      {error && <p className="recommended-status error">{error}</p>}

      {!loading && !error && items.length === 0 && (
        <p className="recommended-status">
          No recommendations yet — pick some interest tags below and RSVP to a
          few events so the engine can learn what you like.
        </p>
      )}

      <div className="recommended-grid">
        {items.map(({ event, score, explanation }) => (
          <div className="recommended-item" key={event.id}>
            <EventCard event={event} />
            <div className="recommended-why">
              <span className="score-badge">score {Number(score).toFixed(2)}</span>
              {explanation && <span className="why-text">{explanation}</span>}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
