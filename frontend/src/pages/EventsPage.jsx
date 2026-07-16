import { useState, useEffect } from 'react';
import { getEvents } from '../api';
import EventCard from '../components/EventCard';
import './EventsPage.css';

const CATEGORIES = ['All', 'Academic', 'Social', 'Sports', 'Workshop', 'Cultural', 'Tech', 'Career'];

export default function EventsPage() {
  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('All');
  const perPage = 12;

  useEffect(() => {
    setLoading(true);
    const params = { page, per_page: perPage };
    if (activeCategory !== 'All') params.category = activeCategory;
    if (search.trim()) params.search = search.trim();

    getEvents(params)
      .then((data) => {
        setEvents(data.events);
        setTotal(data.total);
      })
      .catch(() => {
        setEvents([]);
        setTotal(0);
      })
      .finally(() => setLoading(false));
  }, [page, activeCategory, search]);

  function handleCategoryClick(cat) {
    setActiveCategory(cat);
    setPage(1);
  }

  function handleSearch(e) {
    e.preventDefault();
    setPage(1);
  }

  const totalPages = Math.ceil(total / perPage);

  return (
    <div className="page">
      <div className="container">
        {/* Hero */}
        <div className="events-hero animate-fade-in">
          <h1>Campus Events</h1>
          <p>
            Discover what&apos;s happening at Dedan Kimathi University of Technology
          </p>

          {/* Search */}
          <form className="events-search" onSubmit={handleSearch}>
            <input
              className="form-input"
              type="text"
              placeholder="Search events..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="submit" className="btn btn-primary">
              Search
            </button>
          </form>

          {/* Category chips */}
          <div className="events-categories">
            {CATEGORIES.map((cat) => (
              <button
                key={cat}
                className={`category-chip${activeCategory === cat ? ' active' : ''}`}
                onClick={() => handleCategoryClick(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Content */}
        {loading ? (
          <div className="loading-page">
            <div className="spinner" />
          </div>
        ) : events.length === 0 ? (
          <div className="empty-state animate-fade-in">
            <div className="empty-state-icon">📭</div>
            <h3>No events found</h3>
            <p>
              {search || activeCategory !== 'All'
                ? 'Try adjusting your search or filters'
                : 'No events have been published yet. Check back soon!'}
            </p>
          </div>
        ) : (
          <>
            <div className="events-grid stagger">
              {events.map((event) => (
                <EventCard key={event.id} event={event} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="events-pagination">
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  ← Previous
                </button>
                <span className="events-pagination-info">
                  Page {page} of {totalPages}
                </span>
                <button
                  className="btn btn-secondary btn-sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage(page + 1)}
                >
                  Next →
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
