"""Shared route helpers — DRY utilities used across all route modules."""

from __future__ import annotations

import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from dalva.api.models.tables import ColumnFilter
from dalva.db.schema import DalvaTable, Metric, Project, Run


def get_run_or_404(run_id: int, db: Session) -> Run:
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_table_or_404(table_id: int, db: Session) -> DalvaTable:
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    return table


def extract_metric_value(metric: Metric):
    return next(
        (
            v
            for v in (
                metric.float_value,
                metric.int_value,
                metric.string_value,
                metric.bool_value,
            )
            if v is not None
        ),
        None,
    )


def parse_filters(filters: str | None) -> list[dict] | None:
    if not filters:
        return None
    try:
        raw = json.loads(filters)
        validated = [ColumnFilter(**f) for f in raw]
        return [f.model_dump() for f in validated]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid filters: {e}")
