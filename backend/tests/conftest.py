"""Pytest configuration and shared fixtures for Dalva backend tests."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest
from dalva.api.routes import metrics, projects, runs, tables
from dalva.db.schema import Metric, Run
from dalva.db.schema import DalvaTable as DalvaTableSchema
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# Set test environment before importing dalva modules
os.environ["DALVA_DB_PATH"] = ""


@pytest.fixture(scope="function")
def temp_db_path(tmp_path) -> str:
    """Create a temporary database path for each test."""
    db_file = tmp_path / "test_dalva.duckdb"
    return str(db_file)


@pytest.fixture(scope="function")
def temp_config_dir(tmp_path, monkeypatch) -> Path:
    """Create a temporary config directory and patch config paths."""
    config_dir = tmp_path / ".dalva"
    config_dir.mkdir(parents=True, exist_ok=True)

    # Patch environment and config paths
    monkeypatch.setenv("HOME", str(tmp_path))

    return config_dir


@pytest.fixture(scope="function")
def db_engine(temp_db_path) -> Engine:
    """Create a fresh SQLAlchemy engine for testing."""
    # Set the test database path
    os.environ["DALVA_DB_PATH"] = temp_db_path

    # Create engine with NullPool (same as production)
    engine = create_engine(
        f"duckdb:///{temp_db_path}",
        echo=False,
        poolclass=NullPool,
    )

    # Create all tables
    _create_tables(engine)

    yield engine

    # Cleanup
    engine.dispose()


def _create_tables(engine) -> None:
    """Create all DuckDB tables for testing."""
    with engine.connect() as conn:
        # Create sequences
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS projects_id_seq START 1"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS runs_id_seq START 1"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS configs_id_seq START 1"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS metrics_id_seq START 1"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS files_id_seq START 1"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS custom_views_id_seq START 1"))
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS dalva_tables_id_seq START 1"))
        conn.execute(
            text("CREATE SEQUENCE IF NOT EXISTS dalva_table_rows_id_seq START 1")
        )

        # Projects table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY DEFAULT nextval('projects_id_seq'),
                name VARCHAR UNIQUE NOT NULL,
                project_id VARCHAR UNIQUE NOT NULL,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)
        )

        # Runs table
        conn.execute(
            text("""
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
                last_activity_at TIMESTAMP,
                UNIQUE(project_id, run_id)
            )
        """)
        )

        # Configs table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS configs (
                id INTEGER PRIMARY KEY DEFAULT nextval('configs_id_seq'),
                run_id INTEGER NOT NULL,
                key VARCHAR NOT NULL,
                value VARCHAR,
                UNIQUE(run_id, key)
            )
        """)
        )

        # Metrics table (no inline UNIQUE — created via index below)
        conn.execute(
            text("""
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
        """)
        )

        # UNIQUE index using COALESCE so NULL steps are treated as a sentinel
        # value and duplicate scalar metrics are prevented at the DB level.
        conn.execute(
            text(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS uq_run_metric_attr_step
                ON metrics (run_id, attribute_path, COALESCE(step, -999999999))
            """
            )
        )

        # Files table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY DEFAULT nextval('files_id_seq'),
                run_id INTEGER NOT NULL,
                file_type VARCHAR NOT NULL,
                file_path VARCHAR,
                file_hash VARCHAR,
                size INTEGER,
                file_metadata VARCHAR
            )
        """)
        )

        # Custom views table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS custom_views (
                id INTEGER PRIMARY KEY DEFAULT nextval('custom_views_id_seq'),
                project_id INTEGER NOT NULL,
                name VARCHAR NOT NULL,
                filters VARCHAR,
                columns VARCHAR,
                sort_by VARCHAR,
                created_at TIMESTAMP
            )
        """)
        )

        # Dalva tables table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS dalva_tables (
                id INTEGER PRIMARY KEY DEFAULT nextval('dalva_tables_id_seq'),
                project_id INTEGER NOT NULL,
                table_id VARCHAR NOT NULL,
                name VARCHAR,
                run_id INTEGER,
                log_mode VARCHAR DEFAULT 'IMMUTABLE',
                version INTEGER DEFAULT 0,
                row_count INTEGER DEFAULT 0,
                column_schema VARCHAR,
                config VARCHAR,
                state VARCHAR DEFAULT 'active',
                created_at TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(project_id, table_id)
            )
        """)
        )

        # Dalva table rows table
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS dalva_table_rows (
                id INTEGER PRIMARY KEY DEFAULT nextval('dalva_table_rows_id_seq'),
                table_id INTEGER NOT NULL,
                version INTEGER DEFAULT 0,
                row_data VARCHAR
            )
        """)
        )

        # Indexes
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_runs_project_id ON runs(project_id)")
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_runs_group_name ON runs(group_name)")
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_runs_state ON runs(state)"))
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_metrics_run_attr ON metrics(run_id, attribute_path)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_metrics_run_step ON metrics(run_id, step)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_metrics_attr_type ON metrics(attribute_type)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_tables_project ON dalva_tables(project_id)"
            )
        )
        conn.execute(
            text("CREATE INDEX IF NOT EXISTS idx_tables_run ON dalva_tables(run_id)")
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_tables_table_id_version ON dalva_tables(table_id, version)"
            )
        )
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS idx_table_rows_table_version ON dalva_table_rows(table_id, version)"
            )
        )

        conn.commit()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a database session for testing."""
    SessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def api_client(db_engine, monkeypatch) -> TestClient:
    """Create a test client with mocked dependencies."""
    # Set test database path
    os.environ["DALVA_DB_PATH"] = db_engine.url.database

    # Create a minimal FastAPI app for testing
    app = FastAPI(title="Dalva Test")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
    app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
    app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
    app.include_router(tables.router, prefix="/api/tables", tags=["tables"])

    def get_test_engine():
        return db_engine

    monkeypatch.setattr("dalva.api.routes.projects.get_db", get_test_engine)
    monkeypatch.setattr("dalva.api.routes.runs.get_db", get_test_engine)
    monkeypatch.setattr("dalva.api.routes.metrics.get_db", get_test_engine)
    monkeypatch.setattr("dalva.api.routes.tables.get_db", get_test_engine)

    @app.get("/api/health")
    async def health():
        return {"status": "healthy"}

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
def sample_project(db_session) -> dict:
    """Create a sample project in the database."""
    from dalva.db.schema import Project

    project = Project(
        name="test-project",
        project_id="test-project_abc123",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    return {"id": project.id, "name": project.name, "project_id": project.project_id}


@pytest.fixture(scope="function")
def sample_run(db_session, sample_project) -> dict:
    """Create a sample run in the database."""
    run = Run(
        project_id=sample_project["id"],
        run_id="TST-1",
        name="Test Run",
        state="running",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    return {
        "id": run.id,
        "project_id": run.project_id,
        "run_id": run.run_id,
        "name": run.name,
        "state": run.state,
    }


@pytest.fixture(scope="function")
def sample_metrics(db_session, sample_run) -> list:
    """Create sample metrics in the database."""
    metrics = [
        Metric(
            run_id=sample_run["id"],
            attribute_path="loss",
            attribute_type="float",
            step=0,
            timestamp=datetime.now(timezone.utc),
            float_value=0.5,
        ),
        Metric(
            run_id=sample_run["id"],
            attribute_path="accuracy",
            attribute_type="float",
            step=0,
            timestamp=datetime.now(timezone.utc),
            float_value=0.95,
        ),
        Metric(
            run_id=sample_run["id"],
            attribute_path="loss",
            attribute_type="float",
            step=1,
            timestamp=datetime.now(timezone.utc),
            float_value=0.3,
        ),
        Metric(
            run_id=sample_run["id"],
            attribute_path="accuracy",
            attribute_type="float",
            step=1,
            timestamp=datetime.now(timezone.utc),
            float_value=0.98,
        ),
    ]

    for m in metrics:
        db_session.add(m)
    db_session.commit()

    return [
        {
            "attribute_path": m.attribute_path,
            "step": m.step,
            "float_value": m.float_value,
        }
        for m in metrics
    ]


@pytest.fixture(scope="function")
def sample_table(db_session, sample_project) -> dict:
    """Create a sample table in the database."""
    table = DalvaTableSchema(
        project_id=sample_project["id"],
        table_id="TST-T1",
        name="Test Table",
        log_mode="IMMUTABLE",
        version=0,
        row_count=0,
        column_schema="[]",
        state="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(table)
    db_session.commit()
    db_session.refresh(table)

    return {
        "id": table.id,
        "project_id": table.project_id,
        "table_id": table.table_id,
        "name": table.name,
        "log_mode": table.log_mode,
        "version": table.version,
        "row_count": table.row_count,
        "state": table.state,
    }
