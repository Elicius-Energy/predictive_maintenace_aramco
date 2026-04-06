"""
Feature engineering for predictive maintenance.
Computes RMS, Peak, Kurtosis, FFT, and rolling statistics.
"""
import logging
from typing import List, Dict, Optional, Tuple
import numpy as np
from scipy.stats import kurtosis
from scipy.fft import fft, fftfreq

from app.models import SensorReading, VibrationFeatures, ElectricalFeatures, FeatureVector
from app.config import settings

logger = logging.getLogger(__name__)

class FeatureExtractor:
    """Computes advanced features from raw sensor data."""
    
    def __init__(self):
        # Buffers for rolling calculations per machine
        self.accel_x_buffers: Dict[str, List[float]] = {}
        self.accel_y_buffers: Dict[str, List[float]] = {}
        self.accel_z_buffers: Dict[str, List[float]] = {}
        self.max_buffer_size = settings.FFT_WINDOW_SIZE
        
    def _init_machine_buffer(self, machine_id: str):
        if machine_id not in self.accel_x_buffers:
            self.accel_x_buffers[machine_id] = []
            self.accel_y_buffers[machine_id] = []
            self.accel_z_buffers[machine_id] = []

    def push_reading(self, reading: SensorReading):
        """Add new accel data to buffers for a specific machine."""
        if reading.accel:
            mid = reading.machine_id
            self._init_machine_buffer(mid)
            
            self.accel_x_buffers[mid].append(reading.accel.ax)
            self.accel_y_buffers[mid].append(reading.accel.ay)
            self.accel_z_buffers[mid].append(reading.accel.az)
            
            # Maintain buffer size
            if len(self.accel_x_buffers[mid]) > self.max_buffer_size:
                self.accel_x_buffers[mid].pop(0)
                self.accel_y_buffers[mid].pop(0)
                self.accel_z_buffers[mid].pop(0)

    def extract_features(self, reading: SensorReading) -> Optional[FeatureVector]:
        """Extract all features from the latest reading and machine's buffers."""
        if not reading.accel or not reading.energy:
            return None
            
        mid = reading.machine_id
        self.push_reading(reading)
        
        # Only compute if we have enough data for a decent window
        if len(self.accel_x_buffers[mid]) < 10:
            return None
            
        vibration = self._compute_vibration_features(mid)
        electrical = self._compute_electrical_features(reading)
        
        return FeatureVector(
            timestamp=reading.timestamp,
            machine_id=reading.machine_id,
            vibration=vibration,
            electrical=electrical,
            temperature=reading.temperature or 0.0
        )

    def _compute_vibration_features(self, machine_id: str) -> VibrationFeatures:
        """Compute time and frequency domain vibration features specific to machine."""
        x = np.array(self.accel_x_buffers[machine_id])
        y = np.array(self.accel_y_buffers[machine_id])
        z = np.array(self.accel_z_buffers[machine_id])
        
        # RMS (Root Mean Square)
        rms_x = np.sqrt(np.mean(np.square(x)))
        rms_y = np.sqrt(np.mean(np.square(y)))
        rms_z = np.sqrt(np.mean(np.square(z)))
        rms_overall = np.sqrt(rms_x**2 + rms_y**2 + rms_z**2)
        
        # Peak values
        peak_x = np.max(np.abs(x))
        peak_y = np.max(np.abs(y))
        peak_z = np.max(np.abs(z))
        
        # Kurtosis (Normalized 4th moment) - High kurtosis indicates bearing faults (impulses)
        k_x = kurtosis(x)
        k_y = kurtosis(y)
        k_z = kurtosis(z)
        
        # Crest Factor
        crest_factor = peak_x / rms_x if rms_x > 0 else 0
        
        # FFT Analysis
        fft_mag, fft_freq = self._compute_fft(x)
        
        # Find dominant frequency
        dom_idx = np.argmax(fft_mag[1:]) + 1 if len(fft_mag) > 1 else 0
        dom_freq = fft_freq[dom_idx] if dom_idx < len(fft_freq) else 0.0
        
        return VibrationFeatures(
            rms_x=float(rms_x),
            rms_y=float(rms_y),
            rms_z=float(rms_z),
            rms_overall=float(rms_overall),
            peak_x=float(peak_x),
            peak_y=float(peak_y),
            peak_z=float(peak_z),
            kurtosis_x=float(k_x),
            kurtosis_y=float(k_y),
            kurtosis_z=float(k_z),
            crest_factor=float(crest_factor),
            dominant_freq=float(dom_freq),
            fft_magnitudes=fft_mag.tolist(),
            fft_frequencies=fft_freq.tolist()
        )

    def _compute_fft(self, signal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Compute FFT and return magnitudes and frequencies."""
        N = len(signal)
        T = 1.0 / 100.0  # Assumed sampling rate 100Hz for now, adjustable
        
        yf = fft(signal - np.mean(signal)) # Detrend
        xf = fftfreq(N, T)[:N//2]
        
        mags = 2.0/N * np.abs(yf[0:N//2])
        return mags, xf

    def _compute_electrical_features(self, reading: SensorReading) -> ElectricalFeatures:
        """Extract electrical features."""
        e = reading.energy
        if not e:
            return ElectricalFeatures()
            
        # Estimated efficiency (simplified model)
        # Power loss ~ Copper loss + Iron loss (approximated)
        theoretical_power = e.V * e.I * np.sqrt(3) # Apparent if P was missing
        efficiency = (e.P / theoretical_power * 100) if theoretical_power > 0 else 0
        efficiency = min(100, max(0, efficiency))
        
        # Load percentage (assume nominal 10kW motor)
        load_pct = (e.P / 10.0) * 100 
        
        return ElectricalFeatures(
            voltage=e.V,
            current=e.I,
            active_power=e.P,
            apparent_power=e.KVA,
            power_factor=e.pf,
            frequency=e.Freq,
            efficiency=float(efficiency),
            load_percentage=float(load_pct),
            energy_cumulative=e.Energy
        )

# Singleton
feature_extractor = FeatureExtractor()
