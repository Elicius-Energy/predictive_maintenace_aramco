export interface FormulaEntry {
  name: string;
  expression: string;
  explanation: string;
}

export const FORMULAS = {
  vibrationVelocity: [
    {
      name: 'Axis RMS',
      expression: 'RMS_axis = sqrt(mean(a^2))',
      explanation: 'Root mean square of the acceleration waveform for each axis.'
    },
    {
      name: 'Overall Velocity',
      expression: 'RMS_overall = sqrt(RMSx^2 + RMSy^2 + RMSz^2)',
      explanation: 'Combines the three axes into a single vibration severity value.'
    }
  ],
  vibrationShape: [
    {
      name: 'Crest Factor',
      expression: 'Crest Factor = Peakx / RMSx',
      explanation: 'Highlights impulsive peaks that are typical of looseness or impact events.'
    },
    {
      name: 'Kurtosis',
      expression: 'Kurtosis = E[(x - mu)^4] / sigma^4',
      explanation: 'Elevated kurtosis indicates sharp transients often associated with bearing damage.'
    }
  ],
  fft: [
    {
      name: 'FFT Magnitude',
      expression: 'Magnitude(f) = (2 / N) * |FFT(signal - mean(signal))|',
      explanation: 'Detrended FFT magnitude used to expose dominant mechanical frequencies.'
    },
    {
      name: 'Dominant Frequency',
      expression: 'f_dom = frequency[argmax(Magnitude(f), f > 0)]',
      explanation: 'Primary spectral peak used for fault pattern interpretation.'
    }
  ],
  bearingHealth: [
    {
      name: 'Bearing Health Probability',
      expression: 'P_bearing = clamp((max(kurtosis_x, kurtosis_y) / 4.0) + (RMS_overall / 15.0), 0.02, 0.95)',
      explanation: 'Current rule-engine estimate combining impulsiveness and total vibration severity.'
    }
  ],
  imbalance: [
    {
      name: 'Imbalance Probability',
      expression: 'P_imbalance = clamp(RMS_overall / 8.0, 0.05, 0.90)',
      explanation: 'Uses overall vibration amplitude as the present imbalance proxy.'
    }
  ],
  electricalEfficiency: [
    {
      name: 'Theoretical Apparent Power',
      expression: 'P_theoretical = V * I * sqrt(3)',
      explanation: 'Three-phase apparent power estimate used when assessing efficiency.'
    },
    {
      name: 'Efficiency',
      expression: 'Efficiency(%) = clamp((P_active / P_theoretical) * 100, 0, 100)',
      explanation: 'Current frontend and backend efficiency display follows this simplified model.'
    }
  ],
  load: [
    {
      name: 'Load Percentage',
      expression: 'Load(%) = (P_active / 10.0) * 100',
      explanation: 'Assumes a nominal 10 kW machine rating in the existing feature extractor.'
    },
    {
      name: 'Power Factor',
      expression: 'PF = P_active / P_apparent',
      explanation: 'Standard power factor relation used to judge reactive loading quality.'
    }
  ],
  energyAndFrequency: [
    {
      name: 'Energy',
      expression: 'Energy_cumulative = sum(P_active * delta_t)',
      explanation: 'Cumulative kWh trend represented by the incoming telemetry stream.'
    },
    {
      name: 'Frequency Deviation',
      expression: 'Delta_f = |f_measured - f_nominal|',
      explanation: 'Grid stability can be inferred by deviation from the nominal operating frequency.'
    }
  ],
  temperature: [
    {
      name: 'Thermal Thresholds',
      expression: 'Warning if T > 70C, Critical if T > 85C',
      explanation: 'Matches the current rule-engine over-temperature logic.'
    }
  ],
  healthScore: [
    {
      name: 'Anomaly Score',
      expression: 'Score_anomaly = clamp(1 - (decision_function(x) + 0.5), 0, 1)',
      explanation: 'Isolation Forest output transformed so higher values mean more anomalous behavior.'
    },
    {
      name: 'Health Score',
      expression: 'Health = 100 - penalties(alert severity, alert count, RMS_overall)',
      explanation: 'Aggregate health is reduced by critical alerts, warnings, and sustained vibration.'
    }
  ],
  isoZone: [
    {
      name: 'ISO 10816 Zones',
      expression: 'A: <=1.12, B: <=2.8, C: <=7.1, D: >7.1 mm/s',
      explanation: 'Current ISO-style machine condition bands used in the rule engine.'
    }
  ],
  aiAnalytics: [
    {
      name: 'Efficiency Gain Trend',
      expression: 'Gain(%) = ((Baseline Energy - Current Energy) / Baseline Energy) * 100',
      explanation: 'Business impact chart interpretation for efficiency improvement over time.'
    },
    {
      name: 'Risk Reduction Trend',
      expression: 'Risk Reduction(%) = ((Baseline Risk - Residual Risk) / Baseline Risk) * 100',
      explanation: 'Illustrates projected downtime-risk mitigation after intervention.'
    },
    {
      name: 'Component Vulnerability',
      expression: 'Component Risk(%) = weighted(vibration, thermal, electrical, historical alerts)',
      explanation: 'Displayed as a relative vulnerability index for prioritizing maintenance.'
    }
  ]
} satisfies Record<string, FormulaEntry[]>;
