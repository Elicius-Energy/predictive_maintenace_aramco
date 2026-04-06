/**
 * System constants and config.
 */

export const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/stream';

export const COLORS = {
  HEALTHY: '#10b981',
  WARNING: '#f59e0b',
  CRITICAL: '#ef4444',
  INFO: '#06b6d4',
  DARK: '#0a0e1a',
  CARD: '#111827',
  BORDER: '#1e3a5f',
  TEXT: {
    PRIMARY: '#f8fafc',
    SECONDARY: '#94a3b8',
  }
};

export const MACHINE_PLANTS = [
  { id: 'ras-tanura', name: 'Ras Tanura Refinery' },
  { id: 'jubail', name: 'Jubail Industrial Complex' },
  { id: 'yanbu', name: 'Yanbu Integrated' }
];

export const MACHINE_UNITS = [
  { id: 'pu3', name: 'Processing Unit 3', plantId: 'ras-tanura' },
  { id: 'pu4', name: 'Processing Unit 4', plantId: 'ras-tanura' },
];
