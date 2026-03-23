"""Run class for experiment tracking."""

from datetime import datetime
from pathlib import Path
from typing import Any

from dalva.config import load_config
from dalva.db.connection import init_db
from dalva.s3.sync import sync_from_s3, sync_to_s3
from dalva.services.logger import LoggingService


def _require_s3_config(action: str) -> None:
    """Raise a clear error if S3 is not configured."""
    config = load_config()
    if not config.database.s3_bucket:
        raise ValueError(
            f"{action} requires S3 to be configured. "
            "Run 'dalva config s3 --bucket <name>' first and make sure your "
            "AWS credentials are set (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY)."
        )


class Run:
    """Run object for tracking experiments."""

    def __init__(
        self,
        project: str,
        name: str | None = None,
        config: dict | None = None,
        resume: str | None = None,
        pull: bool = False,
        push: bool = False,
    ):
        """
        Initialize a run.

        Args:
            project: Project name
            name: Optional run name (user-defined, for display only)
            config: Optional configuration dictionary
            resume: run_id to resume (omit to create a new run)
            pull: If True, download the database from S3 before starting.
            push: If True, upload the database to S3 when the run finishes.
        """
        self.project_name = project
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

        # Optional S3 push after finishing
        if self._push:
            db_config = load_config()
            db_path = Path(db_config.database.db_path).expanduser()
            print(f"Pushing database to S3 ← {db_path} ...")
            sync_to_s3(source=db_path)
            print("✓ Push complete")

    def __repr__(self):
        """String representation."""
        return f"Run(project='{self.project_name}', name='{self.name}', id={self.run_id})"
