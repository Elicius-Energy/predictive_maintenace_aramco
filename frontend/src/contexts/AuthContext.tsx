import React, { createContext, useContext, useState, useEffect, type ReactNode } from 'react';
import api, { setAccessToken } from '../utils/api';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    // Check if user is logged in by hitting the /me endpoint
    // First need to try checking if token exists in session storage/cookie, but we decided to keep it in memory
    // For simple persistence across reloads we'll use sessionStorage temporarily until backend issues refresh tokens in httpOnly cookies
    const token = sessionStorage.getItem('accessToken');
    if (token) {
      setAccessToken(token);
      api.get('/api/auth/me')
        .then(() => setIsAuthenticated(true))
        .catch(() => {
          setAccessToken(null);
          sessionStorage.removeItem('accessToken');
          setIsAuthenticated(false);
        })
        .finally(() => setIsLoading(false));
    } else {
      setIsLoading(false);
    }

    const handleLogout = () => {
      logout();
    };

    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, []);

  const login = (token: string) => {
    setAccessToken(token);
    sessionStorage.setItem('accessToken', token);
    setIsAuthenticated(true);
  };

  const logout = () => {
    setAccessToken(null);
    sessionStorage.removeItem('accessToken');
    setIsAuthenticated(false);
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
