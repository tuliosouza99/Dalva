"""Run class for experiment tracking via HTTP."""

from __future__ import annotations

from typing import Mapping

import httpx

from dalva.table import Table


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
        config: Mapping | None = None,
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

    def _verify_server_connection(self) -> None:
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
        self,
        name: str | None,
        config: Mapping | None,
        resume_from: str | None,
    ) -> None:
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

    def log(
        self, metrics: Mapping[str, bool | float | int | str], step: int | None = None
    ):
        """Log metrics to the run.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number for series values

        Example:
            ```python
            run = Run(project="my-project", config={"lr": 0.001})
            run.log({"accuracy": 0.85})
            for step in range(100):
                run.log({"loss": 0.5, "accuracy": 0.5}, step=step)
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
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to log metrics to server: {e}")

    def create_table(
        self,
        name: str | None = None,
        config: Mapping | None = None,
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
