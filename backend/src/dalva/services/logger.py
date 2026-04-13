"""Plain functions for database operations.

Design principle — short-lived connections
------------------------------------------
DuckDB only allows **one writer per file** across OS processes.  If we hold a
session open for the entire training run (the old design), the FastAPI server
cannot connect while training is in progress and the UI goes dark.

Every function here opens a *fresh* session via ``session_scope()``,
performs its work, commits, and immediately closes the connection.  The
DuckDB write lock is therefore held for only a few milliseconds per call,
leaving the file free for the API server between log steps.
"""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Mapping, Optional, Union

from sqlalchemy.orm import Session

from dalva.db.connection import next_id, session_scope
from dalva.db.schema import Config, DalvaTable, DalvaTableRow, Metric, Project, Run
from dalva.types import InputValue


def _generate_abbreviation(project_name: str) -> str:
    """Generate a 3-letter uppercase abbreviation from project name."""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", project_name)
    words = re.split(r"[-_\s]+", clean)
    words = [w for w in words if w]

    if not words:
        return "RUN"

    if len(words) >= 3:
        abbrev = "".join(w[0] for w in words[:3])
    elif len(words) == 1:
        abbrev = words[0][:3]
    else:
        abbrev = words[0][0] + words[1][0] + (words[0][1] if len(words[0]) > 1 else "X")

    return abbrev.upper().ljust(3, "X")[:3]


# ------------------------------------------------------------------
# Run lifecycle
# ------------------------------------------------------------------


def create_run(
    project_name: str,
    run_name: Optional[str] = None,
    config: Optional[Mapping[str, InputValue]] = None,
    resume_from: Optional[str] = None,
) -> tuple[int, str, Optional[str]]:
    """Create or resume a run.

    When resuming, config keys that already exist for the run will cause a
    ``ValueError``.  Use ``remove_config()`` to delete conflicting keys first.

    Returns:
        Tuple of (internal_db_id, run_id_string, descriptive_name)
    """
    with session_scope() as db:
        project = db.query(Project).filter(Project.name == project_name).first()
        if not project:
            project_id_str = f"{project_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
            project = Project(
                id=next_id(db, "projects"), name=project_name, project_id=project_id_str
            )
            db.add(project)
            db.flush()

        project_db_id = project.id

        if resume_from:
            existing = (
                db.query(Run)
                .filter(Run.project_id == project_db_id, Run.run_id == resume_from)
                .first()
            )
            if existing:
                if config:
                    flat: dict[str, Any] = {}
                    _flatten_config(config, "", flat)
                    dup_keys = []
                    for key in flat:
                        if (
                            db.query(Config)
                            .filter(Config.run_id == existing.id, Config.key == key)
                            .first()
                        ):
                            dup_keys.append(key)
                    if dup_keys:
                        raise ValueError(
                            f"Config key(s) {dup_keys} already exist for run "
                            f"'{resume_from}'. Use remove_config() first to overwrite."
                        )
                    _log_config(existing.id, config, session=db)
                existing.state = "running"
                existing.updated_at = datetime.now(timezone.utc)
                existing.last_activity_at = datetime.now(timezone.utc)
                db.flush()
                return existing.id, existing.run_id, existing.name
            raise ValueError(
                f"Run '{resume_from}' not found in project '{project_name}'"
            )

        abbrev = _generate_abbreviation(project_name)
        run_count = db.query(Run).filter(Run.project_id == project_db_id).count()
        run_id_str = f"{abbrev}-{run_count + 1}"

        run = Run(
            id=next_id(db, "runs"),
            project_id=project_db_id,
            run_id=run_id_str,
            name=run_name,
            state="running",
            last_activity_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.flush()
        run_db_id = run.id

    if config:
        _log_config(run_db_id, config)

    return run_db_id, run_id_str, run_name


def fork_run(
    fork_from: str,
    project_name: str,
    name: Optional[str] = None,
    copy_tables_on_fork: Union[bool, list[int]] = False,
) -> tuple[int, str, Optional[str]]:
    """Fork an existing run to create a new one.

    Args:
        fork_from: run_id string of the source run (e.g. "ABC-1").
        project_name: Name of the project (will find or create).
        name: Optional name override. If None, uses "fork of {source_name}".
        copy_tables_on_fork: False (no tables), True (all tables), or list of table IDs.

    Returns:
        Tuple of (internal_db_id, run_id_string, descriptive_name)
    """
    with session_scope() as db:
        project = db.query(Project).filter(Project.name == project_name).first()
        if not project:
            project_id_str = f"{project_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
            project = Project(
                id=next_id(db, "projects"), name=project_name, project_id=project_id_str
            )
            db.add(project)
            db.flush()

        project_db_id = project.id

        source_run = (
            db.query(Run)
            .filter(Run.project_id == project_db_id, Run.run_id == fork_from)
            .first()
        )
        if not source_run:
            raise ValueError(f"Run '{fork_from}' not found in project '{project_name}'")

        abbrev = _generate_abbreviation(project_name)
        run_count = db.query(Run).filter(Run.project_id == project_db_id).count()
        run_id_str = f"{abbrev}-{run_count + 1}"

        new_name = name if name else f"fork of {source_run.name}"

        new_run = Run(
            id=next_id(db, "runs"),
            project_id=project_db_id,
            run_id=run_id_str,
            name=new_name,
            group_name=source_run.group_name,
            tags=source_run.tags,
            state="running",
            last_activity_at=datetime.now(timezone.utc),
            fork_from=source_run.id,
        )
        db.add(new_run)
        db.flush()
        new_run_db_id = new_run.id
        source_run_db_id = source_run.id

        source_configs = (
            db.query(Config).filter(Config.run_id == source_run_db_id).all()
        )
        for cfg in source_configs:
            db.add(
                Config(
                    id=next_id(db, "configs"),
                    run_id=new_run_db_id,
                    key=cfg.key,
                    value=cfg.value,
                )
            )

        source_metrics = (
            db.query(Metric).filter(Metric.run_id == source_run_db_id).all()
        )
        for metric in source_metrics:
            db.add(
                Metric(
                    id=next_id(db, "metrics"),
                    run_id=new_run_db_id,
                    attribute_path=metric.attribute_path,
                    attribute_type=metric.attribute_type,
                    step=metric.step,
                    timestamp=metric.timestamp,
                    float_value=metric.float_value,
                    int_value=metric.int_value,
                    string_value=metric.string_value,
                    bool_value=metric.bool_value,
                )
            )

        if copy_tables_on_fork:
            source_tables_query = db.query(DalvaTable).filter(
                DalvaTable.run_id == source_run_db_id
            )

            if isinstance(copy_tables_on_fork, list):
                source_tables_query = source_tables_query.filter(
                    DalvaTable.id.in_(copy_tables_on_fork)
                )

            source_tables = source_tables_query.all()

            for source_table in source_tables:
                new_table = DalvaTable(
                    id=next_id(db, "dalva_tables"),
                    project_id=project_db_id,
                    table_id=f"{source_table.table_id}_fork_{new_run_db_id}",
                    name=source_table.name,
                    run_id=new_run_db_id,
                    log_mode=source_table.log_mode,
                    version=0,
                    row_count=source_table.row_count,
                    column_schema=source_table.column_schema or "[]",
                    config=source_table.config,
                    state="active",
                )
                db.add(new_table)
                db.flush()

                source_rows = (
                    db.query(DalvaTableRow)
                    .filter(DalvaTableRow.table_id == source_table.id)
                    .all()
                )
                for row in source_rows:
                    db.add(
                        DalvaTableRow(
                            id=next_id(db, "dalva_table_rows"),
                            table_id=new_table.id,
                            version=0,
                            row_data=row.row_data,
                        )
                    )

    return new_run_db_id, run_id_str, new_name


def _log_config(
    run_id: int,
    config: Mapping[str, InputValue],
    prefix: str = "",
    session: Optional[Session] = None,
) -> None:
    """Recursively persist configuration key-value pairs.

    Raises if a config key already exists for the run (strict insert).
    Use remove_config() first to replace a config key.

    Args:
        run_id: Internal database ID of the run.
        config: Config dict to persist.
        prefix: Key prefix for nested dicts.
        session: Optional existing session to reuse (avoids opening a new
            one when called from create_run during resume).
    """
    flat: dict[str, Any] = {}
    _flatten_config(config, prefix, flat)

    def _do_log(db: Session) -> None:
        for key, value in flat.items():
            existing = (
                db.query(Config)
                .filter(Config.run_id == run_id, Config.key == key)
                .first()
            )
            if existing:
                raise ValueError(
                    f"Config key '{key}' already exists for this run. "
                    f"Use remove_config('{key}') first to overwrite."
                )
            db.add(
                Config(
                    id=next_id(db, "configs"),
                    run_id=run_id,
                    key=key,
                    value=json.dumps(value),
                )
            )

    if session is not None:
        _do_log(session)
    else:
        with session_scope() as db:
            _do_log(db)


def _flatten_config(d: Mapping[str, InputValue], prefix: str, out: dict) -> None:
    for key, value in d.items():
        full_key = f"{prefix}{key}" if prefix else key
        if isinstance(value, dict):
            _flatten_config(value, f"{full_key}/", out)
        else:
            out[full_key] = value
