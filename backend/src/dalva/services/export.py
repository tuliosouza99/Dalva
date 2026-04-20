"""Export database to NDJSON format."""

import json
from datetime import datetime
from typing import IO, Optional

from sqlalchemy import text

from dalva.db.connection import get_engine

EXPORT_VERSION = 1


def _serialize(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def _write_record(output: IO[str], record: dict):
    cleaned = {k: v for k, v in record.items() if v is not None}
    output.write(json.dumps(cleaned, default=_serialize, ensure_ascii=False) + "\n")


def _build_in_clause(ids: list[int]) -> str:
    return ",".join(str(i) for i in ids)


def export_db(output: IO[str], project_name: Optional[str] = None) -> dict:
    engine = get_engine()
    counts = {
        "projects": 0,
        "runs": 0,
        "configs": 0,
        "metrics": 0,
        "tables": 0,
        "table_rows": 0,
    }

    with engine.connect() as conn:
        _write_record(
            output,
            {
                "type": "header",
                "version": EXPORT_VERSION,
                "exported_at": datetime.now().isoformat(),
            },
        )

        if project_name:
            projects = conn.execute(
                text(
                    "SELECT id, name, project_id, created_at FROM projects WHERE name = :name"
                ),
                {"name": project_name},
            ).fetchall()
        else:
            projects = conn.execute(
                text("SELECT id, name, project_id, created_at FROM projects")
            ).fetchall()

        if not projects:
            return counts

        project_db_ids = []
        for p in projects:
            project_db_ids.append(p.id)
            _write_record(
                output,
                {
                    "type": "project",
                    "project_id": p.project_id,
                    "name": p.name,
                    "created_at": p.created_at,
                },
            )
            counts["projects"] += 1

        proj_in = _build_in_clause(project_db_ids)

        runs = conn.execute(
            text(f"""
            SELECT r.id as db_id, r.run_id, r.name, r.group_name, r.tags, r.state,
                   r.created_at, p.name as project_name
            FROM runs r JOIN projects p ON r.project_id = p.id
            WHERE r.project_id IN ({proj_in})
            ORDER BY r.id
        """)
        ).fetchall()

        run_db_ids = []
        for r in runs:
            run_db_ids.append(r.db_id)
            record = {
                "type": "run",
                "project_name": r.project_name,
                "run_id": r.run_id,
                "state": r.state,
            }
            for key in ("name", "group_name", "tags", "created_at"):
                val = getattr(r, key)
                if val is not None:
                    record[key] = val
            _write_record(output, record)
            counts["runs"] += 1

        if not run_db_ids:
            run_in = "0"
        else:
            run_in = _build_in_clause(run_db_ids)

        configs = conn.execute(
            text(f"""
            SELECT r.run_id, p.name as project_name, c.key, c.value
            FROM configs c
            JOIN runs r ON c.run_id = r.id
            JOIN projects p ON r.project_id = p.id
            WHERE c.run_id IN ({run_in})
            ORDER BY c.id
        """)
        ).fetchall()

        for c in configs:
            _write_record(
                output,
                {
                    "type": "config",
                    "project_name": c.project_name,
                    "run_id": c.run_id,
                    "key": c.key,
                    "value": c.value,
                },
            )
            counts["configs"] += 1

        metrics_result = conn.execute(
            text(f"""
            SELECT r.run_id, p.name as project_name,
                   m.attribute_path, m.attribute_type, m.step, m.timestamp,
                   m.float_value, m.int_value, m.string_value, m.bool_value
            FROM metrics m
            JOIN runs r ON m.run_id = r.id
            JOIN projects p ON r.project_id = p.id
            WHERE m.run_id IN ({run_in})
            ORDER BY m.id
        """)
        )

        for row in metrics_result:
            record = {
                "type": "metric",
                "project_name": row.project_name,
                "run_id": row.run_id,
                "attribute_path": row.attribute_path,
                "attribute_type": row.attribute_type,
            }
            for key in (
                "step",
                "timestamp",
                "float_value",
                "int_value",
                "string_value",
                "bool_value",
            ):
                val = getattr(row, key)
                if val is not None:
                    record[key] = val
            _write_record(output, record)
            counts["metrics"] += 1

        tables_result = conn.execute(
            text(f"""
            SELECT t.id as db_id, t.table_id, t.name,
                   t.column_schema, t.config, t.state, t.created_at,
                   p.name as project_name,
                   r.run_id as table_run_id
            FROM dalva_tables t
            JOIN projects p ON t.project_id = p.id
            LEFT JOIN runs r ON t.run_id = r.id
            WHERE t.project_id IN ({proj_in})
            ORDER BY t.id
        """)
        ).fetchall()

        table_db_ids = []
        for t in tables_result:
            table_db_ids.append(t.db_id)
            record = {
                "type": "table",
                "project_name": t.project_name,
                "table_id": t.table_id,
            }
            for key in ("name", "column_schema", "config", "state", "created_at"):
                val = getattr(t, key)
                if val is not None:
                    record[key] = val
            if t.table_run_id is not None:
                record["run_id"] = t.table_run_id
            _write_record(output, record)
            counts["tables"] += 1

        if table_db_ids:
            table_in = _build_in_clause(table_db_ids)
            rows_result = conn.execute(
                text(f"""
                SELECT t.table_id, p.name as project_name, tr.version, tr.row_data
                FROM dalva_table_rows tr
                JOIN dalva_tables t ON tr.table_id = t.id
                JOIN projects p ON t.project_id = p.id
                WHERE tr.table_id IN ({table_in})
                ORDER BY tr.id
            """)
            )
            for row in rows_result:
                _write_record(
                    output,
                    {
                        "type": "table_row",
                        "project_name": row.project_name,
                        "table_id": row.table_id,
                        "version": row.version,
                        "row_data": row.row_data,
                    },
                )
                counts["table_rows"] += 1

        conn.commit()

    return counts
