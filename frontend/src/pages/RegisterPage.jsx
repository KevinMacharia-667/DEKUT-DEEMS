import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../components/Toast';
import { updateMyInterests } from '../api';
import './LoginPage.css'; /* Reuses auth page styles */
import Logo from '../components/Logo';

const DEPARTMENTS = [
  'School of Computer Science & IT',
  'School of Engineering',
  'School of Business',
  'School of Science & Applied Tech',
  'Health Sciences',
  'Student Affairs & Sports',
  'Cultural Society',
];

const SIGNUP_INTEREST_SUGGESTIONS = [
  'tech', 'ai', 'python', 'cybersecurity', 'web development',
  'academic', 'research', 'science', 'sports', 'football',
  'athletics', 'fitness', 'career', 'startup', 'entrepreneurship',
  'cultural', 'music', 'dance', 'social', 'networking'
];

export default function RegisterPage() {
  const { register } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    email: '',
    username: '',
    password: '',
    full_name: '',
  });
  const [regNo, setRegNo] = useState('');
  const [department, setDepartment] = useState('School of Computer Science & IT');
  const [selectedInterests, setSelectedInterests] = useState(new Set(['tech']));
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
    setError('');
  }

  function handleRegNoChange(e) {
    const val = e.target.value;
    setRegNo(val);
    const upper = val.toUpperCase().trim();
    if (/^C02[5-9]|^C0[1-9]/.test(upper)) {
      setDepartment('School of Computer Science & IT');
    } else if (/^E02[8-9]|^E0[1-9]/.test(upper)) {
      setDepartment('School of Engineering');
    } else if (/^B01[1-9]|^B0[1-9]/.test(upper)) {
      setDepartment('School of Business');
    } else if (/^S01[4-9]|^S0[1-9]/.test(upper)) {
      setDepartment('School of Science & Applied Tech');
    } else if (/^H03[1-9]|^H0[1-9]/.test(upper)) {
      setDepartment('Health Sciences');
    }
  }

  function toggleInterest(tag) {
    setSelectedInterests((prev) => {
      const next = new Set(prev);
      if (next.has(tag)) next.delete(tag);
      else next.add(tag);
      return next;
    });
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await register({ ...form, department });
      if (selectedInterests.size > 0) {
        try {
          const interestsPayload = [...selectedInterests].map((tag) => ({ tag, weight: 1.0 }));
          await updateMyInterests(interestsPayload);
        } catch {
          // Non-blocking interest seed
        }
      }
      toast.success('Account created! Welcome to DeKUT DEEMS.');
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="glass-card auth-card" style={{ maxWidth: '520px' }}>
        <div className="auth-header">
          <Logo size={64} showWordmark stacked className="logo-hero" />
          <h1>Create account</h1>
          <p>Join the DeKUT DEEMS community</p>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}

          <div className="form-group">
            <label className="form-label" htmlFor="reg-fullname">Full Name</label>
            <input
              id="reg-fullname"
              className="form-input"
              type="text"
              name="full_name"
              placeholder="e.g. Kevin Macharia"
              value={form.full_name}
              onChange={handleChange}
              maxLength={100}
              autoFocus
            />
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="reg-email">Email</label>
            <input
              id="reg-email"
              className="form-input"
              type="email"
              name="email"
              placeholder="you@dekut.ac.ke"
              value={form.email}
              onChange={handleChange}
              required
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div className="form-group">
              <label className="form-label" htmlFor="reg-username">Username</label>
              <input
                id="reg-username"
                className="form-input"
                type="text"
                name="username"
                placeholder="kevin_dev"
                value={form.username}
                onChange={handleChange}
                required
                minLength={3}
                maxLength={50}
                pattern="^[a-zA-Z0-9_]+$"
                title="Letters, numbers, and underscores only"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="reg-regno">Reg. Number</label>
              <input
                id="reg-regno"
                className="form-input"
                type="text"
                placeholder="e.g. C025-01-0649/2023"
                value={regNo}
                onChange={handleRegNoChange}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="reg-dept">Academic School / Faculty</label>
            <select
              id="reg-dept"
              className="form-input"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
            >
              {DEPARTMENTS.map((dept) => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="reg-password">Password</label>
            <input
              id="reg-password"
              className="form-input"
              type="password"
              name="password"
              placeholder="Min. 8 characters"
              value={form.password}
              onChange={handleChange}
              required
              minLength={8}
              maxLength={128}
            />
          </div>

          <div className="form-group">
            <label className="form-label">
              Select Your Interests <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>(powers your recommendation feed)</span>
            </label>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
              {SIGNUP_INTEREST_SUGGESTIONS.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleInterest(tag)}
                  style={{
                    padding: '4px 10px',
                    borderRadius: '999px',
                    fontSize: '0.76rem',
                    border: '1px solid var(--border)',
                    background: selectedInterests.has(tag) ? 'var(--primary-dark)' : 'var(--bg)',
                    color: selectedInterests.has(tag) ? '#ffffff' : 'var(--text)',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease'
                  }}
                >
                  {selectedInterests.has(tag) ? `✓ ${tag}` : `+ ${tag}`}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-lg"
            disabled={loading}
            style={{ width: '100%', marginTop: '12px' }}
          >
            {loading ? <span className="spinner" /> : 'Create account & Go to Feed'}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account?{' '}
          <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
