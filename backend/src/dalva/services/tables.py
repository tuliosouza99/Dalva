"""Plain functions for table database operations."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import func, text

from dalva.db.connection import get_engine, session_scope
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
    filters: Optional[list[dict[str, Any]]] = None,
) -> tuple[list[dict[str, Any]], int, list[dict[str, str]]]:
    """Get table data with pagination, sorting, and filtering.

    Args:
        table_db_id: Internal table ID
        version: Specific version to fetch (None for latest)
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

        ver_where, ver_params = _get_version_filter(table_db_id, version)

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


def _build_filter_sql(
    filters: list[dict[str, Any]], param_offset: int = 0
) -> tuple[str, dict[str, Any]]:
    """Build SQL WHERE clauses from filter definitions.

    Args:
        filters: List of filter dicts with column/op/value keys
        param_offset: Starting index for named parameters (avoids collisions)

    Returns:
        Tuple of (sql_fragment, params_dict)
    """
    clauses = []
    params: dict[str, Any] = {}
    for i, f in enumerate(filters):
        col = f["column"]
        op = f["op"]
        idx = param_offset + i
        if op == "between":
            if f.get("min") is not None and f.get("max") is not None:
                clauses.append(
                    f"CAST(json_extract(row_data, '$.\"{col}\"') AS DOUBLE) "
                    f"BETWEEN :fmin{idx} AND :fmax{idx}"
                )
                params[f"fmin{idx}"] = f["min"]
                params[f"fmax{idx}"] = f["max"]
            elif f.get("min") is not None:
                clauses.append(
                    f"CAST(json_extract(row_data, '$.\"{col}\"') AS DOUBLE) >= :fmin{idx}"
                )
                params[f"fmin{idx}"] = f["min"]
            elif f.get("max") is not None:
                clauses.append(
                    f"CAST(json_extract(row_data, '$.\"{col}\"') AS DOUBLE) <= :fmax{idx}"
                )
                params[f"fmax{idx}"] = f["max"]
            else:
                raise ValueError("Between filter requires at least min or max")
        elif op == "contains":
            clauses.append(
                f"contains(lower(json_extract_string(row_data, '$.\"{col}\"')), lower(:fval{idx}))"
            )
            params[f"fval{idx}"] = str(f["value"])
        elif op == "eq":
            clauses.append(f"json_extract(row_data, '$.\"{col}\"') = :fval{idx}")
            params[f"fval{idx}"] = f["value"]
        else:
            raise ValueError(f"Unsupported filter operator: {op}")

    where = " AND ".join(clauses)
    return where, params


def _get_version_filter(
    table_db_id: int, version: Optional[int] = None
) -> tuple[str, dict[str, Any]]:
    """Get version filter SQL for table rows.

    Returns:
        Tuple of (where_clause, params_dict)
    """
    if version is not None:
        return "table_id = :tid AND version = :ver", {
            "tid": table_db_id,
            "ver": version,
        }

    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT MAX(version) FROM dalva_table_rows WHERE table_id = :tid"),
            {"tid": table_db_id},
        ).fetchone()
    if result and result[0] is not None:
        return "table_id = :tid AND version = :ver", {
            "tid": table_db_id,
            "ver": result[0],
        }
    return "table_id = :tid AND version = -1", {"tid": table_db_id}


def get_table_stats(
    table_db_id: int,
    version: Optional[int] = None,
    filters: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Compute per-column statistics for a table using DuckDB SQL.

    Args:
        table_db_id: Internal table ID
        version: Specific version to analyze (None for latest)
        filters: Optional list of filter dicts to apply before computing stats

    Returns:
        Dict mapping column name -> stats dict
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
        if not column_schema:
            return {}

        ver_where, ver_params = _get_version_filter(table_db_id, version)

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
                if row and row[2] > 0:
                    min_val = float(row[0])
                    max_val = float(row[1])
                    non_null = int(row[2])
                    null_count = int(row[3])

                    num_bins = min(10, non_null)
                    bin_width = (
                        (max_val - min_val) / num_bins
                        if num_bins > 0 and max_val > min_val
                        else 1.0
                    )

                    if num_bins > 0 and max_val > min_val:
                        bin_params = {
                            **base_params,
                            "bmin": min_val,
                            "bwidth": bin_width,
                        }
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

                        bins = []
                        for bin_idx_raw, cnt in bin_rows:
                            bin_idx = int(bin_idx_raw) if bin_idx_raw is not None else 0
                            start = min_val + bin_idx * bin_width
                            end = start + bin_width
                            bins.append({"start": start, "end": end, "count": int(cnt)})
                    else:
                        bins = [{"start": min_val, "end": max_val, "count": non_null}]

                    stats[col_name] = {
                        "type": "numeric",
                        "min": min_val,
                        "max": max_val,
                        "bins": bins,
                        "null_count": null_count,
                    }
                else:
                    null_count = int(row[3]) if row else 0
                    stats[col_name] = {
                        "type": "numeric",
                        "min": None,
                        "max": None,
                        "bins": [],
                        "null_count": null_count,
                    }

            elif col_type == "bool":
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
                stats[col_name] = {
                    "type": "bool",
                    "counts": {
                        "true": int(row[0]) if row else 0,
                        "false": int(row[1]) if row else 0,
                    },
                    "null_count": int(row[2]) if row else 0,
                }

            elif col_type == "str":
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

                stats[col_name] = {
                    "type": "string",
                    "top_values": top_values,
                    "unique_count": distinct_count,
                    "null_count": int(unique_row[1]) if unique_row else 0,
                }

            else:
                sql_null = text(f"""
                    SELECT COUNT(*) FILTER (
                        json_extract(row_data, '$.\"{col_name}\"') IS NULL
                        OR json_type(row_data, '$.\"{col_name}\"') = 'NULL'
                    )
                    FROM dalva_table_rows
                    WHERE {ver_where}{filter_clause}
                """)
                null_count = conn.execute(sql_null, base_params).scalar()
                stats[col_name] = {
                    "type": col_type,
                    "null_count": int(null_count) if null_count else 0,
                }

        return stats
