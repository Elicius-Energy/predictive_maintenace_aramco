"""
Application configuration loaded from environment variables.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from .env file."""
    
    # MQTT Configuration
    MQTT_BROKER_HOST: str = "192.168.68.100"
    MQTT_BROKER_PORT: int = 1883
    MQTT_TOPIC_ENERGY: str = "energy/+"
    MQTT_TOPIC_ACCEL: str = "energy/+/accel"
    MQTT_CLIENT_ID: str = "predictive_maintenance_backend"
    MQTT_RECONNECT_DELAY: int = 5
    MQTT_MAX_RECONNECT_DELAY: int = 60
    
    # Database
    DATABASE_PATH: str = str(Path(__file__).parent.parent / "data" / "sensor_data.db")
    DATA_RETENTION_HOURS: int = 72
    
    # Simulation
    SIMULATION_MODE: str = "auto"  # "auto", "always", "never"
    SIMULATION_INTERVAL_MS: int = 1000
    
    # Anthropic API
    ANTHROPIC_API_KEY: Optional[str] = "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"
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"
    RAG_CACHE_TTL_SECONDS: int = 30
    RAG_AUTO_INTERVAL_SECONDS: int = 60
    ENABLE_AI_CONTINUOUS_DIAGNOSIS: bool = False
    
    # WebSocket
    WS_HEARTBEAT_INTERVAL: int = 30
    
    # Feature Engineering
    FFT_WINDOW_SIZE: int = 256
    ROLLING_WINDOW_SIZE: int = 60
    FEATURE_COMPUTE_INTERVAL_MS: int = 2000
    
    # Paths
    KNOWLEDGE_BASE_DIR: str = str(Path(__file__).parent.parent / "data" / "knowledge")
    FAISS_INDEX_PATH: str = str(Path(__file__).parent.parent / "data" / "faiss_index")
    SAMPLE_DATA_DIR: str = str(Path(__file__).parent.parent / "data" / "sample_data")
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
