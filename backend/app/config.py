"""
Application configuration loaded from environment variables.
"""
import os
import secrets
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, Literal


class Settings(BaseSettings):
    """Application settings loaded from .env file."""
    
    # MQTT Configuration
    MQTT_BROKER_HOST: str = "192.168.68.100"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_TOPIC_ENERGY: str = "energy/+"
    MQTT_TOPIC_ACCEL: str = "energy/+/accel"
    MQTT_TOPIC_LEDL: str = "ledl"
    MQTT_CLIENT_ID: str = "predictive_maintenance_backend"
    MQTT_RECONNECT_DELAY: int = 5
    MQTT_MAX_RECONNECT_DELAY: int = 60
    
    # Database
    DATABASE_PATH: str = str(Path(__file__).parent.parent / "data" / "sensor_data.db")
    DATA_RETENTION_HOURS: int = 72
    
    # Simulation
    SIMULATION_MODE: Literal["auto", "always", "never"] = "auto"
    SIMULATION_INTERVAL_MS: int = 1000
    
    # OpenAI API
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    RAG_CACHE_TTL_SECONDS: int = 30
    RAG_AUTO_INTERVAL_SECONDS: int = 60
    ENABLE_AI_CONTINUOUS_DIAGNOSIS: bool = False
    RAG_CHAT_RATE_LIMIT: str = "10/minute"
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    MAX_WS_CONNECTIONS: int = 100
    
    # Feature Engineering
    FFT_WINDOW_SIZE: int = 256
    ROLLING_WINDOW_SIZE: int = 60
    FEATURE_COMPUTE_INTERVAL_MS: int = 2000
    
    # Paths
    KNOWLEDGE_BASE_DIR: str = str(Path(__file__).parent.parent / "data" / "knowledge")
    FAISS_INDEX_PATH: str = str(Path(__file__).parent.parent / "data" / "faiss_index")
    SAMPLE_DATA_DIR: str = str(Path(__file__).parent.parent / "data" / "sample_data")
    
    # Server & Security
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    ALLOWED_HOSTS: list[str] = ["*"]
    LOG_LEVEL: str = "INFO"
    
    # Auth (JWT)
    # Generate random secret key by default, but it will change every restart! Must set in .env
    JWT_SECRET_KEY: str = secrets.token_hex(32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480
    
    # Admin Account
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = "" # Leave empty for dev mode bypass
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

@lru_cache()
def _get_cached_settings() -> Settings:
    return Settings()

def get_runtime_settings() -> Settings:
    """Reload settings from `.env` for request-time consumers such as AI clients."""
    # Cache clearing isn't perfect TTL, but it ensures we don't recreate on every request
    # while allowing environment variable updates if we flush the cache
    return _get_cached_settings()
