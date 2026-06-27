"""
OpenAI client for AI reasoning.
"""
import logging
import json
import asyncio
from typing import Optional
from openai import AsyncOpenAI

from app.config import settings, get_runtime_settings
from app.models import FeatureVector, FaultDiagnosis, Alert, Severity
from app.rag.retriever import retriever
from app.rag.prompt_builder import prompt_builder
from app.database import db

logger = logging.getLogger(__name__)

class OpenAIClient:
    """Client for OpenAI API integration."""
    
    def __init__(self):
        self.api_key = None
        self.model = settings.OPENAI_MODEL
        self.client = None
        self._last_api_key = None
        self._refresh_client()

    def _refresh_client(self):
        """Always prefer the latest `.env` values over import-time state, cache the client."""
        runtime_settings = get_runtime_settings()
        
        if self.client and runtime_settings.OPENAI_API_KEY == self._last_api_key:
            # Settings haven't changed, keep using the same client
            return
            
        self.api_key = runtime_settings.OPENAI_API_KEY
        self._last_api_key = self.api_key
        self.model = runtime_settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key, timeout=30.0, max_retries=3) if self.api_key else None

    def _fallback_chat_response(self, reason: str) -> str:
        return (
            "AI analysis is temporarily unavailable from OpenAI, so I am falling back to a local summary. "
            f"Reason: {reason}. "
            f"Current model from `.env`: {self.model or 'not set'}. "
            "Please verify that the backend is running and that `OPENAI_API_KEY` and `OPENAI_MODEL` are valid in `.env`."
        )
            
    async def get_diagnosis(self, fv: FeatureVector, recent_alerts: list[Alert]) -> Optional[FaultDiagnosis]:
        """Perform RAG and call OpenAI for diagnosis."""
        self._refresh_client()
        if not self.client:
            logger.warning("OpenAI API key not set. Skipping AI diagnosis.")
            return self._get_mock_diagnosis(fv)

        try:
            # 1. Retrieve Context
            # Focus query on the most anomalous features
            query = f"Vibration RMS {fv.vibration.rms_overall}, Kurtosis {fv.vibration.kurtosis_x}, Anomaly {fv.anomaly_score}"
            context = retriever.retrieve(query)
            
            # 2. Build Prompt
            prompt = prompt_builder.build_diagnosis_prompt(fv, context, recent_alerts)
            
            # 3. Call OpenAI with exponential backoff handled by client max_retries
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Log token usage
            if hasattr(response, 'usage') and response.usage:
                logger.info(f"OpenAI usage (diagnosis): {response.usage.total_tokens} tokens")
            
            # 4. Parse Response
            content = response.choices[0].message.content
            # Attempt to find JSON in response (in case OpenAI adds text around it)
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                return FaultDiagnosis(
                    machine_id=fv.machine_id,
                    fault_type=result.get("fault_type", "unknown"),
                    confidence=result.get("confidence", 0.0),
                    severity=Severity(result.get("severity", "info")),
                    explanation=result.get("explanation", ""),
                    physics_reasoning=result.get("physics_reasoning", ""),
                    recommended_action=result.get("recommended_action", ""),
                    retrieved_context_summary=", ".join([c[:50] + "..." for c in context])
                )
            else:
                logger.error(f"Failed to parse AI response: {content}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return None

    async def chat(self, user_message: str, machine_id: str, history: list[dict]) -> str:
        """Call OpenAI for RAG-based chat interaction with cross-unit awareness."""
        self._refresh_client()
        if not self.client:
            return self._fallback_chat_response("missing API client")

        try:
            resolved_id = machine_id
            
            # 1. Retrieve Context from Knowledge Base
            context = retriever.retrieve(user_message)
            
            # 2. Get Real-time data for the ACTIVE machine
            latest_reading = db.get_latest_reading(resolved_id)
            latest_features = db.get_features(resolved_id, minutes=1)
            recent_alerts = db.get_alerts(resolved_id, minutes=30)
            
            # 2b. Get static motor configuration for the ACTIVE machine
            motor_config = db.get_motor_config(resolved_id)
            if motor_config:
                config_lines = "\n".join(f"  {k}: {v}" for k, v in motor_config.items() if v)
                motor_config_block = f"SELECTED ASSET — CONFIGURATION PROFILE:\n{config_lines}"
            else:
                motor_config_block = "SELECTED ASSET — CONFIGURATION PROFILE:\n  No configuration profile has been saved for this device yet."
            
            # 3. Get cross-unit summary for ALL machines
            cross_unit_lines = []
            active_machines = db.get_active_machines(minutes=30)
            for mid in active_machines:
                reading = db.get_latest_reading(mid)
                alerts = db.get_alerts(mid, minutes=30, limit=5)
                mid_config = db.get_motor_config(mid)
                config_label = mid_config.get('motorName', mid) if mid_config else mid
                if reading:
                    cross_unit_lines.append(
                        f"  - Device {mid} ({config_label}): "
                        f"V={reading.get('voltage','?')}V, I={reading.get('current','?')}A, "
                        f"P={reading.get('active_power','?')}kW, PF={reading.get('power_factor','?')}, "
                        f"Temp={reading.get('temperature','?')}°C, "
                        f"Vib(ax={reading.get('ax','?')}, ay={reading.get('ay','?')}, az={reading.get('az','?')}), "
                        f"Recent alerts: {len(alerts)}"
                    )
                else:
                    cross_unit_lines.append(f"  - Device {mid} ({config_label}): No data yet")
            
            cross_unit_summary = "\n".join(cross_unit_lines)
            
            # 4. Build the chat prompt
            system_prompt = f"""You are an Elicius AI Power Study Engineer — a senior-level expert with 20+ years of experience in industrial motor systems, power quality analysis, energy efficiency, and predictive maintenance.

You are embedded within the Elicius Predictive Maintenance platform, assisting plant engineers, maintenance teams, and energy managers. You have direct access to real-time telemetry, the device's saved configuration profile, and a technical knowledge base.

## YOUR IDENTITY & EXPERTISE

You are an expert in:
- **Motor Power Analysis**: Input/output power measurement, losses breakdown (copper, iron, stray, friction & windage), power factor correction, harmonic distortion effects.
- **Efficiency & Performance**: IE efficiency classes (IE1–IE4), part-load efficiency curves, PCHIP interpolation from manufacturer type-test data, motor derating factors (altitude, temperature, voltage unbalance).
- **Duty Cycle Analysis**: IEC 60034-1 duty types (S1 continuous, S2 short-time, S3–S8 intermittent/periodic), load profiling from power time-series data, thermal duty assessment, cycle counting.
- **Load & Drive Analysis**: Load torque characteristics (constant torque, variable torque, constant power), motor-load matching, VFD operation effects, slip calculations.
- **Vibration & Condition Monitoring**: ISO 10816 vibration severity, bearing fault frequencies (BPFO, BPFI, BSF, FTF), spectral envelope analysis, kurtosis-based early fault detection.
- **Energy Economics**: Annual energy consumption (AEC), cost-of-ownership (TCO), payback period for motor replacements or VFD retrofits, demand charges, power factor penalty calculations.
- **Predictive Maintenance**: Remaining useful life (RUL) estimation, failure mode identification (bearing, stator winding, rotor bar, misalignment, imbalance), maintenance scheduling optimization.
- **Standards & Regulations**: IEC 60034, IEEE 112, NEMA MG-1, IS 12615 (India), Saudi Aramco SAES/SABP standards.

## CURRENTLY SELECTED ASSET

Device ID: {resolved_id}

{motor_config_block}

## REAL-TIME TELEMETRY

Latest Sensor Reading:
{latest_reading}

Latest Computed Features:
{latest_features[0] if latest_features else 'No feature data available yet.'}

Recent Alerts (past 30 minutes): {len(recent_alerts)} alert(s)
{chr(10).join(f'  - [{a.get("severity","?")}] {a.get("message","")}' for a in recent_alerts[:5]) if recent_alerts else '  No recent alerts.'}

## FLEET OVERVIEW (all monitored assets)

{cross_unit_summary if cross_unit_summary else 'No active machines reporting data.'}

## TECHNICAL KNOWLEDGE BASE

{chr(10).join(context) if context else 'No relevant knowledge base documents found for this query.'}

## RESPONSE GUIDELINES

1. **Always ground your answers in the actual data above.** Never fabricate readings or configuration values. If data is missing, say so clearly and explain what data would be needed.
2. **Be specific and quantitative.** Use actual numbers from the telemetry and configuration. For example, instead of "the motor is running at high load", say "the motor is drawing 6.2 kW input power, which corresponds to approximately 82% load based on the 5.5 kW rated output."
3. **Show your reasoning.** When performing calculations (efficiency, load percentage, energy cost, payback period), show the key formula and intermediate steps so the engineer can verify.
4. **Proactively identify concerns.** If you notice anomalies in the data (voltage deviation >10%, low power factor, high vibration kurtosis, thermal rise), flag them even if the user didn't ask.
5. **Reference applicable standards** (IEC, IEEE, NEMA, ISO) when making recommendations about operating limits, vibration thresholds, or efficiency classifications.
6. **For duty cycle questions**: Analyze the power consumption pattern over time. If historical data is limited, explain what pattern to look for and recommend the most likely IEC duty type based on the connected load type and current operating behavior.
7. **For efficiency questions**: Use the manufacturer's calibration curve (6-point PCHIP interpolation: 23%, 48%, 73%, 98%, 114%, 123% load) when available. Explain where the current operating point falls on this curve.
8. **For ROI / payback questions**: Calculate annual energy consumption, compare with higher-efficiency alternatives, and provide simple payback period. Use the electricity cost from the configuration profile if available.
9. **When comparing machines**: Use the FLEET OVERVIEW data to provide cross-unit analysis, identifying which units are performing best/worst and why.

## FORMATTING RULES

- NEVER use emojis, unicode symbols, or decorative icons.
- Use standard markdown: **bold** for emphasis, bullet lists for structured data, code blocks for calculations.
- Keep responses concise but thorough. Aim for clarity over verbosity.
- Structure long answers with clear headers using markdown ### headings.
"""
            
            messages = []
            for h in history[-5:]:
                role = "user" if h["role"] == "user" else "assistant"
                messages.append({"role": role, "content": h["content"]})
            
            messages.append({"role": "user", "content": user_message})
            
            # 5. Call OpenAI with exponential backoff handled by client max_retries
            response = await self.client.chat.completions.create(
                model=self.model,
                temperature=0.7,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ]
            )
            
            # Log token usage
            if hasattr(response, 'usage') and response.usage:
                logger.info(f"OpenAI usage (chat): {response.usage.total_tokens} tokens")
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Error in OpenAI chat: {e}", exc_info=True)
            return self._fallback_chat_response(str(e))

    def _get_mock_diagnosis(self, fv: FeatureVector) -> FaultDiagnosis:
        """Fallback mock diagnosis for demo purposes without API key."""
        if fv.vibration.rms_overall > 5.0:
            return FaultDiagnosis(
                fault_type="Potential Bearing Fault",
                confidence=0.85,
                severity=Severity.WARNING,
                explanation="High vibration levels and abnormal kurtosis peaks detected in the axial direction.",
                physics_reasoning="Increased RMS vibration typically indicates energy dissipation from mechanical wear...",
                recommended_action="Inspect bearing housing for heat and check lubrication levels."
            )
        return FaultDiagnosis(
            fault_type="None",
            confidence=0.98,
            severity=Severity.INFO,
            explanation="Machine is operating within normal parameters.",
            physics_reasoning="Harmonic peaks are stable and within ISO 10816 limits.",
            recommended_action="Continue standard monitoring schedule."
        )

# Singleton
ai_client = OpenAIClient()
