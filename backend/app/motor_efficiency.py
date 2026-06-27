"""
Motor Efficiency Estimator — Manufacturer Test Report Calibration
=================================================================

Provides real-time efficiency estimation for a 5.5 kW, 415 V, 4-pole,
50 Hz induction motor using PCHIP (Piecewise Cubic Hermite Interpolating
Polynomial) interpolation of the manufacturer's tested efficiency curve.

Calibration source: Motor type-test report (6 load points from 23 % to 123 %).
Primary input : measured real input power  P_in  [W].
Outputs       : estimated η (%), shaft output power P_out [W],
                load percentage relative to rated 5500 W, and an
                extrapolation flag.

The module is deliberately self-contained so it can be imported by the
feature-engineering pipeline without touching the data-acquisition layer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
from scipy.interpolate import PchipInterpolator

logger = logging.getLogger(__name__)

# ── Motor Nameplate ────────────────────────────────────────────────────────
RATED_OUTPUT_W: float = 5500.0       # 5.5 kW
RATED_VOLTAGE_V: float = 415.0       # Line-to-line
RATED_FREQUENCY_HZ: float = 50.0
POLES: int = 4

# ── Manufacturer Test Report — Calibration Data ───────────────────────────
# Columns aligned: load_pct, P_in [W], I [A], PF, speed [rpm], η [%]
CALIB_LOAD_PCT   = np.array([23.0,   48.0,   73.0,   98.0,  114.0,  123.0])
CALIB_P_IN_W     = np.array([1742.0, 3230.0, 4762.0, 6431.0, 7519.0, 8265.0])
CALIB_CURRENT_A  = np.array([5.39,   6.62,   8.34,  10.54,  12.09,  13.18])
CALIB_PF         = np.array([0.449,  0.679,  0.794,  0.848,  0.865,  0.872])
CALIB_SPEED_RPM  = np.array([1489.0, 1478.0, 1467.0, 1452.0, 1449.0, 1437.0])
CALIB_ETA_PCT    = np.array([79.09,  85.55,  86.41,  85.33,  84.60,  83.40])

# Calibration range limits (watts)
P_IN_MIN_W: float = float(CALIB_P_IN_W[0])    # 1742 W
P_IN_MAX_W: float = float(CALIB_P_IN_W[-1])   # 8265 W


# ── Result Dataclass ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class EfficiencyResult:
    """Immutable result of an efficiency estimation."""
    efficiency_pct: float       # Estimated motor efficiency [%]
    output_power_w: float       # Estimated shaft output power [W]
    load_pct: float             # Load relative to rated output (5500 W) [%]
    extrapolated: bool          # True if P_in outside calibration range
    validation_flags: List[str] = field(default_factory=list)


# ── Estimator ─────────────────────────────────────────────────────────────

class MotorEfficiencyEstimator:
    """
    PCHIP-interpolated efficiency estimator calibrated from a manufacturer
    type-test report for a 5.5 kW / 415 V / 4-pole induction motor.

    Default method: PCHIP (monotone cubic Hermite) — smooth, overshoot-free.
    Fallback      : piecewise-linear via numpy.interp.
    """

    def __init__(self) -> None:
        # Build the PCHIP interpolator:  η(P_in)
        self._pchip = PchipInterpolator(CALIB_P_IN_W, CALIB_ETA_PCT)

        # Also build interpolators for the ancillary calibration columns
        # so we can cross-check live V / I / PF against expected values.
        self._pchip_current = PchipInterpolator(CALIB_P_IN_W, CALIB_CURRENT_A)
        self._pchip_pf      = PchipInterpolator(CALIB_P_IN_W, CALIB_PF)
        self._pchip_speed   = PchipInterpolator(CALIB_P_IN_W, CALIB_SPEED_RPM)

        logger.info(
            "MotorEfficiencyEstimator initialised — calibration range "
            "%.0f W … %.0f W  (6 test points, PCHIP)", P_IN_MIN_W, P_IN_MAX_W
        )

    # ── Primary estimator (PCHIP) ─────────────────────────────────────

    def estimate(
        self,
        p_in_watts: float,
        *,
        voltage: Optional[float] = None,
        current: Optional[float] = None,
        pf: Optional[float] = None,
        frequency: Optional[float] = None,
    ) -> EfficiencyResult:
        """
        Estimate motor efficiency from measured real input power.

        Parameters
        ----------
        p_in_watts : float
            Measured electrical input power [W].
        voltage, current, pf, frequency : float | None
            Optional live measurements used **only** for validation flags.

        Returns
        -------
        EfficiencyResult
        """
        return self._do_estimate(
            p_in_watts,
            interpolation="pchip",
            voltage=voltage,
            current=current,
            pf=pf,
            frequency=frequency,
        )

    # ── Fallback estimator (piecewise-linear) ─────────────────────────

    def estimate_linear(
        self,
        p_in_watts: float,
        *,
        voltage: Optional[float] = None,
        current: Optional[float] = None,
        pf: Optional[float] = None,
        frequency: Optional[float] = None,
    ) -> EfficiencyResult:
        """Same as `estimate` but uses piecewise-linear interpolation."""
        return self._do_estimate(
            p_in_watts,
            interpolation="linear",
            voltage=voltage,
            current=current,
            pf=pf,
            frequency=frequency,
        )

    # ── Internals ─────────────────────────────────────────────────────

    def _do_estimate(
        self,
        p_in_watts: float,
        interpolation: str,
        *,
        voltage: Optional[float],
        current: Optional[float],
        pf: Optional[float],
        frequency: Optional[float],
    ) -> EfficiencyResult:
        # Guard: non-positive input power
        if p_in_watts <= 0:
            return EfficiencyResult(
                efficiency_pct=0.0,
                output_power_w=0.0,
                load_pct=0.0,
                extrapolated=True,
                validation_flags=["Input power ≤ 0 W"],
            )

        # Determine extrapolation status and clamp
        extrapolated = p_in_watts < P_IN_MIN_W or p_in_watts > P_IN_MAX_W
        p_clamped = float(np.clip(p_in_watts, P_IN_MIN_W, P_IN_MAX_W))

        # Interpolate η
        if interpolation == "pchip":
            eta = float(self._pchip(p_clamped))
        else:
            eta = float(np.interp(p_clamped, CALIB_P_IN_W, CALIB_ETA_PCT))

        # Clamp η to physically valid range
        eta = float(np.clip(eta, 0.0, 100.0))

        # Derived quantities
        output_power_w = p_in_watts * (eta / 100.0)
        load_pct = (output_power_w / RATED_OUTPUT_W) * 100.0

        # Validation flags (informational only)
        flags = self._build_validation_flags(
            p_clamped, extrapolated, voltage, current, pf, frequency
        )

        return EfficiencyResult(
            efficiency_pct=round(eta, 2),
            output_power_w=round(output_power_w, 2),
            load_pct=round(load_pct, 2),
            extrapolated=extrapolated,
            validation_flags=flags,
        )

    def _build_validation_flags(
        self,
        p_clamped: float,
        extrapolated: bool,
        voltage: Optional[float],
        current: Optional[float],
        pf: Optional[float],
        frequency: Optional[float],
    ) -> List[str]:
        """Generate non-blocking validation warnings."""
        flags: List[str] = []

        if extrapolated:
            flags.append(
                f"Operating point outside calibration range "
                f"({P_IN_MIN_W:.0f}–{P_IN_MAX_W:.0f} W)"
            )

        # Voltage deviation from rated 415 V (± 10 %)
        if voltage is not None and voltage > 0:
            v_dev_pct = abs(voltage - RATED_VOLTAGE_V) / RATED_VOLTAGE_V * 100
            if v_dev_pct > 10:
                flags.append(
                    f"Voltage deviation {v_dev_pct:.1f}% from rated "
                    f"{RATED_VOLTAGE_V:.0f} V (measured {voltage:.1f} V)"
                )

        # Power factor vs expected at this load point
        if pf is not None and pf > 0:
            expected_pf = float(self._pchip_pf(p_clamped))
            pf_delta = abs(pf - expected_pf)
            if pf_delta > 0.10:
                flags.append(
                    f"PF deviation {pf_delta:.3f} from expected "
                    f"{expected_pf:.3f} at this load (measured {pf:.3f})"
                )

        # Current vs expected at this load point
        if current is not None and current > 0:
            expected_i = float(self._pchip_current(p_clamped))
            i_dev_pct = abs(current - expected_i) / expected_i * 100
            if i_dev_pct > 15:
                flags.append(
                    f"Current deviation {i_dev_pct:.1f}% from expected "
                    f"{expected_i:.2f} A (measured {current:.2f} A)"
                )

        # Frequency deviation from 50 Hz
        if frequency is not None and frequency > 0:
            f_dev = abs(frequency - RATED_FREQUENCY_HZ)
            if f_dev > 2.0:
                flags.append(
                    f"Frequency deviation {f_dev:.2f} Hz from rated "
                    f"{RATED_FREQUENCY_HZ:.0f} Hz"
                )

        return flags


# ── Module-level singleton ────────────────────────────────────────────────
motor_efficiency_estimator = MotorEfficiencyEstimator()
