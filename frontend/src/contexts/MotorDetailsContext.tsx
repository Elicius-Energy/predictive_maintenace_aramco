import { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode, FC } from 'react';

export interface MotorDetails {
  motorName: string;
  location: string;
  connectedLoad: string;
  motorType: 'Induction Motor' | 'SynRM';
  manufacturer: string;
  ratedPower: number;       // kW
  ratedEfficiency: number;  // %
  motorPrice: number;       // currency
  electricityCost: number;  // per kWh
  nameplateImage: string | null; // base64 data URL
}

interface MotorDetailsContextType {
  motorDetails: MotorDetails | null;
  setMotorDetails: (details: MotorDetails) => void;
  clearMotorDetails: () => void;
  isMotorConfigured: boolean;
}

const STORAGE_KEY = 'ledl_motor_details';

const MotorDetailsContext = createContext<MotorDetailsContextType | undefined>(undefined);

function loadFromStorage(): MotorDetails | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return JSON.parse(stored) as MotorDetails;
    }
  } catch {
    console.warn('Failed to load motor details from localStorage');
  }
  return null;
}

function saveToStorage(details: MotorDetails): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(details));
  } catch {
    console.warn('Failed to save motor details to localStorage');
  }
}

export const MotorDetailsProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [motorDetails, setMotorDetailsState] = useState<MotorDetails | null>(() => loadFromStorage());

  const setMotorDetails = useCallback((details: MotorDetails) => {
    setMotorDetailsState(details);
    saveToStorage(details);
  }, []);

  const clearMotorDetails = useCallback(() => {
    setMotorDetailsState(null);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  const isMotorConfigured = motorDetails !== null &&
    motorDetails.motorName.trim() !== '' &&
    motorDetails.ratedPower > 0 &&
    motorDetails.ratedEfficiency > 0;

  return (
    <MotorDetailsContext.Provider value={{
      motorDetails,
      setMotorDetails,
      clearMotorDetails,
      isMotorConfigured,
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
