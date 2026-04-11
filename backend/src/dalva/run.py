"""Run class for experiment tracking via HTTP."""

from typing import Mapping

import httpx


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
        resume: str | None = None,
        server_url: str = "http://localhost:8000",
    ):
        """
        Initialize a run by creating it on the server.

        Args:
            project: Project name
            name: Optional run name (user-defined, for display only)
            config: Optional configuration dictionary
            resume: run_id to resume (omit to create a new run)
            server_url: Server URL. Defaults to http://localhost:8000
        """
        self.project_name = project
        self.config = config or {}
        self._server_url = server_url
        self._client: httpx.Client | None = None

        # Verify server is accessible
        self._verify_server_connection()

        # Create run via API
        self._create_run_on_server(name=name, config=self.config, resume=resume)

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
        resume: str | None,
    ) -> None:
        """Create the run on the server via API."""
        client = self._get_client()
        payload = {
            "project": self.project_name,
            "name": name,
            "config": config,
            "resume": resume,
        }
        try:
            response = client.post("/api/runs/init", json=payload)
            response.raise_for_status()
            result = response.json()
            self._db_id = result["id"]
            self.run_id = result["run_id"]
            self.name = result.get("name")
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
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to log metrics to server: {e}")

    def finish(self):
        """Finish the run and mark it as completed.

        Example:
            ```python
            run = Run(project="my-project")
            run.log({"loss": 0.5}, step=0)
            run.finish()
            ```
        """
        client = self._get_client()
        try:
            response = client.post(f"/api/runs/{self._db_id}/finish")
            response.raise_for_status()
            result = response.json()
            print(f"[Run] Run finished (state={result['state']})")
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to finish run on server: {e}")
        finally:
            self._client = None

    def __repr__(self):
        """String representation."""
        return f"Run(project='{self.project_name}', name='{self.name}', id={self.run_id}, server={self._server_url})"
