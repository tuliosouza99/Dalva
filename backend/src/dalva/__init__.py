"""Dalva - Lightweight experiment tracker for deep learning."""

from dalva.run import Run
from dalva.table import Table

__version__ = "0.1.0"


def init(
    project: str,
    name: str | None = None,
    config: dict | None = None,
    resume_from: str | None = None,
    server_url: str = "http://localhost:8000",
) -> Run:
    """
    Initialize a new run.

    Args:
        project: Project name
        name: Optional run name (user-defined, for display purposes only)
        config: Optional configuration dictionary
        resume_from: run_id to resume (omit to create a new run)
        server_url: Server URL. Defaults to http://localhost:8000

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
        server_url=server_url,
    )


def table(
    project: str,
    name: str | None = None,
    config: dict | None = None,
    run_id: str | None = None,
    resume_from: str | None = None,
    server_url: str = "http://localhost:8000",
    log_mode: str | None = "IMMUTABLE",
) -> Table:
    """
    Initialize a new table.

    Args:
        project: Project name
        name: Optional table name (user-defined, for display purposes only)
        config: Optional configuration dictionary
        run_id: Optional run_id to link this table to a run
        resume_from: table_id to resume (omit to create a new table)
        server_url: Server URL. Defaults to http://localhost:8000
        log_mode: IMMUTABLE, MUTABLE, or INCREMENTAL

    Returns:
        Table object

    Example:
        ```python
        import dalva
        import pandas as pd
        table = dalva.table(project="my-project", name="my-table")
        table.log(pd.DataFrame({"col1": [1, 2, 3], "col2": ["a", "b", "c"]}))
        table.finish()
        ```
    """
    return Table(
        project=project,
        name=name,
        config=config,
        run_id=run_id,
        resume_from=resume_from,
        server_url=server_url,
        log_mode=log_mode,
    )
