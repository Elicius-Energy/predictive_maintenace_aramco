"""
Realistic industrial data simulator for when MQTT is unavailable.
Generates sensor data mimicking real industrial equipment patterns.
Supports multiple machines with distinct health profiles.
"""
import math
import random
import time
import logging
from datetime import datetime
from typing import Optional, List

import numpy as np

from app.models import (
    EnergyData, AccelData, SensorReading, DataSource, SimulationMode
)

logger = logging.getLogger(__name__)


# ── Machine Profile Definitions ──────────────────────────────────────────

MACHINE_PROFILES = {
    "sim-pump-001": {
        "name": "Centrifugal Pump P-101",
        "mode": SimulationMode.NORMAL,          # Healthy machine
        "base_voltage": 415.0,
        "base_current": 12.5,
        "base_power": 7500.0,
        "base_frequency": 50.0,
        "base_pf": 0.85,
        "rpm": 2950,
        "base_vib": 0.3,        # Low baseline vibration (healthy)
        "temperature": 45.0,
        "cumulative_energy": 1523.7,
        "operational_hours": 2847.3,
        "start_stop_cycles": 127,
    },
    "sim-pump-002": {
        "name": "Booster Pump P-202",
        "mode": SimulationMode.NORMAL,          # Healthy machine
        "base_voltage": 400.0,
        "base_current": 18.0,
        "base_power": 11000.0,
        "base_frequency": 50.0,
        "base_pf": 0.82,
        "rpm": 1450,            # 4-pole motor
        "base_vib": 0.35,       # Subtle baseline
        "temperature": 46.0,
        "cumulative_energy": 4812.5,
        "operational_hours": 8760.0,
        "start_stop_cycles": 342,
    },
    "sim-motor-003": {
        "name": "Compressor Motor M-301",
        "mode": SimulationMode.BEARING_DEGRADATION,  # Defective unit with dynamic variation
        "base_voltage": 440.0,
        "base_current": 22.0,
        "base_power": 15000.0,
        "base_frequency": 50.0,
        "base_pf": 0.88,
        "rpm": 3550,            # High-speed compressor
        "base_vib": 1.2,        # Higher baseline for defect visibility
        "temperature": 55.0,    # Already running warm
        "cumulative_energy": 9245.1,
        "operational_hours": 6500.0,
        "start_stop_cycles": 89,
    },
    "Machine_10": {
        "name": "Actual MQTT Device",
        "mode": SimulationMode.NORMAL,          # Healthy fallback
        "base_voltage": 226.0,
        "base_current": 5.0,
        "base_power": 1100.0,
        "base_frequency": 50.0,
        "base_pf": 0.95,
        "rpm": 1450,
        "base_vib": 0.2,
        "temperature": 40.0,
        "cumulative_energy": 0.0,
        "operational_hours": 100.0,
        "start_stop_cycles": 10,
    },
}

# Backward compatibility (if needed)
MACHINE_ALIASES = {
    "Machine_5": "sim-pump-001",
}

ALL_MACHINE_IDS = list(MACHINE_PROFILES.keys())


class MachineSimState:
    """Per-machine mutable simulation state."""

    def __init__(self, machine_id: str, profile: dict):
        self.machine_id = machine_id
        self.profile = profile
        self.mode = profile["mode"]
        self.tick = 0
        self.start_time = time.time()
        self._bearing_degradation_factor = 0.0
        self._anomaly_active = False
        self._anomaly_start = 0
        self._anomaly_duration = 0
        self._cumulative_energy = profile["cumulative_energy"]
        self._temperature = profile["temperature"]

        # For bearing degradation mode, start partially degraded so the
        # effect is visible quickly in a demo
        if self.mode == SimulationMode.BEARING_DEGRADATION:
            self._bearing_degradation_factor = 0.25


class SimulationEngine:
    """
    Generates realistic sensor data for multiple industrial machines.
    Each machine has its own health profile and simulation mode.
    """

    def __init__(self):
        self._states: dict[str, MachineSimState] = {}
        for mid, profile in MACHINE_PROFILES.items():
            self._states[mid] = MachineSimState(mid, profile)
        logger.info(f"Simulation engine initialized for machines: {ALL_MACHINE_IDS}")

    # ── Public API ────────────────────────────────────────────────────────

    def generate_reading(self, machine_id: str = "sim-pump-001") -> SensorReading:
        """Generate a single sensor reading for a specific machine."""
        # Resolve alias
        machine_id = MACHINE_ALIASES.get(machine_id, machine_id)

        state = self._states.get(machine_id)
        if state is None:
            raise ValueError(f"Unknown machine_id: {machine_id}")

        state.tick += 1
        t = time.time() - state.start_time
        profile = state.profile

        energy = self._generate_energy(t, state, profile)
        accel = self._generate_accel(t, state, profile)
        temp = self._generate_temperature(t, state, profile)

        return SensorReading(
            timestamp=datetime.utcnow(),
            machine_id=machine_id,
            source=DataSource.SIMULATED,
            energy=energy,
            accel=accel,
            temperature=temp,
        )

    def generate_all_readings(self) -> List[SensorReading]:
        """Generate one reading for every registered machine."""
        return [self.generate_reading(mid) for mid in ALL_MACHINE_IDS]

    # ── Energy ────────────────────────────────────────────────────────────

    def _generate_energy(self, t: float, state: MachineSimState, profile: dict) -> EnergyData:
        """Generate realistic electrical parameters."""
        base_v = profile["base_voltage"]
        base_i = profile["base_current"]
        base_pf = profile["base_pf"]

        # Load variation (slow sinusoidal + random)
        load_factor = 0.7 + 0.2 * math.sin(t / 120) + random.gauss(0, 0.02)
        load_factor = max(0.3, min(1.1, load_factor))

        voltage = base_v + random.gauss(0, 2.0)
        current = base_i * load_factor + random.gauss(0, 0.1)

        pf = base_pf + 0.05 * (load_factor - 0.7) + random.gauss(0, 0.005)
        pf = max(0.6, min(0.99, pf))

        active_power = voltage * current * math.sqrt(3) * pf / 1000   # kW
        apparent_power = voltage * current * math.sqrt(3) / 1000      # kVA

        frequency = profile["base_frequency"] + random.gauss(0, 0.05)

        state._cumulative_energy += active_power / 3600  # kWh per second

        # Degradation effects on electrical
        if state.mode == SimulationMode.BEARING_DEGRADATION:
            # Bearing drag increases current draw
            extra = state._bearing_degradation_factor * 0.15
            current *= (1 + extra)
            pf -= extra * 0.3
            active_power = voltage * current * math.sqrt(3) * pf / 1000

        if state.mode == SimulationMode.SUDDEN_ANOMALY and state._anomaly_active:
            current *= 1.3 + random.gauss(0, 0.1)
            pf -= 0.1
            active_power = voltage * current * math.sqrt(3) * pf / 1000

        return EnergyData(
            V=round(voltage, 2),
            I=round(max(0, current), 2),
            P=round(max(0, active_power), 2),
            KVA=round(max(0, apparent_power), 2),
            pf=round(max(0.5, min(1.0, pf)), 3),
            Energy=round(state._cumulative_energy, 2),
            Freq=round(frequency, 2),
        )

    # ── Vibration ─────────────────────────────────────────────────────────

    def _generate_accel(self, t: float, state: MachineSimState, profile: dict) -> AccelData:
        """Generate realistic vibration data with machine-specific profile."""
        rot_freq = profile["rpm"] / 60
        base_vib = profile["base_vib"]

        # 1X component (imbalance)
        ax_1x = base_vib * math.sin(2 * math.pi * rot_freq * t / 100)
        ay_1x = base_vib * math.sin(2 * math.pi * rot_freq * t / 100 + math.pi / 3)
        az_1x = base_vib * 0.5 * math.sin(2 * math.pi * rot_freq * t / 100 + math.pi / 6)

        # 2X component (misalignment)
        ax_2x = 0.1 * math.sin(2 * math.pi * 2 * rot_freq * t / 100)
        ay_2x = 0.1 * math.sin(2 * math.pi * 2 * rot_freq * t / 100 + math.pi / 4)
        az_2x = 0.05 * math.sin(2 * math.pi * 2 * rot_freq * t / 100)

        # Gaussian noise
        noise_x = random.gauss(0, 0.05)
        noise_y = random.gauss(0, 0.05)
        noise_z = random.gauss(0, 0.03)

        ax = ax_1x + ax_2x + noise_x
        ay = ay_1x + ay_2x + noise_y
        az = az_1x + az_2x + noise_z + 1.0  # gravity offset on Z

        # Gyroscope
        gx = random.gauss(0, 0.5)
        gy = random.gauss(0, 0.5)
        gz = random.gauss(0, 0.3)

        # ── Mode-specific vibration modifications ─────────────────────────

        if state.mode == SimulationMode.BEARING_DEGRADATION:
            # Progressive degradation
            state._bearing_degradation_factor = min(
                1.0, state._bearing_degradation_factor + 0.0005
            )
            degradation = state._bearing_degradation_factor

            # Bearing fault frequencies (BPFO-like harmonics)
            bpfo = rot_freq * 3.58
            bearing_vib = degradation * 1.5 * math.sin(2 * math.pi * bpfo * t / 100)

            # Impulse-like kurtosis spikes - Higher frequency for motor
            if random.random() < 0.6:
                impulse = degradation * random.gauss(0, 3.5)
                ax += impulse
                ay += impulse * 0.8

            ax += bearing_vib
            ay += bearing_vib * 0.7

            # Overall vibration amplitude increases significantly
            ax *= (1 + degradation * 3)
            ay *= (1 + degradation * 2.5)
            az *= (1 + degradation * 1.2)

            gx += degradation * random.gauss(0, 2)
            gy += degradation * random.gauss(0, 2)

        elif state.mode == SimulationMode.SUDDEN_ANOMALY:
            # Random anomaly events
            if not state._anomaly_active and random.random() < 0.005:
                state._anomaly_active = True
                state._anomaly_start = time.time()
                state._anomaly_duration = random.uniform(5, 30)
                logger.info(f"[{state.machine_id}] Sudden anomaly spike started")

            if state._anomaly_active:
                if time.time() - state._anomaly_start > state._anomaly_duration:
                    state._anomaly_active = False
                    logger.info(f"[{state.machine_id}] Sudden anomaly spike ended")
                else:
                    spike = random.gauss(0, 3.0)
                    ax += spike
                    ay += spike * 0.9
                    az += abs(spike) * 0.5
                    gx += random.gauss(0, 5)
                    gy += random.gauss(0, 5)

        return AccelData(
            ax=round(ax, 4),
            ay=round(ay, 4),
            az=round(az, 4),
            gx=round(gx, 4),
            gy=round(gy, 4),
            gz=round(gz, 4),
        )

    # ── Temperature ───────────────────────────────────────────────────────

    def _generate_temperature(self, t: float, state: MachineSimState, profile: dict) -> float:
        """Generate realistic temperature data."""
        temp = profile["temperature"] + 2 * math.sin(t / 600)
        temp += random.gauss(0, 0.3)

        if state.mode == SimulationMode.BEARING_DEGRADATION:
            temp += state._bearing_degradation_factor * 25

        if state.mode == SimulationMode.SUDDEN_ANOMALY and state._anomaly_active:
            temp += 15

        return round(max(20, min(120, temp)), 1)

    # ── Helpers ───────────────────────────────────────────────────────────

    def operational_hours(self, machine_id: str = "sim-pump-001") -> float:
        machine_id = MACHINE_ALIASES.get(machine_id, machine_id)
        state = self._states.get(machine_id)
        if state is None:
            return 0.0
        return state.profile["operational_hours"] + (time.time() - state.start_time) / 3600

    def start_stop_cycles(self, machine_id: str = "sim-pump-001") -> int:
        machine_id = MACHINE_ALIASES.get(machine_id, machine_id)
        state = self._states.get(machine_id)
        if state is None:
            return 0
        return state.profile["start_stop_cycles"]


# Singleton
simulation_engine = SimulationEngine()
