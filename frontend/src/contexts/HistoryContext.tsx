import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import type { ReactNode, FC } from 'react';
import api from '../utils/api';

import { useMachine } from './MachineContext';
import type { FeatureVector } from '../types';

interface HistoryContextType {
  tempHistory: any[];
  anomalyHistory: any[];
  mechanicalHistory: any[];
  electricalHistory: any[];
  latestHistoricalFeatures: FeatureVector | null;
  isFetching: boolean;
  periodEnergy: number; // kWh integrated over selected time window
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);

// Max data points kept per history array
const MAX_BUFFER = 500;

/** Parse a timestamp string to epoch ms, handling optional trailing Z */
function toEpoch(ts: string): number {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z').getTime();
}

export const HistoryProvider: FC<{ children: ReactNode }> = ({ children }) => {

  const { activeMachine, timeRange } = useMachine();

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
        api.get(`/api/data/history`, {
          params: { 
            machine_id: activeMachine.machine_id, 
            start_time: new Date(timeRange.start).toISOString(),
            end_time: new Date(timeRange.end).toISOString()
          }
        }),
        api.get(`/api/data/features`, {
          params: { 
            machine_id: activeMachine.machine_id, 
            start_time: new Date(timeRange.start).toISOString(),
            end_time: new Date(timeRange.end).toISOString()
          }
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
          v12: el.v12 || 0, v23: el.v23 || 0, v31: el.v31 || 0,
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
  }, [activeMachine?.machine_id, timeRange.start, timeRange.end]);

  // Trigger fetch on selection changes
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  // Live data appending removed per user request so that line charts only show data for the selected START/END periods.

  // Compute period energy by trapezoid integration of active power over the time window
  const periodEnergy = useMemo(() => {
    if (electricalHistory.length < 2) return 0;
    let totalKwh = 0;
    for (let i = 1; i < electricalHistory.length; i++) {
      const p0 = electricalHistory[i - 1].p || 0; // active power in kW
      const p1 = electricalHistory[i].p || 0;
      const t0 = toEpoch(electricalHistory[i - 1].timestamp);
      const t1 = toEpoch(electricalHistory[i].timestamp);
      const dtHours = (t1 - t0) / 3600000; // ms → hours
      if (dtHours > 0 && dtHours < 1) { // skip gaps > 1 hour
        totalKwh += ((p0 + p1) / 2) * dtHours;
      }
    }
    return Math.abs(totalKwh);
  }, [electricalHistory]);

  return (
    <HistoryContext.Provider value={{
      tempHistory,
      anomalyHistory,
      mechanicalHistory,
      electricalHistory,
      latestHistoricalFeatures,
      isFetching,
      periodEnergy
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

