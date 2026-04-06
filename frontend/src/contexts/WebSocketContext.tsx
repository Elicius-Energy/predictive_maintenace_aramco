import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { flushSync } from 'react-dom';
import type { ReactNode, FC } from 'react';
import { WS_URL } from '../utils/constants';
import type { WSMessage } from '../types';

interface WebSocketContextType {
  lastMessage: WSMessage | null;
  isConnected: boolean;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

/** Generate realistic simulated sensor data */
function generateSimulatedMessage(machineId: string): WSMessage {
  const now = new Date().toISOString();
  const rand = (min: number, max: number) => min + Math.random() * (max - min);
  const randNormal = (mean: number, std: number) => mean + (Math.random() - 0.5) * 2 * std;

  // Cycle through message types to simulate full data flow
  const types: WSMessage['type'][] = ['sensor_data', 'features', 'machine_health'];
  const type = types[Math.floor(Math.random() * types.length)];

  if (type === 'sensor_data') {
    return {
      type: 'sensor_data',
      timestamp: now,
      data: {
        timestamp: now,
        machine_id: machineId,
        source: 'simulated' as const,
        energy: {
          V: randNormal(415, 5),
          I: randNormal(8.5, 1.5),
          P: randNormal(4.2, 0.8),
          KVA: randNormal(5.0, 0.9),
          pf: randNormal(0.85, 0.05),
          Energy: rand(100, 500),
          Freq: randNormal(50.0, 0.2),
        },
        accel: {
          ax: randNormal(0, 1.5),
          ay: randNormal(0, 1.2),
          az: randNormal(0.98, 1.0),
          gx: randNormal(0, 5),
          gy: randNormal(0, 5),
          gz: randNormal(0, 5),
        },
        temperature: randNormal(55, 8),
      },
    };
  }

  if (type === 'features') {
    const rmsOverall = rand(0.5, 4.0);
    return {
      type: 'features',
      timestamp: now,
      data: {
        timestamp: now,
        machine_id: machineId,
        vibration: {
          rms_x: rand(0.3, 3.0),
          rms_y: rand(0.3, 2.5),
          rms_z: rand(0.3, 2.0),
          rms_overall: rmsOverall,
          peak_x: rand(1, 6),
          peak_y: rand(1, 5),
          peak_z: rand(1, 4),
          kurtosis_x: rand(2.5, 5),
          kurtosis_y: rand(2.5, 4.5),
          kurtosis_z: rand(2.5, 4),
          crest_factor: rand(2, 5),
          dominant_freq: rand(20, 120),
          fft_magnitudes: Array.from({ length: 64 }, () => rand(0, 0.8)),
          fft_frequencies: Array.from({ length: 64 }, (_, i) => i * 3.125),
        },
        electrical: {
          voltage: randNormal(415, 5),
          current: randNormal(8.5, 1.5),
          active_power: randNormal(4.2, 0.8),
          apparent_power: randNormal(5.0, 0.9),
          power_factor: randNormal(0.85, 0.05),
          frequency: randNormal(50.0, 0.2),
          efficiency: randNormal(88, 4),
          load_percentage: randNormal(72, 10),
          energy_cumulative: rand(100, 500),
        },
        temperature: randNormal(55, 8),
        anomaly_score: rand(0, 0.4),
        health_score: rand(75, 98),
        iso_zone: rmsOverall < 1.8 ? 'A' : rmsOverall < 4.5 ? 'B' : 'C',
      },
    };
  }

  // machine_health
  return {
    type: 'machine_health',
    timestamp: now,
    data: {
      machine_id: machineId,
      overall_status: 'healthy',
      health_score: rand(80, 98),
      indicators: [
        { name: 'Bearing Health', probability: rand(0.02, 0.15), status: 'healthy', description: 'No anomalous frequency detected' },
        { name: 'Imbalance', probability: rand(0.01, 0.10), status: 'healthy', description: 'Vibration within ISO limits' },
        { name: 'Misalignment', probability: rand(0.01, 0.12), status: 'healthy', description: 'Axial/radial within tolerance' },
        { name: 'Electrical Fault', probability: rand(0.01, 0.08), status: 'healthy', description: 'Power quality nominal' },
      ],
      last_updated: now,
    },
  };
}

export const WebSocketProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [lastMessage, setLastMessage] = useState<WSMessage | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const simIntervalRef = useRef<number | null>(null);
  const failCountRef = useRef(0);

  const startSimulation = useCallback(() => {
    if (simIntervalRef.current) return; // already running
    console.info('Starting simulated data feed.');
    simIntervalRef.current = window.setInterval(() => {
      const machineIds = ['sim-pump-001', 'sim-pump-002', 'sim-motor-003'];
      const id = machineIds[Math.floor(Math.random() * machineIds.length)];
      setLastMessage(generateSimulatedMessage(id));
    }, 150);
  }, []);

  const stopSimulation = useCallback(() => {
    if (simIntervalRef.current) {
      clearInterval(simIntervalRef.current);
      simIntervalRef.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        failCountRef.current = 0;
        stopSimulation();
      };

      ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          flushSync(() => {
            setLastMessage(message);
          });
        } catch (err) {
          console.error('Failed to parse WS message:', err);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        failCountRef.current += 1;
        // After 2 failed attempts, start simulation
        if (failCountRef.current >= 2) {
          startSimulation();
        }
        reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      failCountRef.current += 1;
      if (failCountRef.current >= 2) {
        startSimulation();
      }
      reconnectTimeoutRef.current = window.setTimeout(connect, 5000);
    }
  }, [startSimulation, stopSimulation]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      stopSimulation();
      socketRef.current?.close();
    };
  }, [connect, stopSimulation]);

  return (
    <WebSocketContext.Provider value={{ lastMessage, isConnected }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
