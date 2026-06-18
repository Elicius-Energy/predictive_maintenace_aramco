"""
Anthropic Claude client for AI reasoning.
"""
import logging
import json
import asyncio
from typing import Optional
from anthropic import AsyncAnthropic

from app.config import settings, get_runtime_settings
from app.models import FeatureVector, FaultDiagnosis, Alert, Severity
from app.rag.retriever import retriever
from app.rag.prompt_builder import prompt_builder
from app.database import db

logger = logging.getLogger(__name__)

class ClaudeClient:
    """Client for Anthropic API integration."""
    
    def __init__(self):
        self.api_key = None
        self.model = settings.ANTHROPIC_MODEL
        self.client = None
        self._refresh_client()

    def _refresh_client(self):
        """Always prefer the latest `.env` values over import-time state."""
        runtime_settings = get_runtime_settings()
        self.api_key = runtime_settings.ANTHROPIC_API_KEY
        self.model = runtime_settings.ANTHROPIC_MODEL
        self.client = AsyncAnthropic(api_key=self.api_key) if self.api_key else None

    def _fallback_chat_response(self, reason: str) -> str:
        return (
            "AI analysis is temporarily unavailable from Anthropic, so I am falling back to a local summary. "
            f"Reason: {reason}. "
            f"Current model from `.env`: {self.model or 'not set'}. "
            "Please verify that the backend is running and that `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` are valid in `.env`."
        )
            
    async def get_diagnosis(self, fv: FeatureVector, recent_alerts: list[Alert]) -> Optional[FaultDiagnosis]:
        """Perform RAG and call Claude for diagnosis."""
        self._refresh_client()
        if not self.client:
            logger.warning("Anthropic API key not set. Skipping AI diagnosis.")
            return self._get_mock_diagnosis(fv)

        try:
            # 1. Retrieve Context
            # Focus query on the most anomalous features
            query = f"Vibration RMS {fv.vibration.rms_overall}, Kurtosis {fv.vibration.kurtosis_x}, Anomaly {fv.anomaly_score}"
            context = retriever.retrieve(query)
            
            # 2. Build Prompt
            prompt = prompt_builder.build_diagnosis_prompt(fv, context, recent_alerts)
            
            # 3. Call Claude
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # 4. Parse Response
            content = response.content[0].text
            # Attempt to find JSON in response (in case Claude adds text around it)
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
            logger.error(f"Error calling Anthropic API: {e}")
            return None

    async def chat(self, user_message: str, machine_id: str, history: list[dict]) -> str:
        """Call Claude for RAG-based chat interaction with cross-unit awareness."""
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
            
            # 3. Get cross-unit summary for ALL machines
            cross_unit_lines = []
            active_machines = db.get_active_machines(minutes=30)
            for mid in active_machines:
                reading = db.get_latest_reading(mid)
                alerts = db.get_alerts(mid, minutes=30, limit=5)
                if reading:
                    cross_unit_lines.append(
                        f"  - Device {mid} ({mid}): "
                        f"V={reading.get('voltage','?')}V, I={reading.get('current','?')}A, "
                        f"P={reading.get('active_power','?')}kW, PF={reading.get('power_factor','?')}, "
                        f"Temp={reading.get('temperature','?')}°C, "
                        f"Vib(ax={reading.get('ax','?')}, ay={reading.get('ay','?')}, az={reading.get('az','?')}), "
                        f"Recent alerts: {len(alerts)}"
                    )
                else:
                    cross_unit_lines.append(f"  - Device {mid} ({mid}): No data yet")
            
            cross_unit_summary = "\n".join(cross_unit_lines)
            
            # 4. Build the chat prompt
            system_prompt = f"""You are the Elicius AI Maintenance Copilot.
You are assisting an industrial engineer with predictive maintenance.
The currently selected asset is: Device {resolved_id} ({resolved_id}).
Use the real-time telemetry below AND the RAG knowledge base to answer accurately.
Focus on ROI, technical reliability, and specific maintenance recommendations.
When asked about comparisons across machines, use the FLEET OVERVIEW data.

CRITICAL FORMATTING INSTRUCTIONS:
1. NEVER use emojis, unicode symbols, or icons (e.g. ✅, ⚠️).
2. ONLY use standard markdown asterisks for formatting (e.g., **bold**).

SELECTED ASSET — REAL-TIME DATA:
  Latest Reading: {latest_reading}
  Latest Features: {latest_features[0] if latest_features else 'N/A'}
  Recent Alerts (30 min): {len(recent_alerts)} alert(s)

FLEET OVERVIEW (all monitored assets):
{cross_unit_summary}

KNOWLEDGE BASE CONTEXT:
{chr(10).join(context)}
"""
            
            messages = []
            for h in history[-5:]:
                role = "user" if h["role"] == "user" else "assistant"
                messages.append({"role": role, "content": h["content"]})
            
            messages.append({"role": "user", "content": user_message})
            
            # 5. Call Claude
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                system=system_prompt,
                messages=messages
            )
            
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Error in Claude chat: {e}", exc_info=True)
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
ai_client = ClaudeClient()
