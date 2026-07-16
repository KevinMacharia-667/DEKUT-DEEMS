import { useState, useRef, useEffect } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Navbar.css';

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const dropdownRef = useRef(null);
  const navigate = useNavigate();

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  function handleLogout() {
    logout();
    setDropdownOpen(false);
    navigate('/login');
  }

  const canCreateEvents = user && (user.role === 'organizer' || user.role === 'admin');

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <Link to="/events" className="navbar-brand">
          <span className="navbar-brand-icon">🎓</span>
          DeKUT Events
        </Link>

        {/* Mobile toggle */}
        <button
          className="navbar-toggle"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-label="Toggle navigation"
        >
          {mobileOpen ? '✕' : '☰'}
        </button>

        {/* Nav links */}
        <ul className={`navbar-nav${mobileOpen ? ' open' : ''}`}>
          <li>
            <NavLink
              to="/events"
              className={({ isActive }) => `navbar-link${isActive ? ' active' : ''}`}
              onClick={() => setMobileOpen(false)}
            >
              Events
            </NavLink>
          </li>
          {canCreateEvents && (
            <li>
              <NavLink
                to="/events/new"
                className={({ isActive }) => `navbar-link${isActive ? ' active' : ''}`}
                onClick={() => setMobileOpen(false)}
              >
                Create Event
              </NavLink>
            </li>
          )}
          {isAuthenticated && (
            <li>
              <NavLink
                to="/dashboard"
                className={({ isActive }) => `navbar-link${isActive ? ' active' : ''}`}
                onClick={() => setMobileOpen(false)}
              >
                Dashboard
              </NavLink>
            </li>
          )}
        </ul>

        {/* Auth actions */}
        <div className="navbar-actions">
          {isAuthenticated ? (
            <div ref={dropdownRef} style={{ position: 'relative' }}>
              <button
                className="navbar-user"
                onClick={() => setDropdownOpen(!dropdownOpen)}
              >
                <span className="navbar-avatar">
                  {user?.full_name?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || '?'}
                </span>
                <span className="navbar-username">{user?.username}</span>
              </button>

              {dropdownOpen && (
                <div className="navbar-dropdown">
                  <div style={{ padding: '8px 14px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    {user?.email}
                  </div>
                  <div className="navbar-dropdown-divider" />
                  <Link
                    to="/dashboard"
                    className="navbar-dropdown-item"
                    onClick={() => setDropdownOpen(false)}
                  >
                    Dashboard
                  </Link>
                  <div className="navbar-dropdown-divider" />
                  <button
                    className="navbar-dropdown-item"
                    onClick={handleLogout}
                    style={{ color: '#f87171' }}
                  >
                    Log out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost btn-sm">Log in</Link>
              <Link to="/register" className="btn btn-primary btn-sm">Sign up</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
