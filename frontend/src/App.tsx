import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { DeviceProvider } from './contexts/DeviceContext';
import { Navbar } from './components/layout/Navbar';
import { AppBackdrop } from './components/layout/AppBackdrop';
import { FloatingChat } from './components/chat/FloatingChat';
import Login from './pages/Login';
import Configuration from './pages/Configuration';
import Dashboard from './pages/Dashboard';
import Reports from './pages/Reports';
import UserManagement from './pages/UserManagement';
import ChangePassword from './pages/ChangePassword';

// Protected Route Wrapper
const ProtectedRoute: React.FC = () => {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-8 h-8 border-4 border-[#1F3A8A] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (user?.must_change_password) return <ChangePassword />;

  return (
    <DeviceProvider>
      <div className="relative min-h-screen flex flex-col font-sans text-slate-900">
        {/* Plant photograph backdrop, pinned behind every authenticated screen */}
        <AppBackdrop />
        <div className="relative z-10 flex flex-col flex-1">
          <Navbar />
          <main className="flex-1">
            <Outlet />
          </main>
          {/* Floating Chatbot visible on all three pages */}
          <FloatingChat />
        </div>
      </div>
    </DeviceProvider>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/config" element={<Configuration />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/users" element={<UserManagement />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;
