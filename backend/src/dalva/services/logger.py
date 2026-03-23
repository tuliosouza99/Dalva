"""Logging service for database operations.

Design principle — short-lived connections
------------------------------------------
DuckDB only allows **one writer per file** across OS processes.  If we hold a
session open for the entire training run (the old design), the FastAPI server
cannot connect while training is in progress and the UI goes dark.

Every public method here opens a *fresh* session via ``session_scope()``,
performs its work, commits, and immediately closes the connection.  The
DuckDB write lock is therefore held for only a few milliseconds per call,
leaving the file free for the API server between log steps.
"""

import hashlib
import json
import re
import time
from datetime import datetime
from typing import Any, Optional

from dalva.db.connection import session_scope
from dalva.db.schema import Config, Metric, Project, Run


def _generate_abbreviation(project_name: str) -> str:
    """Generate a 3-letter uppercase abbreviation from project name."""

    # Remove special characters and split
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", project_name)
    words = re.split(r"[-_\s]+", clean)
    words = [w for w in words if w]

    if not words:
        return "RUN"

    # Use first letter of up to 3 words, or first 3 chars of first word
    if len(words) >= 3:
        abbrev = "".join(w[0] for w in words[:3])
    elif len(words) == 1:
        abbrev = words[0][:3]
    else:
        abbrev = words[0][0] + words[1][0] + (words[0][1] if len(words[0]) > 1 else "X")

    return abbrev.upper().ljust(3, "X")[:3]


class LoggingService:
    """Service for logging experiment data to the database.

    Stateless by design: no persistent session is stored.  Each method opens
    its own short-lived connection, commits, and closes immediately.
    """

    # ------------------------------------------------------------------
    # Project helpers
    # ------------------------------------------------------------------

    def get_or_create_project(self, project_name: str) -> int:
        """Return the *id* of the project, creating it if it doesn't exist.

        Returns an integer ID rather than the ORM object so the caller never
        accidentally holds a reference tied to a closed session.
        """
        with session_scope() as db:
            project = db.query(Project).filter(Project.name == project_name).first()
            if not project:
                project_id = f"{project_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
                project = Project(name=project_name, project_id=project_id)
                db.add(project)
                db.flush()  # populate project.id before commit
            return project.id

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def create_run(
        self,
        project_name: str,
        run_name: Optional[str] = None,
        config: Optional[dict] = None,
        resume_run_id: Optional[str] = None,
    ) -> tuple[int, str, Optional[str]]:
        """Create or resume a run.

        Args:
            project_name: Name of the project
            run_name: Optional run name (user-defined, for display only)
            config: Optional configuration dict
            resume_run_id: run_id to resume (omit to create a new run)

        Returns:
            Tuple of (internal_db_id, run_id_string, descriptive_name)
        """
        with session_scope() as db:
            # Resolve project
            project = db.query(Project).filter(Project.name == project_name).first()
            if not project:
                project_id_str = f"{project_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
                project = Project(name=project_name, project_id=project_id_str)
                db.add(project)
                db.flush()

            project_db_id = project.id

            # Resume existing run if resume_run_id is provided
            if resume_run_id:
                existing = (
                    db.query(Run)
                    .filter(
                        Run.project_id == project_db_id, Run.run_id == resume_run_id
                    )
                    .first()
                )
                if existing:
                    existing.state = "running"
                    existing.updated_at = datetime.utcnow()
                    db.flush()
                    return existing.id, existing.run_id, existing.name
                raise ValueError(
                    f"Run '{resume_run_id}' not found in project '{project_name}'"
                )

            # Create new run with auto-generated run_id
            abbrev = _generate_abbreviation(project_name)
            run_count = db.query(Run).filter(Run.project_id == project_db_id).count()
            run_id_str = f"{abbrev}-{run_count + 1}"

            # Simple creation - run_id is guaranteed unique by construction
            run = Run(
                project_id=project_db_id,
                run_id=run_id_str,
                name=run_name,
                state="running",
            )
            db.add(run)
            db.flush()
            run_db_id = run.id

        # Store config in a separate session
        if config:
            self._log_config(run_db_id, config)

        return run_db_id, run_id_str, run_name

    def _log_config(self, run_id: int, config: dict, prefix: str = "") -> None:
        """Recursively persist configuration key-value pairs."""
        # Flatten nested dicts first, then write in one session
        flat: dict[str, Any] = {}
        self._flatten(config, prefix, flat)

        with session_scope() as db:
            for key, value in flat.items():
                db.add(Config(run_id=run_id, key=key, value=json.dumps(value)))

    def _flatten(self, d: dict, prefix: str, out: dict) -> None:
        for key, value in d.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten(value, f"{full_key}/", out)
            else:
                out[full_key] = value

    # ------------------------------------------------------------------
    # Metric logging
    # ------------------------------------------------------------------

    def log_metrics(
        self,
        run_id: int,
        metrics: dict[str, Any],
        step: Optional[int] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Write a batch of metrics and bump the run's ``updated_at``.

        The entire batch — plus the run update — is committed in one session
        so the lock is held for the minimum possible time.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        with session_scope() as db:
            for metric_path, value in metrics.items():
                if isinstance(value, bool):
                    db.add(
                        Metric(
                            run_id=run_id,
                            attribute_path=metric_path,
                            attribute_type="bool",
                            step=step,
                            timestamp=timestamp,
                            bool_value=value,
                        )
                    )
                elif isinstance(value, int):
                    db.add(
                        Metric(
                            run_id=run_id,
                            attribute_path=metric_path,
                            attribute_type="int",
                            step=step,
                            timestamp=timestamp,
                            int_value=value,
                        )
                    )
                elif isinstance(value, float):
                    db.add(
                        Metric(
                            run_id=run_id,
                            attribute_path=metric_path,
                            attribute_type="float",
                            step=step,
                            timestamp=timestamp,
                            float_value=value,
                        )
                    )
                elif isinstance(value, str):
                    db.add(
                        Metric(
                            run_id=run_id,
                            attribute_path=metric_path,
                            attribute_type="string",
                            step=step,
                            timestamp=timestamp,
                            string_value=value,
                        )
                    )
                else:
                    db.add(
                        Metric(
                            run_id=run_id,
                            attribute_path=metric_path,
                            attribute_type="string",
                            step=step,
                            timestamp=timestamp,
                            string_value=str(value),
                        )
                    )

            # Update run timestamp in the same transaction
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.updated_at = datetime.utcnow()

    # ------------------------------------------------------------------
    # Run finalisation
    # ------------------------------------------------------------------

    def finish_run(self, run_id: int) -> None:
        """Mark the run as completed."""
        with session_scope() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.state = "completed"
                run.updated_at = datetime.utcnow()

    def fail_run(self, run_id: int) -> None:
        """Mark the run as failed."""
        with session_scope() as db:
            run = db.query(Run).filter(Run.id == run_id).first()
            if run:
                run.state = "failed"
                run.updated_at = datetime.utcnow()
