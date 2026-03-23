"""API routes for runs."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from dalva.api.models import (
    RunCreate,
    RunResponse,
    RunsListResponse,
    RunSummary,
)
from dalva.db.connection import get_db
from dalva.db.schema import Config, Metric, Run

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
    sort_order: str = "desc",
    db: Session = Depends(get_db),
):
    """
    List runs with filtering, pagination, and sorting.

    Args:
        project_id: Filter by project ID
        group: Filter by group name
        state: Filter by run state (running, completed, failed)
        search: Search in run_id and name
        tags: Filter by tags (comma-separated, AND logic - all tags must match)
        limit: Maximum number of runs to return
        offset: Number of runs to skip
        sort_by: Column to sort by
        sort_order: Sort order (asc or desc)
        db: Database session

    Returns:
        Paginated list of runs
    """
    query = db.query(Run)

    # Apply filters
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
        # Filter by tags (AND logic - run must have all specified tags)
        tag_list = [tag.strip() for tag in tags.split(",")]
        for tag in tag_list:
            # Use LIKE to check if tag exists in comma-separated tags field
            query = query.filter(Run.tags.ilike(f"%{tag}%"))

    # Get total count
    total = query.count()

    # Apply sorting
    sort_column = getattr(Run, sort_by, Run.created_at)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    runs = query.limit(limit).offset(offset).all()

    has_more = (offset + limit) < total

    return RunsListResponse(runs=runs, total=total, has_more=has_more)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """
    Get run details.

    Args:
        run_id: Run database ID
        db: Database session

    Returns:
        Run details
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.get("/{run_id}/summary", response_model=RunSummary)
def get_run_summary(run_id: int, db: Session = Depends(get_db)):
    """
    Get run summary including latest metrics and configuration.

    Args:
        run_id: Run database ID
        db: Database session

    Returns:
        Run summary with metrics and config
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Get latest metrics (summary metrics with step=None)
    summary_metrics = (
        db.query(Metric).filter(Metric.run_id == run_id, Metric.step.is_(None)).all()
    )

    # Build metrics dict
    metrics_dict = {}
    for metric in summary_metrics:
        value = None
        if metric.float_value is not None:
            value = metric.float_value
        elif metric.int_value is not None:
            value = metric.int_value
        elif metric.string_value is not None:
            value = metric.string_value
        elif metric.bool_value is not None:
            value = metric.bool_value

        metrics_dict[metric.attribute_path] = value

    # Get config
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


@router.get("/{run_id}/config")
def get_run_config(run_id: int, db: Session = Depends(get_db)):
    """
    Get run configuration.

    Args:
        run_id: Run database ID
        db: Database session

    Returns:
        Run configuration as dict
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    configs = db.query(Config).filter(Config.run_id == run_id).all()
    config_dict = {c.key: json.loads(c.value) if c.value else None for c in configs}

    return config_dict


@router.post("/", response_model=RunResponse)
def create_run(run: RunCreate, db: Session = Depends(get_db)):
    """
    Create a new run.

    Args:
        run: Run data
        db: Database session

    Returns:
        Created run
    """
    db_run = Run(**run.model_dump())
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


@router.patch("/{run_id}/state")
def update_run_state(
    run_id: int,
    state: str = Query(..., regex="^(running|completed|failed)$"),
    db: Session = Depends(get_db),
):
    """
    Update run state.

    Args:
        run_id: Run database ID
        state: New state (running, completed, failed)
        db: Database session

    Returns:
        Updated run
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run.state = state
    db.commit()
    db.refresh(run)
    return run


@router.delete("/{run_id}")
def delete_run(run_id: int, db: Session = Depends(get_db)):
    """
    Delete a run and all associated data.

    Args:
        run_id: Run database ID
        db: Database session

    Returns:
        Success message
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    db.delete(run)
    db.commit()
    return {"message": "Run deleted successfully"}
