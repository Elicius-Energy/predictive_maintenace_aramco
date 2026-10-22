import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

export interface Device {
  device_id: string;
  alias: string | null;
  fw_ver: string | null;
  first_seen: string | null;
  last_seen: string | null;
  status: string;
  status_detail: Record<string, any>;
  configured: boolean;
}

interface DeviceContextType {
  devices: Device[];
  selectedDevice: Device | null;
  selectedDeviceId: string;
  setSelectedDeviceId: (id: string) => void;
  refreshDevices: () => Promise<void>;
  getStatusColor: (status: string) => { dot: string; bg: string; text: string; border: string };
}

export const DeviceContext = createContext<DeviceContextType | undefined>(undefined);

export const DeviceProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDeviceId, setSelectedDeviceIdState] = useState<string>(() => {
    return localStorage.getItem('elicius_selected_device') || '';
  });

  const fetchDevices = async () => {
    try {
      const res = await axios.get('/api/devices', { withCredentials: true });
      const devList: Device[] = res.data;
      setDevices(devList);

      if (devList.length > 0) {
        // If current selection is invalid or empty, pick first device
        const exists = devList.some((d) => d.device_id === selectedDeviceId);
        if (!exists) {
          const defaultId = devList[0].device_id;
          setSelectedDeviceIdState(defaultId);
          localStorage.setItem('elicius_selected_device', defaultId);
        }
      }
    } catch (err) {
      console.error('Error fetching devices:', err);
    }
  };

  useEffect(() => {
    fetchDevices();
    // Poll every 10s so unknown dIDs auto-registered show up seamlessly
    const interval = setInterval(fetchDevices, 10000);
    return () => clearInterval(interval);
  }, [selectedDeviceId]);

  const setSelectedDeviceId = (id: string) => {
    setSelectedDeviceIdState(id);
    localStorage.setItem('elicius_selected_device', id);
  };

  const selectedDevice = devices.find((d) => d.device_id === selectedDeviceId) || devices[0] || null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'Normal':
        return {
          dot: 'bg-emerald-500',
          bg: 'bg-emerald-50',
          text: 'text-emerald-700',
          border: 'border-emerald-200',
        };
      case 'Warning':
        return {
          dot: 'bg-amber-500',
          bg: 'bg-amber-50',
          text: 'text-amber-800',
          border: 'border-amber-200',
        };
      case 'Incorrect connection':
      case 'Disconnected':
        return {
          dot: 'bg-red-500',
          bg: 'bg-red-50',
          text: 'text-red-700',
          border: 'border-red-200',
        };
      case 'Communication failure':
      case 'New – not configured':
      default:
        return {
          dot: 'bg-slate-400',
          bg: 'bg-slate-50',
          text: 'text-slate-700',
          border: 'border-slate-200',
        };
    }
  };

  return (
    <DeviceContext.Provider
      value={{
        devices,
        selectedDevice,
        selectedDeviceId,
        setSelectedDeviceId,
        refreshDevices: fetchDevices,
        getStatusColor,
      }}
    >
      {children}
    </DeviceContext.Provider>
  );
};

export const useDevice = () => {
  const context = useContext(DeviceContext);
  if (!context) {
    throw new Error('useDevice must be used within a DeviceProvider');
  }
  return context;
};
