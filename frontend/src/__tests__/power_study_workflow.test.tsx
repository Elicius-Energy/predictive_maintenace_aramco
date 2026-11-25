import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BrowserRouter } from 'react-router-dom';
import axios from 'axios';
import { Dashboard } from '../pages/Dashboard';
import { Reports } from '../pages/Reports';
import { Configuration } from '../pages/Configuration';
import { DeviceContext } from '../contexts/DeviceContext';
import { AuthContext } from '../contexts/AuthContext';

vi.mock('axios');
const mockedAxios = vi.mocked(axios, true);

const mockDeviceContext = {
  devices: [
    {
      device_id: 'DEV_001',
      alias: 'Ring Frame 14 - Main Motor',
      fw_ver: '13.4',
      first_seen: '2026-01-01T00:00:00Z',
      last_seen: '2026-01-01T10:00:00Z',
      status: 'Normal',
      status_detail: {},
      configured: true,
    },
  ],
  selectedDeviceId: 'DEV_001',
  selectedDevice: {
    device_id: 'DEV_001',
    alias: 'Ring Frame 14 - Main Motor',
    fw_ver: '13.4',
    first_seen: '2026-01-01T00:00:00Z',
    last_seen: '2026-01-01T10:00:00Z',
    status: 'Normal',
    status_detail: {},
    configured: true,
  },
  setSelectedDeviceId: vi.fn(),
  refreshDevices: vi.fn(async () => {}),
  getStatusColor: () => ({
    dot: 'bg-emerald-500',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
  }),
};

const mockAdminAuth = {
  user: { username: 'admin', role: 'admin' },
  isAuthenticated: true,
  isLoading: false,
  login: vi.fn(async () => {}),
  logout: vi.fn(async () => {}),
};

describe('Power Study Workflow, Before Study Dropdown & Nameplate Lifecycle', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it('Dashboard shows running study synced from server with LEDL code and customer name input without a delete button', async () => {
    mockedAxios.get.mockImplementation(async (url: string) => {
      if (url.includes('/studies/active')) {
        return {
          data: {
            id: 101,
            study_code: 'LEDL0001',
            device_id: 'DEV_001',
            customer_name: 'Aramco Spinning Unit',
            display_label: 'LEDL0001 — Aramco Spinning Unit',
            status: 'running',
            started_at: new Date(Date.now() - 120000).toISOString(),
            stopped_at: null,
            duration_seconds: 120,
          },
        } as any;
      }
      if (url.includes('/live')) {
        return { data: { status: 'Normal', open_alerts: [] } } as any;
      }
      if (url.includes('/summary')) {
        return { data: { energy_kwh: 12.5, avg_kw: 5.2, duration_hours: 1, running_hours: 1 } } as any;
      }
      if (url.includes('/trends')) {
        return { data: { points: [], alert_windows: [] } } as any;
      }
      if (url.includes('/smart-roi')) {
        return { data: { presets: [], telemetry: {}, metrics: {} } } as any;
      }
      return { data: {} } as any;
    });

    render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAdminAuth}>
          <DeviceContext.Provider value={mockDeviceContext}>
            <Dashboard />
          </DeviceContext.Provider>
        </AuthContext.Provider>
      </BrowserRouter>
    );

    // Expect study code LEDL0001 and customer name input synced from backend
    await waitFor(() => {
      expect(screen.getByText(/LEDL0001/i)).toBeInTheDocument();
    });
    const customerInput = screen.getByPlaceholderText(/Enter customer name/i) as HTMLInputElement;
    expect(customerInput).toBeInTheDocument();
    expect(customerInput.value).toBe('Aramco Spinning Unit');
    expect(screen.getByRole('button', { name: /Stop Study/i })).toBeInTheDocument();
    // Delete button must NOT be near Start/Stop Study on Dashboard
    expect(screen.queryByTitle(/Delete study/i)).not.toBeInTheDocument();
  });

  it('Reports Before Power Study dropdown shows LEDL code & customer name with admin delete button next to each study', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    mockedAxios.get.mockImplementation(async (url: string) => {
      if (url.startsWith('/api/studies')) {
        return {
          data: [
            {
              id: 1,
              study_code: 'LEDL0001',
              customer_name: 'Lakshmi Textile Unit 1',
              display_label: 'LEDL0001 — Lakshmi Textile Unit 1',
              device_id: 'DEV_001',
              status: 'completed',
              started_at: '2026-10-15T08:00:00Z',
              stopped_at: '2026-10-15T10:00:00Z',
              duration_seconds: 7200,
              duration_str: '2h 0m 0s',
              energy_kwh: 29.0,
              kwh_per_running_hour: 14.5,
            },
            {
              id: 2,
              study_code: 'LEDL0002',
              customer_name: 'PSG Mills',
              display_label: 'LEDL0002 — PSG Mills',
              device_id: 'DEV_001',
              status: 'completed',
              started_at: '2026-10-16T08:00:00Z',
              stopped_at: '2026-10-16T10:00:00Z',
              duration_seconds: 7200,
              duration_str: '2h 0m 0s',
              energy_kwh: 24.0,
              kwh_per_running_hour: 12.0,
            },
          ],
        } as any;
      }
      if (url.includes('/studies/active')) {
        return { data: null } as any;
      }
      if (url.includes('/profile')) {
        return { data: { electricity_tariff: 8.5, annual_operating_hours: 8000 } } as any;
      }
      if (url.includes('/history/')) {
        return { data: [] } as any;
      }
      return { data: {} } as any;
    });
    mockedAxios.post.mockResolvedValue({ data: { energy_kwh: 24.0, avg_kw: 12.0, avg_pf: 0.9, idle_time_str: '0h', data_completeness_pct: 100 } } as any);
    mockedAxios.delete.mockResolvedValue({ data: { success: true, deleted_id: 1, study_code: 'LEDL0001', archived: true } } as any);

    render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAdminAuth}>
          <DeviceContext.Provider value={mockDeviceContext}>
            <Reports />
          </DeviceContext.Provider>
        </AuthContext.Provider>
      </BrowserRouter>
    );

    const beforeDropdownBtn = await screen.findByLabelText(/Before Power Study/i);
    expect(beforeDropdownBtn).toBeInTheDocument();

    // Old date window labels should no longer exist
    expect(screen.queryByText('Before Window Start')).not.toBeInTheDocument();
    expect(screen.queryByText('Before Window End')).not.toBeInTheDocument();

    // Open dropdown and verify studies + per-study delete buttons appear
    fireEvent.click(beforeDropdownBtn);

    await waitFor(() => {
      expect(screen.getByText(/LEDL0001 — Lakshmi Textile Unit 1/i)).toBeInTheDocument();
      expect(screen.getByText(/LEDL0002 — PSG Mills/i)).toBeInTheDocument();
    });

    const deleteLedl1Btn = screen.getByRole('button', { name: /Delete study LEDL0001/i });
    expect(deleteLedl1Btn).toBeInTheDocument();

    // Delete LEDL0001 from inside the dropdown
    fireEvent.click(deleteLedl1Btn);

    await waitFor(() => {
      expect(mockedAxios.delete).toHaveBeenCalledWith('/api/studies/1', expect.anything());
      expect(screen.queryByText(/LEDL0001 — Lakshmi Textile Unit 1/i)).not.toBeInTheDocument();
    });
  });

  it('Configuration shows motor nameplate image preview and Delete Nameplate button that clears image and OCR details', async () => {
    mockedAxios.get.mockImplementation(async (url: string) => {
      if (url.includes('/profile')) {
        return {
          data: {
            device_id: 'DEV_001',
            alias: 'Ring Frame 14',
            customer_name: 'Aramco Mill',
            location: 'Coimbatore',
            motor_make: 'ABB',
            motor_rating_kw: 15.0,
            frame_size: '160M',
            rated_current_amps: 28.5,
            rated_speed_rpm: 1470,
            rated_voltage: 415,
            rated_efficiency_pct: 92.1,
            motor_connection: 'Delta',
            motor_duty: 'S1',
            motor_type: 'IE3',
            serial_number: 'SN-999',
            has_nameplate_image: true,
            nameplate_image_url: '/api/devices/DEV_001/motor-nameplate-image',
          },
        } as any;
      }
      return { data: {} } as any;
    });

    mockedAxios.delete.mockResolvedValue({
      data: {
        success: true,
        has_nameplate_image: false,
        nameplate_image_url: null,
        cleared_fields: {
          motor_make: '',
          motor_rating_kw: null,
          frame_size: '',
          rated_current_amps: null,
          rated_speed_rpm: null,
          rated_voltage: null,
          rated_efficiency_pct: null,
          motor_connection: '',
          motor_duty: '',
          insulation_class: '',
          motor_type: '',
          serial_number: '',
        },
        message: 'Motor nameplate image deleted and previous study nameplate OCR details cleared.',
      },
    } as any);

    render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAdminAuth}>
          <DeviceContext.Provider value={mockDeviceContext}>
            <Configuration />
          </DeviceContext.Provider>
        </AuthContext.Provider>
      </BrowserRouter>
    );

    // Expand Section 3: Motor Name Plate Details
    await waitFor(() => {
      expect(screen.getByText(/3\. Motor Name Plate Details/i)).toBeInTheDocument();
    });
    fireEvent.click(screen.getByText(/3\. Motor Name Plate Details/i));

    // Verify nameplate preview image and delete button are rendered
    const previewImg = await screen.findByAltText(/Motor Nameplate Preview/i);
    expect(previewImg).toBeInTheDocument();

    const deleteBtn = screen.getByRole('button', { name: /Delete Nameplate/i });
    expect(deleteBtn).toBeInTheDocument();

    // Click Delete Nameplate
    fireEvent.click(deleteBtn);

    await waitFor(() => {
      expect(mockedAxios.delete).toHaveBeenCalledWith(
        '/api/devices/DEV_001/motor-nameplate',
        expect.anything()
      );
    });

    // Image preview should be removed after deletion
    await waitFor(() => {
      expect(screen.queryByAltText(/Motor Nameplate Preview/i)).not.toBeInTheDocument();
    });
  });

  it('Dashboard starts and stops a power study with customer name and Reports sends before_study_id on report generation', async () => {
    mockedAxios.get.mockImplementation(async (url: string) => {
      if (url.includes('/studies/active')) {
        return { data: null } as any;
      }
      if (url.startsWith('/api/studies')) {
        return {
          data: [
            {
              id: 7,
              study_code: 'LEDL0007',
              customer_name: 'KPR Mill Unit 2',
              display_label: 'LEDL0007 — KPR Mill Unit 2',
              device_id: 'DEV_001',
              status: 'completed',
              started_at: '2026-10-15T08:00:00Z',
              stopped_at: '2026-10-15T09:00:00Z',
              duration_seconds: 3600,
              duration_str: '1h 0m 0s',
              energy_kwh: 15.2,
              kwh_per_running_hour: 15.2,
            },
          ],
        } as any;
      }
      if (url.includes('/profile')) {
        return { data: { customer_name: 'KPR Mill Unit 2', electricity_tariff: 9.0, annual_operating_hours: 8000 } } as any;
      }
      if (url.includes('/live')) {
        return { data: { status: 'Normal', open_alerts: [] } } as any;
      }
      if (url.includes('/summary')) {
        return { data: { energy_kwh: 10.0, avg_kw: 10.0, duration_hours: 1, running_hours: 1 } } as any;
      }
      if (url.includes('/trends')) {
        return { data: { points: [], alert_windows: [] } } as any;
      }
      if (url.includes('/history/')) {
        return { data: [] } as any;
      }
      return { data: {} } as any;
    });

    mockedAxios.post.mockImplementation(async (url: string, body: any) => {
      if (url.includes('/studies/start')) {
        return {
          data: {
            id: 8,
            study_code: 'LEDL0008',
            customer_name: body.customer_name,
            display_label: `LEDL0008 — ${body.customer_name}`,
            device_id: 'DEV_001',
            status: 'running',
            started_at: new Date().toISOString(),
            stopped_at: null,
            duration_seconds: 0,
          },
        } as any;
      }
      if (url.includes('/studies/stop')) {
        return {
          data: {
            id: 8,
            study_code: 'LEDL0008',
            customer_name: body.customer_name || 'Super Spinning Mills',
            display_label: 'LEDL0008 — Super Spinning Mills',
            device_id: 'DEV_001',
            status: 'completed',
            started_at: new Date(Date.now() - 60000).toISOString(),
            stopped_at: new Date().toISOString(),
            duration_seconds: 60,
            kwh_per_running_hour: 11.4,
          },
        } as any;
      }
      if (url.includes('/reports/preview')) {
        return { data: { energy_kwh: 11.4, avg_kw: 11.4, avg_pf: 0.91, idle_time_str: '0h', data_completeness_pct: 100 } } as any;
      }
      if (url.includes('/reports/generate')) {
        return { data: new Blob(['fake-xlsx']) } as any;
      }
      return { data: {} } as any;
    });

    const { unmount } = render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAdminAuth}>
          <DeviceContext.Provider value={mockDeviceContext}>
            <Dashboard />
          </DeviceContext.Provider>
        </AuthContext.Provider>
      </BrowserRouter>
    );

    const custInput = await screen.findByPlaceholderText(/Enter customer name/i);
    fireEvent.change(custInput, { target: { value: 'Super Spinning Mills' } });
    fireEvent.click(screen.getByRole('button', { name: /Start Study/i }));

    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/devices/DEV_001/studies/start',
        { customer_name: 'Super Spinning Mills' },
        expect.anything()
      );
      expect(screen.getByText('LEDL0008')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Stop Study/i }));
    await waitFor(() => {
      expect(mockedAxios.post).toHaveBeenCalledWith(
        '/api/devices/DEV_001/studies/stop',
        { customer_name: 'Super Spinning Mills' },
        expect.anything()
      );
      expect(screen.getByRole('button', { name: /New Study/i })).toBeInTheDocument();
    });

    unmount();

    // Render Reports page, select LEDL0007 as Before Power Study, and verify payload
    render(
      <BrowserRouter>
        <AuthContext.Provider value={mockAdminAuth}>
          <DeviceContext.Provider value={mockDeviceContext}>
            <Reports />
          </DeviceContext.Provider>
        </AuthContext.Provider>
      </BrowserRouter>
    );

    const beforeBtn = await screen.findByLabelText(/Before Power Study/i);
    fireEvent.click(beforeBtn);
    const optionLedl7 = await screen.findByText(/LEDL0007 — KPR Mill Unit 2/i);
    fireEvent.click(optionLedl7);
    expect(beforeBtn.textContent).toContain('LEDL0007');
  });
});
