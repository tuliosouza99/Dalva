"""API routes for runs."""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from dalva.api.models.runs import (
    ConfigGetResponse,
    FinishResponse,
    InitRunRequest,
    InitRunResponse,
    LogConfigRequest,
    LogMetricsRequest,
    LogResponse,
    MetricGetResponse,
    RunResponse,
    RunsListResponse,
    RunSummary,
)
from dalva.api.models.tables import TableResponse
from dalva.db.connection import get_db, next_id
from dalva.db.schema import Config, Metric, Run
from dalva.services.logger import _flatten_config, _log_config, create_run, fork_run
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
        db.query(Metric)
        .filter(Metric.run_id == run_id, Metric.step.is_(None))
        .order_by(Metric.id.desc())
        .all()
    )

    # Build metrics dict
    metrics_dict = {
        metric.attribute_path: next(
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
        for metric in summary_metrics
    }

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


@router.post("/init", response_model=InitRunResponse)
def init_run(request: InitRunRequest):
    """
    Initialize a new run (SDK-facing endpoint).

    This endpoint handles project creation/resumption and run creation
    in one call, providing a simple interface for the SDK.

    When fork_from is set, creates a copy of the source run with configs,
    metrics, and optionally tables copied to the new run.

    Args:
        request: Run initialization data

    Returns:
        Created run ID and identifiers
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


@router.patch("/{run_id}/state")
def update_run_state(
    run_id: int,
    state: str = Query(..., pattern="^(running|completed|failed)$"),
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


@router.post("/{run_id}/log", response_model=LogResponse)
def log_metrics_remote(
    run_id: int,
    request: LogMetricsRequest,
    db: Session = Depends(get_db),
):
    """
    Log metrics for a run (strict insert — no overwrites).

    Raises 409 Conflict if:
    - A metric with the same (run_id, attribute_path, step) already exists
    - The same attribute_path has been logged at a different step with a different type
    - The same attribute_path has both scalar (step=NULL) and series (step!=NULL) values

    To overwrite, first use DELETE /api/runs/{run_id}/metrics/{attribute_path} to remove
    the existing metric, then log the new value.

    Args:
        run_id: Run database ID
        request: Metrics to log
        db: Database session

    Returns:
        Success confirmation
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run.last_activity_at = datetime.now(timezone.utc)
    run.updated_at = datetime.now(timezone.utc)

    flat_metrics: dict[str, object] = {}
    _flatten_config(request.metrics, "", flat_metrics)

    non_scalar = [
        k for k, v in flat_metrics.items() if not isinstance(v, (bool, int, float, str))
    ]
    if non_scalar:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Metric values must be scalars (str, bool, int, float)",
                "invalid_keys": non_scalar,
            },
        )

    timestamp = request.timestamp or datetime.now(timezone.utc)
    is_series = request.step is not None
    suffix = "_series" if is_series else ""

    conflicts = []

    for metric_path, value in flat_metrics.items():
        if isinstance(value, bool):
            attr_type = f"bool{suffix}"
        elif isinstance(value, int):
            attr_type = f"int{suffix}"
        elif isinstance(value, float):
            attr_type = f"float{suffix}"
        else:
            attr_type = f"string{suffix}"

        step = request.step

        # Check 1: base type conflict across ALL steps (including int vs float)
        # We check this BEFORE exact duplicate to give the more specific error
        existing_types = (
            db.query(Metric.attribute_type)
            .filter(
                Metric.run_id == run_id,
                Metric.attribute_path == metric_path,
            )
            .distinct()
            .all()
        )
        existing_types = {et[0] for et in existing_types}
        if existing_types:
            base_new = attr_type.replace("_series", "")
            base_existing = {et.replace("_series", "") for et in existing_types}

            # 1a: base type conflict (e.g., int vs float, float vs string, bool vs int)
            if base_new not in base_existing:
                conflicts.append(
                    f"Type conflict for '{metric_path}': "
                    f"cannot log {attr_type}, existing types are {existing_types}"
                )
                continue

            # 1b: scalar/series mismatch for same base type
            has_scalar = any("_series" not in et for et in existing_types)
            has_series = any("_series" in et for et in existing_types)
            if is_series and has_scalar:
                conflicts.append(
                    f"Metric '{metric_path}' already has scalar (summary) values — "
                    f"cannot log series at step {step} (use remove() first)"
                )
                continue
            elif not is_series and has_series:
                conflicts.append(
                    f"Metric '{metric_path}' already has series (stepped) values — "
                    f"cannot log scalar (use remove() first)"
                )
                continue

        # Check 2: exact duplicate (same run_id, attribute_path, step)
        existing_exact = (
            db.query(Metric)
            .filter(
                Metric.run_id == run_id,
                Metric.attribute_path == metric_path,
                Metric.step == step,
            )
            .first()
        )
        if existing_exact:
            conflicts.append(
                f"Metric '{metric_path}' already exists at "
                f"{'step ' + str(step) if step is not None else 'summary'} "
                f"(use remove() first to overwrite)"
            )
            continue

    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={"message": "Metric logging conflict(s)", "conflicts": conflicts},
        )

    # All clear — insert
    for metric_path, value in flat_metrics.items():
        if isinstance(value, bool):
            attr_type = f"bool{suffix}"
            value_key = "bool_value"
        elif isinstance(value, int):
            attr_type = f"int{suffix}"
            value_key = "int_value"
        elif isinstance(value, float):
            attr_type = f"float{suffix}"
            value_key = "float_value"
        else:
            attr_type = f"string{suffix}"
            value_key = "string_value"
            value = str(value)

        db.add(
            Metric(
                id=next_id(db, "metrics"),
                run_id=run_id,
                attribute_path=metric_path,
                attribute_type=attr_type,
                step=request.step,
                timestamp=timestamp,
                **{value_key: value},
            )
        )

    db.commit()
    return LogResponse(success=True)


@router.post("/{run_id}/finish", response_model=FinishResponse)
def finish_run_remote(
    run_id: int,
    db: Session = Depends(get_db),
):
    """
    Finish a run (synchronous).

    Args:
        run_id: Run database ID
        db: Database session

    Returns:
        Final run state
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run.last_activity_at = datetime.now(timezone.utc)
    run.updated_at = datetime.now(timezone.utc)
    run.state = "completed"
    db.commit()

    return FinishResponse(state="completed")


@router.get("/{run_id}/tables")
def get_run_tables(run_id: int, db: Session = Depends(get_db)):
    """Get all tables linked to a run."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    tables = get_tables_for_run(run_id)
    return [TableResponse.model_validate(t) for t in tables]


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


@router.get(
    "/{run_id}/metrics/{attribute_path:path}",
    response_model=MetricGetResponse,
    responses={404: {"description": "Run or metric not found"}},
)
def get_metric(
    run_id: int,
    attribute_path: str,
    step: Optional[int] = Query(
        None,
        description=(
            "Specific step to retrieve. If omitted, returns the value at the "
            "highest step (or the scalar if no series exist)."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Get a specific metric from a run.

    - With `step`: returns the metric at that specific step.
    - Without `step`: returns the metric at the latest step (highest step number),
      or the scalar value if no series steps exist.

    Returns a dict with ``key``, ``value``, and ``step``.
    If the metric does not exist, returns 404.

    Args:
        run_id: Run database ID
        attribute_path: Metric name/path
        step: Optional step number
        db: Database session

    Returns:
        Dict with key, value, step
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if step is not None:
        metric = (
            db.query(Metric)
            .filter(
                Metric.run_id == run_id,
                Metric.attribute_path == attribute_path,
                Metric.step == step,
            )
            .first()
        )
    else:
        series_metric = (
            db.query(Metric)
            .filter(
                Metric.run_id == run_id,
                Metric.attribute_path == attribute_path,
                Metric.step.isnot(None),
            )
            .order_by(Metric.step.desc())
            .first()
        )
        if series_metric:
            metric = series_metric
        else:
            metric = (
                db.query(Metric)
                .filter(
                    Metric.run_id == run_id,
                    Metric.attribute_path == attribute_path,
                    Metric.step.is_(None),
                )
                .first()
            )

    if not metric:
        raise HTTPException(
            status_code=404,
            detail=f"Metric '{attribute_path}' not found for this run",
        )

    value = next(
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

    return MetricGetResponse(key=attribute_path, value=value, step=metric.step)


@router.delete(
    "/{run_id}/metrics/{attribute_path:path}",
    responses={
        404: {"description": "Metric not found"},
        409: {"description": "Ambiguous request — specify step parameter"},
    },
)
def remove_metric(
    run_id: int,
    attribute_path: str,
    step: Optional[int] = Query(
        None,
        description=(
            "Step to remove. If omitted, removes ALL metrics with this attribute_path "
            "across all steps (scalar and series). Requires step to target a specific value."
        ),
    ),
    db: Session = Depends(get_db),
):
    """
    Remove one or more metrics from a run.

    - With `step`: removes the metric at that specific step only.
    - Without `step`: removes ALL metrics with this attribute_path (all steps, scalar and series).

    To overwrite an existing metric, you must remove it first, then log the new value.

    Args:
        run_id: Run database ID
        attribute_path: Metric name/path
        step: Optional step number. If None, removes all entries for this metric.
        db: Database session

    Returns:
        Success message with count of rows deleted
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    query = db.query(Metric).filter(
        Metric.run_id == run_id,
        Metric.attribute_path == attribute_path,
    )

    if step is not None:
        query = query.filter(Metric.step == step)

    rows = query.all()
    count = len(rows)

    if count == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No metric '{attribute_path}' found for this run",
        )

    for row in rows:
        db.delete(row)

    db.commit()
    return {
        "message": f"Removed {count} metric row(s) for '{attribute_path}'",
        "count": count,
    }


@router.get(
    "/{run_id}/config/{key:path}",
    response_model=ConfigGetResponse,
    responses={404: {"description": "Run or config key not found"}},
)
def get_config(
    run_id: int,
    key: str,
    db: Session = Depends(get_db),
):
    """
    Get a specific config key from a run.

    Returns a dict with ``key`` and ``value``.
    If the key does not exist, returns 404.

    Args:
        run_id: Run database ID
        key: Config key name
        db: Database session

    Returns:
        Dict with key, value
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    config = (
        db.query(Config)
        .filter(
            Config.run_id == run_id,
            Config.key == key,
        )
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Config key '{key}' not found for this run",
        )

    value = json.loads(config.value) if config.value else None

    return ConfigGetResponse(key=key, value=value)


@router.delete("/{run_id}/config/{key:path}")
def remove_config(
    run_id: int,
    key: str,
    db: Session = Depends(get_db),
):
    """
    Remove a config key from a run.

    To overwrite an existing config key, you must remove it first, then re-log
    the run with the new config.

    Args:
        run_id: Run database ID
        key: Config key name
        db: Database session

    Returns:
        Success message
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    config = (
        db.query(Config)
        .filter(
            Config.run_id == run_id,
            Config.key == key,
        )
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Config key '{key}' not found for this run",
        )

    db.delete(config)
    db.commit()
    return {"message": f"Config key '{key}' removed"}


@router.post("/{run_id}/config", response_model=LogResponse)
def log_config_remote(
    run_id: int,
    request: LogConfigRequest,
    db: Session = Depends(get_db),
):
    """
    Add config key-value pairs to a run (strict insert — no overwrites).

    Raises 409 Conflict if any key already exists for the run.
    Use DELETE /api/runs/{run_id}/config/{key} to remove a key first.

    Args:
        run_id: Run database ID
        request: Config dict to log
        db: Database session

    Returns:
        Success confirmation
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    try:
        _log_config(run_id, request.config, session=db)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail={"message": "Config logging conflict(s)", "conflicts": [str(e)]},
        )

    db.commit()
    return LogResponse(success=True)
