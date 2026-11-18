"""
Ingestion Service for Elicius Energy IoT Monitoring.
Handles single and batch ingestion with idempotency,
validation of timestamps, fault evaluation, and continuous aggregate window refreshing.
Devices must be manually registered before data is accepted.
"""
from datetime import datetime, timezone, timedelta
import logging
import math
from typing import Dict, Any, List, Union, Tuple, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.db.models import Device, DeviceProfile, Reading
from app.services.fault_engine import fault_engine

logger = logging.getLogger(__name__)

MIN_VALID_YEAR = 2020


class IngestService:
    """Service handling idempotent sensor reading ingestion."""

    def process_payload(
        self,
        payload_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        db: Session
    ) -> Dict[str, int]:
        """
        Process a single reading or batch (list of readings).
        Returns counts: {"inserted": int, "duplicate": int, "rejected": int}
        """
        if isinstance(payload_data, dict):
            readings = [payload_data]
        elif isinstance(payload_data, list):
            readings = payload_data
        else:
            return {"inserted": 0, "duplicate": 0, "rejected": 1}

        inserted = 0
        duplicate = 0
        rejected = 0
        earliest_backfill_ts: Optional[datetime] = None
        now_utc = datetime.now(timezone.utc)

        for item in readings:
            res, reading_ts = self._process_single_reading(item, db, now_utc)
            if res == "inserted":
                inserted += 1
                if (now_utc - reading_ts).total_seconds() > 300:  # Older than 5 min is a backfill
                    if earliest_backfill_ts is None or reading_ts < earliest_backfill_ts:
                        earliest_backfill_ts = reading_ts
            elif res == "duplicate":
                duplicate += 1
            else:
                rejected += 1

        db.commit()

        # If we had backfilled readings in a TimescaleDB environment, refresh aggregates
        if earliest_backfill_ts and inserted > 0:
            self._refresh_continuous_aggregates(db, earliest_backfill_ts, now_utc)

        return {"inserted": inserted, "duplicate": duplicate, "rejected": rejected}

    def _process_single_reading(
        self,
        item: Dict[str, Any],
        db: Session,
        server_now: datetime
    ) -> Tuple[str, Optional[datetime]]:
        """Validate reading and insert if device is registered; reject unknown devices."""
        d_id = item.get("dID")
        d_ts = item.get("dTS")

        if not d_id or d_ts is None:
            return "rejected", None

        # Validate dTS
        try:
            d_ts_int = int(d_ts)
            reading_time = datetime.fromtimestamp(d_ts_int, tz=timezone.utc)
            # Detect if meter firmware generated epoch from IST (+05:30) wall clock time
            diff_sec = (reading_time - server_now).total_seconds()
            if 18000 <= diff_sec <= 21600:
                reading_time = reading_time - timedelta(hours=5, minutes=30)
        except (ValueError, OSError, OverflowError):
            return "rejected", None

        if reading_time.year < MIN_VALID_YEAR:
            return "rejected", reading_time

        # Reject > 24 hours in future
        if (reading_time - server_now).total_seconds() > 86400:
            return "rejected", reading_time

        device_id = str(d_id).strip()

        # Reject data from unregistered devices (manual registration required)
        device = db.query(Device).filter(Device.device_id == device_id).first()
        if not device:
            logger.debug("Rejected reading from unregistered device: %s", device_id)
            return "rejected", reading_time
        else:
            first_seen_utc = self._to_utc_dt(device.first_seen)
            last_seen_utc = self._to_utc_dt(device.last_seen)
            is_newest_reading = last_seen_utc is None or reading_time >= last_seen_utc
            if not first_seen_utc or reading_time < first_seen_utc:
                device.first_seen = reading_time
            if not last_seen_utc or reading_time > last_seen_utc or (last_seen_utc - server_now).total_seconds() > 60:
                device.last_seen = reading_time
            if item.get("fw_ver"):
                device.fw_ver = str(item.get("fw_ver"))

        # Check for existing reading (Idempotency)
        existing = db.query(Reading).filter(
            Reading.device_id == device_id,
            Reading.ts == reading_time
        ).first()
        if existing:
            return "duplicate", reading_time

        # Normalize 3P3W (Two-Wattmeter) readings so virtual phase voltages and
        # individual phase powers (kw1, kw2, kw3) are computed accurately while
        # preserving the original raw meter payload in reading.raw.
        raw_item = dict(item)
        item = self._normalize_3p3w(item)

        # Create reading record
        reading = Reading(
            device_id=device_id,
            ts=reading_time,
            received_at=server_now,
            fw_ver=str(item.get("fw_ver", device.fw_ver)),
            v1n=self._safe_float(item.get("v1n")),
            v2n=self._safe_float(item.get("v2n")),
            v3n=self._safe_float(item.get("v3n")),
            vln_avg=self._safe_float(item.get("vln_avg")),
            v12=self._safe_float(item.get("v12")),
            v23=self._safe_float(item.get("v23")),
            v31=self._safe_float(item.get("v31")),
            vll_avg=self._safe_float(item.get("vll_avg")),
            i1=self._safe_float(item.get("i1")),
            i2=self._safe_float(item.get("i2")),
            i3=self._safe_float(item.get("i3")),
            i_avg=self._safe_float(item.get("i_avg")),
            kw1=self._safe_float(item.get("kw1")),
            kw2=self._safe_float(item.get("kw2")),
            kw3=self._safe_float(item.get("kw3")),
            t_kw=self._safe_float(item.get("t_kw")),
            kvar1=self._safe_float(item.get("kvar1")),
            kvar2=self._safe_float(item.get("kvar2")),
            kvar3=self._safe_float(item.get("kvar3")),
            t_kvar=self._safe_float(item.get("t_kvar")),
            kva1=self._safe_float(item.get("kva1")),
            kva2=self._safe_float(item.get("kva2")),
            kva3=self._safe_float(item.get("kva3")),
            t_kva=self._safe_float(item.get("t_kva")),
            pf1=self._safe_float(item.get("pf1")),
            pf2=self._safe_float(item.get("pf2")),
            pf3=self._safe_float(item.get("pf3")),
            pf_avg=self._safe_float(item.get("pf_avg")),
            freq=self._safe_float(item.get("freq")),
            kwh_imp=self._safe_int(item.get("kwh_imp")),
            kwh_exp=self._safe_int(item.get("kwh_exp")),
            kvarh_imp=self._safe_int(item.get("kvarh_imp")),
            kvarh_exp=self._safe_int(item.get("kvarh_exp")),
            t_kvah=self._safe_int(item.get("t_kvah")),
            md_kw=self._safe_float(item.get("md_kw")),
            md_kvar=self._safe_float(item.get("md_kvar")),
            md_kva=self._safe_float(item.get("md_kva")),
            raw=raw_item
        )
        db.add(reading)

        # Run fault evaluation for real-time / near real-time packets (within 10 minutes of
        # server time) and for the newest packet of a device whose clock is skewed, so the
        # live status always reflects the data that is actually arriving.
        is_live = abs((server_now - reading_time).total_seconds()) < 600
        if is_live or is_newest_reading:
            fault_engine.heal_live_device_status(device, db, server_now)
            status, chips = fault_engine.evaluate_reading(
                device=device,
                profile=device.profile,
                baseline=device.baseline,
                payload=item,
                reading_time=reading_time,
                db=db
            )
            device.status = status
            device.status_detail = chips

        return "inserted", reading_time

    def _normalize_3p3w(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detect 3-Phase 3-Wire (3P3W / Two-Wattmeter) readings where phase-to-neutral
        voltages (v1n, v2n, v3n) are 0 and/or element 2 power (kw2) is 0 while total
        power (t_kw) and phase 2 current (i2) are active.
        Reconstructs virtual-neutral phase voltages and individual phase powers (kw1, kw2, kw3).
        """
        norm = dict(item)
        sqrt3 = math.sqrt(3.0)

        v1n = self._safe_float(norm.get("v1n"))
        v2n = self._safe_float(norm.get("v2n"))
        v3n = self._safe_float(norm.get("v3n"))
        v12 = self._safe_float(norm.get("v12"))
        v23 = self._safe_float(norm.get("v23"))
        v31 = self._safe_float(norm.get("v31"))
        vll_avg = self._safe_float(norm.get("vll_avg"))

        i1 = self._safe_float(norm.get("i1"))
        i2 = self._safe_float(norm.get("i2"))
        i3 = self._safe_float(norm.get("i3"))

        kw2 = self._safe_float(norm.get("kw2"))
        t_kw = self._safe_float(norm.get("t_kw"))
        kvar2 = self._safe_float(norm.get("kvar2"))
        t_kvar = self._safe_float(norm.get("t_kvar"))
        kva1 = self._safe_float(norm.get("kva1"))
        kva2 = self._safe_float(norm.get("kva2"))
        kva3 = self._safe_float(norm.get("kva3"))
        t_kva = self._safe_float(norm.get("t_kva"))

        vln_zero = all((v or 0.0) == 0.0 for v in (v1n, v2n, v3n))
        has_vll = any((v or 0.0) > 10.0 for v in (v12, v23, v31, vll_avg))

        # 1. Reconstruct virtual phase-to-neutral voltages if 3P3W reports v1n=v2n=v3n=0
        if vln_zero and has_vll:
            if (v12 or 0.0) > 0 and (v23 or 0.0) > 0 and (v31 or 0.0) > 0:
                v1n = round((v12 + v31) / (2.0 * sqrt3), 2)
                v2n = round((v12 + v23) / (2.0 * sqrt3), 2)
                v3n = round((v23 + v31) / (2.0 * sqrt3), 2)
            elif (vll_avg or 0.0) > 0:
                v_ln = round(vll_avg / sqrt3, 2)
                v1n = v2n = v3n = v_ln
            norm["v1n"] = v1n
            norm["v2n"] = v2n
            norm["v3n"] = v3n
            if v1n is not None and v2n is not None and v3n is not None:
                norm["vln_avg"] = round((v1n + v2n + v3n) / 3.0, 2)

        # 2. Reconstruct individual phase powers when meter is in 3P3W Two-Wattmeter mode
        is_3p3w_power = (
            (kw2 is None or kw2 == 0.0)
            and t_kw is not None
            and abs(t_kw) > 0.001
            and ((i2 or 0.0) > 0.01 or vln_zero)
        )
        if is_3p3w_power:
            v1_eff = v1n if (v1n or 0.0) > 0 else 1.0
            v2_eff = v2n if (v2n or 0.0) > 0 else 1.0
            v3_eff = v3n if (v3n or 0.0) > 0 else 1.0

            w1 = v1_eff * max(i1 or 0.0, 0.0)
            w2 = v2_eff * max(i2 or 0.0, 0.0)
            w3 = v3_eff * max(i3 or 0.0, 0.0)
            w_sum = w1 + w2 + w3

            if w_sum > 0:
                f1, f2 = w1 / w_sum, w2 / w_sum
            else:
                f1 = f2 = 1.0 / 3.0

            p1 = round(t_kw * f1, 2)
            p2 = round(t_kw * f2, 2)
            p3 = round(t_kw - p1 - p2, 2)
            norm["kw1"] = p1
            norm["kw2"] = p2
            norm["kw3"] = p3

            if (kvar2 is None or kvar2 == 0.0) and t_kvar is not None and abs(t_kvar) > 0.001:
                q1 = round(t_kvar * f1, 2)
                q2 = round(t_kvar * f2, 2)
                q3 = round(t_kvar - q1 - q2, 2)
                norm["kvar1"] = q1
                norm["kvar2"] = q2
                norm["kvar3"] = q3

            if all((s or 0.0) == 0.0 for s in (kva1, kva2, kva3)) and t_kva is not None and abs(t_kva) > 0.001:
                s1 = round(t_kva * f1, 2)
                s2 = round(t_kva * f2, 2)
                s3 = round(t_kva - s1 - s2, 2)
                norm["kva1"] = s1
                norm["kva2"] = s2
                norm["kva3"] = s3

        return norm

    def _to_utc_dt(self, dt: Optional[datetime]) -> Optional[datetime]:
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt

    def _safe_float(self, val: Any) -> Optional[float]:
        if val is None:
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    def _safe_int(self, val: Any) -> Optional[int]:
        if val is None:
            return None
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def _refresh_continuous_aggregates(self, db: Session, start_ts: datetime, end_ts: datetime):
        """In PostgreSQL/TimescaleDB, trigger manual refresh of affected continuous aggregates."""
        is_postgres = db.bind.dialect.name == "postgresql"
        if not is_postgres:
            return
        try:
            db.execute(text("""
                CALL refresh_continuous_aggregate('readings_1m', :start_ts, :end_ts);
                CALL refresh_continuous_aggregate('readings_5m', :start_ts, :end_ts);
                CALL refresh_continuous_aggregate('readings_1h', :start_ts, :end_ts);
            """), {"start_ts": start_ts, "end_ts": end_ts})
            db.commit()
            logger.info("Continuous aggregates refreshed for window %s to %s", start_ts, end_ts)
        except Exception as e:
            logger.warning("Continuous aggregate refresh notice: %s", str(e))


ingest_service = IngestService()
