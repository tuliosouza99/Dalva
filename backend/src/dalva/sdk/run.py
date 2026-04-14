"""Run class for experiment tracking via HTTP."""

from __future__ import annotations

import atexit
import warnings
from pathlib import Path
from typing import overload

import httpx

from ..types import _T, InputDict, Metric
from .table import Table
from .wal import WALManager
from .worker import PendingRequest, SyncWorker


class DalvaError(Exception):
    def __init__(
        self, message: str, errors: list[tuple[PendingRequest, Exception]] | None = None
    ) -> None:
        super().__init__(message)
        self.errors: list[tuple[PendingRequest, Exception]] = errors or []


def _server_error(exc: httpx.HTTPStatusError) -> str:
    try:
        body = exc.response.json()
        detail = body.get("detail", str(exc))
    except Exception:
        detail = str(exc)
    return f"Server error {exc.response.status_code}: {detail}"


class Run:
    """Run object for tracking experiments via HTTP.

    ``log()`` calls are asynchronous — they return immediately and are sent
    to the server in the background. Errors from failed requests are
    accumulated and reported when ``flush()`` or ``finish()`` is called.

    Synchronous operations (``get``, ``remove``, ``log_config``, etc.) drain
    the worker queue first to preserve ordering.

    Example:
        ```python
        run = Run(project="my-project", config={"lr": 0.001})
        run.log({"loss": 0.5}, step=0)
        run.finish()
        ```
    """

    def __init__(
        self,
        project: str,
        name: str | None = None,
        config: InputDict | None = None,
        resume_from: str | None = None,
        fork_from: str | None = None,
        copy_tables_on_fork: bool | list[int] = False,
        server_url: str = "http://localhost:8000",
        outbox_dir: Path | None = None,
    ):
        self.project_name = project
        self.config = config or {}
        self._server_url = server_url
        self._client: httpx.Client | None = None
        self._worker: SyncWorker | None = None
        self._tables: list[Table] = []
        self._finished: bool = False

        self._verify_server_connection()

        self._create_run_on_server(
            name=name,
            config=self.config,
            resume_from=resume_from,
            fork_from=fork_from,
            copy_tables_on_fork=copy_tables_on_fork,
        )

        self._wal = WALManager("run", self._db_id, outbox_dir=outbox_dir)
        self._worker = SyncWorker(server_url, wal_manager=self._wal)
        atexit.register(self._atexit_handler)

        print(f"Run created: {self.run_id}")

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
            print(f"[Run] Server health check OK: {self._server_url}")
        except httpx.HTTPError as e:
            raise ConnectionError(
                f"Cannot connect to Dalva server at {self._server_url}. "
                f"Please ensure the server is running. Error: {e}"
            )

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self._server_url, timeout=30)
        return self._client

    def _create_run_on_server(
        self,
        name: str | None,
        config: InputDict | None,
        resume_from: str | None,
        fork_from: str | None = None,
        copy_tables_on_fork: bool | list[int] = False,
    ):
        client = self._get_client()
        payload = {
            "project": self.project_name,
            "name": name,
            "config": config,
            "resume_from": resume_from,
            "fork_from": fork_from,
            "copy_tables_on_fork": copy_tables_on_fork,
        }
        try:
            response = client.post("/api/runs/init", json=payload)
            response.raise_for_status()
            result = response.json()
            self._db_id = result["id"]
            self.run_id = result["run_id"]
            self.name = result.get("name")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to create run on server: {e}")

    def log(self, metrics: InputDict, step: int | None = None):
        """Log metrics to the run (async — returns immediately).

        Metrics are enqueued and sent in the background. Errors are
        accumulated and reported by ``flush()`` or ``finish()``.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number for series values

        Example:
            ```python
            run.log({"accuracy": 0.85})
            for step in range(100):
                run.log({"loss": 0.5, "accuracy": 0.5}, step=step)
            run.log({"train": {"loss": 0.3, "acc": 0.9}}, step=0)
            ```
        """
        if self._finished:
            raise RuntimeError("Cannot log to a finished run")
        request = PendingRequest(
            method="POST",
            url=f"/api/runs/{self._db_id}/log",
            payload={"metrics": metrics, "step": step},
            batch_key=f"run:{self._db_id}",
        )
        self._worker.enqueue(request)

    def flush(self, timeout: float | None = None) -> list[Exception]:
        if self._worker is None:
            return []
        if self._worker.pending == 0:
            return []
        drained = self._worker.drain_with_progress(label="Flushing", timeout=timeout)
        if not drained:
            count = self._worker.dump_remaining()
            if count > 0:
                print(
                    f"\n[Dalva] {count} operation(s) saved to disk. "
                    f"Run 'dalva sync' to replay."
                )
        return [exc for _, exc in self._worker.clear_errors()]

    def remove(self, metric: str, step: int | None = None):
        """Remove a metric from the run (synchronous — drains queue first).

        Args:
            metric: Metric name/path to remove
            step: Optional step number. If omitted, removes ALL entries for this
                metric across all steps (scalar and series).

        Raises:
            ConnectionError: On server errors (including 404 if metric not found)

        Example:
            ```python
            run.log({"loss": 0.5}, step=0)
            run.remove("loss", step=0)
            run.log({"loss": 0.3}, step=0)
            run.remove("loss")
            ```
        """
        if self._worker is not None:
            self._worker.drain()
        client = self._get_client()
        params = {}
        if step is not None:
            params["step"] = step
        try:
            response = client.delete(
                f"/api/runs/{self._db_id}/metrics/{metric}",
                params=params,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to remove metric from server: {e}")

    @overload
    def get(self, key: str, default: _T, step: int | None = None) -> Metric | _T: ...

    @overload
    def get(
        self, key: str, default: None = None, step: int | None = None
    ) -> Metric | None: ...

    def get(
        self, key: str, default: _T | None = None, step: int | None = None
    ) -> Metric | _T | None:
        """Get a specific metric from the run.

        Returns a dict with ``key``, ``value``, and ``step``.
        If the metric does not exist, returns ``default`` (which defaults to ``None``).

        Args:
            key: Metric name/path to retrieve
            default: Value to return if the metric does not exist. Defaults to None.
            step: Optional step number to retrieve a specific step

        Returns:
            Dict with ``key``, ``value``, ``step``, or ``default`` if not found

        Example:
            ```python
            run.get("loss")               # {"key": "loss", "value": 0.3, "step": 1}
            run.get("missing", default=0) # 0
            ```
        """
        client = self._get_client()
        params = {}
        if step is not None:
            params["step"] = step
        try:
            response = client.get(
                f"/api/runs/{self._db_id}/metrics/{key}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return default
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to get metric from server: {e}")

    def log_config(self, config: InputDict):
        """Add config key-value pairs to the run (strict insert — no overwrites).

        This is synchronous and drains the worker queue first to preserve ordering.

        Raises ``ValueError`` on 409 Conflict if any key already exists.
        Use ``remove_config(key)`` first to overwrite.

        Args:
            config: Dictionary of config key -> value. Nested dicts are flattened
                with '/' as separator.

        Raises:
            ConnectionError: On server errors

        Example:
            ```python
            run.log_config({"lr": 0.001, "batch_size": 32})
            run.log_config({"epochs": 100})
            ```
        """
        if self._worker is not None:
            self._worker.drain()
        client = self._get_client()
        try:
            response = client.post(
                f"/api/runs/{self._db_id}/config",
                json={"config": dict(config)},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise ValueError(_server_error(e))
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to log config to server: {e}")

    def remove_config(self, key: str):
        """Remove a config key from the run.

        Args:
            key: Config key name to remove

        Raises:
            ConnectionError: On server errors

        Example:
            ```python
            run.remove_config("lr")
            run.log_config({"lr": 0.01})
            ```
        """
        client = self._get_client()
        try:
            response = client.delete(f"/api/runs/{self._db_id}/config/{key}")
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to remove config from server: {e}")

    @overload
    def get_config(
        self, key: str, default: _T, step: int | None = None
    ) -> Metric | _T: ...

    @overload
    def get_config(
        self, key: str, default: None = None, step: int | None = None
    ) -> Metric | None: ...

    def get_config(
        self, key: str, default: _T | None = None, step: int | None = None
    ) -> Metric | _T | None:
        """Get a specific config key from the run.

        Returns a dict with ``key`` and ``value``.
        If the key does not exist, returns ``default`` (which defaults to ``None``).

        Args:
            key: Config key name to retrieve
            default: Value to return if the key does not exist. Defaults to None.

        Returns:
            Dict with ``key`` and ``value``, or ``default`` if not found

        Example:
            ```python
            run.get_config("lr")               # {"key": "lr", "value": 0.001}
            run.get_config("missing", default=0) # 0
            ```
        """
        client = self._get_client()
        try:
            response = client.get(f"/api/runs/{self._db_id}/config/{key}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return default
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to get config from server: {e}")

    def create_table(
        self,
        name: str | None = None,
        config: InputDict | None = None,
        log_mode: str | None = "IMMUTABLE",
    ) -> Table:
        """Create a table linked to this run.

        The table is automatically associated with the same project and run.
        When run.finish() is called, all linked tables will be finished first.

        Args:
            name: Optional table name (user-defined, for display only)
            config: Optional configuration dictionary
            log_mode: IMMUTABLE, MUTABLE, or INCREMENTAL

        Returns:
            Table object linked to this run

        Example:
            ```python
            table = run.create_table(name="predictions", log_mode="IMMUTABLE")
            table.log(df)
            run.finish()
            ```
        """
        table = Table(
            project=self.project_name,
            name=name,
            config=config,
            run_id=self.run_id,
            server_url=self._server_url,
            log_mode=log_mode,
        )
        self._tables.append(table)
        return table

    def finish(self, on_error: str = "warn", timeout: float = 120):
        """Finish the run and mark it as completed.

        Drains the worker queue (blocking until all pending requests are
        processed or *timeout* seconds elapse), finishes all linked tables,
        then sends the finish request to the server.

        Args:
            on_error: How to handle accumulated errors from failed ``log()``
                calls. ``"warn"`` (default) prints warnings. ``"raise"`` raises
                a ``DalvaError`` wrapping all accumulated errors.
            timeout: Maximum seconds to wait for the worker queue to drain.
                Defaults to 120.

        Raises:
            DalvaError: If ``on_error="raise"`` and there were failed requests.
            ConnectionError: If the finish request itself fails.

        Example:
            ```python
            run.log({"loss": 0.5}, step=0)
            run.finish()
            run.finish(on_error="raise")
            ```
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
                        label="Finishing run", timeout=timeout
                    )
                if not drained_ok:
                    count = self._worker.dump_remaining()
                    if count > 0:
                        print(
                            f"\n[Dalva] {count} operation(s) saved to disk. "
                            f"Run 'dalva sync' to replay."
                        )
                    return
                errors = self._worker.clear_errors()

            for table in self._tables:
                if not table._finished:
                    try:
                        table.finish(on_error=on_error)
                    except Exception:
                        pass

            client = self._get_client()
            response = client.post(f"/api/runs/{self._db_id}/finish")
            response.raise_for_status()
            result = response.json()
            print(f"[Run] Run finished (state={result['state']})")
            self._finished = True

            if self._worker is not None:
                self._worker.wal_delete()

            if errors:
                if on_error == "raise":
                    msgs = [f"  {req.method} {req.url}: {exc}" for req, exc in errors]
                    raise DalvaError(
                        f"{len(errors)} request(s) failed during run:\n"
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
            raise ConnectionError(f"Failed to finish run on server: {e}")
        finally:
            if self._worker is not None:
                self._worker.stop()
                self._worker = None
            self._client = None

    def __repr__(self):
        return f"Run(project='{self.project_name}', name='{self.name}', id={self.run_id}, server={self._server_url})"
