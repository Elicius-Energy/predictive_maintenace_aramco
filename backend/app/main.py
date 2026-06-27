"""
Main FastAPI application entry point.
Ties together MQTT ingestion, simulation, processing pipeline, and API.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.extension import Limiter
from slowapi.util import get_remote_address

# Setup logging FIRST before importing anything that might create a logger
from app.logging_config import setup_logging
from app.config import settings
setup_logging(log_level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

from app.database import db
from app.mqtt_client import mqtt_client
from app.websocket_manager import ws_manager
from app.models import WSMessage, SensorReading, DataSource, FeatureVector
from app.feature_engineering import feature_extractor
from app.rule_engine import rule_engine
from app.ml_engine import ml_engine
from app.rag.openai_client import ai_client
from app.rag.embeddings import embedding_manager

from app.routes import data, ws, rag, auth
from app.middleware import RequestIDMiddleware, RequestLoggingMiddleware

limiter = Limiter(key_func=get_remote_address)

# Global background tasks store to prevent GC
_background_tasks = set()

# ── Lifespan Management ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing LEDL PdM System...")
    
    # 1. Initialize RAG Index in the background so it doesn't block MQTT startup
    task_rag = asyncio.create_task(asyncio.to_thread(embedding_manager.initialize))
    _background_tasks.add(task_rag)
    task_rag.add_done_callback(_background_tasks.discard)
    
    # 2. Start MQTT Client
    loop = asyncio.get_running_loop()
    await mqtt_client.start(loop)
    
    # 3. Setup Data Pipeline
    mqtt_client.set_data_callback(data_pipeline_handler)
    
    # 4. Start Background Tasks
    task_cleanup = asyncio.create_task(cleanup_task())
    _background_tasks.add(task_cleanup)
    task_cleanup.add_done_callback(_background_tasks.discard)
    
    if settings.ENABLE_AI_CONTINUOUS_DIAGNOSIS:
        task_ai = asyncio.create_task(ai_diagnosis_task())
        _background_tasks.add(task_ai)
        task_ai.add_done_callback(_background_tasks.discard)
    
    yield
    
    # Shutdown tasks
    logger.info("Initiating graceful shutdown...")
    await mqtt_client.stop()
    for task in _background_tasks:
        task.cancel()
    logger.info("System shutdown complete.")

# ── App Definition ────────────────────────────────────────────────────────

app = FastAPI(
    title="Elicius Predictive Maintenance - LEDL Demo",
    description="Real-time IoT PdM with RAG-based AI Insights",
    version="1.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(auth.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(ws.router)

# ── Data Processing Pipeline ──────────────────────────────────────────────

async def data_pipeline_handler(reading: SensorReading):
    """
    Main pipeline for every sensor reading (MQTT or Simulated).
    1. Store raw data
    2. Extract features
    3. Run rule engine (alerts)
    4. Run ML engine (anomaly)
    5. Broadcast to WebSockets
    """
    try:
        # 1. Store Raw
        reading_dict = reading.model_dump()
        # Flatten for DB
        db_ready = {
            "timestamp": reading.timestamp.isoformat(),
            "machine_id": reading.machine_id,
            "source": reading.source.value,
            "voltage": reading.energy.V if reading.energy else None,
            "current": reading.energy.I if reading.energy else None,
            "active_power": reading.energy.P if reading.energy else None,
            "apparent_power": reading.energy.KVA if reading.energy else None,
            "power_factor": reading.energy.pf if reading.energy else None,
            "energy": reading.energy.Energy if reading.energy else None,
            "frequency": reading.energy.Freq if reading.energy else None,
            "ax": reading.accel.ax if reading.accel else None,
            "ay": reading.accel.ay if reading.accel else None,
            "az": reading.accel.az if reading.accel else None,
            "gx": reading.accel.gx if reading.accel else None,
            "gy": reading.accel.gy if reading.accel else None,
            "gz": reading.accel.gz if reading.accel else None,
            "temperature": reading.temperature
        }
        db.insert_reading(db_ready)
        await ws_manager.broadcast(WSMessage(type="sensor_data", data=reading_dict))
        
        # 2. Extract Features
        fv = feature_extractor.extract_features(reading)
        if fv:
            # 3. ML Anomaly
            fv.anomaly_score = ml_engine.predict(fv)
            
            # 4. Rules & Alerts
            alerts = rule_engine.evaluate(fv)
            for alert in alerts:
                db.insert_alert(alert.model_dump())
                await ws_manager.broadcast(WSMessage(type="alert", data=alert.model_dump()))
                
            # Compute health
            health_summary = rule_engine.compute_health_summary(fv, alerts)
            fv.health_score = health_summary.health_score
            fv.iso_zone = rule_engine.get_iso_zone(fv.vibration.rms_overall)
            
            # Save Features
            db.insert_features(fv.machine_id, fv.model_dump(mode='json'))
            
            # 5. Broadcast Real-time
            await ws_manager.broadcast(WSMessage(type="features", data=fv.model_dump(mode='json')))
            await ws_manager.broadcast(WSMessage(type="machine_health", data=health_summary.model_dump(mode='json')))
            
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)

# ── Background Tasks ─────────────────────────────────────────────────────

async def ai_diagnosis_task():
    """Periodic AI reasoning task — cycles through all machines."""
    logger.info("AI Diagnosis background task started.")
    try:
        while True:
            active_machines = db.get_active_machines(minutes=10)
            for machine_id in active_machines:
                try:
                    # 1. Get latest features for this machine
                    feats = db.get_features(machine_id=machine_id, minutes=1)
                    if feats:
                        latest_f_dict = feats[0]["feature_data"]
                        from pydantic import TypeAdapter
                        fv = TypeAdapter(FeatureVector).validate_python(latest_f_dict)
                        
                        # 2. Get recent alerts
                        recent_alerts = db.get_alerts(machine_id=machine_id, minutes=10)
                        from app.models import Alert
                        alert_objs = [Alert(**a) for a in recent_alerts]
                        
                        # 3. Call OpenAI
                        diagnosis = await ai_client.get_diagnosis(fv, alert_objs)
                        if diagnosis:
                            db.insert_diagnosis(diagnosis.model_dump())
                            await ws_manager.broadcast(WSMessage(type="ai_diagnosis", data=diagnosis.model_dump()))
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"AI Task Error for {machine_id}: {e}")
                
            await asyncio.sleep(settings.RAG_AUTO_INTERVAL_SECONDS)
    except asyncio.CancelledError:
        logger.info("AI Diagnosis background task stopped.")

async def cleanup_task():
    """Periodic DB cleanup."""
    logger.info("Cleanup background task started.")
    try:
        while True:
            # We use run_in_executor in database.py eventually, but since it's SQLite we just call it
            db.cleanup_old_data()
            await asyncio.sleep(3600) # Every hour
    except asyncio.CancelledError:
        logger.info("Cleanup background task stopped.")

# ── Root ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "online",
        "system": "LEDL Predictive Maintenance Dashboard",
        "backend": "FastAPI",
        "agent": "Antigravity AI",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Docker and monitoring."""
    db_ok = db.health_check()
    return {
        "status": "healthy" if db_ok else "unhealthy",
        "uptime": "N/A", # Track start time to add uptime
        "version": "1.0.0",
        "mqtt_connected": mqtt_client.client.is_connected() if mqtt_client.client else False,
        "ws_clients": ws_manager.get_connection_count(),
        "db_ok": db_ok,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=False
    )
