"""Table class for tabular data tracking via HTTP."""

import json
from datetime import date, datetime
from typing import Mapping, Optional

import httpx
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors


def _is_na(v):
    return v is None or (isinstance(v, float) and v != v)


def _is_date(s: pd.Series) -> pd.Series:
    return s.map(lambda v: isinstance(v, (datetime, date)) if not _is_na(v) else True)


def _is_list(s: pd.Series) -> pd.Series:
    return s.map(
        lambda v: (
            isinstance(v, list) or (isinstance(v, str) and v.startswith("["))
            if not _is_na(v)
            else True
        )
    )


def _is_dict(s: pd.Series) -> pd.Series:
    return s.map(
        lambda v: (
            isinstance(v, dict) or (isinstance(v, str) and v.startswith("{"))
            if not _is_na(v)
            else True
        )
    )


_OBJECT_CHECKS = {
    "date": pa.Check(_is_date),
    "list": pa.Check(_is_list),
    "dict": pa.Check(_is_dict),
}


def _server_error(exc: httpx.HTTPStatusError) -> str:
    """Extract server error detail from an HTTPStatusError."""
    try:
        body = exc.response.json()
        detail = body.get("detail", str(exc))
    except Exception:
        detail = str(exc)
    return f"Server error {exc.response.status_code}: {detail}"


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
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
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
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
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

    def _infer_type(self, col_name: str, dtype, non_null: "pd.Series") -> str:
        """Infer column type name from pandas dtype and sample."""
        if dtype == "object":
            sample = non_null.iloc[0] if len(non_null) > 0 else None
            if sample is None:
                return "str"
            elif isinstance(sample, (list, dict)):
                return "list" if isinstance(sample, list) else "dict"
            elif isinstance(sample, date):
                return "date"
            else:
                return "str"
        elif dtype == "bool" or pd.api.types.is_bool_dtype(dtype):
            return "bool"
        elif pd.api.types.is_integer_dtype(dtype):
            return "int"
        elif pd.api.types.is_float_dtype(dtype):
            return "float"
        return "str"

    def _build_schema(
        self, df: "pd.DataFrame"
    ) -> tuple[pa.DataFrameSchema, list[dict]]:
        """Build a pandera DataFrameSchema from the DataFrame."""
        columns = {}
        column_schema = []

        for col_name in df.columns:
            non_null = df[col_name].dropna()
            inferred = self._infer_type(col_name, df[col_name].dtype, non_null)

            if inferred not in self.ALLOWED_TYPES:
                raise ValueError(
                    f"Column '{col_name}' has unsupported type: {inferred}"
                )

            column_schema.append({"name": col_name, "type": inferred})

            if inferred in _OBJECT_CHECKS:
                columns[col_name] = pa.Column(
                    "object", nullable=True, checks=_OBJECT_CHECKS[inferred]
                )
            else:
                columns[col_name] = pa.Column(inferred, nullable=True)

        return pa.DataFrameSchema(columns), column_schema

    def _validate_dataframe(
        self, df: "pd.DataFrame"
    ) -> tuple["pd.DataFrame", list[dict]]:
        """Validate DataFrame using pandera.

        Returns:
            Tuple of (validated_df, column_schema)
        """
        schema, column_schema = self._build_schema(df)
        try:
            validated_df = schema.validate(df, lazy=True)
        except SchemaErrors as e:
            msgs = []
            for _, row in e.failure_cases.iterrows():
                col = row.get("column", "?")
                msg = row.get("check", "?")
                msgs.append(f"Column '{col}' {msg}")
            raise ValueError(f"DataFrame validation failed: {'; '.join(msgs)}")
        return validated_df, column_schema

    def _serialize_rows(self, df: "pd.DataFrame"):
        """Serialize DataFrame rows as JSON string for API payload."""
        return df.to_json(orient="records", date_format="iso")

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

        validated_df, column_schema = self._validate_dataframe(df)
        rows_json = self._serialize_rows(validated_df)
        payload = f'{{"rows":{rows_json},"column_schema":{json.dumps(column_schema)}}}'

        try:
            response = client.post(
                f"/api/tables/{self._db_id}/log",
                content=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            self._version = result["version"]
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
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
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(f"Failed to finish table on server: {e}")
        finally:
            self._client = None
            self._finished = True

    def __repr__(self) -> str:
        """String representation."""
        return f"Table(project='{self.project_name}', name='{self.name}', id={self.table_id}, server={self._server_url})"
