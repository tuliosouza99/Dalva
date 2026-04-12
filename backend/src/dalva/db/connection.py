"""Database connection and session management."""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from dalva.config import load_config


def get_db_url() -> str:
    """Get the database URL."""
    config = load_config()

    db_path = os.getenv("DALVA_DB_PATH") or config.database.db_path
    return f"duckdb:///{Path(db_path).expanduser()}"


def _create_duckdb_tables(engine) -> None:
    """Create DuckDB tables using raw SQL (DuckDB doesn't support SERIAL)."""
    with engine.connect() as conn:
        # Create sequence for projects table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS projects_id_seq START 1"))

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

        # Create sequence for runs table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS runs_id_seq START 1"))

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
                UNIQUE(project_id, run_id)
            )
        """)
        )

        # Add last_activity_at column if it doesn't exist (migration for existing databases)
        try:
            conn.execute(text("ALTER TABLE runs ADD COLUMN last_activity_at TIMESTAMP"))
        except Exception:
            pass  # Column already exists

        # Migration: deduplicate metrics before adding unique index.
        # DuckDB treats NULLs as equal in UNIQUE indexes with COALESCE, so we
        # use COALESCE(step, -999999999) as a sentinel for NULL steps.
        # We deduplicate by keeping the row with the highest id per group.
        try:
            conn.execute(
                text("""
                DELETE FROM metrics WHERE id NOT IN (
                    SELECT MAX(id) FROM metrics
                    GROUP BY run_id, attribute_path,
                        COALESCE(step, -999999999)
                )
            """)
            )
            conn.commit()
        except Exception:
            conn.rollback()
            pass  # Table may not exist yet or already deduplicated

        # Replace column-level UNIQUE constraint with expression-based index
        # that treats NULL steps as a sentinel value, so duplicate scalar metrics
        # (step=NULL) are actually prevented at the DB level.
        try:
            conn.execute(
                text("ALTER TABLE metrics DROP CONSTRAINT uq_run_metric_attr_step")
            )
        except Exception:
            pass  # Constraint may not exist

        try:
            conn.execute(text("DROP INDEX IF EXISTS uq_run_metric_attr_step"))
        except Exception:
            pass

        try:
            conn.execute(
                text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uq_run_metric_attr_step
                ON metrics (run_id, attribute_path, COALESCE(step, -999999999))
            """)
            )
        except Exception:
            pass

        # Create sequence for configs table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS configs_id_seq START 1"))

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

        # Create sequence for metrics table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS metrics_id_seq START 1"))

        # Metrics table
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

        # Create sequence for files table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS files_id_seq START 1"))

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

        # Create sequence for custom_views table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS custom_views_id_seq START 1"))

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

        # Create sequence for dalva_tables table ID
        conn.execute(text("CREATE SEQUENCE IF NOT EXISTS dalva_tables_id_seq START 1"))

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

        # Create sequence for dalva_table_rows table ID
        conn.execute(
            text("CREATE SEQUENCE IF NOT EXISTS dalva_table_rows_id_seq START 1")
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

        # Create indexes
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
                "CREATE INDEX IF NOT EXISTS idx_runs_last_activity ON runs(last_activity_at)"
            )
        )
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
                "CREATE INDEX IF NOT EXISTS idx_files_run_type ON files(run_id, file_type)"
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

        _sync_sequences(conn)

        conn.commit()


_SEQUENCE_MAP = {
    "projects": "projects_id_seq",
    "runs": "runs_id_seq",
    "metrics": "metrics_id_seq",
    "configs": "configs_id_seq",
    "files": "files_id_seq",
    "custom_views": "custom_views_id_seq",
    "dalva_tables": "dalva_tables_id_seq",
    "dalva_table_rows": "dalva_table_rows_id_seq",
}


def _sync_sequences(conn) -> None:
    """Set each sequence to MAX(id)+1 so inserts never collide with existing rows.

    DuckDB lacks setval() and ALTER SEQUENCE RESTART, so we drop and
    recreate each sequence with the correct start value.  Sequences that
    already return the right value are left untouched.
    """
    for table, seq in _SEQUENCE_MAP.items():
        max_id = conn.execute(
            text(f"SELECT COALESCE(MAX(id), 0) FROM {table}")
        ).scalar()
        desired = max_id + 1
        cur = conn.execute(text(f"SELECT nextval('{seq}')")).scalar()
        conn.rollback()
        if cur >= desired:
            continue
        conn.execute(text(f"DROP SEQUENCE IF EXISTS {seq}"))
        conn.execute(text(f"CREATE SEQUENCE {seq} START {desired}"))


def init_db(db_path: str | None = None) -> None:
    """
    Initialize the database by creating all tables.

    Args:
        db_path: Optional custom database path. If not provided, uses config.
    """
    if db_path:
        os.environ["DALVA_DB_PATH"] = db_path

    config = load_config()

    # Determine the directory to create
    if db_path:
        db_dir = Path(db_path).expanduser().parent
    else:
        db_dir = Path(config.database.db_path).expanduser().parent

    db_dir.mkdir(parents=True, exist_ok=True)

    engine = create_engine(get_db_url(), echo=False, poolclass=NullPool)
    _create_duckdb_tables(engine)


def get_engine():
    """Return a fresh SQLAlchemy engine with NullPool.

    NullPool is essential for DuckDB:
    - DuckDB only allows **one writer** at a time across processes.
    - With the default QueuePool the connection (and its write lock) is kept
      alive between requests / log calls, blocking every other process.
    - NullPool closes the underlying DuckDB connection immediately after each
      session is released, so the write lock is held only for the duration of
      a single commit — a fraction of a second.
    """
    return create_engine(get_db_url(), echo=False, poolclass=NullPool)


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Context manager that opens a fresh session, commits on success,
    rolls back on error, and *always* closes the connection before returning.

    This is the only correct way to interact with DuckDB from the SDK: the
    write lock is acquired, the operation is committed, and the lock is
    released — all within the ``with`` block.  The UI (FastAPI) can then
    connect freely between SDK log calls.

    Usage::

        with session_scope() as db:
            db.add(some_object)
        # connection is already closed here
    """
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a short-lived database session.

    Route handlers are responsible for calling ``db.commit()`` themselves.
    On exception the session is rolled back; on normal return it is simply
    closed (with NullPool the underlying DuckDB connection is discarded
    immediately, releasing the write lock).

    We intentionally do *not* wrap ``session_scope()`` here because route
    handlers already call ``db.commit()``.  A second commit from
    ``session_scope.__exit__`` would start a new empty transaction on the
    same connection, which can cause stale-snapshot issues in DuckDB
    (subsequent connections may not see the committed changes).
    """
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def next_id(session: Session, table_name: str) -> int:
    """Return the next primary-key value for *table_name* by calling its sequence.

    DuckDB tables in Dalva use ``DEFAULT nextval('<table>_id_seq')`` but that
    column default can be lost after a backup/restore.  Calling the sequence
    explicitly and setting ``obj.id = next_id(...)`` before ``db.add()`` avoids
    the ``FlushError: NULL identity key`` that results.
    """
    return session.execute(text(f"SELECT nextval('{table_name}_id_seq')")).scalar()


def get_session() -> Session:
    """Return a standalone session for one-off usage outside FastAPI.

    The caller is responsible for calling ``session.commit()`` and
    ``session.close()``.  Prefer ``session_scope()`` when possible.
    """
    engine = get_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
