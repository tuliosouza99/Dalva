"""Database connection and session management."""

import os
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from trackai.config import load_config


def get_db_url() -> str:
    """Get the database URL."""
    config = load_config()

    db_path = os.getenv("TRACKAI_DB_PATH") or config.database.db_path
    return f"duckdb:///{Path(db_path).expanduser()}"


def _create_duckdb_tables(engine) -> None:
    """Create DuckDB tables using raw SQL (DuckDB doesn't support SERIAL)."""
    with engine.connect() as conn:
        # Create sequence for projects table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS projects_id_seq START 1"))

        # Projects table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY DEFAULT nextval('projects_id_seq'),
                name VARCHAR UNIQUE NOT NULL,
                project_id VARCHAR UNIQUE NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """))

        # Create sequence for runs table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS runs_id_seq START 1"))

        # Runs table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS runs (
                id INTEGER PRIMARY KEY DEFAULT nextval('runs_id_seq'),
                project_id INTEGER NOT NULL,
                run_id VARCHAR NOT NULL,
                name VARCHAR,
                group_name VARCHAR,
                tags VARCHAR,
                state VARCHAR,
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(project_id, run_id)
            )
        """))

        # Create sequence for configs table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS configs_id_seq START 1"))

        # Configs table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY DEFAULT nextval('configs_id_seq'),
                run_id INTEGER NOT NULL,
                key VARCHAR NOT NULL,
                value VARCHAR,
                UNIQUE(run_id, key)
            )
        """))

        # Create sequence for metrics table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS metrics_id_seq START 1"))

        # Metrics table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY DEFAULT nextval('metrics_id_seq'),
                run_id INTEGER NOT NULL,
                attribute_path VARCHAR NOT NULL,
                attribute_type VARCHAR NOT NULL,
                step INTEGER,
                timestamp TIMESTAMP,
                float_value DOUBLE,
                int_value INTEGER,
                string_value VARCHAR,
                bool_value BOOLEAN
            )
        """))

        # Create sequence for files table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS files_id_seq START 1"))

        # Files table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY DEFAULT nextval('files_id_seq'),
                run_id INTEGER NOT NULL,
                file_type VARCHAR NOT NULL,
                file_path VARCHAR,
                file_hash VARCHAR,
                size INTEGER,
                file_metadata VARCHAR
            )
        """))

        # Create sequence for custom_views table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS custom_views_id_seq START 1"))

        # Custom views table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS custom_views (
                id INTEGER PRIMARY KEY DEFAULT nextval('custom_views_id_seq'),
                project_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                filters VARCHAR,
                columns VARCHAR,
                sort_by VARCHAR,
                created_at TIMESTAMP
            )
        """))

        # Create sequence for dashboards table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS dashboards_id_seq START 1"))

        # Dashboards table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dashboards (
                id INTEGER PRIMARY KEY DEFAULT nextval('dashboards_id_seq'),
                project_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                widgets VARCHAR,
                layout VARCHAR,
                created_at TIMESTAMP
            )
        """))

        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_runs_project_id ON runs(project_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_runs_group_name ON runs(group_name)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_runs_state ON runs(state)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_metrics_run_attr ON metrics(run_id, attribute_path)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_metrics_run_step ON metrics(run_id, step)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_metrics_attr_type ON metrics(attribute_type)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_files_run_type ON files(run_id, file_type)"))

        conn.commit()


def init_db(db_path: str | None = None) -> None:
    """
    Initialize the database by creating all tables.

    Args:
        db_path: Optional custom database path. If not provided, uses config.
    """
    if db_path:
        os.environ["TRACKAI_DB_PATH"] = db_path

    config = load_config()

    # Determine the directory to create
    if db_path:
        db_dir = Path(db_path).expanduser().parent
    else:
        db_dir = Path(config.database.db_path).expanduser().parent

    db_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(get_db_url(), echo=False)
    _create_duckdb_tables(engine)


def get_engine():
    """Get the SQLAlchemy engine.

    Uses NullPool so connections are never cached — every request gets a fresh
    DuckDB connection that sees all data committed by other processes (e.g. the
    Python SDK running in a training script).  Without NullPool, the default
    QueuePool keeps connections alive with a stale MVCC snapshot, hiding rows
    that were committed after the pool connection was first opened.
    """
    return create_engine(get_db_url(), echo=False, poolclass=NullPool)


# Lazy session factory (don't create engine at import time)
_SessionLocal = None



def _get_session_factory():
    """Get or create the session factory lazily."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database sessions.

    Usage:
        @app.get("/...")
        def endpoint(db: Session = Depends(get_db)):
            ...
    """
    SessionLocal = _get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """Get a standalone database session (for non-FastAPI usage)."""
    SessionLocal = _get_session_factory()
    return SessionLocal()
