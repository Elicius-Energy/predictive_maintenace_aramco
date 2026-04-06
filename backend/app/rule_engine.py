"""
Rule-based engine for threshold-based alerts (ISO-like logic).
"""
import logging
from typing import List, Optional
from datetime import datetime

from app.models import FeatureVector, Alert, Severity, MachineStatus, MachineHealth, HealthIndicator
from app.config import settings

logger = logging.getLogger(__name__)

class RuleEngine:
    """Evaluates features against engineering rules and ISO standards."""
    
    def evaluate(self, feature_vector: FeatureVector) -> List[Alert]:
        """Evaluate a feature vector and return any generated alerts."""
        alerts = []
        mv = feature_vector.vibration
        me = feature_vector.electrical
        mt = feature_vector.temperature
        
        # 1. Vibration Severity (ISO 10816 approximation)
        # Assuming Class II medium machines: 1.12-2.8 (Healthy), 2.8-7.1 (Alert), >7.1 (Critical)
        if mv.rms_overall > 7.1:
            alerts.append(self._create_alert("VIBRATION_CRITICAL", f"Excessive vibration: {mv.rms_overall:.2f} mm/s", Severity.CRITICAL, mv.rms_overall, 7.1))
        elif mv.rms_overall > 2.8:
            alerts.append(self._create_alert("VIBRATION_WARNING", f"High vibration: {mv.rms_overall:.2f} mm/s", Severity.WARNING, mv.rms_overall, 2.8))
            
        # 2. Bearing Fault Detection (Kurtosis)
        # Normal kurtosis ~3. Significant increase (> 5) indicates impulsive behavior (pitting/cracking)
        if mv.kurtosis_x > 6 or mv.kurtosis_y > 6:
            alerts.append(self._create_alert("BEARING_FAULT_SEVERE", "Critical bearing signature detected (High Kurtosis)", Severity.CRITICAL, max(mv.kurtosis_x, mv.kurtosis_y), 6.0))
        elif mv.kurtosis_x > 4 or mv.kurtosis_y > 4:
            alerts.append(self._create_alert("BEARING_FAULT_WARNING", "Early bearing wear detected", Severity.WARNING, max(mv.kurtosis_x, mv.kurtosis_y), 4.0))

        # 3. Electrical Anomalies
        if me.voltage > 460: # 415V nominal
            alerts.append(self._create_alert("OVERVOLTAGE", f"Overvoltage detected: {me.voltage:.1f}V", Severity.WARNING, me.voltage, 460.0))
        elif me.voltage < 370:
            alerts.append(self._create_alert("UNDERVOLTAGE", f"Undervoltage detected: {me.voltage:.1f}V", Severity.WARNING, me.voltage, 370.0))
            
        if me.power_factor < 0.7 and me.load_percentage > 50:
            alerts.append(self._create_alert("LOW_POWER_FACTOR", f"Inefficient power factor: {me.power_factor:.2f}", Severity.WARNING, me.power_factor, 0.7))

        # 4. Thermal
        if mt > 85:
            alerts.append(self._create_alert("TEMP_CRITICAL", f"Motor overheating: {mt:.1f}°C", Severity.CRITICAL, mt, 85.0))
        elif mt > 70:
            alerts.append(self._create_alert("TEMP_WARNING", f"High motor temperature: {mt:.1f}°C", Severity.WARNING, mt, 70.0))
            
        return alerts

    def get_iso_zone(self, rms_vibe: float) -> str:
        """Return ISO 10816 Zone (A, B, C, D)."""
        if rms_vibe <= 1.12: return "A" # Newly commissioned
        if rms_vibe <= 2.8: return "B" # Acceptable for long-term
        if rms_vibe <= 7.1: return "C" # Unsatisfactory for long-term
        return "D" # Damage likely

    def compute_health_summary(self, fv: FeatureVector, alerts: List[Alert]) -> MachineHealth:
        """Compute aggregate health score and indicators."""
        # Simple health score logic
        # Start at 100, subtract based on alerts
        base_score = 100.0
        active_severity = MachineStatus.HEALTHY
        
        indicators = []
        
        # Bearing Fault Prob (based on kurtosis and RMS)
        # Using a sensitive curve to ensure dynamic visual changes
        max_kurt = max(fv.vibration.kurtosis_x, fv.vibration.kurtosis_y)
        bearing_prob = min(0.95, max(0.02, (max_kurt / 4.0) + (fv.vibration.rms_overall / 15.0)))
        
        indicators.append(HealthIndicator(
            name="Bearing Health",
            probability=bearing_prob,
            status=MachineStatus.CRITICAL if bearing_prob > 0.6 else (MachineStatus.WARNING if bearing_prob > 0.3 else MachineStatus.HEALTHY)
        ))
        
        # Imbalance Prob (based on RMS)
        # Scales cleanly with overall vibration amplitude rather than strict FFT locks which fail under aliasing
        imbalance_prob = min(0.9, max(0.05, fv.vibration.rms_overall / 8.0))
        
        indicators.append(HealthIndicator(
            name="Imbalance",
            probability=imbalance_prob,
            status=MachineStatus.WARNING if imbalance_prob > 0.4 else MachineStatus.HEALTHY
        ))
        
        # Calculate overall status
        critical_alerts = [a for a in alerts if a.severity == Severity.CRITICAL]
        warning_alerts = [a for a in alerts if a.severity == Severity.WARNING]
        
        if critical_alerts:
            active_severity = MachineStatus.CRITICAL
            base_score = max(0, 100 - 40 - 10 * len(critical_alerts))
        elif warning_alerts:
            active_severity = MachineStatus.WARNING
            base_score = max(40, 100 - 15 * len(warning_alerts))
        else:
            base_score = 100 - (fv.vibration.rms_overall * 2) # Slight penalty for vibration even if not alert
            
        return MachineHealth(
            machine_id=fv.machine_id,
            overall_status=active_severity,
            health_score=max(0, min(100, base_score)),
            indicators=indicators
        )

    def _create_alert(self, category: str, message: str, severity: Severity, value: float, threshold: float) -> Alert:
        return Alert(
            timestamp=datetime.utcnow(),
            severity=severity,
            category=category,
            message=message,
            value=value,
            threshold=threshold
        )

# Singleton
rule_engine = RuleEngine()
