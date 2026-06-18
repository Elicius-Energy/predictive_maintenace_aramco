/**
 * System constants and config.
 */

const normalizeBaseUrl = (value?: string) => {
  const trimmed = value?.trim();
  if (!trimmed) return '';
  return trimmed.endsWith('/') ? trimmed.slice(0, -1) : trimmed;
};

const defaultBackendUrl = import.meta.env.DEV
  ? (typeof window !== 'undefined' ? `${window.location.protocol}//${window.location.hostname}:8000` : 'http://localhost:8000')
  : '';
const browserWsUrl = typeof window !== 'undefined'
  ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/stream`
  : 'ws://localhost:8000/ws/stream';
const defaultWsUrl = import.meta.env.DEV
  ? (typeof window !== 'undefined' ? `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.hostname}:8000/ws/stream` : 'ws://localhost:8000/ws/stream')
  : browserWsUrl;

export const BACKEND_URL = normalizeBaseUrl(import.meta.env.VITE_BACKEND_URL) || defaultBackendUrl;
export const WS_URL = normalizeBaseUrl(import.meta.env.VITE_WS_URL) || defaultWsUrl;

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
