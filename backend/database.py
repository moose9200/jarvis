"""SQLAlchemy engine + session factory.

Production (and Docker dev): PostgreSQL with pgvector extension.
Tests / local-without-docker: SQLite fallback.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jarvis.db")

_connect_args = {}
_engine_kwargs = {}

if DATABASE_URL.startswith("sqlite"):
    _connect_args["check_same_thread"] = False
else:
    # Postgres: keep modest pool, fast recycle to avoid stale conns through proxies.
    _engine_kwargs["pool_size"] = 5
    _engine_kwargs["max_overflow"] = 10
    _engine_kwargs["pool_pre_ping"] = True
    _engine_kwargs["pool_recycle"] = 1800

engine = create_engine(DATABASE_URL, connect_args=_connect_args, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
