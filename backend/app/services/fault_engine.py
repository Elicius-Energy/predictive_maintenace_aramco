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
    FROZEN_SAMPLE_COUNT = 30

    # Rule types from earlier releases that are no longer evaluated. Any alert of
    # these types still open in the database is cleared on startup.
    RETIRED_RULE_TYPES = (
        "sensor_comm_failure",
        "ct_connection_incorrect",
        "ct_position_changed",
        "voltage_connection_incorrect",
    )

    # Short chip labels shown on the dashboard per rule type
    CHIP_LABELS = {
        "ct_polarity_incorrect": "Reverse CT",
        "ct_disconnected": "CT not connected",
        "current_signal_missing": "No signal",
        "voltage_clip_disconnected": "Check clip",
        "voltage_clip_imbalance": "Check clip",
        "voltage_signal_missing": "No signal",
    }

    STATUS_PRECEDENCE = ["Communication failure", "Disconnected", "Incorrect connection", "Warning"]

    @staticmethod
    def _phase_voltages(v1n, v2n, v3n, v12, v23, v31) -> List[float]:
        """
        Per-phase voltage estimate used for clip checks.
        Uses real phase-neutral values when the meter reports them (4-wire). For
        3-wire meters (all V-LN zero / missing) derives a virtual phase value from
        the two line-line voltages that involve that phase, so a missing clip on
        L1 shows up as a low L1 value (V12 and V31 both drop).
        """
        ln = [v1n, v2n, v3n]
        ll = [v12, v23, v31]
        ln_usable = all(x is not None for x in ln) and any(float(x) > 0 for x in ln)
        if ln_usable:
            return [float(x) for x in ln]
        if all(x is not None for x in ll):
            a, b, c = (float(x) for x in ll)  # V12, V23, V31
            s3 = 2.0 * math.sqrt(3.0)
            return [(a + c) / s3, (a + b) / s3, (b + c) / s3]
        return [float(x or 0.0) for x in ln]

    def recompute_status(self, device: Device, db: Session, exclude_types: Tuple[str, ...] = ()) -> str:
        """Derive device status from open, unacknowledged alerts."""
        q = db.query(Alert).filter(
            Alert.device_id == device.device_id,
            Alert.cleared_at.is_(None),
            Alert.acknowledged_at.is_(None),
        )
        if exclude_types:
            q = q.filter(~Alert.type.in_(exclude_types))
        severities = {a.severity for a in q.all()}
        for s in self.STATUS_PRECEDENCE:
            if s in severities:
                return s
        return "Normal"

    def heal_live_device_status(self, device: Device, db: Session, now: Optional[datetime] = None) -> str:
        """
        Ensure a device that is actively sending data is never stuck in
        'Communication failure' and has no lingering retired rule alerts.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        dirty = False

        # Clear any open retired-rule alerts for this device
        retired_open = (
            db.query(Alert)
            .filter(
                Alert.device_id == device.device_id,
                Alert.type.in_(self.RETIRED_RULE_TYPES),
                Alert.cleared_at.is_(None),
            )
            .all()
        )
        for a in retired_open:
            a.cleared_at = now
            dirty = True

        # If the device has sent data within comm_timeout_s, clear any open comm failure alert
        if device.last_seen and not self._comm_timed_out(device, now):
            comm_open = (
                db.query(Alert)
                .filter(
                    Alert.device_id == device.device_id,
                    Alert.type == "device_comm_failure",
                    Alert.cleared_at.is_(None),
                )
                .all()
            )
            for a in comm_open:
                a.cleared_at = now
                dirty = True
            if dirty:
                db.flush()
            if device.status == "Communication failure" or dirty:
                device.status = self.recompute_status(
                    device, db, exclude_types=("device_comm_failure",) + self.RETIRED_RULE_TYPES
                )
                dirty = True

        if dirty:
            db.commit()
        return device.status

    def clear_retired_alerts(self, db: Session):
        """Clear open alerts belonging to rule types that are no longer evaluated."""
        now = datetime.now(timezone.utc)
        stale = (
            db.query(Alert)
            .filter(Alert.type.in_(self.RETIRED_RULE_TYPES), Alert.cleared_at.is_(None))
            .all()
        )
        affected = set()
        for a in stale:
            a.cleared_at = now
            affected.add(a.device_id)
        db.flush()
        for dev in db.query(Device).filter(Device.device_id.in_(affected)).all() if affected else []:
            if dev.status != "Communication failure" or not self._comm_timed_out(dev, now):
                dev.status = self.recompute_status(dev, db)
            detail = dict(dev.status_detail or {})
            for k in ["ct_l1", "ct_l2", "ct_l3", "vclip_l1", "vclip_l2", "vclip_l3"]:
                detail[k] = "Normal"
                detail[f"{k}_detail"] = "Normal"
                detail[f"{k}_label"] = "Normal"
            dev.status_detail = detail

    @staticmethod
    def comm_timeout_s(device: Device) -> int:
        interval = device.expected_interval_s or 60
        return max(3 * interval, 180)

    def _comm_timed_out(self, device: Device, now: datetime) -> bool:
        if not device.last_seen:
            return False
        last_seen = device.last_seen
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        return (now - last_seen).total_seconds() > self.comm_timeout_s(device)

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

        # ── Rule A: Current signal not received ────────────────────────────
        i_missing = any(x is None for x in [i1, i2, i3])
        checks[("current_signal_missing", None, "Disconnected")] = (
            i_missing,
            "Current signal not received: one or more phase currents missing",
            {"i1": i1, "i2": i2, "i3": i3, "i_avg": i_avg}
        )

        # ── Rule B: Voltage signal not received ────────────────────────────
        # A usable voltage set is either all three phase-neutral values (4-wire)
        # or all three line-line values (3-wire meters).
        has_ln = all(x is not None for x in [v1n, v2n, v3n])
        has_ll = all(x is not None for x in [v12, v23, v31])
        v_missing = not (has_ln or has_ll)
        checks[("voltage_signal_missing", None, "Disconnected")] = (
            v_missing,
            "Voltage signal not received: phase voltages missing",
            {"v1n": v1n, "v2n": v2n, "v3n": v3n, "v12": v12, "v23": v23, "v31": v31}
        )

        # ── Rule C: Sensor data quality (Warning only) ─────────────────────
        # Data IS being received, so this must never be reported as a
        # "Communication failure" (that status is reserved for the no-data watchdog).
        data_invalid = False
        data_reason = ""
        non_numeric = False
        try:
            for v in [v1n, v2n, v3n, v12, v23, v31]:
                if v is not None and (float(v) < 0 or float(v) > 600):
                    data_invalid = True
                    data_reason = f"Voltage out of physical bounds: {v} V"
            if freq is not None and (float(freq) < 40 or float(freq) > 60):
                data_invalid = True
                data_reason = f"Frequency out of physical bounds: {freq} Hz"
        except (ValueError, TypeError) as conv_err:
            data_invalid = True
            non_numeric = True
            data_reason = f"Non-numeric telemetry: {conv_err}"

        # Frozen telemetry: the full electrical signature unchanged for 30 consecutive samples
        dev_id = device.device_id
        hist = self._payload_history.setdefault(dev_id, [])
        current_sample = (v12, v23, v31, v1n, v2n, v3n, i1, i2, i3, t_kw, pf1, pf2, pf3, freq, payload.get("t_kvar"))
        hist.append(current_sample)
        if len(hist) > self.FROZEN_SAMPLE_COUNT:
            hist.pop(0)
        if (
            not data_invalid
            and len(hist) == self.FROZEN_SAMPLE_COUNT
            and all(s == current_sample for s in hist)
            and any((x or 0) != 0 for x in (i1, i2, i3))
        ):
            data_invalid = True
            data_reason = f"Frozen telemetry: readings unchanged for {self.FROZEN_SAMPLE_COUNT} consecutive samples"

        checks[("sensor_data_invalid", None, "Warning")] = (
            data_invalid,
            f"Sensor data check: {data_reason}" if data_invalid else "Sensor data normal",
            {"reason": data_reason}
        )

        # Proceed to per-phase CT / clip checks only when signals are present and numeric
        if not (i_missing or v_missing or non_numeric):
            phases = ["L1", "L2", "L3"]
            i_vals = [abs(float(i1)), abs(float(i2)), abs(float(i3))]
            kw_vals = [float(kw1) if kw1 is not None else None,
                       float(kw2) if kw2 is not None else None,
                       float(kw3) if kw3 is not None else None]
            v_phase = self._phase_voltages(v1n, v2n, v3n, v12, v23, v31)

            # ── CT Rule 1: Reverse CT ───────────────────────────────────────
            # Negative active power on any CT while that CT carries current.
            for idx, phase in enumerate(phases):
                kw = kw_vals[idx]
                is_reversed = kw is not None and kw < -0.02 and i_vals[idx] > i_min
                msg = (
                    f"Reverse CT on {phase}: negative active power ({kw:.2f} kW). Check CT direction."
                    if kw is not None else f"Reverse CT on {phase}"
                )
                checks[("ct_polarity_incorrect", phase, "Incorrect connection")] = (
                    is_reversed,
                    msg,
                    {"reason": msg, "kw": kw, "i": i_vals[idx]}
                )

            # ── CT Rule 2: CT not connected ─────────────────────────────────
            # Exactly one CT reads zero current while the other two carry current.
            # All three at zero = motor stopped (not a fault).
            ct_other_min = float(th.get("ct_other_min_a", 0.2))
            zero_flags = [i < i_min for i in i_vals]
            for idx, phase in enumerate(phases):
                others = [i_vals[o] for o in range(3) if o != idx]
                is_ct_open = (
                    zero_flags[idx]
                    and sum(zero_flags) == 1
                    and all(o > ct_other_min for o in others)
                )
                msg = f"CT {phase} not connected: zero current ({i_vals[idx]:.2f} A) while other phases carry load"
                checks[("ct_disconnected", phase, "Disconnected")] = (
                    is_ct_open,
                    msg,
                    {"reason": msg, "i": i_vals[idx], "other_currents": others}
                )

            # ── Clip Rule: voltage missing or highly imbalanced on a phase ─
            clip_tol = float(th.get("clip_imbalance_pct", 10.0)) / 100.0
            for idx, phase in enumerate(phases):
                v_k = v_phase[idx]
                others = [v_phase[o] for o in range(3) if o != idx]
                ref = max(others)
                is_missing = v_k < v_min
                is_imbalanced = (not is_missing) and ref > v_min and v_k < (1.0 - clip_tol) * ref
                miss_msg = f"Check clip {phase}: voltage missing ({v_k:.1f} V)"
                imb_msg = (
                    f"Check clip {phase}: voltage highly imbalanced "
                    f"({v_k:.1f} V vs {ref:.1f} V on other phases)"
                )
                checks[("voltage_clip_disconnected", phase, "Disconnected")] = (
                    is_missing,
                    miss_msg,
                    {"reason": miss_msg, "voltage": v_k, "min_required": v_min}
                )
                checks[("voltage_clip_imbalance", phase, "Warning")] = (
                    is_imbalanced,
                    imb_msg,
                    {"reason": imb_msg, "voltage": v_k, "reference": ref, "tolerance_pct": clip_tol * 100}
                )

            # ── Supply voltage out of nominal range (general warning) ──────
            # Nominal values above 300 V are treated as line-line ratings.
            v_nom_min_f = float(th.get("v_nom_min_pct", 80.0)) / 100.0
            v_nom_max_f = float(th.get("v_nom_max_pct", 120.0)) / 100.0
            if v_nom > 300.0:
                ll_vals = [float(x) for x in (v12, v23, v31) if x is not None]
                avg_v = (sum(ll_vals) / len(ll_vals)) if ll_vals else sum(v_phase) / 3.0 * math.sqrt(3.0)
            else:
                avg_v = sum(v_phase) / 3.0
            v_out_of_range = avg_v < v_nom * v_nom_min_f or avg_v > v_nom * v_nom_max_f
            checks[("voltage_out_of_range", None, "Warning")] = (
                v_out_of_range,
                f"Supply voltage out of nominal range: {avg_v:.1f} V (nominal {v_nom:.0f} V ±20%)",
                {"avg_voltage": avg_v, "nominal": v_nom}
            )

        # ── Apply Debounce Logic and Update DB Alerts ──────────────────────
        active_severities: List[str] = []
        phase_chips: Dict[str, str] = {}
        for k in ["ct_l1", "ct_l2", "ct_l3", "vclip_l1", "vclip_l2", "vclip_l3"]:
            phase_chips[k] = "Normal"
            phase_chips[f"{k}_detail"] = "Normal"
            phase_chips[f"{k}_label"] = "Normal"

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

                    # Only trip active alarm severity if not already acknowledged by operator
                    if open_alert.acknowledged_at is None:
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
                    if open_alert.acknowledged_at is None:
                        active_severities.append(severity)
                        self._update_phase_chips(phase_chips, rule_type, phase, severity, message)

        # ── Compute Overall Status (Precedence order) ─────────────────────
        # Communication failure > Disconnected > Incorrect connection > Warning > Normal
        overall_status = "Normal"
        for sev in self.STATUS_PRECEDENCE:
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
        elif rule_type == "current_signal_missing":
            target_keys.extend(["ct_l1", "ct_l2", "ct_l3"])
        elif rule_type == "voltage_signal_missing":
            target_keys.extend(["vclip_l1", "vclip_l2", "vclip_l3"])

        for k in target_keys:
            curr_sev = chips.get(k, "Normal")
            if severity_rank.get(severity, 0) >= severity_rank.get(curr_sev, 0):
                chips[k] = severity
                chips[f"{k}_detail"] = message
                chips[f"{k}_label"] = self.CHIP_LABELS.get(rule_type, severity)

    def check_comm_watchdog(self, db: Session, now: datetime):
        """
        Watchdog checker: run every 30s to detect network/comm failure.
        IoT device comm failure: now - last_seen > max(3 * interval, 180s).
        "Communication failure" is raised ONLY here (no data received). Once data
        flows again the alert is cleared and the status is recomputed from the
        remaining open, unacknowledged alerts on every cycle, so a device can never
        stay stuck on "Communication failure" while it is sending data.
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
            comm_timeout = self.comm_timeout_s(device)
            elapsed = (now - last_seen).total_seconds()

            open_comm_alerts = (
                db.query(Alert)
                .filter(
                    Alert.device_id == device.device_id,
                    Alert.type == "device_comm_failure",
                    Alert.cleared_at.is_(None)
                )
                .all()
            )

            if elapsed > comm_timeout:
                if not open_comm_alerts:
                    db.add(Alert(
                        device_id=device.device_id,
                        type="device_comm_failure",
                        phase=None,
                        severity="Communication failure",
                        started_at=now,
                        details={
                            "elapsed_seconds": elapsed,
                            "timeout": comm_timeout,
                            "reason": f"No data received for {int(elapsed // 60)} min",
                        }
                    ))
                device.status = "Communication failure"
            else:
                for alert in open_comm_alerts:
                    alert.cleared_at = now
                if open_comm_alerts:
                    db.flush()
                if open_comm_alerts or device.status == "Communication failure":
                    device.status = self.recompute_status(
                        device, db, exclude_types=("device_comm_failure",) + self.RETIRED_RULE_TYPES
                    )


fault_engine = FaultEngine()
