import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode, FC } from 'react';
import axios from 'axios';
import { useSensorData } from '../hooks/useSensorData';
import { useMachine } from './MachineContext';
import { BACKEND_URL } from '../utils/constants';

interface HistoryContextType {
  tempHistory: any[];
  anomalyHistory: any[];
  mechanicalHistory: any[];
  electricalHistory: any[];
  isFetching: boolean;
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);

export const HistoryProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const { latestReading, latestFeatures } = useSensorData();
  const { activeMachine, selectedWindow, isSimulated } = useMachine();

  const [tempHistory, setTempHistory] = useState<any[]>([]);
  const [anomalyHistory, setAnomalyHistory] = useState<any[]>([]);
  const [mechanicalHistory, setMechanicalHistory] = useState<any[]>([]);
  const [electricalHistory, setElectricalHistory] = useState<any[]>([]);
  const [isFetching, setIsFetching] = useState(false);

  /** Fetch historical blocks from the database */
  const fetchHistory = useCallback(async () => {
    if (!activeMachine || isSimulated) {
      // In simulation mode, we just start fresh
      setTempHistory([]);
      setAnomalyHistory([]);
      setMechanicalHistory([]);
      setElectricalHistory([]);
      return;
    }

    setIsFetching(true);
    try {
      const [readingsRes, featuresRes] = await Promise.all([
        axios.get(`${BACKEND_URL}/api/data/history`, {
          params: { machine_id: activeMachine.machine_id, minutes: selectedWindow }
        }),
        axios.get(`${BACKEND_URL}/api/data/features`, {
          params: { machine_id: activeMachine.machine_id, minutes: selectedWindow }
        })
      ]);

      // Backend returns newest first, we want oldest first for charts
      const readings = [...readingsRes.data].sort((a: any, b: any) => 
        new Date(a.timestamp.endsWith('Z') ? a.timestamp : a.timestamp + 'Z').getTime() - new Date(b.timestamp.endsWith('Z') ? b.timestamp : b.timestamp + 'Z').getTime()
      );
      const features = [...featuresRes.data].sort((a: any, b: any) => 
        new Date(a.timestamp.endsWith('Z') ? a.timestamp : a.timestamp + 'Z').getTime() - new Date(b.timestamp.endsWith('Z') ? b.timestamp : b.timestamp + 'Z').getTime()
      );

      setMechanicalHistory(readings.map((r: any) => ({
        timestamp: r.timestamp,
        ax: r.ax || 0,
        ay: r.ay || 0,
        az: r.az || 0,
      })));

      setElectricalHistory(readings.map((r: any) => ({
        timestamp: r.timestamp,
        p: r.active_power || 0,
        kva: r.apparent_power || 0,
        i: r.current || 0,
        pf: r.power_factor || 0,
      })));

      setTempHistory(features.map((f: any) => ({
        timestamp: f.timestamp,
        temperature: f.feature_data?.temperature || 0,
      })));

      setAnomalyHistory(features.map((f: any) => ({
        timestamp: f.timestamp,
        anomaly: (f.feature_data?.anomaly_score || 0) * 100,
        health: f.feature_data?.health_score || 0,
      })));

    } catch (err) {
      console.error('Failed to pre-load historical data:', err);
    } finally {
      setIsFetching(false);
    }
  }, [activeMachine?.machine_id, selectedWindow, isSimulated]);

  // Trigger fetch on selection changes
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Update Mechanical & Electrical History via WebSocket (Append)
  useEffect(() => {
    if (latestReading && latestReading.machine_id === activeMachine?.machine_id) {
      const readingTs = latestReading.timestamp.endsWith('Z') ? latestReading.timestamp : latestReading.timestamp + 'Z';
      const cutoff = new Date(readingTs).getTime() - (selectedWindow * 60 * 1000);
      
      setMechanicalHistory(prev => {
        const newData = [...prev, {
          timestamp: latestReading.timestamp,
          ax: latestReading.accel?.ax || 0,
          ay: latestReading.accel?.ay || 0,
          az: latestReading.accel?.az || 0,
        }].filter(d => new Date(d.timestamp.endsWith('Z') ? d.timestamp : d.timestamp + 'Z').getTime() >= cutoff);
        return newData.slice(-2000); // Buffer size matching DB limit
      });

      if (latestReading.energy) {
        setElectricalHistory(prev => {
          const newData = [...prev, {
            timestamp: latestReading.timestamp,
            p: latestReading.energy?.P || 0,
            kva: latestReading.energy?.KVA || 0,
            i: latestReading.energy?.I || 0,
            pf: latestReading.energy?.pf || 0,
          }].filter(d => new Date(d.timestamp.endsWith('Z') ? d.timestamp : d.timestamp + 'Z').getTime() >= cutoff);
          return newData.slice(-2000);
        });
      }
    }
  }, [latestReading, activeMachine?.machine_id, selectedWindow]);

  // Update Other Params History via WebSocket (Append)
  useEffect(() => {
    if (latestFeatures && latestFeatures.machine_id === activeMachine?.machine_id) {
      const ts = latestFeatures.timestamp;
      const parsedTs = ts.endsWith('Z') ? ts : ts + 'Z';
      const cutoff = new Date(parsedTs).getTime() - (selectedWindow * 60 * 1000);
      
      setTempHistory(prev => {
        const newData = [...prev, {
          timestamp: ts,
          temperature: latestFeatures.temperature || 0,
        }].filter(d => new Date(d.timestamp.endsWith('Z') ? d.timestamp : d.timestamp + 'Z').getTime() >= cutoff);
        return newData.slice(-2000);
      });
      setAnomalyHistory(prev => {
        const newData = [...prev, {
          timestamp: ts,
          anomaly: (latestFeatures.anomaly_score || 0) * 100,
          health: latestFeatures.health_score || 0,
        }].filter(d => new Date(d.timestamp.endsWith('Z') ? d.timestamp : d.timestamp + 'Z').getTime() >= cutoff);
        return newData.slice(-2000);
      });
    }
  }, [latestFeatures, activeMachine?.machine_id, selectedWindow]);

  return (
    <HistoryContext.Provider value={{
      tempHistory,
      anomalyHistory,
      mechanicalHistory,
      electricalHistory,
      isFetching
    }}>
      {children}
    </HistoryContext.Provider>
  );
};

export const useHistory = () => {
  const context = useContext(HistoryContext);
  if (context === undefined) {
    throw new Error('useHistory must be used within a HistoryProvider');
  }
  return context;
};
