import type { FC } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { MachineProvider } from './contexts/MachineContext';
import { WebSocketProvider } from './contexts/WebSocketContext';
import { HistoryProvider } from './contexts/HistoryContext';
import { ChatProvider } from './contexts/ChatContext';
import Layout from './components/layout/Layout';

// Real Pages
import MachineSelection from './pages/MachineSelection';
import MechanicalParams from './pages/MechanicalParams';
import ElectricalParams from './pages/ElectricalParams';
import OtherParams from './pages/OtherParams';
import AIAnalysis from './pages/AIAnalysis';

import Login from './pages/Login';

// Dummy Protected Route Wrapper
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const isAuthenticated = sessionStorage.getItem('isAuthenticated') === 'true';
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const App: FC = () => {
  return (
    <MachineProvider>
      <WebSocketProvider>
        <HistoryProvider>
          <ChatProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/login" element={<Login />} />
                <Route path="/" element={<ProtectedRoute><MachineSelection /></ProtectedRoute>} />
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
    </MachineProvider>
  );
};

export default App;
