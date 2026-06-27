import { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import type { ReactNode, FC } from 'react';
import type { MachineInfo } from '../types';
import api from '../utils/api';

interface MachineContextType {
  activeMachine: MachineInfo | null;
  setActiveMachine: (machine: MachineInfo | null) => void;
  machines: MachineInfo[];
  loading: boolean;
  refreshMachines: () => Promise<void>;
  timeRange: { start: string; end: string };
  setTimeRange: (range: { start: string; end: string }) => void;
}

// Removed TIME_WINDOWS

const MachineContext = createContext<MachineContextType | undefined>(undefined);

export const MachineProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [activeMachine, setActiveMachine] = useState<MachineInfo | null>(null);
  const [machines, setMachines] = useState<MachineInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const now = new Date();
  const defaultStart = new Date(now.getTime() - 5 * 60000);
  const formatDateTimeLocal = (d: Date) => {
    const pad = (n: number) => n.toString().padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  const [timeRange, setTimeRange] = useState<{ start: string; end: string }>({
    start: formatDateTimeLocal(defaultStart),
    end: formatDateTimeLocal(now)
  });
  const userSelectedRef = useRef(false);

  const handleSetActiveMachine = useCallback((machine: MachineInfo | null) => {
    userSelectedRef.current = true;
    setActiveMachine(machine);
  }, []);

  const refreshMachines = useCallback(async () => {
    try {
      const response = await api.get(`/api/data/machines`);
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
      timeRange,
      setTimeRange
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

