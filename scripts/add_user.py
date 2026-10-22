#!/usr/bin/env python3
"""
CLI Utility to create new users for LEDL Motor Energy Monitoring.
Usage:
    python scripts/add_user.py <username> <password> [--role admin|operator]
"""
import sys
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.base import SessionLocal
from app.db.models import User
from app.core.security import hash_password


def add_user(username: str, password: str, role: str = "operator"):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            print(f"Error: User '{username}' already exists.")
            sys.exit(1)

        password_hash = hash_password(password)
        new_user = User(
            username=username,
            password_hash=password_hash,
            role=role
        )
        db.add(new_user)
        db.commit()
        print(f"Success: User '{username}' created with role '{role}'.")
    except Exception as e:
        db.rollback()
        print(f"Failed to create user: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a new user to LEDL Dashboard")
    parser.add_argument("username", help="User login username")
    parser.add_argument("password", help="User login password")
    parser.add_argument("--role", default="operator", choices=["admin", "operator"], help="User role")
    args = parser.parse_args()

    add_user(args.username, args.password, args.role)
