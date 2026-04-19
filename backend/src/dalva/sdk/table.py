"""Table class for tabular data tracking via HTTP."""

from __future__ import annotations

import atexit
import json
import logging
import warnings
from collections.abc import Generator, Iterable, Mapping
from pathlib import Path
from typing import Literal, overload

import httpx

from ..types import InputDict, TableRowValue
from .errors import DalvaError
from .http_utils import _server_error
from .schema import DalvaSchema
from .wal import WALManager
from .worker import PendingRequest, SyncWorker

_logger = logging.getLogger("dalva.sdk")


class Table:
    """Table object for tracking tabular data via HTTP.

    ``log_row()`` and ``log_rows()`` are asynchronous — they return immediately
    and are sent to the server in the background. Errors from failed requests
    are accumulated and reported when ``flush()`` or ``finish()`` is called.

    Example:
        ```python
        from dalva import table, DalvaSchema

        class MySchema(DalvaSchema):
            name: str
            score: float

        t = table(project="my-project", schema=MySchema)
        t.log_row({"name": "test", "score": 0.5})
        t.log_rows([{"name": "a", "score": 0.9}, {"name": "b", "score": 0.3}])
        t.finish()
        ```
    """

    def __init__(
        self,
        project: str,
        schema: type[DalvaSchema] | None = None,
        name: str | None = None,
        config: InputDict | None = None,
        run_id: str | None = None,
        resume_from: str | None = None,
        server_url: str = "http://localhost:8000",
        outbox_dir: Path | None = None,
        http_timeout: float | None = None,
    ):
        if resume_from is None:
            if schema is None:
                raise TypeError(
                    "schema is required when creating a new table. "
                    "For resuming an existing table, pass resume_from."
                )
            if not isinstance(schema, type) or not issubclass(schema, DalvaSchema):
                raise TypeError(
                    f"schema must be a DalvaSchema subclass, got {type(schema)}"
                )

        self.project_name = project
        self._schema_cls = schema
        self.config = config or {}
        self._server_url = server_url
        self._http_timeout = http_timeout
        self._client: httpx.Client | None = None
        self._worker: SyncWorker | None = None
        self._run_id = run_id
        self._run_db_id: int | None = None
        self._finished: bool = False
        self._db_id: int = 0
        self.table_id: str = ""
        self.name: str | None = None
        self._version: int = 0

        self._verify_server_connection()

        self._create_table_on_server(
            name=name,
            config=self.config,
            resume_from=resume_from,
        )

        self._wal = WALManager("table", self._db_id, outbox_dir=outbox_dir)
        self._worker = SyncWorker(
            server_url, wal_manager=self._wal, http_timeout=http_timeout
        )
        atexit.register(self._atexit_handler)

        _logger.info("Table created: %s", self.table_id)

    def _atexit_handler(self) -> None:
        if self._finished:
            return
        try:
            self.finish(timeout=30)
        except Exception:
            pass

    def _verify_server_connection(self):
        try:
            response = httpx.get(f"{self._server_url}/api/health", timeout=10)
            response.raise_for_status()
            _logger.info("[Table] Server health check OK: %s", self._server_url)
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(
                f"Cannot connect to Dalva server at {self._server_url}. "
                f"Please ensure the server is running. Error: {e}"
            )

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self._server_url, timeout=self._http_timeout
            )
        return self._client

    def _create_table_on_server(
        self,
        name: str | None,
        config: InputDict | None,
        resume_from: str | None,
    ):
        client = self._get_client()

        run_db_id = None
        if self._run_id:
            project_id = self._resolve_project_id()
            if project_id is None:
                raise ValueError(
                    f"Project '{self.project_name}' not found on server. "
                    f"Cannot resolve run_id link."
                )
            run_response = client.get(f"/api/runs/?project_id={project_id}")
            run_response.raise_for_status()
            runs = run_response.json()["runs"]
            matched = next((r for r in runs if r["run_id"] == self._run_id), None)
            if not matched:
                raise ValueError(
                    f"Run '{self._run_id}' not found in project '{self.project_name}'"
                )
            run_db_id = matched["id"]
            self._run_db_id = run_db_id

        column_schema = (
            self._schema_cls.to_column_schema() if self._schema_cls else None
        )

        payload = {
            "project": self.project_name,
            "name": name,
            "config": config,
            "run_id": run_db_id,
            "column_schema": column_schema,
            "resume_from": resume_from,
        }
        try:
            response = client.post("/api/tables/init", json=payload)
            response.raise_for_status()
            result = response.json()
            self._db_id = result["id"]
            self.table_id = result["table_id"]
            self.name = result.get("name")
            self._version = result.get("version", 0)
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to create table on server: {e}")

    def _resolve_project_id(self) -> int | None:
        client = self._get_client()
        try:
            response = client.get("/api/projects/")
            response.raise_for_status()
            projects = response.json()
            if isinstance(projects, dict):
                projects = projects.get("projects", [])
            matched = next(
                (p for p in projects if p["name"] == self.project_name), None
            )
            return matched["id"] if matched else None
        except Exception:
            return None

    def log_row(self, row: Mapping[str, object]) -> None:
        """Log a single row to the table (async — returns immediately).

        Args:
            row: Dictionary matching the table schema.

        Raises:
            RuntimeError: If the table is already finished or has no schema.
            ValueError: If the row doesn't match the schema.
        """
        if self._finished:
            raise RuntimeError("Cannot log to a finished table")
        if self._schema_cls is None:
            raise RuntimeError(
                "Cannot log to a table without a schema. "
                "Pass a DalvaSchema when creating or resuming the table."
            )

        validated = self._schema_cls.validate_row(dict(row))

        request = PendingRequest(
            method="POST",
            url=f"/api/tables/{self._db_id}/log",
            payload=json.dumps({"rows": [validated]}),
            headers={"Content-Type": "application/json"},
            batch_key=f"table:{self._db_id}",
        )
        if self._worker:
            self._worker.enqueue(request)

    def log_rows(self, rows: Iterable[Mapping[str, object]]) -> None:
        """Log multiple rows to the table (async — returns immediately).

        Args:
            rows: Iterable of dictionaries matching the table schema.

        Raises:
            RuntimeError: If the table is already finished or has no schema.
            ValueError: If any row doesn't match the schema.
        """
        if self._finished:
            raise RuntimeError("Cannot log to a finished table")
        if self._schema_cls is None:
            raise RuntimeError(
                "Cannot log to a table without a schema. "
                "Pass a DalvaSchema when creating or resuming the table."
            )

        validated = [self._schema_cls.validate_row(dict(r)) for r in rows]

        request = PendingRequest(
            method="POST",
            url=f"/api/tables/{self._db_id}/log",
            payload=json.dumps({"rows": validated}),
            headers={"Content-Type": "application/json"},
            batch_key=f"table:{self._db_id}",
        )
        if self._worker:
            self._worker.enqueue(request)

    @overload
    def get_table(
        self, stream: Literal[False] = False
    ) -> list[dict[str, TableRowValue]]: ...

    @overload
    def get_table(
        self, stream: Literal[True]
    ) -> Generator[dict[str, TableRowValue], None, None]: ...

    def get_table(
        self, stream: bool = False
    ) -> (
        list[dict[str, TableRowValue]] | Generator[dict[str, TableRowValue], None, None]
    ):
        """Get all rows from the table (synchronous — drains worker first).

        Args:
            stream: If True, returns a generator yielding dicts via NDJSON streaming.

        Returns:
            List of row dicts, or a generator of row dicts if stream=True.
        """
        if self._worker is not None:
            self._worker.drain()

        client = self._get_client()

        if stream:
            return self._stream_rows(client)

        all_rows = []
        limit = 1000
        offset = 0
        while True:
            response = client.get(
                f"/api/tables/{self._db_id}/data",
                params={"limit": limit, "offset": offset},
            )
            response.raise_for_status()
            data = response.json()
            all_rows.extend(data["rows"])
            if not data.get("has_more", False):
                break
            offset += limit
        return all_rows

    def _stream_rows(self, client: httpx.Client) -> Generator[dict, None, None]:
        with client.stream(
            "GET", f"/api/tables/{self._db_id}/data", params={"stream": "true"}
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if line.strip():
                    yield json.loads(line)

    def remove_table(self) -> None:
        """Remove all rows from the table (synchronous — drains worker first).

        Keeps table metadata and schema intact.
        """
        if self._worker is not None:
            self._worker.drain()
        client = self._get_client()
        try:
            response = client.delete(f"/api/tables/{self._db_id}/rows")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to remove table rows: {e}")

    def flush(self, timeout: float | None = None) -> list[Exception]:
        if self._worker is None:
            return []
        if self._worker.pending == 0:
            return []
        drained = self._worker.drain_with_progress(label="Flushing", timeout=timeout)
        if not drained:
            count = self._worker.dump_remaining()
            if count > 0:
                _logger.warning(
                    "[Dalva] %d operation(s) saved to disk. "
                    "Run 'dalva sync' to replay.",
                    count,
                )
        return [exc for _, exc in self._worker.clear_errors()]

    def finish(self, on_error: str = "warn", timeout: float | None = None) -> None:
        """Finish the table and mark it as completed.

        Args:
            on_error: How to handle accumulated errors from failed ``log_row()``
                calls. ``"warn"`` (default) prints warnings. ``"raise"`` raises
                a DalvaError wrapping all accumulated errors.
            timeout: Maximum seconds to wait for the worker queue to drain.
                Defaults to None (wait indefinitely).
        """
        if self._finished:
            return

        errors: list[tuple[PendingRequest, Exception]] = []
        drained_ok = True

        try:
            if self._worker is not None:
                total = self._worker.pending
                if total > 0:
                    drained_ok = self._worker.drain_with_progress(
                        label="Finishing table", timeout=timeout
                    )
                if not drained_ok:
                    count = self._worker.dump_remaining()
                    if count > 0:
                        _logger.warning(
                            "[Dalva] %d operation(s) saved to disk. "
                            "Run 'dalva sync' to replay.",
                            count,
                        )
                    self._finished = True
                    return
                errors = self._worker.clear_errors()

            client = self._get_client()
            response = client.post(f"/api/tables/{self._db_id}/finish")
            response.raise_for_status()
            result = response.json()
            _logger.info("[Table] Table finished (state=%s)", result["state"])
            self._finished = True

            if self._worker is not None:
                self._worker.wal_delete()

            if errors:
                if on_error == "raise":
                    msgs = [f"  {req.method} {req.url}: {exc}" for req, exc in errors]
                    raise DalvaError(
                        f"{len(errors)} request(s) failed during table:\n"
                        + "\n".join(msgs),
                        errors=errors,
                    )
                else:
                    for req, exc in errors:
                        warnings.warn(
                            f"[Dalva] Request failed: {req.method} {req.url}: {exc}"
                        )

        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to finish table on server: {e}")
        finally:
            if self._worker is not None:
                self._worker.stop()
                self._worker = None
            self._client = None

    def __repr__(self) -> str:
        return f"Table(project='{self.project_name}', name='{self.name}', id={self.table_id}, server={self._server_url})"
