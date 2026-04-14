"""Table class for tabular data tracking via HTTP."""

from __future__ import annotations

import atexit
import json
import warnings
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import httpx
import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors

from ..types import InputDict
from .wal import WALManager
from .worker import PendingRequest, SyncWorker


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
    try:
        body = exc.response.json()
        detail = body.get("detail", str(exc))
    except Exception:
        detail = str(exc)
    return f"Server error {exc.response.status_code}: {detail}"


class Table:
    """Table object for tracking tabular data via HTTP.

    ``log()`` calls are asynchronous — they return immediately and are
    sent to the server in the background. Errors from failed requests are
    accumulated and reported when ``flush()`` or ``finish()`` is called.

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
        config: InputDict | None = None,
        run_id: str | None = None,
        resume_from: str | None = None,
        server_url: str = "http://localhost:8000",
        log_mode: Optional[str] = "IMMUTABLE",
        outbox_dir: Path | None = None,
    ):
        self.project_name = project
        self.config = config or {}
        self._server_url = server_url
        self._client: httpx.Client | None = None
        self._worker: SyncWorker | None = None
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

        self._wal = WALManager("table", self._db_id, outbox_dir=outbox_dir)
        self._worker = SyncWorker(server_url, wal_manager=self._wal)
        atexit.register(self._atexit_handler)

        print(f"Table created: {self.table_id}")

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
            print(f"[Table] Server health check OK: {self._server_url}")
        except httpx.HTTPStatusError as e:
            raise ConnectionError(_server_error(e))
        except httpx.HTTPError as e:
            raise ConnectionError(
                f"Cannot connect to Dalva server at {self._server_url}. "
                f"Please ensure the server is running. Error: {e}"
            )

    def _get_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self._server_url, timeout=30)
        return self._client

    def _create_table_on_server(
        self,
        name: str | None,
        config: InputDict | None,
        resume_from: str | None,
        log_mode: str,
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

    def _infer_type(self, dtype, non_null: pd.Series) -> str:
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

    def _build_schema(self, df: pd.DataFrame) -> tuple[pa.DataFrameSchema, list[dict]]:
        columns = {}
        column_schema = []

        for col_name in df.columns:
            non_null = df.loc[:, col_name].dropna()
            inferred = self._infer_type(df[col_name].dtype, non_null)

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

    def _validate_dataframe(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
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
        return df.to_json(orient="records", date_format="iso")

    def log(self, df: pd.DataFrame) -> None:
        """Log a pandas DataFrame to the table (async — returns immediately).

        Data is validated locally, then enqueued for background delivery.
        Errors are accumulated and reported by ``flush()`` or ``finish()``.

        Args:
            df: pandas DataFrame with columns of type int, float, bool, str, date, list, or dict

        Example:
            ```python
            table.log(pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]}))
            ```
        """
        if self._finished:
            raise RuntimeError("Cannot log to a finished table")

        validated_df, column_schema = self._validate_dataframe(df)
        rows_json = self._serialize_rows(validated_df)
        payload = f'{{"rows":{rows_json},"column_schema":{json.dumps(column_schema)}}}'

        request = PendingRequest(
            method="POST",
            url=f"/api/tables/{self._db_id}/log",
            payload=payload,
            headers={"Content-Type": "application/json"},
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

    def finish(self, on_error: str = "warn", timeout: float = 120) -> None:
        """Finish the table and mark it as completed.

        Args:
            on_error: How to handle accumulated errors from failed ``log()``
                calls. ``"warn"`` (default) prints warnings. ``"raise"`` raises
                a RuntimeError wrapping all accumulated errors.
            timeout: Maximum seconds to wait for the worker queue to drain.

        Raises:
            ConnectionError: If the finish request itself fails.

        Example:
            ```python
            table.log(df)
            table.finish()
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
                        label="Finishing table", timeout=timeout
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

            client = self._get_client()
            response = client.post(f"/api/tables/{self._db_id}/finish")
            response.raise_for_status()
            result = response.json()
            print(f"[Table] Table finished (state={result['state']})")
            self._finished = True

            if self._worker is not None:
                self._worker.wal_delete()

            if errors:
                if on_error == "raise":
                    msgs = [f"  {req.method} {req.url}: {exc}" for req, exc in errors]
                    raise RuntimeError(
                        f"{len(errors)} request(s) failed during table:\n"
                        + "\n".join(msgs)
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
