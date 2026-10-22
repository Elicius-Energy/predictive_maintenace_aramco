"""
Main FastAPI Application Entry Point for Elicius Energy IoT Monitoring.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db.base import SessionLocal
from app.db.init_db import init_db
from app.services.fault_engine import fault_engine
from app.api.auth import router as auth_router
from app.api.ingest import router as ingest_router
from app.api.devices import router as devices_router
from app.api.reports import router as reports_router
from app.api.chat import router as chat_router
from app.api.users import router as users_router
from app.core.security import _jwt_secret

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def run_watchdog_job():
    """Periodic job running every 30 seconds to check communication timeouts."""
    db = SessionLocal()
    try:
        fault_engine.check_comm_watchdog(db, datetime.now(timezone.utc))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error("Watchdog job error: %s", str(e))
    finally:
        db.close()


from app.services.mqtt_service import mqtt_ingestion_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle manager."""
    logger.info("Starting %s...", settings.PROJECT_NAME)
    # Refuse to start with a missing or short signing key; never mint sessions with a placeholder.
    _jwt_secret()
    # 1. Initialize schema, hypertables, and seed data
    try:
        init_db()
    except Exception as e:
        logger.error("Database initialization failed: %s", str(e), exc_info=True)

    # 2. Start background watchdog job
    scheduler.add_job(run_watchdog_job, "interval", seconds=30, id="comm_watchdog", replace_existing=True)
    scheduler.start()
    logger.info("Watchdog scheduler started.")

    # 3. Start live MQTT Ingestion
    mqtt_ingestion_service.start()

    yield

    # Shutdown
    logger.info("Shutting down %s...", settings.PROJECT_NAME)
    scheduler.shutdown(wait=False)
    mqtt_ingestion_service.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="IoT Energy Monitoring Dashboard for Elicius Energy Private Limited",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(auth_router)
app.include_router(ingest_router)
app.include_router(devices_router)
app.include_router(reports_router)
app.include_router(chat_router)
app.include_router(users_router)


@app.get("/healthz")
@app.get("/api/health")
def healthcheck():
    """Service health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
