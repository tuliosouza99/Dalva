"""API routes for run metrics — single log, batch log, get, delete."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from dalva.api.models.runs import (
    BatchLogMetricsRequest,
    LogMetricsRequest,
    LogResponse,
    MetricGetResponse,
)
from dalva.api.routes._helpers import extract_metric_value, get_run_or_404
from dalva.db.connection import get_db, next_id
from dalva.db.schema import Metric
from dalva.services.logger import _flatten_config

router = APIRouter()


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
    """
    run = get_run_or_404(run_id, db)

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

    conflicts = _check_metric_conflicts(
        run_id, flat_metrics, is_series, suffix, request.step, db
    )

    if conflicts:
        raise HTTPException(
            status_code=409,
            detail={"message": "Metric logging conflict(s)", "conflicts": conflicts},
        )

    _insert_metrics(run_id, flat_metrics, suffix, request.step, timestamp, db)
    db.commit()
    return LogResponse(success=True)


@router.post("/{run_id}/log/batch", response_model=LogResponse)
def log_metrics_batch(
    run_id: int,
    request: BatchLogMetricsRequest,
    db: Session = Depends(get_db),
):
    """Log multiple metric entries in a single request.

    Each entry has its own ``metrics`` and optional ``step``.
    All entries are processed in order within a single transaction.

    Returns success if ALL entries were logged. Returns 409 with details
    of the first conflicting entry if any conflict is found (the entire
    batch is rolled back).
    """
    run = get_run_or_404(run_id, db)

    run.last_activity_at = datetime.now(timezone.utc)
    run.updated_at = datetime.now(timezone.utc)

    all_conflicts = []
    for i, entry in enumerate(request.entries):
        conflicts = _log_single_batch_entry(run_id, entry, db)
        if conflicts:
            all_conflicts.extend([f"Entry {i}: {c}" for c in conflicts])

    if all_conflicts:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Batch metric logging conflict(s)",
                "conflicts": all_conflicts,
            },
        )

    db.commit()
    return LogResponse(success=True)


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
    """
    get_run_or_404(run_id, db)

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

    value = extract_metric_value(metric)

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
    """
    get_run_or_404(run_id, db)

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


def _infer_type(value: object, suffix: str) -> tuple[str, str, object]:
    if isinstance(value, bool):
        return f"bool{suffix}", "bool_value", value
    elif isinstance(value, int):
        return f"int{suffix}", "int_value", value
    elif isinstance(value, float):
        return f"float{suffix}", "float_value", value
    else:
        return f"string{suffix}", "string_value", str(value)


def _check_metric_conflicts(
    run_id: int,
    flat_metrics: dict[str, object],
    is_series: bool,
    suffix: str,
    step: int | None,
    db: Session,
) -> list[str]:
    conflicts = []

    for metric_path, value in flat_metrics.items():
        attr_type, _, _ = _infer_type(value, suffix)

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

            if base_new not in base_existing:
                conflicts.append(
                    f"Type conflict for '{metric_path}': "
                    f"cannot log {attr_type}, existing types are {existing_types}"
                )
                continue

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

    return conflicts


def _insert_metrics(
    run_id: int,
    flat_metrics: dict[str, object],
    suffix: str,
    step: int | None,
    timestamp: datetime,
    db: Session,
) -> None:
    for metric_path, value in flat_metrics.items():
        attr_type, value_key, coerced = _infer_type(value, suffix)
        db.add(
            Metric(
                id=next_id(db, "metrics"),
                run_id=run_id,
                attribute_path=metric_path,
                attribute_type=attr_type,
                step=step,
                timestamp=timestamp,
                **{value_key: coerced},
            )
        )


def _log_single_batch_entry(run_id: int, entry, db: Session) -> list[str]:
    timestamp = datetime.now(timezone.utc)
    flat_metrics: dict[str, object] = {}
    _flatten_config(entry.metrics, "", flat_metrics)

    non_scalar = [
        k for k, v in flat_metrics.items() if not isinstance(v, (bool, int, float, str))
    ]
    if non_scalar:
        return [f"Non-scalar values for keys: {non_scalar}"]

    is_series = entry.step is not None
    suffix = "_series" if is_series else ""

    conflicts = _check_metric_conflicts(
        run_id, flat_metrics, is_series, suffix, entry.step, db
    )

    non_conflicting = {
        k: v for k, v in flat_metrics.items() if not any(k in c for c in conflicts)
    }

    _insert_metrics(run_id, non_conflicting, suffix, entry.step, timestamp, db)
    return conflicts
