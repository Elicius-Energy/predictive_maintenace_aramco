import type { FC } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { MachineProvider } from './contexts/MachineContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { HistoryProvider } from './contexts/HistoryContext';
import { ChatProvider } from './contexts/ChatContext';
import { MotorDetailsProvider } from './contexts/MotorDetailsContext';
import Layout from './components/layout/Layout';

// Real Pages
import MachineSelection from './pages/MachineSelection';
import MechanicalParams from './pages/MechanicalParams';
import ElectricalParams from './pages/ElectricalParams';
import OtherParams from './pages/OtherParams';
import AIAnalysis from './pages/AIAnalysis';

import Login from './pages/Login';

// Protected Route Wrapper using AuthContext
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, isLoading } = useAuth();
  
  if (isLoading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50"><div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin"></div></div>;
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <>{children}</>;
};

// Smart redirect from root
const RootRedirect = () => {
  return <Navigate to="/machines" replace />;
};

const App: FC = () => {
  return (
    <AuthProvider>
      <MachineProvider>
        <MotorDetailsProvider>
          <WebSocketProvider>
            <HistoryProvider>
              <ChatProvider>
                <BrowserRouter>
                  <Routes>
                    <Route path="/login" element={<Login />} />
                    <Route path="/" element={<ProtectedRoute><RootRedirect /></ProtectedRoute>} />
                    <Route path="/machines" element={<ProtectedRoute><MachineSelection /></ProtectedRoute>} />
                    <Route path="/dashboard" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                      <Route index element={<MechanicalParams />} />
                      <Route path="mechanical" element={<MechanicalParams />} />
                      <Route path="electrical" element={<ElectricalParams />} />
                      <Route path="other" element={<OtherParams />} />
                      <Route path="ai-analysis" element={<AIAnalysis />} />
                    </Route>
                  </Routes>
                </BrowserRouter>
              </ChatProvider>
            </HistoryProvider>
          </WebSocketProvider>
        </MotorDetailsProvider>
      </MachineProvider>
    </AuthProvider>
  );
};

export default App;
