"""
Test script for motor_efficiency.py — verifies calibration point accuracy,
boundary behavior, and linear fallback.
"""
import sys
import os

# Ensure the app module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.motor_efficiency import (
    motor_efficiency_estimator,
    CALIB_P_IN_W,
    CALIB_ETA_PCT,
    P_IN_MIN_W,
    P_IN_MAX_W,
    RATED_OUTPUT_W,
)

PASS = 0
FAIL = 0


def check(desc: str, condition: bool, detail: str = ""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅  {desc}")
    else:
        FAIL += 1
        print(f"  ❌  {desc}  — {detail}")


def test_calibration_points_pchip():
    """PCHIP must reproduce the manufacturer's η at each calibration knot."""
    print("\n── Test 1: PCHIP at calibration knots ──")
    for p_in, eta_expected in zip(CALIB_P_IN_W, CALIB_ETA_PCT):
        r = motor_efficiency_estimator.estimate(float(p_in))
        err = abs(r.efficiency_pct - eta_expected)
        check(
            f"P_in={p_in:.0f} W → η={r.efficiency_pct:.2f}% (expected {eta_expected:.2f}%)",
            err < 0.05,
            f"error={err:.4f}%",
        )
        check(
            f"  extrapolated=False",
            not r.extrapolated,
            f"got {r.extrapolated}",
        )


def test_calibration_points_linear():
    """Linear fallback must also match at calibration knots."""
    print("\n── Test 2: Linear at calibration knots ──")
    for p_in, eta_expected in zip(CALIB_P_IN_W, CALIB_ETA_PCT):
        r = motor_efficiency_estimator.estimate_linear(float(p_in))
        err = abs(r.efficiency_pct - eta_expected)
        check(
            f"P_in={p_in:.0f} W → η={r.efficiency_pct:.2f}% (expected {eta_expected:.2f}%)",
            err < 0.05,
            f"error={err:.4f}%",
        )


def test_output_power_and_load():
    """Verify P_out and load% are derived correctly."""
    print("\n── Test 3: P_out and load% derivation ──")
    r = motor_efficiency_estimator.estimate(6431.0)  # ~98% load
    expected_pout = 6431.0 * (r.efficiency_pct / 100)
    expected_load = (expected_pout / RATED_OUTPUT_W) * 100
    check(
        f"P_out = {r.output_power_w:.2f} W (calc {expected_pout:.2f} W)",
        abs(r.output_power_w - expected_pout) < 0.1,
    )
    check(
        f"Load = {r.load_pct:.2f}% (calc {expected_load:.2f}%)",
        abs(r.load_pct - expected_load) < 0.1,
    )


def test_extrapolation():
    """Below min / above max should clamp and flag extrapolated."""
    print("\n── Test 4: Extrapolation handling ──")
    # Below minimum
    r_low = motor_efficiency_estimator.estimate(500.0)
    check("P_in=500 W → extrapolated=True", r_low.extrapolated)
    check(
        f"  η={r_low.efficiency_pct:.2f}% ≈ boundary η(1742)=79.09%",
        abs(r_low.efficiency_pct - 79.09) < 0.05,
        f"got {r_low.efficiency_pct}",
    )

    # Above maximum
    r_high = motor_efficiency_estimator.estimate(10000.0)
    check("P_in=10000 W → extrapolated=True", r_high.extrapolated)
    check(
        f"  η={r_high.efficiency_pct:.2f}% ≈ boundary η(8265)=83.40%",
        abs(r_high.efficiency_pct - 83.40) < 0.05,
        f"got {r_high.efficiency_pct}",
    )


def test_zero_and_negative():
    """Non-positive power should return safe defaults."""
    print("\n── Test 5: Zero / negative power ──")
    for p in [0.0, -100.0]:
        r = motor_efficiency_estimator.estimate(p)
        check(f"P_in={p} → η=0%", r.efficiency_pct == 0.0)
        check(f"  P_out=0", r.output_power_w == 0.0)
        check(f"  extrapolated=True", r.extrapolated)


def test_validation_flags():
    """Voltage/PF/current deviation flags should trigger."""
    print("\n── Test 6: Validation flags ──")
    # Good values — no flags expected (beyond extrapolation)
    r_ok = motor_efficiency_estimator.estimate(4762.0, voltage=415.0, pf=0.794, current=8.34)
    non_extrap_flags = [f for f in r_ok.validation_flags if "outside" not in f.lower()]
    check("Good readings → no validation flags", len(non_extrap_flags) == 0, str(non_extrap_flags))

    # Bad voltage
    r_v = motor_efficiency_estimator.estimate(4762.0, voltage=350.0)
    has_v_flag = any("Voltage" in f for f in r_v.validation_flags)
    check("V=350 → voltage deviation flag", has_v_flag)

    # Bad PF
    r_pf = motor_efficiency_estimator.estimate(4762.0, pf=0.5)
    has_pf_flag = any("PF" in f for f in r_pf.validation_flags)
    check("PF=0.5 at 73% load (expected 0.794) → PF flag", has_pf_flag)


def test_interpolation_midpoint():
    """Verify a midpoint between knots gives a reasonable value."""
    print("\n── Test 7: Midpoint interpolation sanity ──")
    # Between 3230 W (η=85.55) and 4762 W (η=86.41)
    mid_p = (3230 + 4762) / 2  # 3996 W
    r = motor_efficiency_estimator.estimate(mid_p)
    check(
        f"P_in={mid_p:.0f} W → η={r.efficiency_pct:.2f}% (should be ~85–87%)",
        85.0 <= r.efficiency_pct <= 87.0,
        f"got {r.efficiency_pct}",
    )
    check("  extrapolated=False", not r.extrapolated)


if __name__ == "__main__":
    print("=" * 60)
    print("Motor Efficiency Estimator — Test Suite")
    print("=" * 60)

    test_calibration_points_pchip()
    test_calibration_points_linear()
    test_output_power_and_load()
    test_extrapolation()
    test_zero_and_negative()
    test_validation_flags()
    test_interpolation_midpoint()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"Results: {PASS}/{total} passed, {FAIL} failed")
    print("=" * 60)
    sys.exit(1 if FAIL > 0 else 0)
