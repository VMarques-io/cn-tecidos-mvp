#!/usr/bin/env python3
"""Create database tables directly (for local dev without Alembic).

This script creates all tables defined in the models using SQLAlchemy's
create_all method. Use this for local development when you don't need
the full Alembic migration workflow.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db.database import Base, get_engine
from models import User, Message, FashionFlowState


def create_tables() -> None:
    """Create all tables in the database."""
    engine = get_engine()

    if engine is None:
        print("Error: Could not create database engine. Check DATABASE_URL.")
        sys.exit(1)

    print("Creating tables...")
    Base.metadata.create_all(engine)
    print("Tables created successfully!")
    print("\nCreated tables:")
    for table in Base.metadata.tables:
        print(f"  - {table}")


if __name__ == "__main__":
    create_tables()
