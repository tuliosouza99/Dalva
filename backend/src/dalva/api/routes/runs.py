"""API routes for runs — core CRUD, state, and table listing."""

import json
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from dalva.api.models.runs import (
    FinishResponse,
    InitRunRequest,
    InitRunResponse,
    RunResponse,
    RunsListResponse,
    RunSummary,
)
from dalva.api.models.common import MessageResponse
from dalva.api.models.tables import TableResponse
from dalva.api.routes._helpers import extract_metric_value, get_run_or_404
from dalva.db.connection import get_db
from dalva.db.schema import Config, Metric, Run
from dalva.services.logger import create_run, fork_run
from dalva.services.tables import get_tables_for_run

router = APIRouter()


@router.get("/", response_model=RunsListResponse)
def list_runs(
    project_id: Optional[int] = None,
    group: Optional[str] = None,
    state: Optional[str] = None,
    search: Optional[str] = None,
    tags: Optional[str] = Query(
        None, description="Filter by tags (comma-separated, AND logic)"
    ),
    limit: int = 100,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
):
    """List runs with filtering, pagination, and sorting."""
    query = db.query(Run)

    if project_id:
        query = query.filter(Run.project_id == project_id)
    if group:
        query = query.filter(Run.group_name == group)
    if state:
        query = query.filter(Run.state == state)
    if search:
        query = query.filter(
            or_(
                Run.run_id.ilike(f"%{search}%"),
                Run.name.ilike(f"%{search}%"),
            )
        )
    if tags:
        tag_list = [tag.strip() for tag in tags.split(",")]
        for tag in tag_list:
            query = query.filter(
                or_(
                    Run.tags == tag,
                    Run.tags.ilike(f"{tag},%"),
                    Run.tags.ilike(f"%,{tag}"),
                    Run.tags.ilike(f"%,{tag},%"),
                )
            )

    total = query.count()

    sort_column = getattr(Run, sort_by, Run.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    runs = query.limit(limit).offset(offset).all()
    has_more = (offset + limit) < total

    return RunsListResponse(runs=runs, total=total, has_more=has_more)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get run details."""
    return get_run_or_404(run_id, db)


@router.get("/{run_id}/summary", response_model=RunSummary)
def get_run_summary(run_id: int, db: Session = Depends(get_db)):
    """Get run summary including latest metrics and configuration."""
    run = get_run_or_404(run_id, db)

    summary_metrics = (
        db.query(Metric)
        .filter(Metric.run_id == run_id, Metric.step.is_(None))
        .order_by(Metric.id.desc())
        .all()
    )

    metrics_dict = {
        metric.attribute_path: extract_metric_value(metric)
        for metric in summary_metrics
    }

    configs = db.query(Config).filter(Config.run_id == run_id).all()
    config_dict = {c.key: json.loads(c.value) if c.value else None for c in configs}

    return RunSummary(
        id=run.id,
        project_id=run.project_id,
        run_id=run.run_id,
        name=run.name,
        group_name=run.group_name,
        state=run.state,
        created_at=run.created_at,
        updated_at=run.updated_at,
        metrics=metrics_dict,
        config=config_dict,
    )


@router.post("/init", response_model=InitRunResponse)
def init_run(request: InitRunRequest):
    """Initialize a new run (SDK-facing endpoint).

    When fork_from is set, creates a copy of the source run with configs,
    metrics, and optionally tables copied to the new run.
    """
    if request.fork_from is not None:
        try:
            db_id, run_id_str, name = fork_run(
                fork_from=request.fork_from,
                project_name=request.project,
                name=request.name,
                copy_tables_on_fork=request.copy_tables_on_fork,
            )
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
    else:
        db_id, run_id_str, name = create_run(
            project_name=request.project,
            run_name=request.name,
            config=request.config,
            resume_from=request.resume_from,
        )

    return InitRunResponse(id=db_id, run_id=run_id_str, name=name)


@router.patch("/{run_id}/state", response_model=RunResponse)
def update_run_state(
    run_id: int,
    state: str = Query(..., pattern="^(running|completed|failed)$"),
    db: Session = Depends(get_db),
):
    """Update run state."""
    run = get_run_or_404(run_id, db)
    run.state = state
    db.commit()
    db.refresh(run)
    return run


@router.post("/{run_id}/finish", response_model=FinishResponse)
def finish_run_remote(
    run_id: int,
    db: Session = Depends(get_db),
):
    """Finish a run (synchronous)."""
    run = get_run_or_404(run_id, db)

    run.last_activity_at = datetime.now(timezone.utc)
    run.updated_at = datetime.now(timezone.utc)
    run.state = "completed"
    db.commit()

    return FinishResponse(state="completed")


@router.get("/{run_id}/tables", response_model=list[TableResponse])
def get_run_tables(run_id: int, db: Session = Depends(get_db)):
    """Get all tables linked to a run."""
    get_run_or_404(run_id, db)

    tables = get_tables_for_run(run_id)
    return [TableResponse.model_validate(t) for t in tables]


@router.delete("/{run_id}", response_model=MessageResponse)
def delete_run(run_id: int, db: Session = Depends(get_db)):
    """Delete a run and all associated data."""
    run = get_run_or_404(run_id, db)

    db.delete(run)
    db.commit()
    return MessageResponse(message="Run deleted successfully")
