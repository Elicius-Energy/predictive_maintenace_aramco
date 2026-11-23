/**
 * Client-side session persistence helpers (retained across page navigation & reloads,
 * cleared automatically on user login / logout via AuthContext).
 */

export const STORAGE_KEYS = {
  DASHBOARD_PERIOD: 'elicius_dashboard_period',
  DASHBOARD_ACTIVE_PARAMS: 'elicius_dashboard_active_params',
  CONFIG_DRAFTS: 'elicius_config_drafts',
  CONFIG_OPEN_SECTIONS: 'elicius_config_open_sections',
  REPORT_DRAFTS: 'elicius_report_drafts',
  POWER_STUDIES: 'elicius_power_study_sessions',
  LATEST_NAMEPLATE: 'elicius_latest_motor_nameplate',
  SESSION_ACKED_ALERTS: 'elicius_session_acked_alerts',
} as const;

// ── Power Study Stopwatch Sessions (per device) ───────────────────────────────

export interface PowerStudySession {
  status: 'idle' | 'running' | 'completed';
  startedAt: string; // ISO UTC
  stoppedAt: string | null; // ISO UTC
  updatedAt: string; // ISO UTC (used to detect newly started/stopped studies)
}

function readJsonMap<T>(key: string): Record<string, T> {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}

function writeJsonMap<T>(key: string, map: Record<string, T>): void {
  try {
    localStorage.setItem(key, JSON.stringify(map));
  } catch {
    // Ignore storage quota / privacy mode errors
  }
}

export function getPowerStudy(deviceId: string | null): PowerStudySession | null {
  if (!deviceId) return null;
  const map = readJsonMap<PowerStudySession>(STORAGE_KEYS.POWER_STUDIES);
  return map[deviceId] || null;
}

export function startPowerStudy(deviceId: string): PowerStudySession {
  const nowIso = new Date().toISOString();
  const session: PowerStudySession = {
    status: 'running',
    startedAt: nowIso,
    stoppedAt: null,
    updatedAt: nowIso,
  };
  const map = readJsonMap<PowerStudySession>(STORAGE_KEYS.POWER_STUDIES);
  map[deviceId] = session;
  writeJsonMap(STORAGE_KEYS.POWER_STUDIES, map);
  return session;
}

export function stopPowerStudy(deviceId: string): PowerStudySession | null {
  const map = readJsonMap<PowerStudySession>(STORAGE_KEYS.POWER_STUDIES);
  const current = map[deviceId];
  if (!current) return null;
  const nowIso = new Date().toISOString();
  const updated: PowerStudySession = {
    ...current,
    status: 'completed',
    stoppedAt: nowIso,
    updatedAt: nowIso,
  };
  map[deviceId] = updated;
  writeJsonMap(STORAGE_KEYS.POWER_STUDIES, map);
  return updated;
}

export function resetPowerStudy(deviceId: string): void {
  const map = readJsonMap<PowerStudySession>(STORAGE_KEYS.POWER_STUDIES);
  delete map[deviceId];
  writeJsonMap(STORAGE_KEYS.POWER_STUDIES, map);
}

// ── Configuration Page Unsaved Drafts (per device) ────────────────────────────

export function getConfigDraft(deviceId: string | null): Record<string, any> | null {
  if (!deviceId) return null;
  const map = readJsonMap<Record<string, any>>(STORAGE_KEYS.CONFIG_DRAFTS);
  return map[deviceId] || null;
}

export function saveConfigDraft(deviceId: string, draft: Record<string, any>): void {
  if (!deviceId) return;
  const map = readJsonMap<Record<string, any>>(STORAGE_KEYS.CONFIG_DRAFTS);
  map[deviceId] = draft;
  writeJsonMap(STORAGE_KEYS.CONFIG_DRAFTS, map);
}

export function mergeConfigDraft(deviceId: string, patch: Record<string, any>): void {
  if (!deviceId || !patch || Object.keys(patch).length === 0) return;
  const map = readJsonMap<Record<string, any>>(STORAGE_KEYS.CONFIG_DRAFTS);
  if (map[deviceId]) {
    map[deviceId] = { ...map[deviceId], ...patch };
    writeJsonMap(STORAGE_KEYS.CONFIG_DRAFTS, map);
  }
}

export function clearConfigDraft(deviceId: string): void {
  if (!deviceId) return;
  const map = readJsonMap<Record<string, any>>(STORAGE_KEYS.CONFIG_DRAFTS);
  delete map[deviceId];
  writeJsonMap(STORAGE_KEYS.CONFIG_DRAFTS, map);
}

// ── Reports Page Unsaved Drafts (per device) ──────────────────────────────────

export interface ReportFormDraft {
  preset: 'study' | '1h' | '8h' | '24h' | '7d' | 'custom';
  startDate: string;
  startTime: string;
  endDate: string;
  endTime: string;
  interval: '1-minute' | '5-minute' | '1-hour';
  title: string;
  remarks: string;
  includeAiSummary: boolean;
  beforeStart: string;
  beforeEnd: string;
  tariff: number | '';
  operatingHours: number | '';
  motorInvestment: number;
  installationCost: number;
  manualBeforeKwhHr: string;
  manualAfterKwhHr: string;
  /** Tracks whether user edited commercial fields so profile fetch doesn't overwrite them */
  commercialTouched?: boolean;
  /** updatedAt of the PowerStudySession when this draft was created/synced */
  studyAnchor?: string | null;
}

export function getReportDraft(deviceId: string | null): ReportFormDraft | null {
  if (!deviceId) return null;
  const map = readJsonMap<ReportFormDraft>(STORAGE_KEYS.REPORT_DRAFTS);
  return map[deviceId] || null;
}

export function saveReportDraft(deviceId: string, draft: ReportFormDraft): void {
  if (!deviceId) return;
  const map = readJsonMap<ReportFormDraft>(STORAGE_KEYS.REPORT_DRAFTS);
  map[deviceId] = draft;
  writeJsonMap(STORAGE_KEYS.REPORT_DRAFTS, map);
}

export function clearReportDraft(deviceId: string): void {
  if (!deviceId) return;
  const map = readJsonMap<ReportFormDraft>(STORAGE_KEYS.REPORT_DRAFTS);
  delete map[deviceId];
  writeJsonMap(STORAGE_KEYS.REPORT_DRAFTS, map);
}

// ── Latest Motor Nameplate Badge (per device, session-scoped) ─────────────────

export function getLatestNameplate(deviceId: string | null): Record<string, any> | null {
  if (!deviceId) return null;
  const map = readJsonMap<Record<string, any>>(STORAGE_KEYS.LATEST_NAMEPLATE);
  return map[deviceId] || null;
}

export function saveLatestNameplate(deviceId: string, data: Record<string, any>): void {
  if (!deviceId) return;
  const map = readJsonMap<Record<string, any>>(STORAGE_KEYS.LATEST_NAMEPLATE);
  map[deviceId] = data;
  writeJsonMap(STORAGE_KEYS.LATEST_NAMEPLATE, map);
}

// ── Clear all session preferences & drafts on login/logout ────────────────────

export function clearAllSessionData(): void {
  try {
    localStorage.removeItem(STORAGE_KEYS.DASHBOARD_PERIOD);
    localStorage.removeItem(STORAGE_KEYS.DASHBOARD_ACTIVE_PARAMS);
    localStorage.removeItem(STORAGE_KEYS.CONFIG_DRAFTS);
    localStorage.removeItem(STORAGE_KEYS.CONFIG_OPEN_SECTIONS);
    localStorage.removeItem(STORAGE_KEYS.REPORT_DRAFTS);
    localStorage.removeItem(STORAGE_KEYS.POWER_STUDIES);
    localStorage.removeItem(STORAGE_KEYS.LATEST_NAMEPLATE);
    sessionStorage.removeItem(STORAGE_KEYS.SESSION_ACKED_ALERTS);
  } catch {
    // Ignore storage errors
  }
}
