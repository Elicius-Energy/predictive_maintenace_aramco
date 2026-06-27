"""
Builds structured prompts for OpenAI API.
"""
from typing import List, Dict, Any
from app.models import FeatureVector, Alert

class PromptBuilder:
    """Constructs complex engineering prompts for the AI."""
    
    @staticmethod
    def build_diagnosis_prompt(fv: FeatureVector, context: List[str], recent_alerts: List[Alert]) -> str:
        """Create the final prompt with sensor data and RAG context."""
        
        v = fv.vibration
        e = fv.electrical
        
        alerts_str = "\n".join([f"- {a.severity.value.upper()}: {a.message}" for a in recent_alerts]) if recent_alerts else "None"
        context_str = "\n\n".join(context)
        
        prompt = f"""
Given the following real-time machine data for {fv.machine_id}:

* Vibration features:
  - RMS Overall: {v.rms_overall:.3f} mm/s
  - RMS (X/Y/Z): {v.rms_x:.3f}, {v.rms_y:.3f}, {v.rms_z:.3f}
  - Kurtosis (X/Y/Z): {v.kurtosis_x:.2f}, {v.kurtosis_y:.2f}, {v.kurtosis_z:.2f}
  - Peak-to-Peak: {v.peak_x:.3f}
  - Dominant Frequency: {v.dominant_freq:.1f} Hz
  - Anomaly Score: {fv.anomaly_score:.2f}
  - ISO Zone: {fv.iso_zone}

* Electrical features:
  - Voltage: {e.voltage:.1f} V
  - Current: {e.current:.1f} A
  - Active Power: {e.active_power:.2f} kW
  - Apparent Power: {e.apparent_power:.2f} kVA
  - Power Factor: {e.power_factor:.2f}
  - Efficiency: {e.efficiency:.1f} %
  - Load: {e.load_percentage:.1f} %

* Operational Metadata:
  - Temperature: {fv.temperature:.1f} °C
  - Recent Alerts:
{alerts_str}

And the following domain knowledge retrieved from technical manuals:
{context_str}

Determine:
1. Is there a fault?
2. What type of fault? (Bearing, Imbalance, Misalignment, Electrical, etc.)
3. Severity (low/medium/high)
4. Estimated cause based on physics (e.g. "High kurtosis suggests impacting in the bearing cage...")
5. Recommended action

Ensure the reasoning is grounded in first principles and signal characteristics. 
Return your response ONLY as a valid JSON object with the following fields:
{{
  "fault_type": string,
  "confidence": float (0-1),
  "severity": "info" | "warning" | "critical",
  "explanation": string,
  "physics_reasoning": string,
  "recommended_action": string
}}
"""
        return prompt

# Singleton
prompt_builder = PromptBuilder()
