"""Plain functions for table database operations."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from pydantic import BaseModel, create_model
from sqlalchemy import func, text

from dalva.db.connection import get_engine, next_id, session_scope
from dalva.db.schema import DalvaTable, DalvaTableRow, Project

_COLUMN_TYPES: dict[str, type] = {
    "int": int,
    "float": float,
    "bool": bool,
    "str": str,
    "list": list,
    "dict": dict,
}


def _build_row_model(
    column_schema: list[dict[str, str]],
) -> type[BaseModel]:
    """Build a Pydantic model from the column schema."""
    fields = {}
    for col in column_schema:
        python_type = _COLUMN_TYPES.get(col["type"], str)
        fields[col["name"]] = (Optional[python_type], None)
    return create_model("RowModel", **fields)


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
    column_schema: Optional[list[dict[str, str]]] = None,
    name: Optional[str] = None,
    config: Optional[dict] = None,
    run_id: Optional[int] = None,
    resume_from: Optional[str] = None,
) -> tuple[int, str, Optional[str]]:
    """Create or resume a table.

    Args:
        project_name: Project name
        column_schema: Column schema from DalvaSchema.to_column_schema()
        name: Optional table name (user-defined, for display only)
        config: Optional configuration dictionary
        run_id: Optional run ID to link this table to
        resume_from: table_id to resume (omit to create a new table)

    Returns:
        Tuple of (internal_db_id, table_id_string, descriptive_name)
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
            existing.updated_at = datetime.now(timezone.utc)
            db.flush()
            return existing.id, existing.table_id, existing.name

        abbrev = _generate_table_abbreviation(project_name)
        table_count = (
            db.query(DalvaTable).filter(DalvaTable.project_id == project_db_id).count()
        )
        table_id_str = f"{abbrev}-T{table_count + 1}"

        table = DalvaTable(
            id=next_id(db, "dalva_tables"),
            project_id=project_db_id,
            table_id=table_id_str,
            name=name,
            run_id=run_id,
            version=0,
            row_count=0,
            column_schema=json.dumps(column_schema) if column_schema else "[]",
            config=json.dumps(config) if config else None,
            state="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(table)
        db.flush()
        table_db_id = table.id

    return table_db_id, table_id_str, name


def add_table_rows(
    table_db_id: int,
    rows: list[dict[str, Any]],
    column_schema: list[dict[str, str]],
) -> tuple[int, int]:
    """Add rows to a table.

    Args:
        table_db_id: Internal table ID
        rows: List of row dictionaries
        column_schema: Column schema for validation

    Returns:
        Tuple of (new_version, rows_added)
    """
    if not rows:
        return 0, 0

    if not column_schema:
        raise ValueError("Cannot log rows to a table with no column schema")

    RowModel = _build_row_model(column_schema)
    validated_rows = []
    for i, row in enumerate(rows):
        try:
            validated_rows.append(RowModel(**row).model_dump())
        except Exception as e:
            raise ValueError(f"Row {i} validation failed: {e}")

    with session_scope() as db:
        table = db.query(DalvaTable).filter(DalvaTable.id == table_db_id).first()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        if table.state == "finished":
            raise ValueError(f"Table {table.table_id} is already finished")

        new_version = table.version + 1

        for row in validated_rows:
            db.add(
                DalvaTableRow(
                    id=next_id(db, "dalva_table_rows"),
                    table_id=table_db_id,
                    version=new_version,
                    row_data=json.dumps(row),
                )
            )

        table.version = new_version
        table.row_count = (table.row_count or 0) + len(rows)
        table.updated_at = datetime.now(timezone.utc)
        db.flush()

        return new_version, len(rows)


def remove_all_rows(table_db_id: int) -> None:
    """Remove all rows from a table, reset version and row_count.

    Args:
        table_db_id: Internal table ID
    """
    with session_scope() as db:
        table = db.query(DalvaTable).filter(DalvaTable.id == table_db_id).first()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        db.query(DalvaTableRow).filter(DalvaTableRow.table_id == table_db_id).delete()

        table.version = 0
        table.row_count = 0
        table.updated_at = datetime.now(timezone.utc)
        db.flush()


def get_table_data(
    table_db_id: int,
    version: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    filters: Optional[list[dict[str, Any]]] = None,
) -> tuple[list[dict[str, Any]], int, list[dict[str, str]]]:
    """Get table data with pagination, sorting, and filtering.

    Args:
        table_db_id: Internal table ID
        version: Specific version to fetch (None for all rows)
        limit: Maximum rows to return
        offset: Number of rows to skip
        sort_by: Column name to sort by
        sort_order: 'asc' or 'desc'
        filters: List of filter dicts with column/op/value keys

    Returns:
        Tuple of (rows, total_count, column_schema)
    """
    engine = get_engine()
    with engine.connect() as conn:
        table = conn.execute(
            text("SELECT column_schema FROM dalva_tables WHERE id = :tid"),
            {"tid": table_db_id},
        ).fetchone()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        column_schema = json.loads(table[0]) if table[0] else []

        if version is not None:
            ver_where = "table_id = :tid AND version = :ver"
            ver_params: dict[str, Any] = {"tid": table_db_id, "ver": version}
        else:
            ver_where = "table_id = :tid"
            ver_params = {"tid": table_db_id}

        filter_clause = ""
        filter_params: dict[str, Any] = {}
        if filters:
            where, params = _build_filter_sql(filters)
            filter_clause = f" AND {where}"
            filter_params = params

        base_params = {**ver_params, **filter_params}

        count_sql = text(
            f"SELECT COUNT(*) FROM dalva_table_rows WHERE {ver_where}{filter_clause}"
        )
        total = conn.execute(count_sql, base_params).scalar()

        order_clause = ""
        if sort_by:
            direction = "DESC" if sort_order == "desc" else "ASC"
            order_clause = (
                f" ORDER BY json_extract(row_data, '$.\"{sort_by}\"') {direction}"
            )

        data_sql = text(f"""
            SELECT row_data FROM dalva_table_rows
            WHERE {ver_where}{filter_clause}
            {order_clause}
            LIMIT :lim OFFSET :offs
        """)
        rows_raw = conn.execute(
            data_sql, {**base_params, "lim": limit, "offs": offset}
        ).fetchall()

        rows = [json.loads(r[0]) for r in rows_raw]

        return rows, total or 0, column_schema


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
    """Get all tables for a project."""
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
    """Get all tables linked to a run."""
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
    """Delete a table and all its rows."""
    with session_scope() as db:
        table = db.query(DalvaTable).filter(DalvaTable.id == table_db_id).first()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        db.delete(table)
        db.flush()


def _build_between_clause(
    col: str, idx: int, f: dict[str, Any]
) -> tuple[str, dict[str, Any]]:
    if f.get("min") is not None and f.get("max") is not None:
        return (
            f"CAST(json_extract(row_data, '$.\"{col}\"') AS DOUBLE) "
            f"BETWEEN :fmin{idx} AND :fmax{idx}",
            {f"fmin{idx}": f["min"], f"fmax{idx}": f["max"]},
        )
    if f.get("min") is not None:
        return (
            f"CAST(json_extract(row_data, '$.\"{col}\"') AS DOUBLE) >= :fmin{idx}",
            {f"fmin{idx}": f["min"]},
        )
    if f.get("max") is not None:
        return (
            f"CAST(json_extract(row_data, '$.\"{col}\"') AS DOUBLE) <= :fmax{idx}",
            {f"fmax{idx}": f["max"]},
        )
    raise ValueError("Between filter requires at least min or max")


_FILTER_CLAUSE_BUILDERS: dict[str, Callable] = {
    "between": lambda col, idx, f: _build_between_clause(col, idx, f),
    "contains": lambda col, idx, f: (
        f"contains(lower(json_extract_string(row_data, '$.\"{col}\"')), lower(:fval{idx}))",
        {f"fval{idx}": str(f["value"])},
    ),
    "eq": lambda col, idx, f: (
        f"json_extract(row_data, '$.\"{col}\"') = :fval{idx}",
        {f"fval{idx}": f["value"]},
    ),
}


def _build_filter_sql(
    filters: list[dict[str, Any]], param_offset: int = 0
) -> tuple[str, dict[str, Any]]:
    """Build SQL WHERE clauses from filter definitions."""
    clauses = []
    params: dict[str, Any] = {}
    for i, f in enumerate(filters):
        col = f["column"]
        op = f["op"]
        idx = param_offset + i
        builder = _FILTER_CLAUSE_BUILDERS.get(op)
        if not builder:
            raise ValueError(f"Unsupported filter operator: {op}")
        clause, clause_params = builder(col, idx, f)
        clauses.append(clause)
        params.update(clause_params)

    where = " AND ".join(clauses)
    return where, params


def _compute_numeric_stats(
    conn: Any,
    col_name: str,
    base_params: dict[str, Any],
    ver_where: str,
    filter_clause: str,
) -> dict[str, Any]:
    sql = text(f"""
        SELECT
            MIN(CAST(json_extract(row_data, '$.\"{col_name}\"') AS DOUBLE)),
            MAX(CAST(json_extract(row_data, '$.\"{col_name}\"') AS DOUBLE)),
            COUNT(*) FILTER (
                json_type(row_data, '$.\"{col_name}\"') IS NOT NULL
                AND json_type(row_data, '$.\"{col_name}\"') != 'NULL'
            ),
            COUNT(*) FILTER (
                json_extract(row_data, '$.\"{col_name}\"') IS NULL
                OR json_type(row_data, '$.\"{col_name}\"') = 'NULL'
            )
        FROM dalva_table_rows
        WHERE {ver_where}{filter_clause}
    """)
    row = conn.execute(sql, base_params).fetchone()
    if not row or row[2] == 0:
        return {
            "type": "numeric",
            "min": None,
            "max": None,
            "bins": [],
            "null_count": int(row[3]) if row else 0,
        }

    min_val = float(row[0])
    max_val = float(row[1])
    non_null = int(row[2])
    null_count = int(row[3])

    num_bins = min(10, non_null)
    bin_width = (
        (max_val - min_val) / num_bins if num_bins > 0 and max_val > min_val else 1.0
    )

    if num_bins > 0 and max_val > min_val:
        bin_params = {**base_params, "bmin": min_val, "bwidth": bin_width}
        bin_sql = text(f"""
            SELECT
                FLOOR((CAST(json_extract(row_data, '$.\"{col_name}\"') AS DOUBLE) - :bmin) / :bwidth) AS bin_idx,
                COUNT(*) AS cnt
            FROM dalva_table_rows
            WHERE {ver_where}{filter_clause}
              AND json_type(row_data, '$.\"{col_name}\"') IS NOT NULL
              AND json_type(row_data, '$.\"{col_name}\"') != 'NULL'
            GROUP BY bin_idx
            ORDER BY bin_idx
        """)
        bin_rows = conn.execute(bin_sql, bin_params).fetchall()
        bins = [
            {
                "start": min_val + (int(b[0]) if b[0] is not None else 0) * bin_width,
                "end": min_val
                + (int(b[0]) if b[0] is not None else 0) * bin_width
                + bin_width,
                "count": int(b[1]),
            }
            for b in bin_rows
        ]
    else:
        bins = [{"start": min_val, "end": max_val, "count": non_null}]

    return {
        "type": "numeric",
        "min": min_val,
        "max": max_val,
        "bins": bins,
        "null_count": null_count,
    }


def _compute_bool_stats(
    conn: Any,
    col_name: str,
    base_params: dict[str, Any],
    ver_where: str,
    filter_clause: str,
) -> dict[str, Any]:
    sql = text(f"""
        SELECT
            COUNT(*) FILTER (json_extract(row_data, '$.\"{col_name}\"') = true),
            COUNT(*) FILTER (json_extract(row_data, '$.\"{col_name}\"') = false),
            COUNT(*) FILTER (
                json_extract(row_data, '$.\"{col_name}\"') IS NULL
                OR json_type(row_data, '$.\"{col_name}\"') = 'NULL'
            )
        FROM dalva_table_rows
        WHERE {ver_where}{filter_clause}
    """)
    row = conn.execute(sql, base_params).fetchone()
    return {
        "type": "bool",
        "counts": {
            "true": int(row[0]) if row else 0,
            "false": int(row[1]) if row else 0,
        },
        "null_count": int(row[2]) if row else 0,
    }


def _compute_string_stats(
    conn: Any,
    col_name: str,
    base_params: dict[str, Any],
    ver_where: str,
    filter_clause: str,
) -> dict[str, Any]:
    sql_unique = text(f"""
        SELECT
            COUNT(DISTINCT json_extract_string(row_data, '$.\"{col_name}\"')),
            COUNT(*) FILTER (
                json_extract(row_data, '$.\"{col_name}\"') IS NULL
                OR json_type(row_data, '$.\"{col_name}\"') = 'NULL'
            ),
            COUNT(*) FILTER (
                json_extract(row_data, '$.\"{col_name}\"') IS NOT NULL
                AND json_type(row_data, '$.\"{col_name}\"') != 'NULL'
            )
        FROM dalva_table_rows
        WHERE {ver_where}{filter_clause}
    """)
    unique_row = conn.execute(sql_unique, base_params).fetchone()

    sql_top = text(f"""
        SELECT
            json_extract_string(row_data, '$.\"{col_name}\"') AS val,
            COUNT(*) AS cnt
        FROM dalva_table_rows
        WHERE {ver_where}{filter_clause}
          AND json_type(row_data, '$.\"{col_name}\"') IS NOT NULL
          AND json_type(row_data, '$.\"{col_name}\"') != 'NULL'
        GROUP BY val
        ORDER BY cnt DESC
        LIMIT 4
    """)
    top_rows = conn.execute(sql_top, base_params).fetchall()

    distinct_count = int(unique_row[0]) if unique_row else 0
    total_non_null = int(unique_row[2]) if unique_row else 0
    shown_count = sum(int(r[1]) for r in top_rows)
    other_count = total_non_null - shown_count

    top_values = [{"value": r[0], "count": int(r[1])} for r in top_rows]
    if other_count > 0:
        top_values.append({"value": "(other)", "count": other_count})

    return {
        "type": "string",
        "top_values": top_values,
        "unique_count": distinct_count,
        "null_count": int(unique_row[1]) if unique_row else 0,
    }


def _compute_default_stats(
    conn: Any,
    col_name: str,
    col_type: str,
    base_params: dict[str, Any],
    ver_where: str,
    filter_clause: str,
) -> dict[str, Any]:
    sql_null = text(f"""
        SELECT COUNT(*) FILTER (
            json_extract(row_data, '$.\"{col_name}\"') IS NULL
            OR json_type(row_data, '$.\"{col_name}\"') = 'NULL'
        )
        FROM dalva_table_rows
        WHERE {ver_where}{filter_clause}
    """)
    null_count = conn.execute(sql_null, base_params).scalar()
    return {"type": col_type, "null_count": int(null_count) if null_count else 0}


_STAT_HANDLERS: dict[str, Callable] = {
    "bool": _compute_bool_stats,
    "str": _compute_string_stats,
}


def get_table_stats(
    table_db_id: int,
    version: Optional[int] = None,
    filters: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Compute per-column statistics for a table using DuckDB SQL."""
    engine = get_engine()
    with engine.connect() as conn:
        table = conn.execute(
            text("SELECT column_schema FROM dalva_tables WHERE id = :tid"),
            {"tid": table_db_id},
        ).fetchone()
        if not table:
            raise ValueError(f"Table {table_db_id} not found")

        column_schema = json.loads(table[0]) if table[0] else []
        if not column_schema:
            return {}

        if version is not None:
            ver_where = "table_id = :tid AND version = :ver"
            ver_params: dict[str, Any] = {
                "tid": table_db_id,
                "ver": version,
            }
        else:
            ver_where = "table_id = :tid"
            ver_params = {"tid": table_db_id}

        filter_clause = ""
        filter_params: dict[str, Any] = {}
        if filters:
            where, params = _build_filter_sql(filters)
            filter_clause = f" AND {where}"
            filter_params = params

        base_params = {**ver_params, **filter_params}

        stats: dict[str, Any] = {}

        for col in column_schema:
            col_name = col["name"]
            col_type = col["type"]

            if col_type in ("int", "float"):
                stats[col_name] = _compute_numeric_stats(
                    conn, col_name, base_params, ver_where, filter_clause
                )
            elif col_type in _STAT_HANDLERS:
                stats[col_name] = _STAT_HANDLERS[col_type](
                    conn, col_name, base_params, ver_where, filter_clause
                )
            else:
                stats[col_name] = _compute_default_stats(
                    conn, col_name, col_type, base_params, ver_where, filter_clause
                )

        return stats
