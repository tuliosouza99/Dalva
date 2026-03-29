"""
Dalva - Lightweight experiment tracker for deep learning.
"""

from dalva.run import Run

__version__ = "0.1.0"


def init(
    project: str,
    name: str | None = None,
    config: dict | None = None,
    resume: str | None = None,
    server_url: str = "http://localhost:8000",
) -> Run:
    """
    Initialize a new run.

    Args:
        project: Project name
        name: Optional run name (user-defined, for display purposes only)
        config: Optional configuration dictionary
        resume: run_id to resume (omit to create a new run)
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
        resume=resume,
        server_url=server_url,
    )
