import { createContext, useContext, useState, useEffect } from 'react';
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
  isSimulated: boolean;
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

/** Default simulated machines when backend is unavailable */
const SIMULATED_MACHINES: MachineInfo[] = [
  {
    machine_id: 'sim-pump-001',
    name: 'Centrifugal Pump P-101',
    type: 'Centrifugal Pump',
    location: 'Ras Tanura Refinery',
    unit: 'Processing Unit 3',
    plant: 'Ras Tanura',
    status: 'healthy',
    health_score: 94.2,
    uptime_hours: 4320,
    last_maintenance: '2026-03-01T08:00:00Z',
  },
  {
    machine_id: 'sim-pump-002',
    name: 'Booster Pump P-202',
    type: 'Reciprocating Pump',
    location: 'Jubail Industrial Complex',
    unit: 'Processing Unit 5',
    plant: 'Jubail',
    status: 'warning',
    health_score: 72.8,
    uptime_hours: 8760,
    last_maintenance: '2026-01-15T08:00:00Z',
  },
  {
    machine_id: 'sim-motor-003',
    name: 'Compressor Motor M-301',
    type: 'Induction Motor',
    location: 'Yanbu Integrated',
    unit: 'Gas Processing Unit 1',
    plant: 'Yanbu',
    status: 'healthy',
    health_score: 88.5,
    uptime_hours: 6500,
    last_maintenance: '2026-02-10T08:00:00Z',
  },
  {
    machine_id: 'Machine_10',
    name: 'Actual MQTT Device',
    type: 'Unknown Asset Type',
    location: 'Field Operations',
    unit: 'Remote Unit 10',
    plant: 'Remote Substation',
    status: 'healthy',
    health_score: 100.0,
    uptime_hours: 100,
    last_maintenance: '2026-04-06T08:00:00Z',
  },
];

export const MachineProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [activeMachine, setActiveMachine] = useState<MachineInfo | null>(null);
  const [machines, setMachines] = useState<MachineInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [isSimulated, setIsSimulated] = useState(false);
  const [selectedWindow, setSelectedWindow] = useState<number>(5);

  const refreshMachines = async () => {
    try {
      const response = await axios.get(`${BACKEND_URL}/api/data/machines`);
      const realMachines: MachineInfo[] = response.data;
      setMachines(realMachines);
      setIsSimulated(false);
      if (!activeMachine && realMachines.length > 0) {
        setActiveMachine(realMachines[0]);
      }
    } catch {
      // Backend unavailable — use simulated machines
      console.info('Backend unavailable. Using simulated machine data.');
      setMachines(SIMULATED_MACHINES);
      setIsSimulated(true);
      if (!activeMachine && SIMULATED_MACHINES.length > 0) {
        setActiveMachine(SIMULATED_MACHINES[0]);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshMachines();
  }, []);

  return (
    <MachineContext.Provider value={{ 
      activeMachine, 
      setActiveMachine, 
      machines, 
      loading, 
      refreshMachines, 
      isSimulated,
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
