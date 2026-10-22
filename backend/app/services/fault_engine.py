"""
Fault Detection Engine for Elicius Energy Motor Energy Monitoring.
Implements debounced real-time electrical fault detection rules, per-phase diagnostic chips,
and overall device status calculation.
"""
from datetime import datetime, timezone
import math
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
from app.db.models import Device, DeviceProfile, DeviceBaseline, Alert


class FaultEngine:
    """
    Stateful fault detection engine with debouncing per (device_id, rule_type, phase).
    """
    def __init__(self):
        # Debounce state: key -> {"bad_count": int, "good_count": int}
        # Key format: (device_id, rule_type, phase)
        self._debounce_state: Dict[Tuple[str, str, Optional[str]], Dict[str, int]] = {}
        # Frozen telemetry detection: device_id -> list of payload hashes or tuples
        self._payload_history: Dict[str, List[Tuple]] = {}

    def _get_thresholds(self, profile: Optional[DeviceProfile]) -> Dict[str, Any]:
        """Extract thresholds from profile with defaults."""
        defaults = {
            "active_current_a": 1.0,
            "debounce_raise_count": 3,
            "debounce_clear_count": 3,
            "v_min_present": 50.0,
            "i_min_present": 0.05,
            "ct_swap_pf_diff": 0.25,
            "v_line_tol_pct": 6.0,
            "v_nom_min_pct": 80.0,
            "v_nom_max_pct": 120.0,
            "baseline_tol_pct": 30.0,
            "nominal_voltage": 240.0,
        }
        if profile and profile.thresholds:
            defaults.update(profile.thresholds)
        if profile and profile.nominal_voltage:
            defaults["nominal_voltage"] = profile.nominal_voltage
        return defaults

    def evaluate_reading(
        self,
        device: Device,
        profile: Optional[DeviceProfile],
        baseline: Optional[DeviceBaseline],
        payload: Dict[str, Any],
        reading_time: datetime,
        db: Session
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Evaluate a reading against all 10 fault rules with debouncing.
        Returns: (overall_status, status_detail_dict)
        """
        th = self._get_thresholds(profile)
        active_i = float(th["active_current_a"])
        n_raise = int(th.get("debounce_raise_count", 3))
        n_clear = int(th.get("debounce_clear_count", 3))
        v_min = float(th.get("v_min_present", 50.0))
        i_min = float(th.get("i_min_present", 0.05))
        v_nom = float(th.get("nominal_voltage", 240.0))

        # Raw signals extraction
        v1n = payload.get("v1n")
        v2n = payload.get("v2n")
        v3n = payload.get("v3n")
        vln_avg = payload.get("vln_avg")
        v12 = payload.get("v12")
        v23 = payload.get("v23")
        v31 = payload.get("v31")
        vll_avg = payload.get("vll_avg")

        i1 = payload.get("i1")
        i2 = payload.get("i2")
        i3 = payload.get("i3")
        i_avg = payload.get("i_avg")

        kw1 = payload.get("kw1")
        kw2 = payload.get("kw2")
        kw3 = payload.get("kw3")
        t_kw = payload.get("t_kw")

        pf1 = payload.get("pf1")
        pf2 = payload.get("pf2")
        pf3 = payload.get("pf3")
        pf_avg = payload.get("pf_avg")

        freq = payload.get("freq")

        # Map of (rule_type, phase, severity) -> (is_fault_active: bool, message: str, details: dict)
        checks: Dict[Tuple[str, Optional[str], str], Tuple[bool, str, Dict[str, Any]]] = {}

        # ── Rule 7: Current signal not received ────────────────────────────
        i_missing = any(x is None for x in [i1, i2, i3, i_avg])
        checks[("current_signal_missing", None, "Disconnected")] = (
            i_missing,
            "Current signal not received: one or more current values missing",
            {"i1": i1, "i2": i2, "i3": i3, "i_avg": i_avg}
        )

        # ── Rule 8: Voltage signal not received ────────────────────────────
        v_missing = any(x is None for x in [v1n, v2n, v3n, v12, v23, v31, vln_avg, vll_avg])
        checks[("voltage_signal_missing", None, "Disconnected")] = (
            v_missing,
            "Voltage signal not received: one or more voltage values missing",
            {"v1n": v1n, "v2n": v2n, "v3n": v3n, "vln_avg": vln_avg}
        )

        # ── Rule 9: Sensor communication failure ───────────────────────────
        sensor_failure = False
        sensor_reason = ""
        # 1. Non-numeric or physical range
        try:
            for v in [v1n, v2n, v3n, vln_avg, v12, v23, v31, vll_avg]:
                if v is not None and (float(v) < 0 or float(v) > 600):
                    sensor_failure = True
                    sensor_reason = f"Voltage out of physical bounds: {v} V"
            if freq is not None and (float(freq) < 40 or float(freq) > 60):
                sensor_failure = True
                sensor_reason = f"Frequency out of physical bounds: {freq} Hz"
            # 2. t_kw differs from kw1+kw2+kw3 by > 5% + 0.05 kW
            if all(x is not None for x in [t_kw, kw1, kw2, kw3]):
                kw_sum = float(kw1) + float(kw2) + float(kw3)
                diff = abs(float(t_kw) - kw_sum)
                allowed_tol = 0.05 * abs(float(t_kw)) + 0.05
                if diff > allowed_tol:
                    sensor_failure = True
                    sensor_reason = f"Active power mismatch: t_kw={t_kw} kW vs sum={kw_sum:.2f} kW (diff {diff:.2f} > {allowed_tol:.2f})"
        except (ValueError, TypeError) as conv_err:
            sensor_failure = True
            sensor_reason = f"Non-numeric telemetry: {conv_err}"

        # 3. Frozen telemetry check (10 consecutive samples byte-identical)
        dev_id = device.device_id
        if dev_id not in self._payload_history:
            self._payload_history[dev_id] = []
        hist = self._payload_history[dev_id]
        current_sample = (v1n, v2n, v3n, i1, i2, i3, kw1, kw2, kw3)
        hist.append(current_sample)
        if len(hist) > 10:
            hist.pop(0)
        if len(hist) == 10 and all(s == current_sample for s in hist) and not sensor_failure:
            sensor_failure = True
            sensor_reason = "Frozen telemetry: readings unchanged for 10 consecutive samples"

        checks[("sensor_comm_failure", None, "Communication failure")] = (
            sensor_failure,
            f"Sensor communication failure: {sensor_reason}" if sensor_failure else "Sensor communication normal",
            {"reason": sensor_reason}
        )

        # Proceed to electrical per-phase checks only if signals are numeric
        if not (i_missing or v_missing or sensor_failure):
            v_vals = [float(v1n), float(v2n), float(v3n)]
            i_vals = [float(i1), float(i2), float(i3)]
            kw_vals = [float(kw1), float(kw2), float(kw3)]
            pf_vals = [float(pf1), float(pf2), float(pf3)]
            phases = ["L1", "L2", "L3"]

            # ── Rule 1: CT Polarity / Direction Incorrect (Reversed Connection)
            # kw_n < -0.02 kW while i_n > 1.0 A -> Reversed CT wiring
            all_reversed = all(kw < -0.02 and i > active_i for kw, i in zip(kw_vals, i_vals))
            for idx, phase in enumerate(phases):
                is_reversed = kw_vals[idx] < -0.02 and i_vals[idx] > active_i
                msg = "All CTs reversed or reverse power flow" if all_reversed else f"CT {phase} wrong direction / reversed connection: negative active power ({kw_vals[idx]:.2f} kW)"
                checks[("ct_polarity_incorrect", phase, "Incorrect connection")] = (
                    is_reversed,
                    msg,
                    {"reason": msg, "kw": kw_vals[idx], "i": i_vals[idx], "all_reversed": all_reversed}
                )

            # ── Rule 2: CT Disconnected ────────────────────────────────────
            # v_nn > 50 V AND i_n < 0.05 A AND at least one other phase active (> 1.0 A)
            # If all three currents ~0 and voltage present: motor stopped / idle, NOT a fault!
            all_stopped = all(i < i_min for i in i_vals) and all(v > v_min for v in v_vals)
            for idx, phase in enumerate(phases):
                other_active = any(i_vals[o] > active_i for o in range(3) if o != idx)
                is_ct_disconnected = (v_vals[idx] > v_min) and (i_vals[idx] < i_min) and other_active and not all_stopped
                msg = f"CT {phase} disconnected (voltage present {v_vals[idx]:.1f} V, current {i_vals[idx]:.3f} A)"
                checks[("ct_disconnected", phase, "Disconnected")] = (
                    is_ct_disconnected,
                    msg,
                    {"reason": msg, "v": v_vals[idx], "i": i_vals[idx]}
                )

            # ── Rule 3: CT Connection / Phase Swap (Warning) ───────────────
            # pf_n differs from median of other two by > 0.25 (and kw_n >= -0.02)
            # OR |pf_n| < 0.3 while others > 0.6
            for idx, phase in enumerate(phases):
                other_pfs = [pf_vals[o] for o in range(3) if o != idx]
                other_median = (other_pfs[0] + other_pfs[1]) / 2.0
                pf_diff = abs(pf_vals[idx] - other_median)
                is_swap = (
                    i_vals[idx] > active_i and
                    kw_vals[idx] >= -0.02 and
                    (pf_diff > float(th.get("ct_swap_pf_diff", 0.25)) or (abs(pf_vals[idx]) < 0.3 and all(p > 0.6 for p in other_pfs)))
                )
                msg = f"CT {phase} phase swap / PF imbalance (PF={pf_vals[idx]:.2f} vs others={other_median:.2f})"
                checks[("ct_connection_incorrect", phase, "Warning")] = (
                    is_swap,
                    msg,
                    {"reason": msg, "pf": pf_vals[idx], "other_median_pf": other_median, "diff": pf_diff}
                )

            # ── Rule 4: CT Position Changed ────────────────────────────────
            # Baseline comparison: per-phase current share or PF deviates > tolerance (30%)
            if baseline and baseline.per_phase_current_share and baseline.per_phase_pf:
                tol_pct = float(baseline.tolerance_pct or th.get("baseline_tol_pct", 30.0))
                total_i = sum(i_vals)
                if total_i > 3.0:  # Running motor
                    for idx, phase in enumerate(phases):
                        share_key = f"i{idx+1}_share"
                        pf_key = f"pf{idx+1}"
                        curr_share = i_vals[idx] / total_i
                        base_share = float(baseline.per_phase_current_share.get(share_key, curr_share))
                        base_pf = float(baseline.per_phase_pf.get(pf_key, pf_vals[idx]))
                        
                        share_dev = abs(curr_share - base_share) / max(base_share, 0.01) * 100.0
                        pf_dev = abs(pf_vals[idx] - base_pf) / max(abs(base_pf), 0.01) * 100.0
                        has_pos_changed = (share_dev > tol_pct) or (pf_dev > tol_pct)
                        checks[("ct_position_changed", phase, "Warning")] = (
                            has_pos_changed,
                            f"CT {phase} position changed: deviation from installation baseline > {tol_pct:.0f}%",
                            {"share_dev_pct": share_dev, "pf_dev_pct": pf_dev, "tolerance": tol_pct}
                        )

            # ── Rule 5: Voltage Clip Disconnected ──────────────────────────
            # v_nn < 50 V while device is online
            for idx, phase in enumerate(phases):
                is_clip_off = v_vals[idx] < v_min
                checks[("voltage_clip_disconnected", phase, "Disconnected")] = (
                    is_clip_off,
                    f"Voltage clip {phase} disconnected (voltage {v_vals[idx]:.1f} V < {v_min} V)",
                    {"voltage": v_vals[idx], "min_required": v_min}
                )

            # ── Rule 6: Voltage Connection Incorrect ───────────────────────
            # Any line-to-line voltage not within +-6% of sqrt(3) * line-to-neutral
            # or vln_avg outside 80-120% of nominal voltage
            sqrt3 = math.sqrt(3.0)
            v_line_tol = float(th.get("v_line_tol_pct", 6.0)) / 100.0
            
            # Check v12 vs v1n, v23 vs v2n, v31 vs v3n
            ll_pairs = [("L1-L2", float(v12), float(v1n)), ("L2-L3", float(v23), float(v2n)), ("L3-L1", float(v31), float(v3n))]
            ll_mismatch = False
            ll_details = {}
            for label, v_ll, v_ln in ll_pairs:
                ideal_ll = sqrt3 * v_ln
                if ideal_ll > 50.0:
                    diff_pct = abs(v_ll - ideal_ll) / ideal_ll
                    if diff_pct > v_line_tol:
                        ll_mismatch = True
                        ll_details[label] = {"v_ll": v_ll, "ideal_ll": ideal_ll, "diff_pct": diff_pct * 100}

            checks[("voltage_connection_incorrect", None, "Incorrect connection")] = (
                ll_mismatch,
                "Voltage connection incorrect: line-to-line vs line-to-neutral ratio error",
                ll_details
            )

            # Check nominal range (80% - 120%)
            v_nom_min = v_nom * float(th.get("v_nom_min_pct", 80.0)) / 100.0
            v_nom_max = v_nom * float(th.get("v_nom_max_pct", 120.0)) / 100.0
            avg_v = float(vln_avg) if vln_avg is not None else sum(v_vals) / 3.0
            v_out_of_range = avg_v < v_nom_min or avg_v > v_nom_max
            checks[("voltage_out_of_range", None, "Warning")] = (
                v_out_of_range,
                f"Voltage out of nominal range: {avg_v:.1f} V (nominal {v_nom} V +-20%)",
                {"vln_avg": avg_v, "nominal": v_nom, "range": [v_nom_min, v_nom_max]}
            )

        # ── Apply Debounce Logic and Update DB Alerts ──────────────────────
        active_severities: List[str] = []
        phase_chips = {
            "ct_l1": "Normal",
            "ct_l2": "Normal",
            "ct_l3": "Normal",
            "vclip_l1": "Normal",
            "vclip_l2": "Normal",
            "vclip_l3": "Normal",
            "ct_l1_detail": "Normal",
            "ct_l2_detail": "Normal",
            "ct_l3_detail": "Normal",
            "vclip_l1_detail": "Normal",
            "vclip_l2_detail": "Normal",
            "vclip_l3_detail": "Normal",
        }

        for (rule_type, phase, severity), (is_fault, message, details) in checks.items():
            debounce_key = (device.device_id, rule_type, phase)
            if debounce_key not in self._debounce_state:
                self._debounce_state[debounce_key] = {"bad_count": 0, "good_count": 0}
            state = self._debounce_state[debounce_key]

            # Query currently open alert in DB
            open_alert = (
                db.query(Alert)
                .filter(
                    Alert.device_id == device.device_id,
                    Alert.type == rule_type,
                    Alert.phase == phase,
                    Alert.cleared_at.is_(None)
                )
                .first()
            )

            if is_fault:
                state["bad_count"] += 1
                state["good_count"] = 0
                if state["bad_count"] >= n_raise:
                    # Raise or keep open
                    alert_details = dict(details)
                    if "reason" not in alert_details:
                        alert_details["reason"] = message
                    if not open_alert:
                        open_alert = Alert(
                            device_id=device.device_id,
                            type=rule_type,
                            phase=phase,
                            severity=severity,
                            started_at=reading_time,
                            details=alert_details
                        )
                        db.add(open_alert)
                    else:
                        open_alert.severity = severity
                        open_alert.details = alert_details
                    active_severities.append(severity)
                    self._update_phase_chips(phase_chips, rule_type, phase, severity, message)
            else:
                state["good_count"] += 1
                state["bad_count"] = 0
                if state["good_count"] >= n_clear and open_alert:
                    # Clear alert
                    open_alert.cleared_at = reading_time
                elif open_alert:
                    # Still open while clearing debounce in progress
                    active_severities.append(severity)
                    self._update_phase_chips(phase_chips, rule_type, phase, severity, message)

        # ── Compute Overall Status (Precedence order) ─────────────────────
        # Communication failure > Disconnected > Incorrect connection > Warning > Normal
        overall_status = "Normal"
        precedence = ["Communication failure", "Disconnected", "Incorrect connection", "Warning"]
        for sev in precedence:
            if sev in active_severities:
                overall_status = sev
                break

        return overall_status, phase_chips

    def _update_phase_chips(
        self,
        chips: Dict[str, str],
        rule_type: str,
        phase: Optional[str],
        severity: str,
        message: str
    ):
        """Update phase status chips with highest severity fault message."""
        severity_rank = {
            "Normal": 0,
            "Warning": 1,
            "Incorrect connection": 2,
            "Disconnected": 3,
            "Communication failure": 4
        }
        
        target_keys = []
        if rule_type.startswith("ct_"):
            if phase:
                target_keys.append(f"ct_{phase.lower()}")
            else:
                target_keys.extend(["ct_l1", "ct_l2", "ct_l3"])
        elif rule_type.startswith("voltage_clip_"):
            if phase:
                target_keys.append(f"vclip_{phase.lower()}")
            else:
                target_keys.extend(["vclip_l1", "vclip_l2", "vclip_l3"])
        elif rule_type == "sensor_comm_failure" or rule_type == "current_signal_missing":
            target_keys.extend(["ct_l1", "ct_l2", "ct_l3"])
        elif rule_type == "voltage_signal_missing" or rule_type == "voltage_connection_incorrect":
            target_keys.extend(["vclip_l1", "vclip_l2", "vclip_l3"])

        for k in target_keys:
            curr_sev = chips.get(k, "Normal")
            if severity_rank.get(severity, 0) >= severity_rank.get(curr_sev, 0):
                chips[k] = severity
                chips[f"{k}_detail"] = message

    def check_comm_watchdog(self, db: Session, now: datetime):
        """
        Watchdog checker: run every 30s to detect network/comm failure.
        IoT device comm failure: now - last_seen > max(3 * interval, 180s).
        """
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
            
        devices = db.query(Device).all()
        for device in devices:
            if not device.last_seen:
                continue
            last_seen = device.last_seen
            if last_seen.tzinfo is None:
                last_seen = last_seen.replace(tzinfo=timezone.utc)
            interval = device.expected_interval_s or 60
            comm_timeout = max(3 * interval, 180)
            elapsed = (now - last_seen).total_seconds()
            
            open_alert = (
                db.query(Alert)
                .filter(
                    Alert.device_id == device.device_id,
                    Alert.type == "device_comm_failure",
                    Alert.cleared_at.is_(None)
                )
                .first()
            )

            if elapsed > comm_timeout:
                if not open_alert:
                    open_alert = Alert(
                        device_id=device.device_id,
                        type="device_comm_failure",
                        phase=None,
                        severity="Communication failure",
                        started_at=now,
                        details={"elapsed_seconds": elapsed, "timeout": comm_timeout}
                    )
                    db.add(open_alert)
                    device.status = "Communication failure"
            else:
                if open_alert:
                    open_alert.cleared_at = now
                    # Recompute device status
                    other_open = (
                        db.query(Alert)
                        .filter(
                            Alert.device_id == device.device_id,
                            Alert.cleared_at.is_(None)
                        )
                        .all()
                    )
                    if other_open:
                        precedence = ["Communication failure", "Disconnected", "Incorrect connection", "Warning"]
                        severities = [a.severity for a in other_open]
                        for s in precedence:
                            if s in severities:
                                device.status = s
                                break
                    else:
                        device.status = "Normal"


fault_engine = FaultEngine()
