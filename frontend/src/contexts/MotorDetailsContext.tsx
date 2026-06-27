import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode, FC } from 'react';
import { useMachine } from './MachineContext';
import api from '../utils/api';

export interface MotorDetails {
  motorName: string;
  location: string;
  connectedLoad: string;
  motorType: 'Induction Motor' | 'SynRM';
  manufacturer: string;
  ratedPower: number;       // kW
  ratedSpeed: number;       // RPM
  ratedEfficiency: number;  // %
  motorPrice: number;       // currency
  electricityCost: number;  // per kWh
  nameplateImage: string | null; // base64 data URL
}

interface MotorDetailsContextType {
  motorDetails: MotorDetails | null;
  saveMotorDetails: (details: MotorDetails) => Promise<void>;
  resetMotorDetails: () => Promise<void>;
  refreshMotorDetails: () => Promise<void>;
  isMotorConfigured: boolean;
  loading: boolean;
}

const MotorDetailsContext = createContext<MotorDetailsContextType | undefined>(undefined);

export const MotorDetailsProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const { activeMachine } = useMachine();
  const [motorDetails, setMotorDetailsState] = useState<MotorDetails | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const refreshMotorDetails = useCallback(async () => {
    if (!activeMachine?.machine_id) {
      setMotorDetailsState(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await api.get(`/api/data/machines/${activeMachine.machine_id}/config`);
      if (res.data) {
        setMotorDetailsState(res.data as MotorDetails);
      } else {
        setMotorDetailsState(null);
      }
    } catch (err: any) {
      if (err.response?.status === 404) {
        setMotorDetailsState(null); // No config exists yet
      } else {
        console.error('Failed to load motor config:', err);
      }
    } finally {
      setLoading(false);
    }
  }, [activeMachine]);

  useEffect(() => {
    refreshMotorDetails();
  }, [refreshMotorDetails]);

  const saveMotorDetails = async (details: MotorDetails) => {
    if (!activeMachine?.machine_id) return;
    try {
      await api.post(`/api/data/machines/${activeMachine.machine_id}/config`, details);
      setMotorDetailsState(details);
    } catch (err) {
      console.error('Failed to save motor config:', err);
      throw err;
    }
  };

  const resetMotorDetails = async () => {
    if (!activeMachine?.machine_id) return;
    try {
      await api.delete(`/api/data/machines/${activeMachine.machine_id}/config`);
      setMotorDetailsState(null);
    } catch (err) {
      console.error('Failed to reset motor config:', err);
      throw err;
    }
  };

  const isMotorConfigured = motorDetails !== null &&
    motorDetails.motorName.trim() !== '' &&
    motorDetails.ratedPower > 0 &&
    motorDetails.ratedSpeed > 0 &&
    motorDetails.ratedEfficiency > 0;

  return (
    <MotorDetailsContext.Provider value={{
      motorDetails,
      saveMotorDetails,
      resetMotorDetails,
      refreshMotorDetails,
      isMotorConfigured,
      loading,
    }}>
      {children}
    </MotorDetailsContext.Provider>
  );
};

export const useMotorDetails = () => {
  const context = useContext(MotorDetailsContext);
  if (context === undefined) {
    throw new Error('useMotorDetails must be used within a MotorDetailsProvider');
  }
  return context;
};
