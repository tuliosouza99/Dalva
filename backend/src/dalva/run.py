"""Run class for experiment tracking."""

from datetime import datetime
from typing import Any

from dalva.db.connection import init_db
from dalva.services.logger import LoggingService


class Run:
    """Run object for tracking experiments."""

    def __init__(
        self,
        project: str,
        name: str | None = None,
        config: dict | None = None,
        resume: str | None = None,
    ):
        """
        Initialize a run.

        Args:
            project: Project name
            name: Optional run name (user-defined, for display only)
            config: Optional configuration dictionary
            resume: run_id to resume (omit to create a new run)
        """
        self.project_name = project
        self.config = config or {}
        self._step_counter = 0

        # Ensure database and tables exist
        init_db()

        # Create run in database
        logger = LoggingService()
        db_id, run_id_str, descriptive_name = logger.create_run(
            project_name=project,
            run_name=name,
            config=self.config,
            resume_run_id=resume,
        )

        # Store identifiers
        self._db_id = db_id
        self.run_id = run_id_str
        self.name = descriptive_name

    def log(self, metrics: dict[str, Any], step: int | None = None):
        """Log metrics to the run.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number (auto-incremented if not provided)
        """
        if step is None:
            step = self._step_counter
            self._step_counter += 1

        LoggingService().log_metrics(
            run_id=self._db_id,
            metrics=metrics,
            step=step,
            timestamp=datetime.utcnow(),
        )

    def finish(self):
        """Finish the run and mark it as completed."""
        LoggingService().finish_run(self._db_id)

    def __repr__(self):
        """String representation."""
        return f"Run(project='{self.project_name}', name='{self.name}', id={self.run_id})"
