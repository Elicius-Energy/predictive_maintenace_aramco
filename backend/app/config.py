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
    MQTT_TOPIC_LEDL: str = "ledl"
    MQTT_CLIENT_ID: str = "predictive_maintenance_backend"
    MQTT_RECONNECT_DELAY: int = 5
    MQTT_MAX_RECONNECT_DELAY: int = 60
    
    # Database
    DATABASE_PATH: str = str(Path(__file__).parent.parent / "data" / "sensor_data.db")
    DATA_RETENTION_HOURS: int = 72
    
    # Simulation
    SIMULATION_MODE: str = "auto"  # "auto", "always", "never"
    SIMULATION_INTERVAL_MS: int = 1000
    
    # OpenAI API
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
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
    CORS_ORIGINS: list[str] = ["*"]
    CORS_ORIGIN_REGEX: str = r".*"
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()

def get_runtime_settings() -> Settings:
    """Reload settings from `.env` for request-time consumers such as AI clients."""
    return Settings()
