import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import { Navbar } from '../components/layout/Navbar';
import Login from '../pages/Login';
import { FloatingChat } from '../components/chat/FloatingChat';
import { DeviceContext } from '../contexts/DeviceContext';
import { AuthContext } from '../contexts/AuthContext';

// Mock contexts
const mockDeviceContext = {
  devices: [
    {
      device_id: '002D00203335471332323632',
      alias: 'Ring Frame 14 - Main Motor',
      fw_ver: '13.4',
      first_seen: '2026-01-01T00:00:00Z',
      last_seen: '2026-01-01T10:00:00Z',
      status: 'Normal',
      status_detail: {},
      configured: true
    }
  ],
  selectedDeviceId: '002D00203335471332323632',
  selectedDevice: {
    device_id: '002D00203335471332323632',
    alias: 'Ring Frame 14 - Main Motor',
    fw_ver: '13.4',
    first_seen: '2026-01-01T00:00:00Z',
    last_seen: '2026-01-01T10:00:00Z',
    status: 'Normal',
    status_detail: {},
    configured: true
  },
  setSelectedDeviceId: vi.fn(),
  refreshDevices: vi.fn(async () => {}),
  getStatusColor: () => ({
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200'
  })
};

const mockAuthContext = {
  user: { username: 'admin', role: 'admin' },
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(async () => {}),
  logout: vi.fn(async () => {})
};

describe('Elicius Frontend Smoke Tests', () => {
  it('renders Navbar with exactly 3 tabs and device selector', () => {
    render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAuthContext}>
          <DeviceContext.Provider value={mockDeviceContext}>
            <Navbar />
          </DeviceContext.Provider>
        </AuthContext.Provider>
      </BrowserRouter>
    );

    // Verify Brand title
    expect(screen.getByText('Elicius Energy')).toBeInTheDocument();
    expect(screen.getByText('IoT Energy Monitoring')).toBeInTheDocument();

    // Verify EXACTLY 3 page tabs
    expect(screen.getByText('Configuration')).toBeInTheDocument();
    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Reports & Downloads')).toBeInTheDocument();

    // Verify Device selector
    expect(screen.getByDisplayValue('Ring Frame 14 - Main Motor (Normal)')).toBeInTheDocument();

    // Verify Logout button
    expect(screen.getByTitle('Sign Out')).toBeInTheDocument();
  });

  it('renders Login page cleanly with credentials form', () => {
    render(
      <BrowserRouter>
        <AuthContext.Provider value={{ ...mockAuthContext, user: null, isAuthenticated: false }}>
          <Login />
        </AuthContext.Provider>
      </BrowserRouter>
    );

    expect(screen.getByText('Elicius Energy Private Limited')).toBeInTheDocument();
    expect(screen.getByText(/IoT Energy Monitoring Portal/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter username/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Enter password/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Sign In to Dashboard/i })).toBeInTheDocument();
  });

  it('renders FloatingChat button and opens drawer on click', () => {
    render(
      <BrowserRouter>
        <DeviceContext.Provider value={mockDeviceContext}>
          <FloatingChat />
        </DeviceContext.Provider>
      </BrowserRouter>
    );

    const chatButton = screen.getByTitle('Open AI Diagnostics Assistant');
    expect(chatButton).toBeInTheDocument();

    // Click to open drawer
    fireEvent.click(chatButton);

    expect(screen.getByText(/Elicius AI Assistant/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/Ask about motor energy/i)).toBeInTheDocument();
  });
});
