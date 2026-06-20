"""
MQTT client for subscribing to ESP32 sensor data with auto-reconnect.
"""
import json
import asyncio
import logging
import time
import uuid
from typing import Callable, Optional
from datetime import datetime

import paho.mqtt.client as mqtt

from app.config import settings
from app.models import EnergyData, AccelData, SensorReading, DataSource, ThreePhaseEnergyData

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client with auto-reconnect and data parsing."""
    
    # Map device IDs to friendly names
    DEVICE_NAME_MAP: dict[str, str] = {
        "002200203335471332323632": "LEDL_Demo",
    }

    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self.last_energy_data: dict[str, EnergyData] = {}
        self.last_three_phase_data: dict[str, ThreePhaseEnergyData] = {}
        self.last_accel_data: dict[str, AccelData] = {}
        self.last_message_time: float = 0
        self._reconnect_delay = settings.MQTT_RECONNECT_DELAY
        self._on_data_callback: Optional[Callable] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def set_data_callback(self, callback: Callable):
        """Set callback for when new data arrives."""
        self._on_data_callback = callback
    
    def _on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker."""
        if rc == 0:
            logger.info(f"Connected to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            self.connected = True
            self._reconnect_delay = settings.MQTT_RECONNECT_DELAY
            # Subscribe to both topics
            client.subscribe(settings.MQTT_TOPIC_ENERGY)
            client.subscribe(settings.MQTT_TOPIC_ACCEL)
            client.subscribe(settings.MQTT_TOPIC_LEDL)
            logger.info(f"Subscribed to: {settings.MQTT_TOPIC_ENERGY}, {settings.MQTT_TOPIC_ACCEL}, {settings.MQTT_TOPIC_LEDL}")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
            self.connected = False
    
    def _on_disconnect(self, client, userdata, rc):
        """Called when disconnected from MQTT broker."""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (rc={rc}). Will auto-reconnect.")
    
    def _on_message(self, client, userdata, msg):
        """Called when a message is received."""
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.last_message_time = time.time()

            # ── Handle 3-phase LEDL topic ──────────────────────────────────
            if msg.topic == settings.MQTT_TOPIC_LEDL:
                self._handle_ledl_message(payload)
                return

            # ── Handle legacy energy / accel topics ────────────────────────
            machine_id = payload.get("dID")
            if not machine_id:
                parts = msg.topic.split("/")
                machine_id = parts[1] if len(parts) >= 2 else "Machine_10"
            
            is_accel = msg.topic.endswith("/accel")
            
            if not is_accel and msg.topic.startswith("energy/"):
                self.last_energy_data[machine_id] = EnergyData(**payload)
                logger.debug(f"[{machine_id}] Energy data: V={self.last_energy_data[machine_id].V}, I={self.last_energy_data[machine_id].I}")
                
            elif is_accel and msg.topic.startswith("energy/"):
                self.last_accel_data[machine_id] = AccelData(**payload)
                logger.debug(f"[{machine_id}] Accel data: ax={self.last_accel_data[machine_id].ax}, ay={self.last_accel_data[machine_id].ay}")
            
            # Build combined reading when we have at least one type of data
            if machine_id in self.last_energy_data or machine_id in self.last_accel_data:
                reading = SensorReading(
                    timestamp=datetime.utcnow(),
                    machine_id=machine_id,
                    source=DataSource.MQTT,
                    energy=self.last_energy_data.get(machine_id),
                    accel=self.last_accel_data.get(machine_id),
                    temperature=self.last_accel_data[machine_id].temp if machine_id in self.last_accel_data else None,
                )
                if self._on_data_callback and self._loop:
                    asyncio.run_coroutine_threadsafe(
                        self._on_data_callback(reading),
                        self._loop
                    )
                    
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON on topic {msg.topic}: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _handle_ledl_message(self, payload: dict):
        """Parse a 3-phase energy meter message from the 'ledl' topic."""
        try:
            three_phase = ThreePhaseEnergyData(**payload)
            raw_id = three_phase.dID
            machine_id = self.DEVICE_NAME_MAP.get(raw_id, raw_id)

            self.last_three_phase_data[machine_id] = three_phase
            logger.debug(
                f"[{machine_id}] 3-Phase: V1N={three_phase.v1n}, V2N={three_phase.v2n}, "
                f"V3N={three_phase.v3n}, I1={three_phase.i1}, freq={three_phase.freq}"
            )

            # Build backward-compatible EnergyData using averages/totals
            compat_energy = EnergyData(
                V=three_phase.vln_avg,
                I=three_phase.i_avg,
                P=three_phase.t_kw,
                KVA=three_phase.t_kva,
                pf=three_phase.pf_avg,
                Energy=three_phase.kwh_imp,
                Freq=three_phase.freq,
            )
            self.last_energy_data[machine_id] = compat_energy

            # Convert device epoch timestamp → datetime
            ts = datetime.utcfromtimestamp(three_phase.dTS) if three_phase.dTS > 0 else datetime.utcnow()

            reading = SensorReading(
                timestamp=ts,
                machine_id=machine_id,
                source=DataSource.MQTT,
                energy=compat_energy,
                accel=self.last_accel_data.get(machine_id),
                temperature=None,
            )
            # Attach the full 3-phase payload as an extra attribute for feature_engineering
            reading._three_phase = three_phase  # type: ignore[attr-defined]

            if self._on_data_callback and self._loop:
                asyncio.run_coroutine_threadsafe(
                    self._on_data_callback(reading),
                    self._loop
                )
        except Exception as e:
            logger.error(f"Error processing LEDL 3-phase message: {e}")
    
    async def start(self, loop: asyncio.AbstractEventLoop):
        """Start MQTT client in background."""
        self._loop = loop
        self._running = True
        
        client_id = f"{settings.MQTT_CLIENT_ID}_{uuid.uuid4().hex[:8]}"
        self.client = mqtt.Client(client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Try connecting in background thread
        asyncio.get_event_loop().run_in_executor(None, self._connect_loop)
    
    def _connect_loop(self):
        """Connection loop with exponential backoff (runs in thread)."""
        while self._running:
            if not self.connected:
                try:
                    logger.info(f"Attempting MQTT connection to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}...")
                    self.client.connect(
                        settings.MQTT_BROKER_HOST,
                        settings.MQTT_BROKER_PORT,
                        keepalive=60
                    )
                    self.client.loop_start()
                    # Wait a bit to see if connection succeeds
                    time.sleep(3)
                    if self.connected:
                        break  # Connected successfully, loop_start handles the rest
                except Exception as e:
                    logger.warning(f"MQTT connection failed: {e}. Retrying in {self._reconnect_delay}s...")
                    time.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(
                        self._reconnect_delay * 2,
                        settings.MQTT_MAX_RECONNECT_DELAY
                    )
            else:
                time.sleep(5)  # Check periodically
    
    async def stop(self):
        """Stop MQTT client."""
        self._running = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("MQTT client stopped")
    
    @property
    def is_stale(self) -> bool:
        """Check if data is stale (no message in last 5 seconds)."""
        if self.last_message_time == 0:
            return True
        return (time.time() - self.last_message_time) > 5


# Singleton
mqtt_client = MQTTClient()
