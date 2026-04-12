"""Table class for tabular data tracking via HTTP."""

import json
from datetime import date, datetime
from typing import TYPE_CHECKING, Mapping, Optional

import httpx
import numpy as np

if TYPE_CHECKING:
    import pandas as pd


class Table:
    """Table object for tracking tabular data via HTTP.

    All operations are performed via HTTP requests to the server.
    No local database operations are performed.

    Example:
        ```python
        import pandas as pd
        import dalva

        table = dalva.table(project="my-project", name="my-table")
        df = pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]})
        table.log(df)
        table.finish()
        ```
    """

    ALLOWED_TYPES = {"int", "float", "bool", "str", "date", "list", "dict"}

    def __init__(
        self,
        project: str,
        name: str | None = None,
        config: Mapping | None = None,
        run_id: str | None = None,
        resume_from: str | None = None,
        server_url: str = "http://localhost:8000",
        log_mode: Optional[str] = "IMMUTABLE",
    ):
        """
        Initialize a table by creating it on the server.

        Args:
            project: Project name
            name: Optional table name (user-defined, for display only)
            config: Optional configuration dictionary
            run_id: Optional run_id to link this table to a run
            resume_from: table_id to resume (omit to create a new table)
            server_url: Server URL. Defaults to http://localhost:8000
            log_mode: IMMUTABLE, MUTABLE, or INCREMENTAL
        """
        self.project_name = project
        self.config = config or {}
        self._server_url = server_url
        self._client: httpx.Client | None = None
        self._log_mode = log_mode or "IMMUTABLE"
        self._run_id = run_id
        self._run_db_id: int | None = None
        self._finished: bool = False

        self._verify_server_connection()

        self._create_table_on_server(
            name=name,
            config=self.config,
            resume_from=resume_from,
            log_mode=self._log_mode,
        )

        print(f"Table created: {self.table_id}")

    def _verify_server_connection(self) -> None:
        """Verify server is accessible via health check endpoint."""
        try:
            response = httpx.get(f"{self._server_url}/api/health", timeout=10)
            response.raise_for_status()
            print(f"[Table] Server health check OK: {self._server_url}")
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

    def _create_table_on_server(
        self,
        name: str | None,
        config: Mapping | None,
        resume_from: str | None,
        log_mode: str,
    ) -> None:
        """Create the table on the server via API."""
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

        payload = {
            "project": self.project_name,
            "name": name,
            "config": config,
            "run_id": run_db_id,
            "log_mode": log_mode,
            "resume_from": resume_from,
        }
        try:
            response = client.post("/api/tables/init", json=payload)
            response.raise_for_status()
            result = response.json()
            self._db_id = result["id"]
            self.table_id = result["table_id"]
            self.name = result.get("name")
            self._log_mode = result.get("log_mode", log_mode)
            self._version = result.get("version", 0)
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to create table on server: {e}")

    def _resolve_project_id(self) -> int | None:
        """Resolve project name to project ID."""
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

    def _validate_dataframe(self, df) -> tuple[list[dict], list[dict]]:
        """Validate DataFrame and convert to records.

        Returns:
            Tuple of (rows, column_schema)
        """
        import pandas as pd

        rows = []
        column_schema = []

        for col_name in df.columns:
            col = df[col_name]
            dtype = col.dtype

            if dtype == "object":
                sample = col.dropna().iloc[0] if len(col.dropna()) > 0 else None
                if isinstance(sample, (list, dict)):
                    inferred_type = "list" if isinstance(sample, list) else "dict"
                elif isinstance(
                    sample, datetime
                ) or pd.api.types.is_datetime64_any_dtype(dtype):
                    inferred_type = "date"
                else:
                    inferred_type = "str"
            elif dtype == "bool" or pd.api.types.is_bool_dtype(dtype):
                inferred_type = "bool"
            elif pd.api.types.is_integer_dtype(dtype):
                inferred_type = "int"
            elif pd.api.types.is_float_dtype(dtype):
                inferred_type = "float"
            else:
                inferred_type = "str"

            if inferred_type not in self.ALLOWED_TYPES:
                raise ValueError(
                    f"Column '{col_name}' has unsupported type: {inferred_type}"
                )

            column_schema.append({"name": col_name, "type": inferred_type})

        for _, row in df.iterrows():
            record = {}
            for col_name, schema_col in zip(df.columns, column_schema):
                val = row[col_name]
                if pd.isna(val) or val is None:
                    record[col_name] = None
                elif schema_col["type"] == "date":
                    if isinstance(val, datetime):
                        record[col_name] = val.isoformat()
                    elif isinstance(val, date):
                        record[col_name] = val.isoformat()
                    else:
                        record[col_name] = str(val)
                elif schema_col["type"] in ("list", "dict"):
                    record[col_name] = (
                        json.dumps(val) if isinstance(val, (list, dict)) else val
                    )
                else:
                    if isinstance(val, (np.integer, np.floating, np.bool_)):
                        val = val.item()
                    record[col_name] = val
            rows.append(record)

        for i, col_schema in enumerate(column_schema):
            col = df.iloc[:, i]
            non_null = col.dropna()
            if len(non_null) > 0:
                sample = non_null.iloc[0]
                inferred = col_schema["type"]

                def check_type(v, t):
                    if t == "int":
                        return isinstance(v, int) and not isinstance(v, bool)
                    if t == "float":
                        return isinstance(v, float)
                    if t == "bool":
                        return isinstance(v, bool)
                    if t == "str":
                        return isinstance(v, str)
                    if t == "date":
                        return isinstance(v, (datetime, date, str))
                    if t == "list":
                        return isinstance(v, list) or (
                            isinstance(v, str) and v.startswith("[")
                        )
                    if t == "dict":
                        return isinstance(v, dict) or (
                            isinstance(v, str) and v.startswith("{")
                        )
                    return False

                for v in non_null:
                    if not check_type(v, inferred):
                        raise ValueError(
                            f"Column '{col_schema['name']}' has mixed types. "
                            f"Expected {inferred}, got {type(v).__name__}"
                        )

        return rows, column_schema

    def log(self, df: "pd.DataFrame") -> None:
        """Log a pandas DataFrame to the table.

        Args:
            df: pandas DataFrame with columns of type int, float, bool, str, date, list, or dict

        Example:
            ```python
            import pandas as pd
            table = Table(project="my-project", name="my-table")
            table.log(pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]}))
            table.finish()
            ```
        """
        client = self._get_client()

        rows, column_schema = self._validate_dataframe(df)

        payload = {
            "rows": rows,
            "column_schema": column_schema,
        }
        try:
            response = client.post(f"/api/tables/{self._db_id}/log", json=payload)
            response.raise_for_status()
            result = response.json()
            self._version = result["version"]
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to log data to server: {e}")

    def finish(self) -> None:
        """Finish the table and mark it as completed.

        Example:
            ```python
            table = Table(project="my-project", name="my-table")
            table.log(df)
            table.finish()
            ```
        """
        if self._finished:
            return
        client = self._get_client()
        try:
            response = client.post(f"/api/tables/{self._db_id}/finish")
            response.raise_for_status()
            result = response.json()
            print(f"[Table] Table finished (state={result['state']})")
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to finish table on server: {e}")
        finally:
            self._client = None
            self._finished = True

    def __repr__(self) -> str:
        """String representation."""
        return f"Table(project='{self.project_name}', name='{self.name}', id={self.table_id}, server={self._server_url})"
