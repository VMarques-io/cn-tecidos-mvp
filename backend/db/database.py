"""Database connection and session management."""

from __future__ import annotations

import os
import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool, StaticPool

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_database_url() -> str:
    """Get database URL from environment variable."""
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/cn_tecidos"
    )


def create_db_engine(fail_silently: bool = False) -> Engine | None:
    database_url = get_database_url()

    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False} if ":///:memory:" in database_url or "mode=memory" in database_url else {},
            poolclass=StaticPool if ":memory:" in database_url or "mode=memory" in database_url else QueuePool,
            echo=False,
        )
    else:
        engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
        )

    if fail_silently:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully")
        except Exception as e:
            logger.warning(f"Database connection unavailable: {e!s}. Engine created but not verified.")
            return engine
    else:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Database connection established successfully")

    return engine


def create_all_tables():
    """Create all tables defined in models."""
    from models import User, Message, FashionFlowState
    engine = get_engine()
    if engine is not None:
        Base.metadata.create_all(bind=engine)


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_db_engine(fail_silently=True)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    factory = get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
