"""Plain functions for table database operations."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func

from dalva.db.connection import session_scope
from dalva.db.schema import DalvaTable, DalvaTableRow, Project


def _generate_table_abbreviation(project_name: str) -> str:
    """Generate a 3-letter uppercase abbreviation from project name."""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", project_name)
    words = re.split(r"[-_\s]+", clean)
    words = [w for w in words if w]

    if not words:
        return "TBL"
    if len(words) >= 3:
        abbrev = "".join(w[0] for w in words[:3])
    elif len(words) == 1:
        abbrev = words[0][:3]
    else:
        abbrev = words[0][0] + words[1][0] + (words[0][1] if len(words[0]) > 1 else "X")
    return abbrev.upper().ljust(3, "X")[:3]


def create_table(
    project_name: str,
    name: Optional[str] = None,
    config: Optional[dict] = None,
    run_id: Optional[int] = None,
    log_mode: str = "IMMUTABLE",
    resume_from: Optional[str] = None,
) -> tuple[int, str, Optional[str], str]:
    """Create or resume a table.

    Args:
        project_name: Project name
        name: Optional table name (user-defined, for display only)
        config: Optional configuration dictionary
        run_id: Optional run ID to link this table to
        log_mode: IMMUTABLE, MUTABLE, or INCREMENTAL
        resume_from: table_id to resume (omit to create a new table)

    Returns:
        Tuple of (internal_db_id, table_id_string, descriptive_name, log_mode)
    """
    with session_scope() as db:
        project = db.query(Project).filter(Project.name == project_name).first()
        if not project:
            project_id_str = f"{project_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
            project = Project(name=project_name, project_id=project_id_str)
            db.add(project)
            db.flush()

        project_db_id = project.id

        if resume_from:
            existing = (
                db.query(DalvaTable)
                .filter(
                    DalvaTable.project_id == project_db_id,
                    DalvaTable.table_id == resume_from,
                )
                .first()
            )
            if not existing:
                raise ValueError(
                    f"Table '{resume_from}' not found in project '{project_name}'"
                )
            if existing.log_mode not in ("MUTABLE", "INCREMENTAL"):
                raise ValueError(
                    f"Table '{resume_from}' is not resumable (log_mode={existing.log_mode})"
                )
            existing.updated_at = datetime.now(timezone.utc)
            db.flush()
            return existing.id, existing.table_id, existing.name, existing.log_mode

        abbrev = _generate_table_abbreviation(project_name)
        table_count = (
            db.query(DalvaTable).filter(DalvaTable.project_id == project_db_id).count()
        )
        table_id_str = f"{abbrev}-T{table_count + 1}"

        table = DalvaTable(
            project_id=project_db_id,
            table_id=table_id_str,
            name=name,
            run_id=run_id,
            log_mode=log_mode,
            version=0,
            row_count=0,
            column_schema="[]",
            config=json.dumps(config) if config else None,
            state="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(table)
        db.flush()
        table_db_id = table.id

    return table_db_id, table_id_str, name, log_mode


def add_table_rows(
    table_db_id: int,
    rows: list[dict[str, Any]],
    column_schema: list[dict[str, str]],
    log_mode: str,
    current_version: Optional[int] = None,
) -> tuple[int, int]:
    """Add rows to a table.

    Args:
        table_db_id: Internal table ID
        rows: List of row dictionaries
        column_schema: Column schema from validated DataFrame
        log_mode: IMMUTABLE, MUTABLE, or INCREMENTAL
        current_version: Hint for expected version; actual version is read inside session

    Returns:
        Tuple of (new_version, rows_added)
    """
    if not rows:
        return current_version or 0, 0

    with session_scope() as db:
        table = db.query(DalvaTable).filter(DalvaTable.id == table_db_id).first()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        if table.state == "finished":
            raise ValueError(f"Table {table.table_id} is already finished")

        actual_version = table.version

        if log_mode == "IMMUTABLE" and actual_version > 0:
            raise ValueError(
                f"Table {table.table_id} is IMMUTABLE and already has data"
            )

        if log_mode == "INCREMENTAL":
            existing_schema = (
                json.loads(table.column_schema) if table.column_schema else []
            )
            if existing_schema:
                if len(existing_schema) != len(column_schema):
                    raise ValueError(
                        f"Column count mismatch: expected {len(existing_schema)}, got {len(column_schema)}"
                    )
                for i, col in enumerate(existing_schema):
                    if col != column_schema[i]:
                        raise ValueError(
                            f"Column type mismatch at index {i}: expected {col}, got {column_schema[i]}"
                        )

        new_version = actual_version + 1

        for row in rows:
            db.add(
                DalvaTableRow(
                    table_id=table_db_id,
                    version=new_version,
                    row_data=json.dumps(row),
                )
            )

        table.version = new_version
        if log_mode == "MUTABLE":
            table.row_count = len(rows)
            table.column_schema = json.dumps(column_schema)
        else:
            table.row_count = (table.row_count or 0) + len(rows)
            if not table.column_schema or table.column_schema == "[]":
                table.column_schema = json.dumps(column_schema)
        table.updated_at = datetime.now(timezone.utc)
        db.flush()

        return new_version, len(rows)


def get_table_data(
    table_db_id: int,
    version: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    filters: Optional[dict[str, Any]] = None,
) -> tuple[list[dict[str, Any]], int, list[dict[str, str]]]:
    """Get table data with pagination, sorting, and filtering.

    Args:
        table_db_id: Internal table ID
        version: Specific version to fetch (None for latest)
        limit: Maximum rows to return
        offset: Number of rows to skip
        sort_by: Column name to sort by
        sort_order: 'asc' or 'desc'
        filters: Dictionary of column -> filter value

    Returns:
        Tuple of (rows, total_count, column_schema)
    """
    with session_scope() as db:
        table = db.query(DalvaTable).filter(DalvaTable.id == table_db_id).first()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        column_schema = json.loads(table.column_schema) if table.column_schema else []
        query = db.query(DalvaTableRow).filter(DalvaTableRow.table_id == table_db_id)

        if version is not None:
            query = query.filter(DalvaTableRow.version == version)
        else:
            max_version = (
                db.query(DalvaTableRow.version)
                .filter(DalvaTableRow.table_id == table_db_id)
                .order_by(DalvaTableRow.version.desc())
                .first()
            )
            if max_version:
                query = query.filter(DalvaTableRow.version == max_version[0])

        rows_raw = query.all()

        rows = []
        for row in rows_raw:
            row_dict = json.loads(row.row_data)
            if filters:
                match = True
                for col, val in filters.items():
                    if col in row_dict and row_dict[col] != val:
                        match = False
                        break
                if match:
                    rows.append(row_dict)
            else:
                rows.append(row_dict)

        if sort_by:
            rows.sort(
                key=lambda r: (r.get(sort_by) is None, r.get(sort_by, "")),
                reverse=(sort_order == "desc"),
            )

        total = len(rows)
        paginated = rows[offset : offset + limit]

        return paginated, total, column_schema


def finish_table(table_db_id: int) -> str:
    """Mark a table as finished.

    Args:
        table_db_id: Internal table ID

    Returns:
        Final table state
    """
    with session_scope() as db:
        table = db.query(DalvaTable).filter(DalvaTable.id == table_db_id).first()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        table.state = "finished"
        table.updated_at = datetime.now(timezone.utc)
        db.flush()

    return "finished"


def get_tables_for_project(
    project_db_id: int,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[DalvaTable], int]:
    """Get all tables for a project.

    Args:
        project_db_id: Project internal ID
        limit: Maximum tables to return
        offset: Number of tables to skip

    Returns:
        Tuple of (tables, total_count)
    """
    with session_scope() as db:
        query = db.query(DalvaTable).filter(DalvaTable.project_id == project_db_id)
        total = query.count()
        tables = (
            query.order_by(DalvaTable.created_at.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )
        for t in tables:
            actual = (
                db.query(func.count(DalvaTableRow.id))
                .filter(DalvaTableRow.table_id == t.id)
                .scalar()
            )
            t.row_count = actual or 0
            db.expunge(t)
        return list(tables), total


def get_tables_for_run(run_db_id: int) -> list[DalvaTable]:
    """Get all tables linked to a run.

    Args:
        run_db_id: Run internal ID

    Returns:
        List of linked tables
    """
    with session_scope() as db:
        tables = db.query(DalvaTable).filter(DalvaTable.run_id == run_db_id).all()
        for t in tables:
            actual = (
                db.query(func.count(DalvaTableRow.id))
                .filter(DalvaTableRow.table_id == t.id)
                .scalar()
            )
            t.row_count = actual or 0
            db.expunge(t)
        return list(tables)


def delete_table(table_db_id: int) -> None:
    """Delete a table and all its rows.

    Args:
        table_db_id: Internal table ID
    """
    with session_scope() as db:
        table = db.query(DalvaTable).filter(DalvaTable.id == table_db_id).first()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        db.delete(table)
        db.flush()
