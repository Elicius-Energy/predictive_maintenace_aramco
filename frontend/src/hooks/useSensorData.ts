import { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useMachine } from '../contexts/MachineContext';
import type { SensorReading, FeatureVector, MachineHealth, Alert, FaultDiagnosis } from '../types';

export const useSensorData = () => {
  const { subscribe, isConnected } = useWebSocket();
  const { activeMachine } = useMachine();
  
  const [latestReading, setLatestReading] = useState<SensorReading | null>(null);
  const [latestFeatures, setLatestFeatures] = useState<FeatureVector | null>(null);
  const [latestHealth, setLatestHealth] = useState<MachineHealth | null>(null);
  const [latestDiagnosis, setLatestDiagnosis] = useState<FaultDiagnosis | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([]);

  // Reset all state when machine changes
  useEffect(() => {
    setLatestReading(null);
    setLatestFeatures(null);
    setLatestHealth(null);
    setLatestDiagnosis(null);
    setActiveAlerts([]);
  }, [activeMachine?.machine_id]);

  useEffect(() => {
    return subscribe((message) => {
      // Filter by active machine
      if (message.data.machine_id && activeMachine && message.data.machine_id !== activeMachine.machine_id) {
          return;
      }

      switch (message.type) {
        case 'sensor_data':
          setLatestReading(message.data);
          break;
        case 'features':
          setLatestFeatures(message.data);
          break;
        case 'machine_health':
          setLatestHealth(message.data);
          break;
        case 'ai_diagnosis':
          setLatestDiagnosis(message.data);
          break;
        case 'alert':
          setActiveAlerts(prev => [message.data, ...prev].slice(0, 50));
          break;
      }
    });
  }, [subscribe, activeMachine]);

  return {
    latestReading,
    latestFeatures,
    latestHealth,
    latestDiagnosis,
    activeAlerts,
    isConnected
  };
};
