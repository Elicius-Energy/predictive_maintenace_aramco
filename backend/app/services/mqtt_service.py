"""
MQTT Ingestion Service for LEDL Motor Energy Monitoring.
Subscribes to live MQTT broker topics (e.g. node.kaatru.org), parses real meter packets,
and seamlessly pipes them into the idempotent ingestion service and database.
"""
import json
import logging
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Optional
import paho.mqtt.client as mqtt

from app.config import settings
from app.db.base import SessionLocal
from app.services.ingest_service import ingest_service

logger = logging.getLogger(__name__)


class MQTTIngestionService:
    """
    Subscribes to live MQTT topics and feeds telemetry directly into the database.
    Runs paho-mqtt loop_forever with auto-reconnect in a background thread.
    """
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._reconnect_delay = 5
        self.last_message_ts: Optional[datetime] = None

    def start(self):
        """Start MQTT client connection in a background thread."""
        if not settings.MQTT_ENABLED:
            logger.info("MQTT Ingestion is disabled in configuration.")
            return

        self._running = True
        client_id = f"{settings.MQTT_CLIENT_ID}_{uuid.uuid4().hex[:6]}"

        try:
            if hasattr(mqtt, "CallbackAPIVersion"):
                self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
            else:
                self.client = mqtt.Client(client_id=client_id)
        except Exception:
            self.client = mqtt.Client(client_id=client_id)

        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        self._thread = threading.Thread(target=self._connection_loop, daemon=True)
        self._thread.start()
        logger.info("MQTT Ingestion background worker launched.")

    def stop(self):
        """Stop MQTT client."""
        self._running = False
        if self.client:
            try:
                self.client.disconnect()
            except Exception as e:
                logger.warning("Error stopping MQTT client: %s", e)
        logger.info("MQTT Ingestion service stopped.")

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback when MQTT connection is established."""
        is_success = (rc == 0) or (hasattr(rc, "value") and rc.value == 0) or (hasattr(rc, "is_failure") and not rc.is_failure)
        if is_success:
            self.connected = True
            self._reconnect_delay = 5
            logger.info(
                "Successfully connected to MQTT Broker at %s:%s",
                settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT
            )
            topics = [
                "ledl",
                "ledl2",
                "ledl/#",
                settings.MQTT_TOPIC,
            ]
            for t in set(topics):
                if t:
                    client.subscribe(t)
                    logger.info("MQTT subscribed to: %s", t)
        else:
            self.connected = False
            logger.error("MQTT connection failed with return code %s", rc)

    def _on_disconnect(self, client, userdata, *args, **kwargs):
        """Callback on disconnect."""
        self.connected = False
        logger.warning("MQTT broker connection disconnected. Will auto-reconnect.")

    def _on_message(self, client, userdata, msg):
        """Handle incoming telemetry message from MQTT broker."""
        try:
            payload_str = msg.payload.decode("utf-8", errors="replace")
            logger.info(">>> LIVE MQTT PACKET on [%s]: %s", msg.topic, payload_str[:160])
            self.last_message_ts = datetime.now(timezone.utc)
            payload = json.loads(payload_str)

            items = payload if isinstance(payload, list) else [payload]
            cleaned_items = []

            for item in items:
                if not isinstance(item, dict):
                    continue

                d_id = item.get("dID") or item.get("machine_id") or item.get("deviceId")
                if not d_id:
                    parts = msg.topic.split("/")
                    if len(parts) >= 2 and parts[1]:
                        d_id = parts[1]
                    else:
                        d_id = "002200203335471332323632"
                
                item["dID"] = str(d_id)

                if "dTS" not in item or item["dTS"] is None:
                    item["dTS"] = int(time.time())

                # Phase Voltages
                if "v_l1_n" in item and "v1n" not in item:
                    item["v1n"] = item["v_l1_n"]
                if "v_l2_n" in item and "v2n" not in item:
                    item["v2n"] = item["v_l2_n"]
                if "v_l3_n" in item and "v3n" not in item:
                    item["v3n"] = item["v_l3_n"]

                # Phase Currents
                if "i_l1" in item and "i1" not in item:
                    item["i1"] = item["i_l1"]
                if "i_l2" in item and "i2" not in item:
                    item["i2"] = item["i_l2"]
                if "i_l3" in item and "i3" not in item:
                    item["i3"] = item["i_l3"]

                # Phase Active Powers
                if "kw_l1" in item and "kw1" not in item:
                    item["kw1"] = item["kw_l1"]
                if "kw_l2" in item and "kw2" not in item:
                    item["kw2"] = item["kw_l2"]
                if "kw_l3" in item and "kw3" not in item:
                    item["kw3"] = item["kw_l3"]

                # Frequency
                if "hz" in item and "freq" not in item:
                    item["freq"] = item["hz"]

                # Power Factor
                if "t_pf" in item and "pf_avg" not in item:
                    item["pf_avg"] = item["t_pf"]

                cleaned_items.append(item)

            if cleaned_items:
                db = SessionLocal()
                try:
                    res = ingest_service.process_payload(cleaned_items, db)
                    logger.info("Ingested live MQTT packet: %s", res)
                except Exception as e:
                    logger.error("Error storing MQTT reading to DB: %s", e)
                finally:
                    db.close()

        except json.JSONDecodeError:
            logger.warning("Dropped non-JSON MQTT payload on topic %s", msg.topic)
        except Exception as e:
            logger.error("Error processing MQTT message: %s", e, exc_info=True)

    def _connection_loop(self):
        """Persistent connection loop using loop_forever."""
        while self._running:
            try:
                logger.info(
                    "Connecting to MQTT Broker at %s:%s...",
                    settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT
                )
                self.client.connect(
                    settings.MQTT_BROKER_HOST,
                    settings.MQTT_BROKER_PORT,
                    keepalive=60
                )
                self.client.loop_forever()
            except Exception as e:
                if not self._running:
                    break
                logger.warning("MQTT loop error: %s. Reconnecting in %ds...", e, self._reconnect_delay)
                time.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 60)


mqtt_ingestion_service = MQTTIngestionService()
