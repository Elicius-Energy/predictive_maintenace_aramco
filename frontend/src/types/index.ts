/**
 * Shared types for the Saudi Aramco PdM system.
 * Mirrors the backend models.
 */

export type Severity = 'info' | 'warning' | 'critical';
export type MachineStatusType = 'healthy' | 'warning' | 'critical' | 'offline';
export type DataSource = 'mqtt';

export interface EnergyData {
  V: number;
  I: number;
  P: number;
  KVA: number;
  pf: number;
  Energy: number;
  Freq: number;
}

export interface AccelData {
  ax: number;
  ay: number;
  az: number;
  gx: number;
  gy: number;
  gz: number;
}

export interface SensorReading {
  timestamp: string;
  machine_id: string;
  source: DataSource;
  energy?: EnergyData;
  accel?: AccelData;
  temperature?: number;
}

export interface VibrationFeatures {
  rms_x: number;
  rms_y: number;
  rms_z: number;
  rms_overall: number;
  peak_x: number;
  peak_y: number;
  peak_z: number;
  kurtosis_x: number;
  kurtosis_y: number;
  kurtosis_z: number;
  crest_factor: number;
  dominant_freq: number;
  fft_magnitudes: number[];
  fft_frequencies: number[];
}

export interface ElectricalFeatures {
  voltage: number;
  current: number;
  active_power: number;
  apparent_power: number;
  power_factor: number;
  frequency: number;
  efficiency: number;
  load_percentage: number;
  energy_cumulative: number;
  // ── 3-Phase Fields ─────────────────────────────────────────────────
  is_three_phase?: boolean;
  dTS?: number;
  // Phase-to-neutral voltages
  v1n?: number;
  v2n?: number;
  v3n?: number;
  vln_avg?: number;
  // Line-to-line voltages
  v12?: number;
  v23?: number;
  v31?: number;
  vll_avg?: number;
  // Per-phase currents
  i1?: number;
  i2?: number;
  i3?: number;
  i_avg?: number;
  // Per-phase Active Power (kW)
  kw1?: number;
  kw2?: number;
  kw3?: number;
  // Per-phase Reactive Power (kVAR)
  kvar1?: number;
  kvar2?: number;
  kvar3?: number;
  // Per-phase Apparent Power (kVA)
  kva1?: number;
  kva2?: number;
  kva3?: number;
  // Totals
  t_kw?: number;
  t_kvar?: number;
  t_kva?: number;
  // Per-phase Power Factor
  pf1?: number;
  pf2?: number;
  pf3?: number;
  pf_avg?: number;
  // Energy counters
  kwh_imp?: number;
  kwh_exp?: number;
  kvarh_imp?: number;
  kvarh_exp?: number;
  t_kvah?: number;
  // Max Demand
  md_kw?: number;
  md_kvar?: number;
  md_kva?: number;
}

export interface FeatureVector {
  timestamp: string;
  machine_id: string;
  vibration: VibrationFeatures;
  electrical: ElectricalFeatures;
  temperature: number;
  anomaly_score: number;
  health_score: number;
  iso_zone: string;
}

export interface Alert {
  id?: string;
  timestamp: string;
  machine_id: string;
  severity: Severity;
  category: string;
  message: string;
  value?: number;
  threshold?: number;
  acknowledged: boolean;
}

export interface FaultDiagnosis {
  timestamp: string;
  machine_id: string;
  fault_type: string;
  confidence: number;
  severity: Severity;
  explanation: string;
  recommended_action: string;
  physics_reasoning: string;
  retrieved_context_summary: string;
}

export interface MachineHealthIndicator {
  name: string;
  probability: number;
  status: MachineStatusType;
  description?: string;
}

export interface MachineHealth {
  machine_id: string;
  overall_status: MachineStatusType;
  health_score: number;
  indicators: MachineHealthIndicator[];
  last_updated: string;
}

export interface MachineInfo {
  machine_id: string;
  name: string;
  type: string;
  location: string;
  unit: string;
  plant: string;
  status: MachineStatusType;
  health_score: number;
  uptime_hours: number;
  last_maintenance?: string;
}

export interface WSMessage {
  type: 'sensor_data' | 'features' | 'alert' | 'ai_diagnosis' | 'machine_health' | 'system_status';
  data: any;
  timestamp: string;
}
