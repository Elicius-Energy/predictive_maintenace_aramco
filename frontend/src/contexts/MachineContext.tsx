import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import type { ReactNode, FC } from 'react';
import type { MachineInfo } from '../types';
import axios from 'axios';
import { BACKEND_URL } from '../utils/constants';

interface MachineContextType {
  activeMachine: MachineInfo | null;
  setActiveMachine: (machine: MachineInfo | null) => void;
  machines: MachineInfo[];
  loading: boolean;
  refreshMachines: () => Promise<void>;
  selectedWindow: number;
  setSelectedWindow: (minutes: number) => void;
}

export const TIME_WINDOWS = [
  { label: '1m', minutes: 1 },
  { label: '5m', minutes: 5 },
  { label: '15m', minutes: 15 },
  { label: '1h', minutes: 60 },
  { label: 'All Time', minutes: 4320 },
];

const MachineContext = createContext<MachineContextType | undefined>(undefined);

export const MachineProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [activeMachine, setActiveMachine] = useState<MachineInfo | null>(null);
  const [machines, setMachines] = useState<MachineInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedWindow, setSelectedWindow] = useState<number>(5);
  const userSelectedRef = useRef(false);

  const handleSetActiveMachine = useCallback((machine: MachineInfo | null) => {
    userSelectedRef.current = true;
    setActiveMachine(machine);
  }, []);

  const refreshMachines = useCallback(async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/data/machines`);
      const realMachines: MachineInfo[] = response.data;
      setMachines(realMachines);
      // Auto-select the first machine (most recently active) if user hasn't manually selected one
      if (realMachines.length > 0 && !userSelectedRef.current) {
        setActiveMachine(realMachines[0]);
      }
    } catch {
      console.error('Backend unavailable. No machines to display.');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch + periodic refresh every 15 seconds so newly active machines appear
  useEffect(() => {
    refreshMachines();
    const interval = window.setInterval(refreshMachines, 15000);
    return () => clearInterval(interval);
  }, [refreshMachines]);

  return (
    <MachineContext.Provider value={{ 
      activeMachine, 
      setActiveMachine: handleSetActiveMachine, 
      machines, 
      loading, 
      refreshMachines,
      selectedWindow,
      setSelectedWindow
    }}>
      {children}
    </MachineContext.Provider>
  );
};

export const useMachine = () => {
  const context = useContext(MachineContext);
  if (context === undefined) {
    throw new Error('useMachine must be used within a MachineProvider');
  }
  return context;
};

