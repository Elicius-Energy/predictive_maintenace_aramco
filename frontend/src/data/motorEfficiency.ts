/**
 * Motor Efficiency Estimator — Manufacturer Test Report Calibration
 * =================================================================
 *
 * TypeScript implementation of PCHIP (Piecewise Cubic Hermite
 * Interpolating Polynomial) interpolation using the Fritsch-Carlson
 * method for monotone cubic splines.
 *
 * Calibration source : Manufacturer type-test report for
 *                      5.5 kW / 415 V / 4-pole / 50 Hz induction motor.
 * Primary input      : measured real input power P_in [W].
 * Outputs            : η (%), P_out [W], load %, extrapolation flag.
 *
 * No external dependencies — pure TypeScript math.
 */

// ── Motor Nameplate ──────────────────────────────────────────────────────
export const RATED_OUTPUT_W = 5500;     // 5.5 kW
export const RATED_VOLTAGE_V = 415;     // Line-to-line
export const RATED_FREQUENCY_HZ = 50;

// ── Manufacturer Test Report — Calibration Data ─────────────────────────
// 6 tested load points: 23 %, 48 %, 73 %, 98 %, 114 %, 123 %
export const CALIB_P_IN_W   = [1742, 3230, 4762, 6431, 7519, 8265];
export const CALIB_CURRENT  = [5.39, 6.62, 8.34, 10.54, 12.09, 13.18];
export const CALIB_PF       = [0.449, 0.679, 0.794, 0.848, 0.865, 0.872];
export const CALIB_SPEED    = [1489, 1478, 1467, 1452, 1449, 1437];
export const CALIB_ETA_PCT  = [79.09, 85.55, 86.41, 85.33, 84.60, 83.40];
export const CALIB_LOAD_PCT = [23, 48, 73, 98, 114, 123];

export const P_IN_MIN_W = CALIB_P_IN_W[0];    // 1742 W
export const P_IN_MAX_W = CALIB_P_IN_W[CALIB_P_IN_W.length - 1]; // 8265 W

// ── Result Interface ─────────────────────────────────────────────────────

export interface EfficiencyResult {
  /** Estimated motor efficiency [%] */
  efficiencyPct: number;
  /** Estimated shaft output power [W] */
  outputPowerW: number;
  /** Load relative to rated output (5500 W) [%] */
  loadPct: number;
  /** True if P_in is outside calibration range (1742–8265 W) */
  extrapolated: boolean;
  /** Non-blocking validation warnings */
  validationFlags: string[];
}

// ══════════════════════════════════════════════════════════════════════════
// PCHIP Implementation — Fritsch-Carlson Monotone Cubic Hermite
// ══════════════════════════════════════════════════════════════════════════

/**
 * Compute Fritsch-Carlson monotone slopes for PCHIP interpolation.
 *
 * Given arrays x[] and y[] (both strictly increasing in x), returns
 * an array of tangent slopes m[] such that the resulting cubic Hermite
 * interpolant is shape-preserving (no overshoots).
 */
function computePchipSlopes(x: number[], y: number[]): number[] {
  const n = x.length;
  const m = new Array<number>(n).fill(0);

  // Step 1: secant slopes δ_k = (y[k+1] - y[k]) / (x[k+1] - x[k])
  const delta = new Array<number>(n - 1);
  for (let k = 0; k < n - 1; k++) {
    delta[k] = (y[k + 1] - y[k]) / (x[k + 1] - x[k]);
  }

  // Step 2: initial tangent estimates (arithmetic mean of adjacent secants)
  m[0] = delta[0];
  m[n - 1] = delta[n - 2];
  for (let k = 1; k < n - 1; k++) {
    if (delta[k - 1] * delta[k] <= 0) {
      // Sign change or zero — set tangent to 0 (local extremum)
      m[k] = 0;
    } else {
      // Harmonic mean weighting (Fritsch-Carlson)
      const w1 = 2 * (x[k + 1] - x[k]) + (x[k] - x[k - 1]);
      const w2 = (x[k + 1] - x[k]) + 2 * (x[k] - x[k - 1]);
      m[k] = (w1 + w2) / (w1 / delta[k - 1] + w2 / delta[k]);
    }
  }

  return m;
}

/**
 * Evaluate PCHIP interpolant at a single x-value.
 * Assumes `xp` is within [x[0], x[n-1]] (caller must clamp).
 */
function pchipEval(
  x: number[],
  y: number[],
  m: number[],
  xp: number,
): number {
  const n = x.length;

  // Find the interval [x[k], x[k+1]] containing xp
  let k = 0;
  for (let i = 0; i < n - 1; i++) {
    if (xp >= x[i]) k = i;
  }
  // Clamp k to valid range
  if (k >= n - 1) k = n - 2;

  const h = x[k + 1] - x[k];
  const t = (xp - x[k]) / h;

  // Hermite basis functions
  const h00 = (1 + 2 * t) * (1 - t) * (1 - t);
  const h10 = t * (1 - t) * (1 - t);
  const h01 = t * t * (3 - 2 * t);
  const h11 = t * t * (t - 1);

  return h00 * y[k] + h10 * h * m[k] + h01 * y[k + 1] + h11 * h * m[k + 1];
}

// Pre-compute slopes once at module load
const _pchipSlopesEta = computePchipSlopes(CALIB_P_IN_W, CALIB_ETA_PCT);
const _pchipSlopesCurrent = computePchipSlopes(CALIB_P_IN_W, CALIB_CURRENT);
const _pchipSlopesPF = computePchipSlopes(CALIB_P_IN_W, CALIB_PF);

// ══════════════════════════════════════════════════════════════════════════
// Public API
// ══════════════════════════════════════════════════════════════════════════

/**
 * Estimate motor efficiency from measured real input power using PCHIP
 * interpolation of the manufacturer's tested efficiency curve.
 *
 * @param pInWatts - Measured electrical input power [W]
 * @param opts     - Optional live measurements for validation flags only
 */
export function estimateMotorEfficiency(
  pInWatts: number,
  opts?: { voltage?: number; current?: number; pf?: number; frequency?: number },
): EfficiencyResult {
  return _estimate(pInWatts, 'pchip', opts);
}

/**
 * Piecewise-linear fallback estimator.
 */
export function estimateMotorEfficiencyLinear(
  pInWatts: number,
  opts?: { voltage?: number; current?: number; pf?: number; frequency?: number },
): EfficiencyResult {
  return _estimate(pInWatts, 'linear', opts);
}

// ── Internal ─────────────────────────────────────────────────────────────

function _estimate(
  pInWatts: number,
  method: 'pchip' | 'linear',
  opts?: { voltage?: number; current?: number; pf?: number; frequency?: number },
): EfficiencyResult {
  // Guard: non-positive input
  if (pInWatts <= 0) {
    return {
      efficiencyPct: 0,
      outputPowerW: 0,
      loadPct: 0,
      extrapolated: true,
      validationFlags: ['Input power ≤ 0 W'],
    };
  }

  // Extrapolation check
  const extrapolated = pInWatts < P_IN_MIN_W || pInWatts > P_IN_MAX_W;
  const pClamped = Math.min(Math.max(pInWatts, P_IN_MIN_W), P_IN_MAX_W);

  // Interpolate η
  let eta: number;
  if (method === 'pchip') {
    eta = pchipEval(CALIB_P_IN_W, CALIB_ETA_PCT, _pchipSlopesEta, pClamped);
  } else {
    eta = linearInterp(CALIB_P_IN_W, CALIB_ETA_PCT, pClamped);
  }
  eta = Math.min(100, Math.max(0, eta));

  // Derived quantities
  const outputPowerW = pInWatts * (eta / 100);
  const loadPct = (outputPowerW / RATED_OUTPUT_W) * 100;

  // Validation flags
  const validationFlags = buildValidationFlags(pClamped, extrapolated, opts);

  return {
    efficiencyPct: Math.round(eta * 100) / 100,
    outputPowerW: Math.round(outputPowerW * 100) / 100,
    loadPct: Math.round(loadPct * 100) / 100,
    extrapolated,
    validationFlags,
  };
}

/** Simple piecewise-linear interpolation (equivalent to numpy.interp). */
function linearInterp(x: number[], y: number[], xp: number): number {
  const n = x.length;
  if (xp <= x[0]) return y[0];
  if (xp >= x[n - 1]) return y[n - 1];
  for (let i = 0; i < n - 1; i++) {
    if (xp >= x[i] && xp <= x[i + 1]) {
      const t = (xp - x[i]) / (x[i + 1] - x[i]);
      return y[i] + t * (y[i + 1] - y[i]);
    }
  }
  return y[n - 1];
}

/** Build non-blocking validation flags from optional live measurements. */
function buildValidationFlags(
  pClamped: number,
  extrapolated: boolean,
  opts?: { voltage?: number; current?: number; pf?: number; frequency?: number },
): string[] {
  const flags: string[] = [];

  if (extrapolated) {
    flags.push(`Operating point outside calibration range (${P_IN_MIN_W}–${P_IN_MAX_W} W)`);
  }

  if (!opts) return flags;

  // Voltage deviation from rated 415 V (± 10 %)
  if (opts.voltage != null && opts.voltage > 0) {
    const vDevPct = Math.abs(opts.voltage - RATED_VOLTAGE_V) / RATED_VOLTAGE_V * 100;
    if (vDevPct > 10) {
      flags.push(
        `Voltage deviation ${vDevPct.toFixed(1)}% from rated ${RATED_VOLTAGE_V} V (measured ${opts.voltage.toFixed(1)} V)`,
      );
    }
  }

  // PF vs expected at this load point
  if (opts.pf != null && opts.pf > 0) {
    const expectedPf = pchipEval(CALIB_P_IN_W, CALIB_PF, _pchipSlopesPF, pClamped);
    const pfDelta = Math.abs(opts.pf - expectedPf);
    if (pfDelta > 0.10) {
      flags.push(
        `PF deviation ${pfDelta.toFixed(3)} from expected ${expectedPf.toFixed(3)} (measured ${opts.pf.toFixed(3)})`,
      );
    }
  }

  // Current vs expected at this load point
  if (opts.current != null && opts.current > 0) {
    const expectedI = pchipEval(CALIB_P_IN_W, CALIB_CURRENT, _pchipSlopesCurrent, pClamped);
    const iDevPct = Math.abs(opts.current - expectedI) / expectedI * 100;
    if (iDevPct > 15) {
      flags.push(
        `Current deviation ${iDevPct.toFixed(1)}% from expected ${expectedI.toFixed(2)} A (measured ${opts.current.toFixed(2)} A)`,
      );
    }
  }

  // Frequency deviation from 50 Hz
  if (opts.frequency != null && opts.frequency > 0) {
    const fDev = Math.abs(opts.frequency - RATED_FREQUENCY_HZ);
    if (fDev > 2.0) {
      flags.push(
        `Frequency deviation ${fDev.toFixed(2)} Hz from rated ${RATED_FREQUENCY_HZ} Hz`,
      );
    }
  }

  return flags;
}

/**
 * Validate an operating point against the manufacturer curve.
 * Returns an array of warning strings (empty if all OK).
 */
export function validateOperatingPoint(opts: {
  voltage?: number;
  current?: number;
  pf?: number;
  frequency?: number;
  pInWatts?: number;
}): string[] {
  const pClamped = opts.pInWatts
    ? Math.min(Math.max(opts.pInWatts, P_IN_MIN_W), P_IN_MAX_W)
    : CALIB_P_IN_W[3]; // default to ~rated point
  const extrapolated = opts.pInWatts
    ? opts.pInWatts < P_IN_MIN_W || opts.pInWatts > P_IN_MAX_W
    : false;
  return buildValidationFlags(pClamped, extrapolated, opts);
}
