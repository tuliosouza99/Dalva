"""
TrackAI - Lightweight experiment tracker for deep learning.
"""

from trackai.run import Run

__version__ = "0.1.0"


def init(
    project: str,
    name: str | None = None,
    config: dict | None = None,
    resume: str | None = None,
    pull: bool = False,
    push: bool = False,
) -> Run:
    """
    Initialize a new run.

    Args:
        project: Project name
        name: Optional run name (user-defined, for display purposes only)
        config: Optional configuration dictionary
        resume: run_id to resume (omit to create a new run)
        pull: If True, download the database from S3 before starting the run.
        push: If True, upload the database to S3 after the run finishes.

    Returns:
        Run object

    Example:
        ```python
        import trackai
        run = trackai.init(project="my-project", config={"lr": 0.001})
        run.log({"loss": 0.5}, step=0)
        run.finish()
        ```
    """
    return Run(
        project=project,
        name=name,
        config=config,
        resume=resume,
        pull=pull,
        push=push,
    )
