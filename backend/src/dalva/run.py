"""Run class for experiment tracking via HTTP."""

from __future__ import annotations

from typing import TypedDict, Union, overload

import httpx

from ._table import Table
from .types import _T, InputDict


class Metric(TypedDict):
    key: str
    value: Union[int, float, str, bool, None]
    step: int | None


def _server_error(exc: httpx.HTTPStatusError) -> str:
    """Extract server error detail from an HTTPStatusError."""
    try:
        body = exc.response.json()
        detail = body.get("detail", str(exc))
    except Exception:
        detail = str(exc)
    return f"Server error {exc.response.status_code}: {detail}"


class Run:
    """Run object for tracking experiments via HTTP.

    All operations are performed via HTTP requests to the server.
    No local database operations are performed.

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
        server_url: str = "http://localhost:8000",
    ):
        """
        Initialize a run by creating it on the server.

        Args:
            project: Project name
            name: Optional run name (user-defined, for display only)
            config: Optional configuration dictionary
            resume_from: run_id to resume (omit to create a new run)
            server_url: Server URL. Defaults to http://localhost:8000
        """
        self.project_name = project
        self.config = config or {}
        self._server_url = server_url
        self._client: httpx.Client | None = None
        self._tables: list[Table] = []
        self._finished: bool = False

        # Verify server is accessible
        self._verify_server_connection()

        # Create run via API
        self._create_run_on_server(
            name=name, config=self.config, resume_from=resume_from
        )

        # Print run ID for user convenience
        print(f"Run created: {self.run_id}")

    def _verify_server_connection(self):
        """Verify server is accessible via health check endpoint."""
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
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(base_url=self._server_url, timeout=30)
        return self._client

    def _create_run_on_server(
        self, name: str | None, config: InputDict | None, resume_from: str | None
    ):
        """Create the run on the server via API."""
        client = self._get_client()
        payload = {
            "project": self.project_name,
            "name": name,
            "config": config,
            "resume_from": resume_from,
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
        """Log metrics to the run.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number for series values

        Raises:
            ConnectionError: On server errors (including 409 Conflict if a metric
                with the same key already exists — use remove() first to overwrite)

        Example:
            ```python
            run = Run(project="my-project", config={"lr": 0.001})
            run.log({"accuracy": 0.85})
            for step in range(100):
                run.log({"loss": 0.5, "accuracy": 0.5}, step=step)
            # Nested dicts are flattened with '/' separator:
            run.log({"train": {"loss": 0.3, "acc": 0.9}}, step=0)
            # equivalent to: run.log({"train/loss": 0.3, "train/acc": 0.9}, step=0)
            run.finish()
            ```
        """
        client = self._get_client()
        payload = {
            "metrics": metrics,
            "step": step,
        }
        try:
            response = client.post(f"/api/runs/{self._db_id}/log", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 409:
                raise ValueError(_server_error(e))
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to log metrics to server: {e}")

    def remove(self, metric: str, step: int | None = None):
        """Remove a metric from the run.

        Args:
            metric: Metric name/path to remove
            step: Optional step number. If omitted, removes ALL entries for this
                metric across all steps (scalar and series).

        Raises:
            ConnectionError: On server errors (including 404 if metric not found)

        Example:
            ```python
            run = dalva.init(project="my-project")
            run.log({"loss": 0.5}, step=0)
            # To overwrite:
            run.remove("loss", step=0)
            run.log({"loss": 0.3}, step=0)
            # To remove all entries for a metric:
            run.remove("loss")
            # Works with nested/flattened keys too:
            run.log({"train": {"loss": 0.5}}, step=0)
            run.remove("train/loss", step=0)
            run.log({"train": {"loss": 0.3}}, step=0)
            ```
        """
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

        - With ``step``: returns the metric at that specific step.
        - Without ``step``: returns the metric at the latest step (highest step
          number), or the scalar value if no series steps exist.

        Args:
            key: Metric name/path to retrieve
            default: Value to return if the metric does not exist. Defaults to None.
            step: Optional step number to retrieve a specific step

        Returns:
            Dict with ``key``, ``value``, ``step``, or ``default`` if not found

        Example:
            ```python
            run = dalva.init(project="my-project")
            run.log({"loss": 0.5}, step=0)
            run.log({"loss": 0.3}, step=1)
            run.get("loss")               # {"key": "loss", "value": 0.3, "step": 1}
            run.get("loss", step=0)       # {"key": "loss", "value": 0.5, "step": 0}
            run.get("missing")            # None
            run.get("missing", default=0) # 0
            # Works with nested/flattened keys too:
            run.log({"train": {"loss": 0.4}}, step=0)
            run.get("train/loss", step=0) # {"key": "train/loss", "value": 0.4, "step": 0}
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

        Raises ``ValueError`` on 409 Conflict if any key already exists.
        Use ``remove_config(key)`` first to overwrite.

        Args:
            config: Dictionary of config key -> value. Nested dicts are flattened
                with '/' as separator (e.g. ``{"optimizer": {"lr": 0.001}}`` becomes
                ``{"optimizer/lr": 0.001}``).

        Raises:
            ConnectionError: On server errors

        Example:
            ```python
            run = dalva.init(project="my-project")
            run.log_config({"lr": 0.001, "batch_size": 32})
            # To add more config later:
            run.log_config({"epochs": 100})  # succeeds if keys don't exist
            run.log_config({"lr": 0.01})     # raises ValueError — key exists
            run.remove_config("lr")
            run.log_config({"lr": 0.01})     # now succeeds
            ```
        """
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
            ConnectionError: On server errors (including 404 if key not found)

        Example:
            ```python
            run = dalva.init(project="my-project", config={"lr": 0.001})
            # To overwrite config:
            run.remove_config("lr")
            run.log_config({"lr": 0.01})  # succeeds after removal
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
            run = dalva.init(project="my-project", config={"lr": 0.001})
            run.get_config("lr")               # {"key": "lr", "value": 0.001}
            run.get_config("missing")          # None
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
            run = dalva.init(project="my-project")
            table = run.create_table(name="predictions", log_mode="IMMUTABLE")
            table.log(df)
            run.finish()  # auto-finishes table too
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

    def finish(self):
        """Finish the run and mark it as completed.

        All tables created via run.create_table() will be finished first.

        Example:
            ```python
            run = dalva.init(project="my-project")
            run.log({"loss": 0.5}, step=0)
            run.finish()
            ```
        """
        if self._finished:
            return
        for table in self._tables:
            if not table._finished:
                try:
                    table.finish()
                except Exception:
                    pass
        client = self._get_client()
        try:
            response = client.post(f"/api/runs/{self._db_id}/finish")
            response.raise_for_status()
            result = response.json()
            print(f"[Run] Run finished (state={result['state']})")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to finish run on server: {e}")
        finally:
            self._client = None
            self._finished = True

    def __repr__(self):
        """String representation."""
        return f"Run(project='{self.project_name}', name='{self.name}', id={self.run_id}, server={self._server_url})"
