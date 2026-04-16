"""Shared service-layer utilities used across logger.py and tables.py."""

from __future__ import annotations

import hashlib
import re
import time

from sqlalchemy.orm import Session

from dalva.db.connection import next_id
from dalva.db.schema import Project


def generate_abbreviation(project_name: str, fallback: str = "RUN") -> str:
    """Generate a 3-letter uppercase abbreviation from a project name."""
    clean = re.sub(r"[^a-zA-Z0-9\s-]", "", project_name)
    words = re.split(r"[-_\s]+", clean)
    words = [w for w in words if w]

    if not words:
        return fallback.ljust(3, "X")[:3]

    if len(words) >= 3:
        abbrev = "".join(w[0] for w in words[:3])
    elif len(words) == 1:
        abbrev = words[0][:3]
    else:
        abbrev = words[0][0] + words[1][0] + (words[0][1] if len(words[0]) > 1 else "X")

    return abbrev.upper().ljust(3, "X")[:3]


def get_or_create_project(project_name: str, db: Session) -> Project:
    """Find an existing project by name or create a new one."""
    project = db.query(Project).filter(Project.name == project_name).first()
    if not project:
        project_id_str = (
            f"{project_name}_{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
        )
        project = Project(
            id=next_id(db, "projects"),
            name=project_name,
            project_id=project_id_str,
        )
        db.add(project)
        db.flush()
    return project
