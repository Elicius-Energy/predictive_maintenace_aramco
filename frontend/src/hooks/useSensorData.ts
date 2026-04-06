import { useState, useEffect } from 'react';
import { useWebSocket } from '../contexts/WebSocketContext';
import { useMachine } from '../contexts/MachineContext';
import type { SensorReading, FeatureVector, MachineHealth, Alert, FaultDiagnosis } from '../types';

export const useSensorData = () => {
  const { lastMessage, isConnected } = useWebSocket();
  const { activeMachine } = useMachine();
  
  const [latestReading, setLatestReading] = useState<SensorReading | null>(null);
  const [latestFeatures, setLatestFeatures] = useState<FeatureVector | null>(null);
  const [latestHealth, setLatestHealth] = useState<MachineHealth | null>(null);
  const [latestDiagnosis, setLatestDiagnosis] = useState<FaultDiagnosis | null>(null);
  const [activeAlerts, setActiveAlerts] = useState<Alert[]>([]);

  // Reset all state when machine changes to avoid stale data from previous asset
  useEffect(() => {
    setLatestReading(null);
    setLatestFeatures(null);
    setLatestHealth(null);
    setLatestDiagnosis(null);
    setActiveAlerts([]);
  }, [activeMachine?.machine_id]);

  useEffect(() => {
    if (!lastMessage) return;
    
    // Filter by active machine
    if (lastMessage.data.machine_id && activeMachine && lastMessage.data.machine_id !== activeMachine.machine_id) {
        return;
    }

    switch (lastMessage.type) {
      case 'sensor_data':
        setLatestReading(lastMessage.data);
        break;
      case 'features':
        setLatestFeatures(lastMessage.data);
        break;
      case 'machine_health':
        setLatestHealth(lastMessage.data);
        break;
      case 'ai_diagnosis':
        setLatestDiagnosis(lastMessage.data);
        break;
      case 'alert':
        setActiveAlerts(prev => [lastMessage.data, ...prev].slice(0, 50));
        break;
    }
  }, [lastMessage, activeMachine]);

  return {
    latestReading,
    latestFeatures,
    latestHealth,
    latestDiagnosis,
    activeAlerts,
    isConnected
  };
};
