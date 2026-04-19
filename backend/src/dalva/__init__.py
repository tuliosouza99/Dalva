"""Dalva - Lightweight experiment tracker for deep learning."""

from pathlib import Path

from dalva.sdk.errors import DalvaError
from dalva.sdk.run import Run
from dalva.sdk.schema import DalvaSchema
from dalva.sdk.table import Table

__all__ = ["DalvaError", "DalvaSchema", "Run", "Table", "init", "table"]


def init(
    project: str,
    name: str | None = None,
    config: dict | None = None,
    resume_from: str | None = None,
    fork_from: str | None = None,
    copy_tables_on_fork: bool | list[int] = False,
    server_url: str = "http://localhost:8000",
    outbox_dir: Path | None = None,
    http_timeout: float | None = None,
) -> Run:
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
        server_url: Server URL. Defaults to http://localhost:8000
        outbox_dir: Directory for WAL files. Defaults to ~/.dalva/outbox/
        http_timeout: HTTP timeout in seconds. Defaults to None (no timeout).

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
    return Run(
        project=project,
        name=name,
        config=config,
        resume_from=resume_from,
        fork_from=fork_from,
        copy_tables_on_fork=copy_tables_on_fork,
        server_url=server_url,
        outbox_dir=outbox_dir,
        http_timeout=http_timeout,
    )


def table(
    project: str,
    schema: type[DalvaSchema] | None = None,
    name: str | None = None,
    config: dict | None = None,
    run_id: str | None = None,
    resume_from: str | None = None,
    server_url: str = "http://localhost:8000",
    outbox_dir: Path | None = None,
    http_timeout: float | None = None,
) -> Table:
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
        server_url: Server URL. Defaults to http://localhost:8000
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
    return Table(
        project=project,
        schema=schema,
        name=name,
        config=config,
        run_id=run_id,
        resume_from=resume_from,
        server_url=server_url,
        outbox_dir=outbox_dir,
        http_timeout=http_timeout,
    )
