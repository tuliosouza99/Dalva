"""Materialize daemonless journals into DuckDB for the on-demand UI."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from dalva.db.connection import next_id, session_scope
from dalva.db.schema import Config, DalvaTable, DalvaTableRow, Metric, Run
from dalva.services._shared import get_or_create_project
from dalva.services.logger import _flatten_config

_logger = logging.getLogger("dalva.journal_import")


def import_journals_once(runs_dir: Path) -> int:
    """Import all journal events not yet present in the materialized database."""
    if not runs_dir.exists():
        return 0
    imported = 0
    manifests = sorted(
        runs_dir.rglob("manifest.json"),
        key=lambda path: (len(path.relative_to(runs_dir).parts), str(path)),
    )
    for manifest_path in manifests:
        try:
            manifest = json.loads(manifest_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        events = _read_resource_events(manifest_path.parent / "events")
        for event in events:
            try:
                with session_scope() as db:
                    if _is_imported(manifest, event, db):
                        continue
                    _apply_event(manifest, event, db)
                    _mark_imported(manifest, event, db)
                imported += 1
            except Exception:
                # Active writers can leave a temporarily incomplete dependency
                # (for example a table event observed before its run event). The
                # event is intentionally left unmarked and retried next scan.
                _logger.debug(
                    "Journal event import deferred: %s seq=%s",
                    manifest.get("run_id") or manifest.get("table_id"),
                    event.get("seq"),
                    exc_info=True,
                )
    return imported


def _resource_id(manifest: dict) -> str:
    if manifest["resource_type"] == "table":
        return manifest["table_id"]
    return manifest["run_id"]


def _is_imported(manifest: dict, event: dict, db: Session) -> bool:
    return (
        db.execute(
            text(
                "SELECT 1 FROM journal_events "
                "WHERE resource_id = :resource_id AND seq = :seq"
            ),
            {"resource_id": _resource_id(manifest), "seq": event["seq"]},
        ).first()
        is not None
    )


def _mark_imported(manifest: dict, event: dict, db: Session) -> None:
    db.execute(
        text(
            "INSERT INTO journal_events "
            "(id, resource_id, seq, event_type, imported_at) "
            "VALUES (:id, :resource_id, :seq, :event_type, :imported_at)"
        ),
        {
            "id": next_id(db, "journal_events"),
            "resource_id": _resource_id(manifest),
            "seq": event["seq"],
            "event_type": event["type"],
            "imported_at": datetime.now(timezone.utc),
        },
    )


def _read_resource_events(events_dir: Path) -> list[dict]:
    if not events_dir.exists():
        return []
    events: dict[int, dict] = {}
    for path in events_dir.glob("*.jsonl"):
        try:
            with path.open() as stream:
                for line in stream:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    events[int(event["seq"])] = event
        except OSError:
            continue
    return [events[seq] for seq in sorted(events)]


def _apply_event(manifest: dict, event: dict, db: Session) -> None:
    if manifest["resource_type"] == "run":
        _apply_run_event(manifest, event, db)
    elif manifest["resource_type"] == "table":
        _apply_table_event(manifest, event, db)


def _find_run(manifest: dict, db: Session) -> Run | None:
    project = get_or_create_project(manifest["project"], db)
    return (
        db.query(Run)
        .filter(Run.project_id == project.id, Run.run_id == manifest["run_id"])
        .first()
    )


def _ensure_run(manifest: dict, payload: dict, db: Session) -> Run:
    existing = _find_run(manifest, db)
    if existing:
        return existing
    project = get_or_create_project(manifest["project"], db)
    now = datetime.now(timezone.utc)
    run = Run(
        id=next_id(db, "runs"),
        project_id=project.id,
        run_id=manifest["run_id"],
        name=payload.get("name") or manifest.get("name"),
        state="running",
        created_at=now,
        updated_at=now,
        last_activity_at=now,
    )
    db.add(run)
    db.flush()
    return run


def _apply_run_event(manifest: dict, event: dict, db: Session) -> None:
    kind = event["type"]
    payload = event["payload"]
    if kind == "run_created":
        run = _ensure_run(manifest, payload, db)
        flattened: dict[str, object] = {}
        _flatten_config(payload.get("config", {}), "", flattened)
        _insert_config(run.id, flattened, db)
        return

    run = _find_run(manifest, db)
    if run is None:
        raise LookupError(f"Run {manifest['run_id']} has not been imported yet")

    if kind == "metrics_logged":
        _insert_metrics(run.id, payload["metrics"], payload.get("step"), event, db)
        run.last_activity_at = datetime.now(timezone.utc)
        run.updated_at = run.last_activity_at
    elif kind == "metric_removed":
        query = db.query(Metric).filter(
            Metric.run_id == run.id,
            Metric.attribute_path == payload["metric"],
        )
        if payload.get("step") is not None:
            query = query.filter(Metric.step == payload["step"])
        query.delete()
    elif kind == "config_logged":
        _insert_config(run.id, payload["config"], db)
    elif kind == "config_removed":
        db.query(Config).filter(
            Config.run_id == run.id, Config.key == payload["key"]
        ).delete()
    elif kind == "run_resumed":
        run.state = "running"
    elif kind == "run_finished":
        run.state = "completed"
        run.updated_at = datetime.now(timezone.utc)


def _insert_config(run_id: int, values: dict[str, object], db: Session) -> None:
    for key, value in values.items():
        exists = (
            db.query(Config).filter(Config.run_id == run_id, Config.key == key).first()
        )
        if not exists:
            db.add(
                Config(
                    id=next_id(db, "configs"),
                    run_id=run_id,
                    key=key,
                    value=json.dumps(value),
                )
            )


def _insert_metrics(
    run_id: int,
    metrics: dict[str, object],
    step: int | None,
    event: dict,
    db: Session,
) -> None:
    suffix = "_series" if step is not None else ""
    timestamp = datetime.fromisoformat(event["timestamp"])
    for key, value in metrics.items():
        exists = (
            db.query(Metric)
            .filter(
                Metric.run_id == run_id,
                Metric.attribute_path == key,
                Metric.step == step,
            )
            .first()
        )
        if exists:
            continue
        if isinstance(value, bool):
            attr_type, column = f"bool{suffix}", "bool_value"
        elif isinstance(value, int):
            attr_type, column = f"int{suffix}", "int_value"
        elif isinstance(value, float):
            attr_type, column = f"float{suffix}", "float_value"
        else:
            attr_type, column = f"string{suffix}", "string_value"
        db.add(
            Metric(
                id=next_id(db, "metrics"),
                run_id=run_id,
                attribute_path=key,
                attribute_type=attr_type,
                step=step,
                timestamp=timestamp,
                **{column: value},
            )
        )


def _find_table(manifest: dict, db: Session) -> DalvaTable | None:
    project = get_or_create_project(manifest["project"], db)
    return (
        db.query(DalvaTable)
        .filter(
            DalvaTable.project_id == project.id,
            DalvaTable.table_id == manifest["table_id"],
        )
        .first()
    )


def _apply_table_event(manifest: dict, event: dict, db: Session) -> None:
    kind = event["type"]
    payload = event["payload"]
    if kind == "table_created":
        if _find_table(manifest, db):
            return
        project = get_or_create_project(manifest["project"], db)
        linked_run = None
        if manifest.get("run_id"):
            linked_run = (
                db.query(Run)
                .filter(
                    Run.project_id == project.id,
                    Run.run_id == manifest["run_id"],
                )
                .first()
            )
            if linked_run is None:
                raise LookupError("Linked run has not been imported yet")
        table = DalvaTable(
            id=next_id(db, "dalva_tables"),
            project_id=project.id,
            table_id=manifest["table_id"],
            name=manifest.get("name"),
            run_id=linked_run.id if linked_run else None,
            version=0,
            row_count=0,
            column_schema=json.dumps(payload["column_schema"]),
            config=json.dumps(manifest.get("config") or {}),
            state="active",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db.add(table)
        db.flush()
        return

    table = _find_table(manifest, db)
    if table is None:
        raise LookupError(f"Table {manifest['table_id']} has not been imported yet")
    if kind == "table_rows_logged":
        table.version = (table.version or 0) + 1
        for row in payload["rows"]:
            db.add(
                DalvaTableRow(
                    id=next_id(db, "dalva_table_rows"),
                    table_id=table.id,
                    version=table.version,
                    row_data=json.dumps(row),
                )
            )
        table.row_count = (table.row_count or 0) + len(payload["rows"])
    elif kind == "table_rows_removed":
        db.query(DalvaTableRow).filter(DalvaTableRow.table_id == table.id).delete()
        table.version = 0
        table.row_count = 0
    elif kind == "table_finished":
        table.state = "finished"
    table.updated_at = datetime.now(timezone.utc)
