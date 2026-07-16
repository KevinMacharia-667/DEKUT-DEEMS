import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * Wrapper that redirects unauthenticated users to /login.
 * Optionally restricts by role(s).
 *
 * Usage:
 *   <Route element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
 *   <Route element={<ProtectedRoute roles={['organizer','admin']}><CreateEventPage /></ProtectedRoute>} />
 */
export default function ProtectedRoute({ children, roles }) {
  const { isAuthenticated, user, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-page">
        <div className="spinner" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (roles && !roles.includes(user?.role)) {
    return <Navigate to="/events" replace />;
  }

  return children;
}
