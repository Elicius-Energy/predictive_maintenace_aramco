import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import type { ReactNode, FC } from 'react';
import api from '../utils/api';

import { useMachine } from './MachineContext';
import { useSensorData } from '../hooks/useSensorData';
import type { FeatureVector } from '../types';

interface HistoryContextType {
  tempHistory: any[];
  anomalyHistory: any[];
  mechanicalHistory: any[];
  electricalHistory: any[];
  latestHistoricalFeatures: FeatureVector | null;
  isFetching: boolean;
  periodEnergy: number; // kWh integrated over selected time window
  runTimeHours: number; // hours motor was running over selected time window
}

const HistoryContext = createContext<HistoryContextType | undefined>(undefined);

// Max data points kept per history array
const MAX_BUFFER = 500;

/** Parse a timestamp string to epoch ms, handling optional trailing Z */
function toEpoch(ts: string): number {
  return new Date(ts.endsWith('Z') ? ts : ts + 'Z').getTime();
}

export const HistoryProvider: FC<{ children: ReactNode }> = ({ children }) => {

  const { activeMachine, timeRange, isAutoUpdate } = useMachine();
  const { latestFeatures } = useSensorData();

  const [tempHistory, setTempHistory] = useState<any[]>([]);
  const [anomalyHistory, setAnomalyHistory] = useState<any[]>([]);
  const [mechanicalHistory, setMechanicalHistory] = useState<any[]>([]);
  const [electricalHistory, setElectricalHistory] = useState<any[]>([]);
  const [latestHistoricalFeatures, setLatestHistoricalFeatures] = useState<FeatureVector | null>(null);
  const [isFetching, setIsFetching] = useState(false);
  const [periodEnergy, setPeriodEnergy] = useState(0);
  const [runTimeHours, setRunTimeHours] = useState(0);

  /** Fetch historical blocks from the database */
  const fetchHistory = useCallback(async () => {
    if (!activeMachine) {
      return;
    }

    setIsFetching(true);
    try {
      const [readingsRes, featuresRes, statsRes] = await Promise.all([
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
        }),
        api.get(`/api/data/stats`, {
          params: { machine_id: activeMachine.machine_id }
        })
      ]);

      // Backend returns newest first, we want oldest first for charts
      let readings = [...readingsRes.data].sort((a: any, b: any) => 
        toEpoch(a.timestamp) - toEpoch(b.timestamp)
      );
      let features = [...featuresRes.data].sort((a: any, b: any) => 
        toEpoch(a.timestamp) - toEpoch(b.timestamp)
      );

      const downsample10Min = (data: any[]) => {
        if (!data || data.length === 0) return [];
        const downsampled = [];
        const TEN_MIN_MS = 10 * 60 * 1000;
        let currentBucket = Math.floor(toEpoch(data[0].timestamp) / TEN_MIN_MS);
        let latestInBucket = data[0];

        for (let i = 1; i < data.length; i++) {
          const bucket = Math.floor(toEpoch(data[i].timestamp) / TEN_MIN_MS);
          if (bucket === currentBucket) {
            latestInBucket = data[i];
          } else {
            downsampled.push(latestInBucket);
            currentBucket = bucket;
            latestInBucket = data[i];
          }
        }
        downsampled.push(latestInBucket);
        return downsampled;
      };

      readings = downsample10Min(readings);
      features = downsample10Min(features);

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
          p: el.t_kw || el.active_power || 0,
          kva: el.t_kva || el.apparent_power || 0,
          i: el.i_avg || el.current || 0,
          pf: el.pf_avg || el.power_factor || 0,
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

      if (statsRes.data) {
        setPeriodEnergy(statsRes.data.total_energy_kwh || 0);
        setRunTimeHours(statsRes.data.run_time_hours || 0);
      }

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

  // Live data appending
  useEffect(() => {
    if (!isAutoUpdate || !latestFeatures) return;

    const f = latestFeatures as any;
    const el = f.electrical || f.feature_data?.electrical || {};

    setMechanicalHistory(prev => {
      const newEntry = {
        timestamp: f.timestamp,
        ax: f.vibration?.rms_x || 0,
        ay: f.vibration?.rms_y || 0,
        az: f.vibration?.rms_z || 0,
      };
      return [...prev, newEntry].slice(-MAX_BUFFER);
    });

    setElectricalHistory(prev => {
      const newEntry = {
        timestamp: f.timestamp,
        dTS: el.dTS || 0,
        p: el.t_kw ?? el.active_power ?? 0,
        kva: el.t_kva ?? el.apparent_power ?? 0,
        i: el.i_avg ?? el.current ?? 0,
        pf: el.pf_avg ?? el.power_factor ?? 0,
        v1n: el.v1n || 0, v2n: el.v2n || 0, v3n: el.v3n || 0,
        v12: el.v12 || 0, v23: el.v23 || 0, v31: el.v31 || 0,
        i1: el.i1 || 0, i2: el.i2 || 0, i3: el.i3 || 0,
        kw1: el.kw1 || 0, kw2: el.kw2 || 0, kw3: el.kw3 || 0,
      };
      return [...prev, newEntry].slice(-MAX_BUFFER);
    });

    setTempHistory(prev => {
      const newEntry = {
        timestamp: f.timestamp,
        temperature: f.temperature || f.feature_data?.temperature || 0,
      };
      return [...prev, newEntry].slice(-MAX_BUFFER);
    });

    setAnomalyHistory(prev => {
      const newEntry = {
        timestamp: f.timestamp,
        anomaly: (f.anomaly_score || f.feature_data?.anomaly_score || 0) * 100,
        health: f.health_score || f.feature_data?.health_score || 0,
      };
      return [...prev, newEntry].slice(-MAX_BUFFER);
    });

  }, [latestFeatures, isAutoUpdate]);



  return (
    <HistoryContext.Provider value={{
      tempHistory,
      anomalyHistory,
      mechanicalHistory,
      electricalHistory,
      latestHistoricalFeatures,
      isFetching,
      periodEnergy,
      runTimeHours
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

