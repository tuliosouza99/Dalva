"""Daemonless Run and Table implementations backed by event journals."""

from __future__ import annotations

import atexit
import json
import warnings
from collections.abc import Generator, Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, TypeVar, overload

from pydantic import create_model

from ..types import InputDict, Metric, TableRowValue
from .errors import DalvaError
from .journal import (
    Durability,
    SegmentedJournal,
    default_runs_dir,
    new_resource_id,
    write_manifest,
)
from .schema import DalvaSchema
from .transport import SegmentTransport

_T = TypeVar("_T")
_MISSING = object()


def _flatten(values: Mapping[str, object], prefix: str = "") -> dict[str, object]:
    flattened: dict[str, object] = {}
    for key, value in values.items():
        path = f"{prefix}/{key}" if prefix else key
        if isinstance(value, Mapping):
            flattened.update(_flatten(value, path))
        else:
            flattened[path] = value
    return flattened


class JournalRun:
    """A daemonless experiment run whose source of truth is a local journal."""

    def __init__(
        self,
        project: str,
        name: str | None = None,
        config: InputDict | None = None,
        resume_from: str | None = None,
        fork_from: str | None = None,
        copy_tables_on_fork: bool | list[int] = False,
        *,
        sync: str | Path | SegmentTransport | None = None,
        runs_dir: Path | None = None,
        durability: Durability = "balanced",
        segment_bytes: int = 256 * 1024,
        segment_interval: float = 0.5,
    ):
        if resume_from and fork_from:
            raise ValueError("resume_from and fork_from are mutually exclusive")
        if copy_tables_on_fork:
            raise NotImplementedError(
                "copy_tables_on_fork is not yet supported in daemonless mode"
            )

        self.project_name = project
        self.name = name
        self._runs_dir = (runs_dir or default_runs_dir()).expanduser()
        self._runs_dir.mkdir(parents=True, exist_ok=True)
        self.run_id = resume_from or new_resource_id("RUN")
        self._resource_dir = self._runs_dir / self.run_id
        self._manifest_path = self._resource_dir / "manifest.json"
        self._tables: list[JournalTable] = []
        self._finished = False
        self._metrics: dict[tuple[str, int | None], object] = {}
        self._metric_kinds: dict[str, tuple[type, bool]] = {}
        self._config: dict[str, object] = {}
        self._durability = durability
        self._segment_bytes = segment_bytes
        self._segment_interval = segment_interval

        existing = self._manifest_path.exists()
        if resume_from and not existing:
            raise ValueError(f"Run '{resume_from}' was not found in {self._runs_dir}")

        self._journal = SegmentedJournal(
            self._resource_dir,
            root=self._runs_dir,
            sync_target=sync,
            durability=durability,
            segment_bytes=segment_bytes,
            segment_interval=segment_interval,
        )

        if existing:
            manifest = json.loads(self._manifest_path.read_text())
            if manifest["project"] != project:
                raise ValueError(
                    f"Run '{self.run_id}' belongs to project "
                    f"'{manifest['project']}', not '{project}'"
                )
            self.name = name or manifest.get("name")
            self._replay()
            self._finished = False
            self._journal.append("run_resumed")
            self._write_manifest("running")
        else:
            self._write_manifest("running", fork_from=fork_from)
            self._journal.append(
                "run_created",
                {
                    "run_id": self.run_id,
                    "project": project,
                    "name": name,
                    "config": dict(config or {}),
                    "fork_from": fork_from,
                },
            )
            if config:
                self._config.update(_flatten(config))

        if fork_from:
            self._copy_fork_source(fork_from)

        self.config = dict(self._config)
        atexit.register(self._atexit_handler)

    def _write_manifest(self, state: str, **extra) -> None:
        now = datetime.now(timezone.utc).isoformat()
        created_at = now
        if self._manifest_path.exists():
            created_at = json.loads(self._manifest_path.read_text()).get(
                "created_at", now
            )
        write_manifest(
            self._manifest_path,
            {
                "format_version": 1,
                "resource_type": "run",
                "run_id": self.run_id,
                "project": self.project_name,
                "name": self.name,
                "state": state,
                "created_at": created_at,
                "updated_at": now,
                **extra,
            },
        )
        if hasattr(self, "_journal"):
            self._journal.replicate_manifest()

    def _copy_fork_source(self, fork_from: str) -> None:
        source = self._runs_dir / fork_from / "events"
        if not source.exists():
            raise ValueError(f"Run '{fork_from}' was not found in {self._runs_dir}")
        config: dict[str, object] = {}
        metrics: dict[tuple[str, int | None], object] = {}
        for event in _read_events(source):
            _apply_run_event(event, config, metrics)
        if config:
            self.log_config(config)
        grouped: dict[int | None, dict[str, object]] = {}
        for (key, step), value in metrics.items():
            grouped.setdefault(step, {})[key] = value
        for step, values in grouped.items():
            self.log(values, step=step)
        self._journal.append("run_forked", {"source_run_id": fork_from})

    def _replay(self) -> None:
        for event in self._journal.iter_events():
            _apply_run_event(event, self._config, self._metrics)
        for (key, step), value in self._metrics.items():
            self._metric_kinds[key] = (type(value), step is not None)

    def _atexit_handler(self) -> None:
        if self._finished:
            return
        try:
            self.finish(timeout=30)
        except Exception:  # noqa: BLE001
            self._journal.close()

    def log(self, metrics: InputDict, step: int | None = None) -> None:
        if self._finished:
            raise RuntimeError("Cannot log to a finished run")
        flattened = _flatten(metrics)
        for key, value in flattened.items():
            if not isinstance(value, (bool, int, float, str)):
                raise TypeError(f"Metric '{key}' must be a scalar value")
            kind = self._metric_kinds.get(key)
            new_kind = (type(value), step is not None)
            if kind and kind != new_kind:
                raise ValueError(
                    f"Metric '{key}' has already been logged with a different type "
                    "or scalar/series shape"
                )
            if (key, step) in self._metrics:
                raise ValueError(
                    f"Metric '{key}' already exists at "
                    f"{'step ' + str(step) if step is not None else 'summary'}"
                )
        self._journal.append("metrics_logged", {"metrics": flattened, "step": step})
        for key, value in flattened.items():
            self._metrics[(key, step)] = value
            self._metric_kinds[key] = (type(value), step is not None)

    def flush(self, timeout: float | None = None) -> list[Exception]:
        del timeout
        self._journal.flush()
        return []

    def sync(self, timeout: float | None = None) -> list[Exception]:
        return [error for _, error in self._journal.sync(timeout)]

    def remove(self, metric: str, step: int | None = None) -> None:
        matches = [
            key
            for key in self._metrics
            if key[0] == metric and (step is None or key[1] == step)
        ]
        if not matches:
            raise ValueError(f"No metric '{metric}' was found")
        self._journal.append("metric_removed", {"metric": metric, "step": step})
        for key in matches:
            del self._metrics[key]
        if not any(key == metric for key, _ in self._metrics):
            self._metric_kinds.pop(metric, None)

    @overload
    def get(self, key: str, default: _T, step: int | None = None) -> Metric | _T: ...

    @overload
    def get(
        self, key: str, default: None = None, step: int | None = None
    ) -> Metric | None: ...

    def get(self, key: str, default=None, step: int | None = None):
        if step is not None:
            value = self._metrics.get((key, step), _MISSING)
            if value is _MISSING:
                return default
            return {"key": key, "value": value, "step": step}
        candidates = [
            (metric_step, value)
            for (metric_key, metric_step), value in self._metrics.items()
            if metric_key == key
        ]
        if not candidates:
            return default
        series = [(s, v) for s, v in candidates if s is not None]
        selected_step, value = max(series) if series else candidates[0]
        return {"key": key, "value": value, "step": selected_step}

    def log_config(self, config: InputDict) -> None:
        flattened = _flatten(config)
        duplicates = sorted(set(flattened) & set(self._config))
        if duplicates:
            raise ValueError(f"Config key(s) already exist: {duplicates}")
        self._journal.append("config_logged", {"config": flattened})
        self._config.update(flattened)
        self.config = dict(self._config)

    def remove_config(self, key: str) -> None:
        if key not in self._config:
            raise ValueError(f"Config key '{key}' was not found")
        self._journal.append("config_removed", {"key": key})
        del self._config[key]
        self.config = dict(self._config)

    def get_config(self, key: str, default=None, step: int | None = None):
        del step
        if key not in self._config:
            return default
        return {"key": key, "value": self._config[key]}

    def create_table(
        self,
        schema: type[DalvaSchema],
        name: str | None = None,
        config: InputDict | None = None,
    ) -> JournalTable:
        table = JournalTable(
            project=self.project_name,
            schema=schema,
            name=name,
            config=config,
            run_id=self.run_id,
            resource_dir=self._resource_dir / "tables" / new_resource_id("TBL"),
            root=self._runs_dir,
            sync_target=self._journal.transport,
            durability=self._durability,
            segment_bytes=self._segment_bytes,
            segment_interval=self._segment_interval,
        )
        self._tables.append(table)
        self._journal.append(
            "table_created", {"table_id": table.table_id, "name": name}
        )
        return table

    def finish(self, on_error: str = "warn", timeout: float | None = None) -> None:
        if self._finished:
            return
        for table in self._tables:
            table.finish(on_error=on_error, timeout=timeout)
        self._journal.append("run_finished", {"state": "completed"})
        self._write_manifest("completed")
        errors = self.sync(timeout)
        self._finished = True
        self._journal.close()
        if errors and on_error == "raise":
            raise DalvaError(
                f"{len(errors)} segment(s) failed to synchronize",
                errors=[],
            )
        for error in errors:
            warnings.warn(f"[Dalva] Segment synchronization failed: {error}")

    def __repr__(self) -> str:
        return (
            f"JournalRun(project='{self.project_name}', name='{self.name}', "
            f"id={self.run_id})"
        )


class JournalTable:
    """Daemonless table stored as validated append-only row events."""

    def __init__(
        self,
        project: str,
        schema: type[DalvaSchema] | None = None,
        name: str | None = None,
        config: InputDict | None = None,
        run_id: str | None = None,
        resume_from: str | None = None,
        *,
        sync_target: str | Path | SegmentTransport | None = None,
        runs_dir: Path | None = None,
        resource_dir: Path | None = None,
        root: Path | None = None,
        durability: Durability = "balanced",
        segment_bytes: int = 256 * 1024,
        segment_interval: float = 0.5,
    ):
        self.project_name = project
        self.name = name
        self._run_id = run_id
        self.table_id = resume_from or (
            resource_dir.name if resource_dir else new_resource_id("TBL")
        )
        base = (runs_dir or default_runs_dir()).expanduser()
        self._resource_dir = resource_dir or base / "_tables" / self.table_id
        self._root = root or base
        self._manifest_path = self._resource_dir / "manifest.json"
        if schema is None:
            if not self._manifest_path.exists():
                raise TypeError("schema is required when creating a daemonless table")
            stored = json.loads(self._manifest_path.read_text())["column_schema"]
            schema = _schema_from_columns(stored)
        self._schema_cls = schema
        self._rows: list[dict[str, TableRowValue]] = []
        self._finished = False
        self._journal = SegmentedJournal(
            self._resource_dir,
            root=self._root,
            sync_target=sync_target,
            durability=durability,
            segment_bytes=segment_bytes,
            segment_interval=segment_interval,
        )
        if self._manifest_path.exists():
            for event in self._journal.iter_events():
                self._apply_event(event)
            self._journal.append("table_resumed")
        else:
            write_manifest(
                self._manifest_path,
                {
                    "format_version": 1,
                    "resource_type": "table",
                    "table_id": self.table_id,
                    "project": project,
                    "run_id": run_id,
                    "name": name,
                    "config": dict(config or {}),
                    "column_schema": schema.to_column_schema(),
                    "state": "active",
                },
            )
            self._journal.replicate_manifest()
            self._journal.append(
                "table_created",
                {
                    "table_id": self.table_id,
                    "project": project,
                    "run_id": run_id,
                    "name": name,
                    "column_schema": schema.to_column_schema(),
                },
            )
        atexit.register(self._atexit_handler)

    def _atexit_handler(self) -> None:
        if not self._finished:
            try:
                self.finish(timeout=30)
            except Exception:  # noqa: BLE001
                self._journal.close()

    def _apply_event(self, event: dict) -> None:
        event_type = event["type"]
        if event_type == "table_rows_logged":
            self._rows.extend(event["payload"]["rows"])
        elif event_type == "table_rows_removed":
            self._rows.clear()

    def log_row(self, row: Mapping[str, object]) -> None:
        self.log_rows([row])

    def log_rows(self, rows: Iterable[Mapping[str, object]]) -> None:
        if self._finished:
            raise RuntimeError("Cannot log to a finished table")
        validated = [self._schema_cls.validate_row(dict(row)) for row in rows]
        if not validated:
            return
        self._journal.append("table_rows_logged", {"rows": validated})
        self._rows.extend(validated)

    @overload
    def get_table(
        self, stream: Literal[False] = False
    ) -> list[dict[str, TableRowValue]]: ...

    @overload
    def get_table(
        self, stream: Literal[True]
    ) -> Generator[dict[str, TableRowValue], None, None]: ...

    def get_table(self, stream: bool = False):
        if stream:
            return (row for row in self._rows)
        return list(self._rows)

    def remove_table(self) -> None:
        self._journal.append("table_rows_removed")
        self._rows.clear()

    def flush(self, timeout: float | None = None) -> list[Exception]:
        del timeout
        self._journal.flush()
        return []

    def sync(self, timeout: float | None = None) -> list[Exception]:
        return [error for _, error in self._journal.sync(timeout)]

    def finish(self, on_error: str = "warn", timeout: float | None = None) -> None:
        if self._finished:
            return
        self._journal.append("table_finished", {"state": "finished"})
        manifest = json.loads(self._manifest_path.read_text())
        manifest["state"] = "finished"
        manifest["row_count"] = len(self._rows)
        write_manifest(self._manifest_path, manifest)
        self._journal.replicate_manifest()
        errors = self.sync(timeout)
        self._finished = True
        self._journal.close()
        if errors and on_error == "raise":
            raise DalvaError(
                f"{len(errors)} table segment(s) failed to synchronize",
                errors=[],
            )
        for error in errors:
            warnings.warn(f"[Dalva] Segment synchronization failed: {error}")


def _read_events(events_dir: Path):
    for path in sorted(events_dir.glob("*.jsonl")):
        with path.open() as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)


def _schema_from_columns(columns: list[dict[str, str]]) -> type[DalvaSchema]:
    types = {
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "list": list,
        "dict": dict,
    }
    fields = {
        column["name"]: (types.get(column["type"], object), ...) for column in columns
    }
    return create_model("RestoredDalvaSchema", __base__=DalvaSchema, **fields)


def _apply_run_event(
    event: dict,
    config: dict[str, object],
    metrics: dict[tuple[str, int | None], object],
) -> None:
    event_type = event["type"]
    payload = event["payload"]
    if event_type == "run_created":
        config.update(_flatten(payload.get("config", {})))
    elif event_type == "config_logged":
        config.update(payload["config"])
    elif event_type == "config_removed":
        config.pop(payload["key"], None)
    elif event_type == "metrics_logged":
        for key, value in payload["metrics"].items():
            metrics[(key, payload.get("step"))] = value
    elif event_type == "metric_removed":
        metric = payload["metric"]
        step = payload.get("step")
        for key in list(metrics):
            if key[0] == metric and (step is None or key[1] == step):
                del metrics[key]
