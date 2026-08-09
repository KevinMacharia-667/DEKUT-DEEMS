import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getEvent, updateEvent } from '../api';
import { useToast } from '../components/Toast';
import './CreateEventPage.css';

const CATEGORIES = ['Academic', 'Social', 'Sports', 'Workshop', 'Cultural', 'Tech', 'Career'];

export default function EditEventPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const toast = useToast();

  const [form, setForm] = useState({
    title: '',
    description: '',
    category: '',
    tags: '',
    location: '',
    start_time: '',
    end_time: '',
    max_attendees: '',
    image_url: '',
    is_published: false,
  });
  const [loading, setLoading] = useState(false);
  const [fetching, setFetching] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getEvent(id)
      .then((event) => {
        setForm({
          title: event.title || '',
          description: event.description || '',
          category: event.category || '',
          tags: event.tags || '',
          location: event.location || '',
          start_time: event.start_time ? new Date(event.start_time).toISOString().slice(0, 16) : '',
          end_time: event.end_time ? new Date(event.end_time).toISOString().slice(0, 16) : '',
          max_attendees: event.max_attendees || '',
          image_url: event.image_url || '',
          is_published: event.is_published || false,
        });
      })
      .catch(() => {
        toast.error('Event not found or failed to load');
        navigate('/events');
      })
      .finally(() => setFetching(false));
  }, [id, navigate, toast]);

  function handleChange(e) {
    const { name, value, type, checked } = e.target;
    setForm({ ...form, [name]: type === 'checkbox' ? checked : value });
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const payload = {
        title: form.title,
        description: form.description || null,
        category: form.category || null,
        tags: form.tags.trim() || null,
        location: form.location || null,
        start_time: new Date(form.start_time).toISOString(),
        end_time: form.end_time ? new Date(form.end_time).toISOString() : null,
        max_attendees: form.max_attendees ? parseInt(form.max_attendees, 10) : null,
        image_url: form.image_url || null,
        is_published: form.is_published,
      };

      await updateEvent(id, payload);

      toast.success('Event updated successfully!');
      navigate(`/events/${id}`);
    } catch (err) {
      setError(err.message || 'Failed to update event');
    } finally {
      setLoading(false);
    }
  }

  if (fetching) {
    return <div className="page"><div className="loading-page"><div className="spinner" /></div></div>;
  }

  return (
    <div className="page">
      <div className="container create-event-page">
        <div className="page-header">
          <h1>Edit Event</h1>
          <p>Update the details of your event</p>
        </div>

        <form className="glass-card create-event-form" onSubmit={handleSubmit}>
          {error && <div className="auth-error" style={{ marginBottom: '16px' }}>{error}</div>}

          <div className="form-group">
            <label className="form-label" htmlFor="event-title">Event Title *</label>
            <input
              id="event-title"
              className="form-input"
              type="text"
              name="title"
              placeholder="e.g. Hackathon 2026"
              value={form.title}
              onChange={handleChange}
              required
              maxLength={200}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="event-desc">Description</label>
            <textarea
              id="event-desc"
              className="form-textarea"
              name="description"
              placeholder="Tell people what this event is about..."
              value={form.description}
              onChange={handleChange}
              rows={4}
            />
          </div>

          <div className="create-event-row">
            <div className="form-group">
              <label className="form-label" htmlFor="event-category">Category</label>
              <select
                id="event-category"
                className="form-select"
                name="category"
                value={form.category}
                onChange={handleChange}
              >
                <option value="">Select category</option>
                {CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="event-location">Location</label>
              <input
                id="event-location"
                className="form-input"
                type="text"
                name="location"
                placeholder="e.g. Main Hall"
                value={form.location}
                onChange={handleChange}
                maxLength={200}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="event-tags">Tags</label>
            <input
              id="event-tags"
              className="form-input"
              type="text"
              name="tags"
              placeholder="e.g. python, hackathon, beginner (comma-separated)"
              value={form.tags}
              onChange={handleChange}
              maxLength={500}
            />
            <span className="form-hint">Separate tags with commas. Helps with event recommendations.</span>
          </div>

          <div className="create-event-row">
            <div className="form-group">
              <label className="form-label" htmlFor="event-start">Start Date & Time *</label>
              <input
                id="event-start"
                className="form-input"
                type="datetime-local"
                name="start_time"
                value={form.start_time}
                onChange={handleChange}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="event-end">End Date & Time</label>
              <input
                id="event-end"
                className="form-input"
                type="datetime-local"
                name="end_time"
                value={form.end_time}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="create-event-row">
            <div className="form-group">
              <label className="form-label" htmlFor="event-max">Max Attendees</label>
              <input
                id="event-max"
                className="form-input"
                type="number"
                name="max_attendees"
                placeholder="Unlimited"
                value={form.max_attendees}
                onChange={handleChange}
                min={1}
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="event-image">Image URL</label>
              <input
                id="event-image"
                className="form-input"
                type="url"
                name="image_url"
                placeholder="https://..."
                value={form.image_url}
                onChange={handleChange}
              />
            </div>
          </div>

          <div className="toggle-group">
            <label className="toggle">
              <input
                type="checkbox"
                name="is_published"
                checked={form.is_published}
                onChange={handleChange}
              />
              <span className="toggle-slider" />
            </label>
            <span className="toggle-label">
              {form.is_published ? 'Published — visible to everyone' : 'Draft — only you can see it'}
            </span>
          </div>

          <div className="create-event-actions">
            <button
              type="submit"
              className="btn btn-primary btn-lg"
              disabled={loading}
              style={{ flex: 1 }}
            >
              {loading ? <span className="spinner" /> : 'Update Event'}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-lg"
              onClick={() => navigate(`/events/${id}`)}
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
