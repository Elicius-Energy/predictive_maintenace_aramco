"""
SQLAlchemy database engine, session factory, and base model class.
Supports PostgreSQL with TimescaleDB and pgvector, with graceful SQLite fallback for testing.
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool
from app.config import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

def get_engine():
    """Create and return the database engine."""
    # Attempt Postgres connection first
    db_url = settings.DATABASE_URL
    try:
        if db_url.startswith("postgresql"):
            engine = create_engine(
                db_url,
                pool_size=20,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            # Test connection
            with engine.connect() as conn:
                logger.info("Connected successfully to PostgreSQL/TimescaleDB at %s", db_url.split("@")[-1])
            return engine
    except Exception as e:
        logger.warning(
            "Could not connect to PostgreSQL (%s). Falling back to SQLite for local development/testing.",
            str(e)
        )
    
    # Fallback SQLite
    fallback_url = settings.SQLITE_FALLBACK_URL
    if fallback_url.startswith("sqlite:///./"):
        import os
        from pathlib import Path
        db_path = Path(fallback_url.replace("sqlite:///", ""))
        os.makedirs(db_path.parent, exist_ok=True)
        
    engine = create_engine(
        fallback_url,
        connect_args={"check_same_thread": False} if "sqlite" in fallback_url else {},
        poolclass=StaticPool if ":memory:" in fallback_url else None
    )
    return engine

engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
