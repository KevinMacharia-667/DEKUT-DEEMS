import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { loginUser, registerUser, getMe } from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('dekut_token'));
  const [loading, setLoading] = useState(true);

  // Fetch user profile when token exists on mount
  useEffect(() => {
    if (token) {
      getMe()
        .then(setUser)
        .catch(() => {
          // Token is invalid/expired — clear it
          localStorage.removeItem('dekut_token');
          setToken(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  const login = useCallback(async (credentials) => {
    const data = await loginUser(credentials);
    localStorage.setItem('dekut_token', data.access_token);
    setToken(data.access_token);
    const profile = await getMe();
    setUser(profile);
    return profile;
  }, []);

  const register = useCallback(async (userData) => {
    const created = await registerUser(userData);
    // Auto-login after registration
    const data = await loginUser({
      email: userData.email,
      password: userData.password,
    });
    localStorage.setItem('dekut_token', data.access_token);
    setToken(data.access_token);
    setUser(created);
    return created;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('dekut_token');
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    if (token) {
      const profile = await getMe();
      setUser(profile);
    }
  }, [token]);

  const value = {
    user,
    token,
    loading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
