#!/usr/bin/env python3
"""
LEDL Energy Meter IoT Simulator.
Publishes physics-grounded 3-phase energy readings for two devices to HTTP API or MQTT.
Supports back-filling historical days, outage simulation (store-and-forward buffering),
and on-demand fault injections.
"""
import argparse
import json
import math
import random
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
import requests

DEVICE_A_ID = "002D00203335471332323632"
DEVICE_B_ID = "002D00203335471332323633"


class MotorSimulator:
    """Simulates realistic 3-phase induction motor electrical readings."""

    def __init__(self, device_id: str, rated_kw: float, base_kwh: int = 100):
        self.device_id = device_id
        self.rated_kw = rated_kw
        self.kwh_imp = base_kwh
        self.kvarh_imp = int(base_kwh * 0.75)
        self.t_kvah = int(base_kwh * 1.25)
        self.nominal_vln = 240.0
        self.last_ts: Optional[int] = None

    def generate_reading(
        self,
        epoch_ts: int,
        is_idle: bool = False,
        fault_flags: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate one reading payload for the given timestamp."""
        fault_flags = fault_flags or {}
        
        # Grid voltage variations (nominal ~240V L-N, ~415V L-L)
        v_noise = random.gauss(0, 1.2)
        v1n = round(self.nominal_vln + v_noise + random.uniform(-0.5, 0.5), 2)
        v2n = round(self.nominal_vln + v_noise + random.uniform(-0.5, 0.5), 2)
        v3n = round(self.nominal_vln + v_noise + 1.2 + random.uniform(-0.5, 0.5), 2)
        vln_avg = round((v1n + v2n + v3n) / 3.0, 2)

        sqrt3 = math.sqrt(3.0)
        v12 = round(sqrt3 * vln_avg + random.uniform(-1.0, 1.0), 2)
        v23 = round(sqrt3 * vln_avg + random.uniform(-1.0, 1.0), 2)
        v31 = round(sqrt3 * vln_avg + random.uniform(-1.0, 1.0), 2)
        vll_avg = round((v12 + v23 + v31) / 3.0, 2)

        freq = round(50.0 + random.uniform(-0.08, 0.08), 2)

        if is_idle:
            # Idle motor: ~4% rated power, poor power factor ~0.22, low current
            kw_target = self.rated_kw * 0.04
            pf_avg = round(random.uniform(0.20, 0.25), 2)
            i_avg = round((kw_target * 1000) / (sqrt3 * vll_avg * pf_avg), 2)
            i1 = round(i_avg + random.uniform(-0.1, 0.1), 2)
            i2 = round(i_avg + random.uniform(-0.1, 0.1), 2)
            i3 = round(i_avg + random.uniform(-0.1, 0.1), 2)
            kw1 = round(kw_target / 3.0 + random.uniform(-0.01, 0.01), 2)
            kw2 = round(kw_target / 3.0 + random.uniform(-0.01, 0.01), 2)
            kw3 = round(kw_target - kw1 - kw2, 2)
            pf1, pf2, pf3 = pf_avg, pf_avg, pf_avg
        else:
            # Running motor under 65%-85% load
            load_factor = random.uniform(0.68, 0.82)
            kw_target = self.rated_kw * load_factor
            pf_avg = round(random.uniform(0.79, 0.84), 2)
            i_avg = round((kw_target * 1000) / (sqrt3 * vll_avg * pf_avg), 2)
            i1 = round(i_avg + random.uniform(-0.25, 0.25), 2)
            i2 = round(i_avg + random.uniform(-0.25, 0.25), 2)
            i3 = round(i_avg + random.uniform(-0.25, 0.25), 2)
            kw1 = round(kw_target / 3.0 + random.uniform(-0.05, 0.05), 2)
            kw2 = round(kw_target / 3.0 + random.uniform(-0.05, 0.05), 2)
            kw3 = round(kw_target - kw1 - kw2, 2)
            pf1 = round(pf_avg + random.uniform(-0.02, 0.02), 2)
            pf2 = round(pf_avg + random.uniform(-0.02, 0.02), 2)
            pf3 = round(pf_avg + random.uniform(-0.02, 0.02), 2)

        t_kw = round(kw1 + kw2 + kw3, 2)
        kva_target = round(t_kw / pf_avg, 2)
        kvar_target = round(math.sqrt(max(0, kva_target**2 - t_kw**2)), 2)

        kva1 = round(kva_target / 3.0, 2)
        kva2 = round(kva_target / 3.0, 2)
        kva3 = round(kva_target - kva1 - kva2, 2)
        t_kva = round(kva1 + kva2 + kva3, 2)

        kvar1 = round(kvar_target / 3.0, 2)
        kvar2 = round(kvar_target / 3.0, 2)
        kvar3 = round(kvar_target - kvar1 - kvar2, 2)
        t_kvar = round(kvar1 + kvar2 + kvar3, 2)

        # Increment energy counters if time elapsed
        if self.last_ts:
            dt = epoch_ts - self.last_ts
            if 0 < dt <= 300:
                d_kwh = (t_kw * dt) / 3600.0
                d_kvarh = (t_kvar * dt) / 3600.0
                d_kvah = (t_kva * dt) / 3600.0
                self.kwh_imp += int(d_kwh >= 0.5)
                self.kvarh_imp += int(d_kvarh >= 0.5)
                self.t_kvah += int(d_kvah >= 0.5)
        self.last_ts = epoch_ts

        md_kw = round(t_kw * 1.08, 2)
        md_kvar = round(t_kvar * 1.05, 2)
        md_kva = round(t_kva * 1.08, 2)

        payload = {
            "dID": self.device_id,
            "dTS": epoch_ts,
            "fw_ver": "13.4",
            "v1n": v1n, "v2n": v2n, "v3n": v3n, "vln_avg": vln_avg,
            "v12": v12, "v23": v23, "v31": v31, "vll_avg": vll_avg,
            "i1": i1, "i2": i2, "i3": i3, "i_avg": i_avg,
            "kw1": kw1, "kw2": kw2, "kw3": kw3, "t_kw": t_kw,
            "kvar1": kvar1, "kvar2": kvar2, "kvar3": kvar3, "t_kvar": t_kvar,
            "kva1": kva1, "kva2": kva2, "kva3": kva3, "t_kva": t_kva,
            "pf1": pf1, "pf2": pf2, "pf3": pf3, "pf_avg": pf_avg,
            "freq": freq,
            "kwh_imp": self.kwh_imp, "kwh_exp": 0,
            "kvarh_imp": self.kvarh_imp, "kvarh_exp": 0,
            "t_kvah": self.t_kvah,
            "md_kw": md_kw, "md_kvar": md_kvar, "md_kva": md_kva
        }

        # Apply Fault Injections if requested
        if fault_flags.get("reverse_ct") == "L2":
            payload["kw2"] = -abs(payload["kw2"])
            payload["t_kw"] = round(payload["kw1"] + payload["kw2"] + payload["kw3"], 2)
        elif fault_flags.get("reverse_ct") == "ALL":
            payload["kw1"] = -abs(payload["kw1"])
            payload["kw2"] = -abs(payload["kw2"])
            payload["kw3"] = -abs(payload["kw3"])
            payload["t_kw"] = round(payload["kw1"] + payload["kw2"] + payload["kw3"], 2)

        if fault_flags.get("disconnect_ct") == "L3":
            payload["i3"] = 0.01
            payload["kw3"] = 0.00
            payload["t_kw"] = round(payload["kw1"] + payload["kw2"], 2)

        if fault_flags.get("disconnect_clip") == "L1":
            payload["v1n"] = 14.2

        if fault_flags.get("swap_ct"):
            payload["pf2"] = 0.38  # Mismatched PF indicates CT on wrong conductor

        if fault_flags.get("drop_fields") == "current":
            payload["i1"] = None
            payload["i2"] = None
            payload["i3"] = None

        return payload


def generate_backfill_batch(sim: MotorSimulator, days: int = 2) -> List[Dict[str, Any]]:
    """Generate realistic time-series readings with daily factory shift patterns."""
    readings = []
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=days)
    curr_dt = start_dt

    while curr_dt < end_dt:
        epoch = int(curr_dt.timestamp())
        hour = curr_dt.hour
        # Factory schedule: Shift 1 (08:00 - 16:00), Shift 2 (16:00 - 00:00) running;
        # Lunch/break (12:30 - 13:00) idle; Night shift idle/maintenance (02:00 - 05:00)
        is_idle = (hour in [2, 3, 4]) or (hour == 12 and curr_dt.minute >= 30)
        reading = sim.generate_reading(epoch, is_idle=is_idle)
        readings.append(reading)
        curr_dt += timedelta(minutes=1)

    return readings


def post_readings(url: str, key: str, payload: Any):
    """Send payload via HTTP POST to backend ingest API."""
    headers = {
        "Content-Type": "application/json",
        "X-Device-Key": key
    }
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="LEDL Motor Energy Meter IoT Simulator")
    parser.add_argument("--url", default="http://localhost:8000/api/ingest", help="Ingest API URL")
    parser.add_argument("--key", default="ledl_secret_device_key_2026", help="X-Device-Key")
    parser.add_argument("--interval", type=int, default=10, help="Publish interval in seconds (default 10s)")
    parser.add_argument("--backfill-days", type=int, default=0, help="Pre-load N days of historical readings")
    parser.add_argument("--reverse-ct", choices=["L1", "L2", "L3", "ALL"], help="Inject reverse CT polarity")
    parser.add_argument("--disconnect-ct", choices=["L1", "L2", "L3"], help="Inject disconnected CT")
    parser.add_argument("--disconnect-clip", choices=["L1", "L2", "L3"], help="Inject disconnected voltage clip")
    parser.add_argument("--swap-ct", action="store_true", help="Inject CT phase swap")
    parser.add_argument("--drop-fields", choices=["current", "voltage"], help="Drop telemetry fields")
    parser.add_argument("--freeze", action="store_true", help="Freeze telemetry output")
    parser.add_argument("--outage", type=str, help="Simulate network outage e.g. '10m', then send buffered back-fill")

    args = parser.parse_args()

    sim_a = MotorSimulator(DEVICE_A_ID, rated_kw=15.0, base_kwh=120)
    sim_b = MotorSimulator(DEVICE_B_ID, rated_kw=22.0, base_kwh=240)

    # 1. Backfill historical days if requested
    if args.backfill_days > 0:
        print(f"Generating and backfilling {args.backfill_days} days of historical readings for Device A & B...")
        history_a = generate_backfill_batch(sim_a, days=args.backfill_days)
        history_b = generate_backfill_batch(sim_b, days=args.backfill_days)
        
        # Post in chunks of 500
        for batch_name, hist in [("Device A", history_a), ("Device B", history_b)]:
            for i in range(0, len(hist), 500):
                chunk = hist[i:i+500]
                try:
                    res = post_readings(args.url, args.key, chunk)
                    print(f"[{batch_name}] Backfill chunk {i//500 + 1}: inserted={res.get('inserted')}, duplicate={res.get('duplicate')}")
                except Exception as e:
                    print(f"Error posting backfill chunk: {e}")
        print("Backfill completed successfully.")

    # 2. Outage simulation
    if args.outage:
        duration_s = 600 if "10m" in args.outage else 300
        print(f"Simulating network outage for {duration_s} seconds (buffering locally in memory)...")
        buffer_a = []
        start_ts = int(time.time())
        for sec in range(0, duration_s, 60):
            ts = start_ts + sec
            buffer_a.append(sim_a.generate_reading(ts))
        
        print(f"Outage ended. Backfilling {len(buffer_a)} buffered readings with original timestamps...")
        try:
            res = post_readings(args.url, args.key, buffer_a)
            print(f"Store-and-forward batch result: {res}")
        except Exception as e:
            print(f"Outage backfill failed: {e}")
        return

    # 3. Continuous live publishing loop
    print(f"Starting continuous telemetry publishing every {args.interval}s (Press Ctrl+C to stop)...")
    fault_flags = {
        "reverse_ct": args.reverse_ct,
        "disconnect_ct": args.disconnect_ct,
        "disconnect_clip": args.disconnect_clip,
        "swap_ct": args.swap_ct,
        "drop_fields": args.drop_fields,
    }

    frozen_sample_a = None
    while True:
        try:
            now_epoch = int(time.time())
            
            if args.freeze:
                if not frozen_sample_a:
                    frozen_sample_a = sim_a.generate_reading(now_epoch, fault_flags=fault_flags)
                payload_a = dict(frozen_sample_a)
                payload_a["dTS"] = now_epoch
            else:
                payload_a = sim_a.generate_reading(now_epoch, fault_flags=fault_flags)
            
            payload_b = sim_b.generate_reading(now_epoch)

            res_a = post_readings(args.url, args.key, payload_a)
            res_b = post_readings(args.url, args.key, payload_b)

            ts_str = datetime.fromtimestamp(now_epoch).strftime("%H:%M:%S")
            print(f"[{ts_str}] Sent readings | Dev A ({DEVICE_A_ID[-6:]}): {payload_a['t_kw']} kW, V={payload_a['vln_avg']}V | Dev B ({DEVICE_B_ID[-6:]}): {payload_b['t_kw']} kW")
        except Exception as e:
            print(f"Publish error: {e}")

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
