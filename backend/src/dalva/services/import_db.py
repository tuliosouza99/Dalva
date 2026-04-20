"""Import NDJSON data into database."""

import json
from datetime import datetime
from typing import IO

from sqlalchemy import text

from dalva.db.connection import _sync_sequences, get_engine

BATCH_SIZE = 1000


def _parse_datetime(val):
    if val is None:
        return None
    return datetime.fromisoformat(val)


def _flush_metrics(conn, buffer, run_map, counts):
    if not buffer:
        return

    params_list = []
    for record in buffer:
        run_key = (record["project_name"], record["run_id"])
        run_db_id = run_map.get(run_key)
        if run_db_id is None:
            continue
        params_list.append(
            {
                "run_id": run_db_id,
                "path": record["attribute_path"],
                "type": record["attribute_type"],
                "step": record.get("step"),
                "ts": _parse_datetime(record.get("timestamp")),
                "fv": record.get("float_value"),
                "iv": record.get("int_value"),
                "sv": record.get("string_value"),
                "bv": record.get("bool_value"),
            }
        )

    if params_list:
        conn.execute(
            text("""
            INSERT INTO metrics (id, run_id, attribute_path, attribute_type,
                                 step, timestamp, float_value, int_value,
                                 string_value, bool_value)
            VALUES (nextval('metrics_id_seq'), :run_id, :path, :type, :step, :ts,
                    :fv, :iv, :sv, :bv)
            ON CONFLICT DO NOTHING
        """),
            params_list,
        )
        counts["metrics_imported"] += len(params_list)

    buffer.clear()


def _flush_table_rows(conn, buffer, table_map, counts):
    if not buffer:
        return

    params_list = []
    for record in buffer:
        table_key = (record["project_name"], record["table_id"])
        table_db_id = table_map.get(table_key)
        if table_db_id is None:
            continue
        params_list.append(
            {
                "table_id": table_db_id,
                "version": record.get("version", 0),
                "row_data": record.get("row_data"),
            }
        )

    if params_list:
        conn.execute(
            text("""
            INSERT INTO dalva_table_rows (id, table_id, version, row_data)
            VALUES (nextval('dalva_table_rows_id_seq'), :table_id, :version, :row_data)
        """),
            params_list,
        )
        counts["table_rows_imported"] += len(params_list)

    buffer.clear()


def _handle_project(conn, record, project_map, counts, fail_on_conflict):
    name = record["name"]
    if name in project_map:
        return

    existing = conn.execute(
        text("SELECT id FROM projects WHERE name = :name"),
        {"name": name},
    ).fetchone()

    if existing:
        if fail_on_conflict:
            raise ValueError(f"Project already exists: {name}")
        project_map[name] = existing.id
        counts["projects_skipped"] += 1
    else:
        pid = conn.execute(text("SELECT nextval('projects_id_seq')")).scalar()
        conn.execute(
            text("""
            INSERT INTO projects (id, name, project_id, created_at)
            VALUES (:id, :name, :project_id, :created_at)
        """),
            {
                "id": pid,
                "name": name,
                "project_id": record["project_id"],
                "created_at": _parse_datetime(record.get("created_at")),
            },
        )
        project_map[name] = pid
        counts["projects_created"] += 1


def _handle_run(conn, record, project_map, run_map, counts, fail_on_conflict):
    project_name = record["project_name"]
    run_id = record["run_id"]
    run_key = (project_name, run_id)

    if run_key in run_map:
        return

    project_db_id = project_map.get(project_name)
    if project_db_id is None:
        raise ValueError(f"Project not found: {project_name}")

    existing = conn.execute(
        text("SELECT id FROM runs WHERE project_id = :pid AND run_id = :rid"),
        {"pid": project_db_id, "rid": run_id},
    ).fetchone()

    if existing:
        if fail_on_conflict:
            raise ValueError(f"Run already exists: {project_name}/{run_id}")
        run_map[run_key] = existing.id
        counts["runs_skipped"] += 1
    else:
        rid = conn.execute(text("SELECT nextval('runs_id_seq')")).scalar()
        conn.execute(
            text("""
            INSERT INTO runs (id, project_id, run_id, name, group_name, tags,
                              state, created_at, updated_at)
            VALUES (:id, :pid, :rid, :name, :group_name, :tags, :state,
                    :created_at, :updated_at)
        """),
            {
                "id": rid,
                "pid": project_db_id,
                "rid": run_id,
                "name": record.get("name"),
                "group_name": record.get("group_name"),
                "tags": record.get("tags"),
                "state": record.get("state", "running"),
                "created_at": _parse_datetime(record.get("created_at")),
                "updated_at": _parse_datetime(record.get("created_at")),
            },
        )
        run_map[run_key] = rid
        counts["runs_created"] += 1


def _handle_config(conn, record, run_map, counts, fail_on_conflict):
    run_key = (record["project_name"], record["run_id"])
    run_db_id = run_map.get(run_key)
    if run_db_id is None:
        return

    existing = conn.execute(
        text("SELECT id FROM configs WHERE run_id = :rid AND key = :key"),
        {"rid": run_db_id, "key": record["key"]},
    ).fetchone()

    if existing:
        if fail_on_conflict:
            raise ValueError(f"Config already exists: {record['key']}")
        counts["configs_skipped"] += 1
        return

    cid = conn.execute(text("SELECT nextval('configs_id_seq')")).scalar()
    conn.execute(
        text("""
        INSERT INTO configs (id, run_id, key, value)
        VALUES (:id, :rid, :key, :value)
    """),
        {
            "id": cid,
            "rid": run_db_id,
            "key": record["key"],
            "value": record.get("value"),
        },
    )
    counts["configs_imported"] += 1


def _handle_table(
    conn, record, project_map, run_map, table_map, counts, fail_on_conflict
):
    project_name = record["project_name"]
    table_id = record["table_id"]
    table_key = (project_name, table_id)

    if table_key in table_map:
        return

    project_db_id = project_map.get(project_name)
    if project_db_id is None:
        raise ValueError(f"Project not found: {project_name}")

    run_db_id = None
    if record.get("run_id"):
        run_key = (project_name, record["run_id"])
        run_db_id = run_map.get(run_key)

    existing = conn.execute(
        text("SELECT id FROM dalva_tables WHERE project_id = :pid AND table_id = :tid"),
        {"pid": project_db_id, "tid": table_id},
    ).fetchone()

    if existing:
        if fail_on_conflict:
            raise ValueError(f"Table already exists: {project_name}/{table_id}")
        table_map[table_key] = existing.id
        counts["tables_skipped"] += 1
    else:
        tid = conn.execute(text("SELECT nextval('dalva_tables_id_seq')")).scalar()
        conn.execute(
            text("""
            INSERT INTO dalva_tables (id, project_id, table_id, name, run_id,
                                      column_schema, config, state, created_at, updated_at)
            VALUES (:id, :pid, :tid, :name, :run_db_id, :schema, :config, :state,
                    :created_at, :updated_at)
        """),
            {
                "id": tid,
                "pid": project_db_id,
                "tid": table_id,
                "name": record.get("name"),
                "run_db_id": run_db_id,
                "schema": record.get("column_schema"),
                "config": record.get("config"),
                "state": record.get("state", "active"),
                "created_at": _parse_datetime(record.get("created_at")),
                "updated_at": _parse_datetime(record.get("created_at")),
            },
        )
        table_map[table_key] = tid
        counts["tables_created"] += 1


def import_db(input: IO[str], fail_on_conflict: bool = False) -> dict:
    engine = get_engine()
    counts = {
        "projects_created": 0,
        "projects_skipped": 0,
        "runs_created": 0,
        "runs_skipped": 0,
        "configs_imported": 0,
        "configs_skipped": 0,
        "metrics_imported": 0,
        "tables_created": 0,
        "tables_skipped": 0,
        "table_rows_imported": 0,
    }

    project_map = {}
    run_map = {}
    table_map = {}
    metrics_buffer = []
    table_rows_buffer = []

    with engine.connect() as conn:
        for line in input:
            line = line.strip()
            if not line:
                continue

            record = json.loads(line)
            rec_type = record.get("type")

            if rec_type == "header":
                version = record.get("version", 0)
                if version != 1:
                    raise ValueError(f"Unsupported export version: {version}")

            elif rec_type == "project":
                _handle_project(conn, record, project_map, counts, fail_on_conflict)

            elif rec_type == "run":
                _flush_metrics(conn, metrics_buffer, run_map, counts)
                _flush_table_rows(conn, table_rows_buffer, table_map, counts)
                _handle_run(
                    conn, record, project_map, run_map, counts, fail_on_conflict
                )

            elif rec_type == "config":
                _handle_config(conn, record, run_map, counts, fail_on_conflict)

            elif rec_type == "metric":
                metrics_buffer.append(record)
                if len(metrics_buffer) >= BATCH_SIZE:
                    _flush_metrics(conn, metrics_buffer, run_map, counts)

            elif rec_type == "table":
                _flush_metrics(conn, metrics_buffer, run_map, counts)
                _handle_table(
                    conn,
                    record,
                    project_map,
                    run_map,
                    table_map,
                    counts,
                    fail_on_conflict,
                )

            elif rec_type == "table_row":
                table_rows_buffer.append(record)
                if len(table_rows_buffer) >= BATCH_SIZE:
                    _flush_table_rows(conn, table_rows_buffer, table_map, counts)

        _flush_metrics(conn, metrics_buffer, run_map, counts)
        _flush_table_rows(conn, table_rows_buffer, table_map, counts)

        conn.commit()
        _sync_sequences(conn)
        conn.commit()

    return counts
