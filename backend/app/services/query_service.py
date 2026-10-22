"""
Query Service for Elicius Energy Motor Energy Monitoring.
Handles continuous aggregate retrieval, data point capping, trapezoidal energy integration with gaps,
energy-weighted power factor, running vs idle time, and period summaries.
"""
from datetime import datetime, timezone, timedelta
import math
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text, desc
from sqlalchemy.orm import Session
from app.db.models import Device, DeviceProfile, Reading, Alert


class QueryService:
    """Service providing aggregated telemetry queries and engineering calculations."""

    MAX_CHART_POINTS = 5000

    def get_live_cards(self, device_id: str, db: Session) -> Dict[str, Any]:
        """
        Fetch data for the Six Live Cards on the dashboard:
        Voltage, Current, Power, Energy, Power Factor, Frequency,
        plus overall status and per-phase chips.
        """
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            return {"error": "Device not found"}

        latest = (
            db.query(Reading)
            .filter(Reading.device_id == device_id)
            .order_by(desc(Reading.ts))
            .first()
        )

        now_utc = datetime.now(timezone.utc)
        last_seen_str = "Never"
        seconds_ago = None
        if device.last_seen:
            dt = device.last_seen
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            seconds_ago = int((now_utc - dt).total_seconds())
            if seconds_ago <= 5:
                last_seen_str = "Just now"
            elif seconds_ago < 60:
                last_seen_str = f"{seconds_ago} s ago"
            elif seconds_ago < 3600:
                last_seen_str = f"{seconds_ago // 60} m ago"
            else:
                last_seen_str = f"{seconds_ago // 3600} h ago"

        # Energy consumed today (since midnight IST)
        IST = timezone(timedelta(hours=5, minutes=30))
        now_ist = datetime.now(timezone.utc).astimezone(IST)
        today_start_ist = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        today_start = today_start_ist.astimezone(timezone.utc).replace(tzinfo=None)
        today_readings = (
            db.query(Reading.ts, Reading.t_kw)
            .filter(Reading.device_id == device_id, Reading.ts >= today_start)
            .order_by(Reading.ts.asc())
            .all()
        )
        today_kwh = self._integrate_energy([(r.ts, r.t_kw) for r in today_readings], expected_interval_s=device.expected_interval_s or 60)

        # Active open alerts
        open_alerts = (
            db.query(Alert)
            .filter(Alert.device_id == device_id, Alert.cleared_at.is_(None))
            .order_by(desc(Alert.started_at))
            .all()
        )

        cards = {
            "device_id": device.device_id,
            "alias": device.alias or device.device_id,
            "status": device.status,
            "status_detail": device.status_detail or {},
            "last_seen_str": last_seen_str,
            "seconds_ago": seconds_ago,
            "voltage": {
                "avg": round(latest.vll_avg, 1) if latest and latest.vll_avg is not None else (round(latest.vln_avg * 1.732, 1) if latest and latest.vln_avg is not None else 0.0),
                "v12": round(latest.v12, 1) if latest and latest.v12 is not None else (round(latest.v1n * 1.732, 1) if latest and latest.v1n is not None else 0.0),
                "v23": round(latest.v23, 1) if latest and latest.v23 is not None else (round(latest.v2n * 1.732, 1) if latest and latest.v2n is not None else 0.0),
                "v31": round(latest.v31, 1) if latest and latest.v31 is not None else (round(latest.v3n * 1.732, 1) if latest and latest.v3n is not None else 0.0),
                "vll_avg": round(latest.vll_avg, 1) if latest and latest.vll_avg is not None else 0.0,
                "v1": round(latest.v12, 1) if latest and latest.v12 is not None else 0.0,
                "v2": round(latest.v23, 1) if latest and latest.v23 is not None else 0.0,
                "v3": round(latest.v31, 1) if latest and latest.v31 is not None else 0.0,
                "unit": "V"
            },
            "current": {
                "avg": round(latest.i_avg, 2) if latest and latest.i_avg is not None else 0.0,
                "i1": round(latest.i1, 2) if latest and latest.i1 is not None else 0.0,
                "i2": round(latest.i2, 2) if latest and latest.i2 is not None else 0.0,
                "i3": round(latest.i3, 2) if latest and latest.i3 is not None else 0.0,
                "unit": "A"
            },
            "power": {
                "total": round(latest.t_kw, 2) if latest and latest.t_kw is not None else 0.0,
                "kw1": round(latest.kw1, 2) if latest and latest.kw1 is not None else 0.0,
                "kw2": round(latest.kw2, 2) if latest and latest.kw2 is not None else 0.0,
                "kw3": round(latest.kw3, 2) if latest and latest.kw3 is not None else 0.0,
                "unit": "kW"
            },
            "energy": {
                "lifetime_kwh": int(latest.kwh_imp) if latest and latest.kwh_imp is not None else 0,
                "today_kwh": round(today_kwh, 2),
                "unit": "kWh"
            },
            "power_factor": {
                "avg": round(latest.pf_avg, 2) if latest and latest.pf_avg is not None else 1.0,
                "pf1": round(latest.pf1, 2) if latest and latest.pf1 is not None else 1.0,
                "pf2": round(latest.pf2, 2) if latest and latest.pf2 is not None else 1.0,
                "pf3": round(latest.pf3, 2) if latest and latest.pf3 is not None else 1.0,
                "unit": ""
            },
            "frequency": {
                "freq": round(latest.freq, 2) if latest and latest.freq is not None else 50.0,
                "unit": "Hz"
            },
            "open_alerts": [
                {
                    "id": a.id,
                    "type": a.type,
                    "phase": a.phase,
                    "severity": a.severity,
                    "started_at": a.started_at.isoformat() if a.started_at else None,
                    "details": a.details
                }
                for a in open_alerts
            ]
        }
        return cards

    def get_trend_charts(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Query time-series points for the dashboard charts using the appropriate continuous aggregate.
        interval: '1-minute', '5-minute', or '1-hour'
        Checks point-cap limit (5,000 points) and returns friendly hint if exceeded.
        """
        # Ensure UTC
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        duration_s = (end_time - start_time).total_seconds()
        interval_seconds = 60 if interval == "1-minute" else (300 if interval == "5-minute" else 3600)
        expected_points = int(duration_s / interval_seconds)

        if expected_points > self.MAX_CHART_POINTS:
            return {
                "hint": "Choose 5-minute or 1-hour interval for this long period",
                "points": [],
                "alert_windows": []
            }

        # Query readings in window
        readings = (
            db.query(Reading)
            .filter(
                Reading.device_id == device_id,
                Reading.ts >= start_time,
                Reading.ts <= end_time
            )
            .order_by(Reading.ts.asc())
            .all()
        )

        # Alerts in window for shaded alert bands
        alerts = (
            db.query(Alert)
            .filter(
                Alert.device_id == device_id,
                Alert.started_at <= end_time,
                (Alert.cleared_at.is_(None) | (Alert.cleared_at >= start_time))
            )
            .all()
        )
        alert_windows = [
            {
                "type": a.type,
                "phase": a.phase,
                "severity": a.severity,
                "start": a.started_at.isoformat(),
                "end": a.cleared_at.isoformat() if a.cleared_at else end_time.isoformat()
            }
            for a in alerts
        ]

        if not readings:
            return {"points": [], "alert_windows": alert_windows}

        # Bucket readings by interval
        bucket_map = self._bucket_readings(readings, interval_seconds, start_time, end_time)

        # Integrate interval energy (kWh per bucket)
        prev_cum_kwh = 0.0
        points = []
        for b_ts, vals in bucket_map.items():
            dt_str = datetime.fromtimestamp(b_ts, tz=timezone.utc).isoformat()
            if not vals:
                # Missing bucket -> nulls for gaps
                points.append({
                    "ts": dt_str,
                    "kwh": None, "cum_kwh": prev_cum_kwh,
                    "kw": None, "kw1": None, "kw2": None, "kw3": None,
                    "v_avg": None, "vll_avg": None, "v12": None, "v23": None, "v31": None,
                    "v1n": None, "v2n": None, "v3n": None,
                    "i_avg": None, "i1": None, "i2": None, "i3": None,
                    "pf_avg": None, "pf1": None, "pf2": None, "pf3": None,
                    "freq": None
                })
            else:
                avg_kw = sum(v["t_kw"] for v in vals if v["t_kw"] is not None) / max(len(vals), 1)
                b_kwh = avg_kw * (interval_seconds / 3600.0)
                prev_cum_kwh += b_kwh

                vll_avg = self._avg([v.get("vll_avg") for v in vals])
                vln_avg = self._avg([v.get("vln_avg") for v in vals])
                if vll_avg is not None:
                    v_avg = round(vll_avg, 1)
                elif vln_avg is not None:
                    v_avg = round(vln_avg * 1.732, 1)
                else:
                    v_avg = None

                points.append({
                    "ts": dt_str,
                    "kwh": round(b_kwh, 3),
                    "cum_kwh": round(prev_cum_kwh, 3),
                    "kw": round(avg_kw, 2),
                    "kw1": self._safe_round(self._avg([v.get("kw1") for v in vals]), 2),
                    "kw2": self._safe_round(self._avg([v.get("kw2") for v in vals]), 2),
                    "kw3": self._safe_round(self._avg([v.get("kw3") for v in vals]), 2),
                    "v_avg": v_avg,
                    "vll_avg": self._safe_round(vll_avg, 1),
                    "v12": self._safe_round(self._avg([v.get("v12") for v in vals]), 1),
                    "v23": self._safe_round(self._avg([v.get("v23") for v in vals]), 1),
                    "v31": self._safe_round(self._avg([v.get("v31") for v in vals]), 1),
                    "v1n": self._safe_round(self._avg([v.get("v1n") for v in vals]), 1),
                    "v2n": self._safe_round(self._avg([v.get("v2n") for v in vals]), 1),
                    "v3n": self._safe_round(self._avg([v.get("v3n") for v in vals]), 1),
                    "i_avg": self._safe_round(self._avg([v.get("i_avg") for v in vals]), 2),
                    "i1": self._safe_round(self._avg([v.get("i1") for v in vals]), 2),
                    "i2": self._safe_round(self._avg([v.get("i2") for v in vals]), 2),
                    "i3": self._safe_round(self._avg([v.get("i3") for v in vals]), 2),
                    "pf_avg": self._safe_round(self._avg([v.get("pf_avg") for v in vals]), 2),
                    "pf1": self._safe_round(self._avg([v.get("pf1") for v in vals]), 2),
                    "pf2": self._safe_round(self._avg([v.get("pf2") for v in vals]), 2),
                    "pf3": self._safe_round(self._avg([v.get("pf3") for v in vals]), 2),
                    "freq": self._safe_round(self._avg([v.get("freq") for v in vals]), 2)
                })

        return {"points": points, "alert_windows": alert_windows}

    def get_period_summary(
        self,
        device_id: str,
        start_time: datetime,
        end_time: datetime,
        db: Session
    ) -> Dict[str, Any]:
        """
        Compute the Period Summary Strip:
        Start Time, End Time, Analysis Period, Idle Time, Energy Consumption (kWh).
        Also includes advanced audit metrics for reports.
        """
        device = db.query(Device).filter(Device.device_id == device_id).first()
        profile = device.profile if device else None

        # Idle threshold: profile.idle_threshold_kw or 5% of motor rating or 0.2 kW
        idle_th = 0.2
        if profile and profile.idle_threshold_kw:
            idle_th = profile.idle_threshold_kw
        elif profile and profile.motor_rating_kw:
            idle_th = profile.motor_rating_kw * 0.05

        readings = (
            db.query(Reading)
            .filter(
                Reading.device_id == device_id,
                Reading.ts >= start_time,
                Reading.ts <= end_time
            )
            .order_by(Reading.ts.asc())
            .all()
        )

        expected_interval_s = device.expected_interval_s if device else 60
        duration_s = max((end_time - start_time).total_seconds(), 0)
        duration_hours = duration_s / 3600.0

        if not readings:
            return {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_str": self._format_duration(duration_s),
                "energy_kwh": 0.0,
                "idle_time_str": "0 h 0 min (0.0%)",
                "idle_hours": 0.0,
                "running_hours": 0.0,
                "avg_kw": 0.0,
                "avg_pf": None,
                "weighted_pf": None,
                "avg_voltage": None,
                "avg_current": None,
                "avg_frequency": None,
                "duration_hours": round(duration_hours, 2),
                "max_kw": None,
                "min_kw": None,
                "max_demand_kw": None,
                "load_factor": None,
                "voltage_unbalance_pct": None,
                "current_unbalance_pct": None,
                "samples_count": 0,
                "data_completeness_pct": 0.0
            }

        # Energy integration (trapezoidal) & idle vs running hours calculation
        total_energy_kwh = 0.0
        total_apparent_kvah = 0.0
        idle_seconds = 0.0
        running_seconds = 0.0
        received_samples = len(readings)

        kw_list = []
        pf_list = []
        v_list = []
        i_list = []
        freq_list = []
        v1n_list = []
        v2n_list = []
        v3n_list = []
        v12_list = []
        v23_list = []
        v31_list = []
        i1_list = []
        i2_list = []
        i3_list = []
        max_demand_kw = 0.0

        for idx in range(len(readings)):
            curr = readings[idx]
            curr_kw = curr.t_kw if curr.t_kw is not None else 0.0
            curr_kva = curr.t_kva if curr.t_kva is not None else curr_kw
            kw_list.append(curr_kw)
            if curr.pf_avg is not None:
                pf_list.append(curr.pf_avg)
            if curr.vll_avg is not None:
                v_list.append(curr.vll_avg)
            elif curr.vln_avg is not None:
                v_list.append(curr.vln_avg * 1.732)
            if curr.i_avg is not None:
                i_list.append(curr.i_avg)
            if curr.freq is not None:
                freq_list.append(curr.freq)
            if curr.v12 is not None:
                v12_list.append(curr.v12)
            elif curr.v1n is not None:
                v12_list.append(curr.v1n * 1.732)
            if curr.v23 is not None:
                v23_list.append(curr.v23)
            elif curr.v2n is not None:
                v23_list.append(curr.v2n * 1.732)
            if curr.v31 is not None:
                v31_list.append(curr.v31)
            elif curr.v3n is not None:
                v31_list.append(curr.v3n * 1.732)
            if curr.v1n is not None:
                v1n_list.append(curr.v1n)
            if curr.v2n is not None:
                v2n_list.append(curr.v2n)
            if curr.v3n is not None:
                v3n_list.append(curr.v3n)
            if curr.i1 is not None:
                i1_list.append(curr.i1)
            if curr.i2 is not None:
                i2_list.append(curr.i2)
            if curr.i3 is not None:
                i3_list.append(curr.i3)
            if curr.md_kw and curr.md_kw > max_demand_kw:
                max_demand_kw = curr.md_kw

            # Trapezoidal integration between consecutive points
            if idx > 0:
                prev = readings[idx - 1]
                t_prev = prev.ts.timestamp() if prev.ts.tzinfo else prev.ts.replace(tzinfo=timezone.utc).timestamp()
                t_curr = curr.ts.timestamp() if curr.ts.tzinfo else curr.ts.replace(tzinfo=timezone.utc).timestamp()
                dt = t_curr - t_prev
                
                # Gap rule: if gap > 3x expected interval, treat as gap (do not interpolate)
                if 0 < dt <= 3 * expected_interval_s:
                    kw_prev = prev.t_kw if prev.t_kw is not None else 0.0
                    kva_prev = prev.t_kva if prev.t_kva is not None else kw_prev
                    avg_p = (kw_prev + curr_kw) / 2.0
                    avg_s = (kva_prev + curr_kva) / 2.0
                    
                    total_energy_kwh += avg_p * (dt / 3600.0)
                    total_apparent_kvah += avg_s * (dt / 3600.0)
                    
                    if avg_p < idle_th:
                        idle_seconds += dt
                    else:
                        running_seconds += dt

        # Energy-weighted PF = kWh / kVAh
        weighted_pf = total_energy_kwh / total_apparent_kvah if total_apparent_kvah > 0 else (sum(pf_list) / len(pf_list) if pf_list else None)
        weighted_pf = max(0.0, min(1.0, weighted_pf)) if weighted_pf is not None else None

        # Expected samples vs received
        expected_samples = max(int(duration_s / expected_interval_s), 1)
        data_completeness = min(100.0, round((received_samples / expected_samples) * 100.0, 1))

        avg_kw = sum(kw_list) / max(len(kw_list), 1)
        max_kw = max(kw_list) if kw_list else 0.0
        min_kw = min(kw_list) if kw_list else 0.0
        load_factor = (avg_kw / max_kw) if max_kw > 0 else 0.0

        # Line-to-line voltage unbalance calculation
        v_unbalance_pct = 0.0
        target_v_list = (v12_list, v23_list, v31_list) if (v12_list and v23_list and v31_list) else (v1n_list, v2n_list, v3n_list)
        if target_v_list[0] and target_v_list[1] and target_v_list[2]:
            avg_v1 = sum(target_v_list[0]) / len(target_v_list[0])
            avg_v2 = sum(target_v_list[1]) / len(target_v_list[1])
            avg_v3 = sum(target_v_list[2]) / len(target_v_list[2])
            mean_v = (avg_v1 + avg_v2 + avg_v3) / 3.0
            if mean_v > 0:
                max_dev = max(abs(avg_v1 - mean_v), abs(avg_v2 - mean_v), abs(avg_v3 - mean_v))
                v_unbalance_pct = round((max_dev / mean_v) * 100.0, 2)

        i_unbalance_pct = 0.0
        if i1_list and i2_list and i3_list:
            avg_i1 = sum(i1_list) / len(i1_list)
            avg_i2 = sum(i2_list) / len(i2_list)
            avg_i3 = sum(i3_list) / len(i3_list)
            mean_i = (avg_i1 + avg_i2 + avg_i3) / 3.0
            if mean_i > 0:
                max_dev_i = max(abs(avg_i1 - mean_i), abs(avg_i2 - mean_i), abs(avg_i3 - mean_i))
                i_unbalance_pct = round((max_dev_i / mean_i) * 100.0, 2)

        idle_hours = idle_seconds / 3600.0
        running_hours = running_seconds / 3600.0
        idle_pct = (idle_seconds / max(duration_s, 1)) * 100.0

        # Discrepancy against hardware counter delta
        counter_delta = 0
        if readings[0].kwh_imp is not None and readings[-1].kwh_imp is not None:
            counter_delta = max(0, readings[-1].kwh_imp - readings[0].kwh_imp)
        discrepancy_pct = 0.0
        if counter_delta > 0:
            discrepancy_pct = round(abs(total_energy_kwh - counter_delta) / counter_delta * 100.0, 1)

        return {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_str": self._format_duration(duration_s),
            "duration_hours": round(duration_hours, 2),
            "energy_kwh": round(total_energy_kwh, 2),
            "counter_kwh_delta": counter_delta,
            "discrepancy_pct": discrepancy_pct,
            "idle_time_str": f"{self._format_duration(idle_seconds)} ({idle_pct:.1f}%)",
            "running_time_str": f"{self._format_duration(running_seconds)} ({max(0.0, 100.0 - idle_pct):.1f}%)",
            "idle_hours": round(idle_hours, 2),
            "running_hours": round(running_hours, 2),
            "idle_pct": round(idle_pct, 1),
            "running_pct": round(max(0.0, 100.0 - idle_pct), 1),
            "avg_kw": round(avg_kw, 2),
            "max_kw": round(max_kw, 2) if kw_list else None,
            "min_kw": round(min_kw, 2) if kw_list else None,
            "load_factor": round(load_factor, 2),
            "max_demand_kw": round(max_demand_kw, 2),
            "avg_pf": round(sum(pf_list) / len(pf_list), 2) if pf_list else None,
            "weighted_pf": round(weighted_pf, 2) if weighted_pf is not None else None,
            "avg_voltage": round(sum(v_list) / len(v_list), 1) if v_list else None,
            "voltage_unbalance_pct": v_unbalance_pct,
            "avg_current": round(sum(i_list) / len(i_list), 2) if i_list else None,
            "avg_frequency": round(sum(freq_list) / len(freq_list), 2) if freq_list else None,
            "current_unbalance_pct": i_unbalance_pct,
            "data_completeness_pct": data_completeness,
            "samples_count": received_samples
        }

    def _integrate_energy(self, time_kw_pairs: List[Tuple[datetime, Optional[float]]], expected_interval_s: int = 60) -> float:
        """Helper to integrate active power into total kWh."""
        total_kwh = 0.0
        for i in range(1, len(time_kw_pairs)):
            t_prev, kw_prev = time_kw_pairs[i - 1]
            t_curr, kw_curr = time_kw_pairs[i]
            if kw_prev is None or kw_curr is None:
                continue
            ts1 = t_prev.timestamp() if t_prev.tzinfo else t_prev.replace(tzinfo=timezone.utc).timestamp()
            ts2 = t_curr.timestamp() if t_curr.tzinfo else t_curr.replace(tzinfo=timezone.utc).timestamp()
            dt = ts2 - ts1
            if 0 < dt <= 3 * expected_interval_s:
                total_kwh += ((kw_prev + kw_curr) / 2.0) * (dt / 3600.0)
        return total_kwh

    def _bucket_readings(self, readings: List[Reading], interval_s: int, start: datetime, end: datetime) -> Dict[int, List[Dict[str, Any]]]:
        """Group readings into regular timestamp buckets with missing intervals represented."""
        start_aligned = (int(start.timestamp()) // interval_s) * interval_s
        end_aligned = (int(end.timestamp()) // interval_s) * interval_s
        
        # Initialize buckets aligned to interval_s
        buckets: Dict[int, List[Dict[str, Any]]] = {}
        for b in range(start_aligned, end_aligned + 1, interval_s):
            buckets[b] = []

        for r in readings:
            r_ts = int(r.ts.timestamp()) if r.ts.tzinfo else int(r.ts.replace(tzinfo=timezone.utc).timestamp())
            b_key = (r_ts // interval_s) * interval_s
            if b_key in buckets:
                vll = r.vll_avg if r.vll_avg is not None else (r.vln_avg * 1.732 if r.vln_avg is not None else None)
                v12_val = r.v12 if r.v12 is not None else (r.v1n * 1.732 if r.v1n is not None else None)
                v23_val = r.v23 if r.v23 is not None else (r.v2n * 1.732 if r.v2n is not None else None)
                v31_val = r.v31 if r.v31 is not None else (r.v3n * 1.732 if r.v3n is not None else None)
                buckets[b_key].append({
                    "t_kw": r.t_kw, "kw1": r.kw1, "kw2": r.kw2, "kw3": r.kw3,
                    "vln_avg": r.vln_avg, "v1n": r.v1n, "v2n": r.v2n, "v3n": r.v3n,
                    "vll_avg": vll, "v12": v12_val, "v23": v23_val, "v31": v31_val,
                    "i_avg": r.i_avg, "i1": r.i1, "i2": r.i2, "i3": r.i3,
                    "pf_avg": r.pf_avg, "pf1": r.pf1, "pf2": r.pf2, "pf3": r.pf3,
                    "freq": r.freq
                })
        return buckets

    def _avg(self, vals: List[Optional[float]]) -> Optional[float]:
        valid = [v for v in vals if v is not None]
        return sum(valid) / len(valid) if valid else None

    @staticmethod
    def _safe_round(val: Optional[float], decimals: int = 2) -> Optional[float]:
        return round(val, decimals) if val is not None else None

    def _format_duration(self, seconds: float) -> str:
        s = int(seconds)
        h = s // 3600
        m = (s % 3600) // 60
        return f"{h} h {m} min"


query_service = QueryService()
