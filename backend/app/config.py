"""
Configuration module for Elicius Energy IoT Monitoring Platform.
Loads configuration from environment variables with sensible defaults.
"""
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application & Environment
    PROJECT_NAME: str = "Elicius Energy IoT Monitoring"
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    DISPLAY_TIMEZONE: str = "Asia/Kolkata"
    
    # Server & Security
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "http://localhost", "http://localhost:8080"]
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Authentication (JWT & Argon2)
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 480
    COOKIE_NAME: str = "elicius_access_token"
    COOKIE_SECURE: Optional[bool] = None
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 300
    
    # Default Admin Seed
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = ""
    ADMIN_PASSWORD_HASH: Optional[str] = None
    
    # Device Ingest Authentication Key
    DEVICE_KEY: str = "elicius_secret_device_key_2026"
    
    # Database (PostgreSQL 16 + TimescaleDB + pgvector)
    # Default URL points to docker-compose timescale db service, or local postgres
    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@db:5432/elicius_energy"
    # Fallback to local sqlite if POSTGRES is unavailable for quick testing
    SQLITE_FALLBACK_URL: str = "sqlite:///./data/elicius_energy.db"
    RAW_DATA_RETENTION_MONTHS: int = 24
    
    # MQTT Ingestion (Live IoT Broker)
    MQTT_ENABLED: bool = True
    MQTT_BROKER_HOST: str = "node.kaatru.org"
    MQTT_BROKER_PORT: int = 1883
    MQTT_USERNAME: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_TOPIC: str = "ledl"  # Keep original MQTT topic to match the broker
    MQTT_CLIENT_ID: str = "elicius_energy_backend"
    MQTT_RECONNECT_DELAY: int = 5
    MQTT_MAX_RECONNECT_DELAY: int = 300
    MQTT_TOPIC_ENERGY: str = "ledl/energy"
    MQTT_TOPIC_ACCEL: str = "ledl/accel"
    MQTT_TOPIC_LEDL: str = "ledl"
    MAX_WS_CONNECTIONS: int = 100
    
    # AI & RAG Configuration (OpenAI)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBED_MODEL: str = "text-embedding-3-small"
    RAG_TOP_K: int = 4
    RAG_CHAT_RATE_LIMIT: str = "10/minute"
    
    # SMTP / Alerts (Optional)
    SMTP_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: str = "alerts@eliciusenergy.com"
    
    # Paths
    KB_DIR: str = str(Path(__file__).parent.parent.parent / "kb")
    REPORTS_DIR: str = str(Path(__file__).parent.parent / "data" / "reports")
    KNOWLEDGE_BASE_DIR: Optional[str] = None
    FAISS_INDEX_PATH: str = str(Path(__file__).parent.parent / "data" / "faiss_index")
    DATABASE_PATH: Optional[str] = None
    DATA_RETENTION_HOURS: int = 24 * 30
    FFT_WINDOW_SIZE: int = 1024
    
    class Config:
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()


def get_runtime_settings() -> Settings:
    """Reload environment configuration for callers that need current settings."""
    return Settings()
