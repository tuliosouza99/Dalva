"""Dalva - Lightweight experiment tracker for deep learning."""

import os
from pathlib import Path

from dalva.sdk.errors import DalvaError
from dalva.sdk.journal import Durability
from dalva.sdk.local import JournalRun, JournalTable
from dalva.sdk.run import Run
from dalva.sdk.schema import DalvaSchema
from dalva.sdk.table import Table

__all__ = [
    "DalvaError",
    "DalvaSchema",
    "JournalRun",
    "JournalTable",
    "Run",
    "Table",
    "init",
    "table",
]


def init(
    project: str,
    name: str | None = None,
    config: dict | None = None,
    resume_from: str | None = None,
    fork_from: str | None = None,
    copy_tables_on_fork: bool | list[int] = False,
    server_url: str | None = None,
    outbox_dir: Path | None = None,
    http_timeout: float | None = None,
    sync: str | Path | None = None,
    runs_dir: Path | None = None,
    durability: Durability = "balanced",
    segment_bytes: int = 256 * 1024,
    segment_interval: float = 0.5,
) -> Run | JournalRun:
    """
    Initialize a new run.

    Args:
        project: Project name
        name: Optional run name (user-defined, for display purposes only)
        config: Optional configuration dictionary
        resume_from: run_id to resume (omit to create a new run)
        fork_from: run_id to fork from (creates a copy with configs/metrics)
        copy_tables_on_fork: False (no tables), True (all tables), or list of table IDs.
            Only used when fork_from is set.
        server_url: Optional legacy HTTP server URL. When omitted, Dalva runs
            daemonlessly and journals events on local disk.
        outbox_dir: Directory for WAL files. Defaults to ~/.dalva/outbox/
        http_timeout: HTTP timeout in seconds. Defaults to None (no timeout).
        sync: Optional daemonless replication target. Supports local paths,
            ``file://`` URIs, and ``s3://bucket/prefix`` URIs.
        runs_dir: Local daemonless journal root. Defaults to ~/.dalva/runs/.
        durability: ``balanced`` flushes each event to the OS; ``strict`` also
            fsyncs every event before ``log()`` returns.

    Returns:
        Run object

    Example:
        ```python
        import dalva
        run = dalva.init(project="my-project", config={"lr": 0.001})
        run.log({"loss": 0.5}, step=0)
        run.finish()
        ```
    """
    resolved_server = server_url or os.getenv("DALVA_SERVER_URL")
    if resolved_server:
        return Run(
            project=project,
            name=name,
            config=config,
            resume_from=resume_from,
            fork_from=fork_from,
            copy_tables_on_fork=copy_tables_on_fork,
            server_url=resolved_server,
            outbox_dir=outbox_dir,
            http_timeout=http_timeout,
        )
    return JournalRun(
        project=project,
        name=name,
        config=config,
        resume_from=resume_from,
        fork_from=fork_from,
        copy_tables_on_fork=copy_tables_on_fork,
        sync=sync,
        runs_dir=runs_dir,
        durability=durability,
        segment_bytes=segment_bytes,
        segment_interval=segment_interval,
    )


def table(
    project: str,
    schema: type[DalvaSchema] | None = None,
    name: str | None = None,
    config: dict | None = None,
    run_id: str | None = None,
    resume_from: str | None = None,
    server_url: str | None = None,
    outbox_dir: Path | None = None,
    http_timeout: float | None = None,
    sync: str | Path | None = None,
    runs_dir: Path | None = None,
    durability: Durability = "balanced",
    segment_bytes: int = 256 * 1024,
    segment_interval: float = 0.5,
) -> Table | JournalTable:
    """
    Initialize a new table or resume an existing one.

    Args:
        project: Project name
        schema: A DalvaSchema subclass defining the table columns. Required unless
            resuming an existing table via ``resume_from``.
        name: Optional table name (user-defined, for display purposes only)
        config: Optional configuration dictionary
        run_id: Optional run_id to link this table to a run
        resume_from: table_id to resume (omit to create a new table)
        server_url: Optional legacy HTTP server URL. Omit for daemonless mode.
        outbox_dir: Directory for WAL files. Defaults to ~/.dalva/outbox/
        http_timeout: HTTP timeout in seconds. Defaults to None (no timeout).

    Returns:
        Table object

    Example:
        ```python
        import dalva

        class MySchema(dalva.DalvaSchema):
            name: str
            score: float

        t = dalva.table(project="my-project", schema=MySchema)
        t.log_row({"name": "test", "score": 0.5})
        t.finish()
        ```
    """
    resolved_server = server_url or os.getenv("DALVA_SERVER_URL")
    if resolved_server:
        return Table(
            project=project,
            schema=schema,
            name=name,
            config=config,
            run_id=run_id,
            resume_from=resume_from,
            server_url=resolved_server,
            outbox_dir=outbox_dir,
            http_timeout=http_timeout,
        )
    return JournalTable(
        project=project,
        schema=schema,
        name=name,
        config=config,
        run_id=run_id,
        resume_from=resume_from,
        sync_target=sync,
        runs_dir=runs_dir,
        durability=durability,
        segment_bytes=segment_bytes,
        segment_interval=segment_interval,
    )
