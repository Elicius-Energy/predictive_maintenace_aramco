"""
FastAPI dependency for database sessions.
"""
from typing import Generator
from sqlalchemy.orm import Session
from app.db.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    """Provide a transactional database session scope."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
