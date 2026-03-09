"""
TrackAI - Lightweight experiment tracker for deep learning.

Compatible with trackio API for easy migration.
"""

from typing import Any, Optional
from trackai.run import Run

__version__ = "0.1.0"

# Global state for current run
_current_run: Optional[Run] = None


def init(
    project: str,
    name: Optional[str] = None,
    group: Optional[str] = None,
    config: Optional[dict] = None,
    resume: str = "never",
    pull: bool = False,
    push: bool = False,
    **kwargs,
) -> Run:
    """
    Initialize a new run.

    Args:
        project: Project name
        name: Optional run name (auto-generated if not provided)
        group: Optional group name for organizing runs
        config: Optional configuration dictionary
        resume: Resume mode ("never", "allow", "must")
        pull: If True, download the database from S3 before starting the run.
              Requires S3 to be configured (``trackai config s3``).
        push: If True, upload the database to S3 after the run finishes.
              Requires S3 to be configured (``trackai config s3``).
        **kwargs: Additional arguments (for compatibility with trackio)

    Returns:
        Run object

    Example:
        >>> import trackai
        >>> run = trackai.init(project="my-project", config={"lr": 0.001})
        >>> trackai.log({"loss": 0.5}, step=0)
        >>> trackai.finish()
    """
    global _current_run

    _current_run = Run(
        project=project,
        name=name,
        group=group,
        config=config,
        resume=resume,
        pull=pull,
        push=push,
        **kwargs,
    )

    return _current_run


def log(metrics: dict[str, Any], step: Optional[int] = None):
    """
    Log metrics to the current run.

    Args:
        metrics: Dictionary of metric name -> value
        step: Optional step number (auto-incremented if not provided)

    Raises:
        RuntimeError: If no run is active

    Example:
        >>> trackai.log({"loss": 0.5, "accuracy": 0.8}, step=0)
    """
    if _current_run is None:
        raise RuntimeError("No active run. Call trackai.init() first.")

    _current_run.log(metrics, step)


def log_system(metrics: dict[str, Any]):
    """
    Log system metrics (GPU, etc.) to the current run.

    These metrics use timestamps for the x-axis instead of steps.

    Args:
        metrics: Dictionary of system metrics

    Raises:
        RuntimeError: If no run is active

    Example:
        >>> trackai.log_system({"gpu_utilization": 0.95, "memory_used": 8192})
    """
    if _current_run is None:
        raise RuntimeError("No active run. Call trackai.init() first.")

    _current_run.log_system(metrics)


def finish():
    """
    Finish the current run and mark it as completed.

    Example:
        >>> trackai.finish()
    """
    global _current_run

    if _current_run is not None:
        _current_run.finish()
        _current_run = None


# Export public API
__all__ = [
    "Run",
    "init",
    "log",
    "log_system",
    "finish",
    "__version__",
]
