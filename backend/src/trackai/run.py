"""Run class for experiment tracking."""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from trackai.config import load_config
from trackai.db.connection import init_db
from trackai.db.schema import Run as DBRun
from trackai.s3.sync import sync_from_s3, sync_to_s3
from trackai.services.logger import LoggingService


def _require_s3_config(action: str) -> None:
    """Raise a clear error if S3 is not configured."""
    config = load_config()
    if not config.database.s3_bucket:
        raise ValueError(
            f"{action} requires S3 to be configured. "
            "Run 'trackai config s3 --bucket <name>' first and make sure your "
            "AWS credentials are set (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)."
        )


class Run:
    """
    Run object for tracking experiments.

    Compatible with trackio.Run API.
    """

    def __init__(
        self,
        project: str,
        name: Optional[str] = None,
        group: Optional[str] = None,
        config: Optional[dict] = None,
        resume: str = "never",
        pull: bool = False,
        push: bool = False,
        **kwargs,
    ):
        """
        Initialize a run.

        Args:
            project: Project name
            name: Optional run name (auto-generated if not provided)
            group: Optional group name for organizing runs
            config: Optional configuration dictionary
            resume: Resume mode ("never", "allow", "must")
            pull: If True, download the database from S3 before starting.
                  Requires S3 to be configured (``trackai config s3``).
                  Useful to pick up runs logged on other machines.
            push: If True, upload the database to S3 when the run finishes.
                  Requires S3 to be configured (``trackai config s3``).
            **kwargs: Additional arguments (for compatibility)
        """
        self.project_name = project
        self.run_name = name
        self.group_name = group
        self.config = config or {}
        self._step_counter = 0
        self._push = push

        db_config = load_config()

        # Optional S3 pull before starting
        if pull:
            _require_s3_config("pull=True")
            db_path = Path(db_config.database.db_path).expanduser()
            print(f"Pulling database from S3 → {db_path} ...")
            sync_from_s3(destination=db_path)
            print("✓ Pull complete")

        # Validate push config eagerly so we fail fast, not at finish()
        if push:
            _require_s3_config("push=True")

        # Ensure database and tables exist
        init_db()

        # Initialize logging service
        self._logger = LoggingService()

        # Create run in database
        self._db_run = self._logger.create_run(
            project_name=project,
            run_name=name,
            group=group,
            config=config,
            resume=resume,
        )

        # Update run_name to actual name (in case it was auto-generated)
        self.run_name = self._db_run.run_id
        self.run_id = self._db_run.id

    def log(self, metrics: dict[str, Any], step: Optional[int] = None):
        """
        Log metrics to the run.

        Args:
            metrics: Dictionary of metric name -> value
            step: Optional step number (auto-incremented if not provided)
        """
        if step is None:
            step = self._step_counter
            self._step_counter += 1

        self._logger.log_metrics(
            run_id=self.run_id,
            metrics=metrics,
            step=step,
            timestamp=datetime.utcnow(),
        )

    def log_system(self, metrics: dict[str, Any]):
        """
        Log system metrics (GPU, etc.) without a step number.

        These metrics use timestamps for the x-axis instead of steps.

        Args:
            metrics: Dictionary of system metrics
        """
        self._logger.log_metrics(
            run_id=self.run_id,
            metrics=metrics,
            step=None,
            timestamp=datetime.utcnow(),
        )

    def finish(self):
        """Finish the run and mark it as completed."""
        self._logger.finish_run(self.run_id)
        self._logger.close()

        # Optional S3 push after finishing
        if self._push:
            db_config = load_config()
            db_path = Path(db_config.database.db_path).expanduser()
            print(f"Pushing database to S3 ← {db_path} ...")
            sync_to_s3(source=db_path)
            print("✓ Push complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - automatically finish the run."""
        if exc_type is None:
            self.finish()
        else:
            run = self._logger.db.query(DBRun).filter(DBRun.id == self.run_id).first()
            if run:
                run.state = "failed"
                self._logger.db.commit()
            self._logger.close()
        return False

    def __repr__(self):
        """String representation."""
        return f"Run(project='{self.project_name}', name='{self.run_name}', id={self.run_id})"
