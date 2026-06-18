"""
Main FastAPI application entry point.
Ties together MQTT ingestion, simulation, processing pipeline, and API.
"""
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import db
from app.mqtt_client import mqtt_client

from app.websocket_manager import ws_manager
from app.models import WSMessage, SensorReading, DataSource, FeatureVector
from app.feature_engineering import feature_extractor
from app.rule_engine import rule_engine
from app.ml_engine import ml_engine
from app.rag.claude_client import ai_client
from app.rag.embeddings import embedding_manager

from app.routes import data, ws, rag

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ── Lifespan Management ──────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    logger.info("Initializing Saudi Aramco PdM System...")
    
    # 1. Initialize RAG Index
    embedding_manager.initialize()
    
    # 2. Start MQTT Client
    loop = asyncio.get_running_loop()
    await mqtt_client.start(loop)
    
    # 3. Setup Data Pipeline
    mqtt_client.set_data_callback(data_pipeline_handler)
    
    # 4. Start Background Tasks

    asyncio.create_task(cleanup_task())
    
    if settings.ENABLE_AI_CONTINUOUS_DIAGNOSIS:
        asyncio.create_task(ai_diagnosis_task())
    
    yield
    
    # Shutdown tasks
    await mqtt_client.stop()
    logger.info("System shutdown complete.")

# ── App Definition ────────────────────────────────────────────────────────

app = FastAPI(
    title="Elicius Predictive Maintenance - Saudi Aramco Demo",
    description="Real-time IoT PdM with RAG-based AI Insights",
    version="1.0.0",
    lifespan=lifespan
)

# CORS workaround
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=settings.CORS_ORIGIN_REGEX,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
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
                    
                    # 3. Call Claude
                    diagnosis = await ai_client.get_diagnosis(fv, alert_objs)
                    if diagnosis:
                        db.insert_diagnosis(diagnosis.model_dump())
                        await ws_manager.broadcast(WSMessage(type="ai_diagnosis", data=diagnosis.model_dump()))
            except Exception as e:
                logger.error(f"AI Task Error for {machine_id}: {e}")
            
        await asyncio.sleep(settings.RAG_AUTO_INTERVAL_SECONDS)

async def cleanup_task():
    """Periodic DB cleanup."""
    while True:
        db.cleanup_old_data()
        await asyncio.sleep(3600) # Every hour

# ── Root ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "online",
        "system": "Saudi Aramco Predictive Maintenance Dashboard",
        "backend": "FastAPI",
        "agent": "Antigravity AI",
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=False
    )
