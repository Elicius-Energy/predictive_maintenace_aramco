import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode, FC } from 'react';
import axios from 'axios';
import { useSensorData } from '../hooks/useSensorData';
import { useMachine } from './MachineContext';
import { BACKEND_URL } from '../utils/constants';
import type { FeatureVector } from '../types';

interface HistoryContextType {
  tempHistory: any[];
  anomalyHistory: any[];
  mechanicalHistory: any[];
  electricalHistory: any[];
  latestHistoricalFeatures: FeatureVector | null;
  isFetching: boolean;
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);

// Max data points kept per history array
const MAX_BUFFER = 500;

/** Parse a timestamp string to epoch ms, handling optional trailing Z */
function toEpoch(ts: string): number {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z').getTime();
}

export const HistoryProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const { latestReading, latestFeatures } = useSensorData();
  const { activeMachine, selectedWindow } = useMachine();

  const [tempHistory, setTempHistory] = useState<any[]>([]);
  const [anomalyHistory, setAnomalyHistory] = useState<any[]>([]);
  const [mechanicalHistory, setMechanicalHistory] = useState<any[]>([]);
  const [electricalHistory, setElectricalHistory] = useState<any[]>([]);
  const [latestHistoricalFeatures, setLatestHistoricalFeatures] = useState<FeatureVector | null>(null);
  const [isFetching, setIsFetching] = useState(false);

  /** Fetch historical blocks from the database */
  const fetchHistory = useCallback(async () => {
    if (!activeMachine) {
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
        toEpoch(a.timestamp) - toEpoch(b.timestamp)
      );
      const features = [...featuresRes.data].sort((a: any, b: any) => 
        toEpoch(a.timestamp) - toEpoch(b.timestamp)
      );

      if (features.length > 0) {
        setLatestHistoricalFeatures(features[features.length - 1].feature_data || features[features.length - 1]);
      }

      setMechanicalHistory(readings.map((r: any) => ({
        timestamp: r.timestamp,
        ax: r.ax || 0,
        ay: r.ay || 0,
        az: r.az || 0,
      })).slice(-MAX_BUFFER));

      // Build electrical history from features (not readings) since features contain
      // the full 3-phase data from ElectricalFeatures. The raw sensor_readings table
      // doesn't store per-phase columns (v1n, i1, kw1, etc.).
      setElectricalHistory(features.map((f: any) => {
        const el = f.feature_data?.electrical || {};
        return {
          timestamp: f.timestamp,
          dTS: el.dTS || 0,
          p: el.active_power || 0,
          kva: el.apparent_power || 0,
          i: el.current || 0,
          pf: el.power_factor || 0,
          v1n: el.v1n || 0, v2n: el.v2n || 0, v3n: el.v3n || 0,
          i1: el.i1 || 0, i2: el.i2 || 0, i3: el.i3 || 0,
          kw1: el.kw1 || 0, kw2: el.kw2 || 0, kw3: el.kw3 || 0,
        };
      }).slice(-MAX_BUFFER));

      setTempHistory(features.map((f: any) => ({
        timestamp: f.timestamp,
        temperature: f.feature_data?.temperature || 0,
      })).slice(-MAX_BUFFER));

      setAnomalyHistory(features.map((f: any) => ({
        timestamp: f.timestamp,
        anomaly: (f.feature_data?.anomaly_score || 0) * 100,
        health: f.feature_data?.health_score || 0,
      })).slice(-MAX_BUFFER));

    } catch (err) {
      console.error('Failed to pre-load historical data:', err);
    } finally {
      setIsFetching(false);
    }
  }, [activeMachine?.machine_id, selectedWindow]);

  // Trigger fetch on selection changes
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Append sensor readings directly (no 1-second delay)
  useEffect(() => {
    if (latestReading && latestReading.machine_id === activeMachine?.machine_id) {
      const cutoff = Date.now() - selectedWindow * 60 * 1000;
      
      setMechanicalHistory(prev => {
        const merged = [...prev, {
          timestamp: latestReading.timestamp,
          ax: latestReading.accel?.ax || 0,
          ay: latestReading.accel?.ay || 0,
          az: latestReading.accel?.az || 0,
        }];
        return merged.filter(d => toEpoch(d.timestamp) >= cutoff).slice(-MAX_BUFFER);
      });

      // NOTE: We intentionally do NOT append to electricalHistory here.
      // The raw sensor_data message has a legacy EnergyData object without
      // per-phase fields (v1n, i1, kw1 etc.), so appending it would inject
      // rows with 0 values that pollute the chart tooltips.
      // Instead, electricalHistory is populated exclusively from the
      // latestFeatures effect below, which carries the full 3-phase data.
    }
  }, [latestReading, activeMachine?.machine_id, selectedWindow]);

  // Append feature data directly
  useEffect(() => {
    if (latestFeatures && latestFeatures.machine_id === activeMachine?.machine_id) {
      const cutoff = Date.now() - selectedWindow * 60 * 1000;
      
      // Also update electrical history from features since it contains the full 3-phase data
      setElectricalHistory(prev => {
        const merged = [...prev, {
          timestamp: latestFeatures.timestamp,
          dTS: latestFeatures.electrical?.dTS || 0,
          p: latestFeatures.electrical.active_power || 0,
          kva: latestFeatures.electrical.apparent_power || 0,
          i: latestFeatures.electrical.current || 0,
          pf: latestFeatures.electrical.power_factor || 0,
          v1n: latestFeatures.electrical.v1n || 0,
          v2n: latestFeatures.electrical.v2n || 0,
          v3n: latestFeatures.electrical.v3n || 0,
          i1: latestFeatures.electrical.i1 || 0,
          i2: latestFeatures.electrical.i2 || 0,
          i3: latestFeatures.electrical.i3 || 0,
          kw1: latestFeatures.electrical.kw1 || 0,
          kw2: latestFeatures.electrical.kw2 || 0,
          kw3: latestFeatures.electrical.kw3 || 0,
        }];
        // Deduplicate by timestamp if needed, but for simplicity just append and sort/filter
        return merged.filter(d => toEpoch(d.timestamp) >= cutoff).slice(-MAX_BUFFER);
      });

      setTempHistory(prev => {
        const merged = [...prev, {
          timestamp: latestFeatures.timestamp,
          temperature: latestFeatures.temperature || 0,
        }];
        return merged.filter(d => toEpoch(d.timestamp) >= cutoff).slice(-MAX_BUFFER);
      });
      
      setAnomalyHistory(prev => {
        const merged = [...prev, {
          timestamp: latestFeatures.timestamp,
          anomaly: (latestFeatures.anomaly_score || 0) * 100,
          health: latestFeatures.health_score || 0,
        }];
        return merged.filter(d => toEpoch(d.timestamp) >= cutoff).slice(-MAX_BUFFER);
      });
    }
  }, [latestFeatures, activeMachine?.machine_id, selectedWindow]);

  return (
    <HistoryContext.Provider value={{
      tempHistory,
      anomalyHistory,
      mechanicalHistory,
      electricalHistory,
      latestHistoricalFeatures,
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

