#!/usr/bin/env python3
"""Create database tables directly (for local dev without Alembic)."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import Base, get_engine
from models import User, Message, FashionFlowState


def create_tables() -> None:
    engine = get_engine()
    if engine is None:
        print("Error: Could not create database engine. Check DATABASE_URL.")
        sys.exit(1)
    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully!")


if __name__ == "__main__":
    create_tables()
