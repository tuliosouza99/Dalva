"""API routes for metrics."""

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dalva.api.models.metrics import (
    MetricInfo,
    MetricValue,
    MetricValuesResponse,
    SummaryMetricsRequest,
    SummaryMetricsResponse,
)
from dalva.api.routes._helpers import extract_metric_value, get_run_or_404
from dalva.db.connection import get_db
from dalva.db.schema import Metric

router = APIRouter()


@router.post("/summary", response_model=SummaryMetricsResponse)
def get_summary_metrics(
    request: SummaryMetricsRequest,
    db: Session = Depends(get_db),
):
    """
    Get latest metric values for multiple runs and metric paths.

    Returns a dict mapping run_id -> { metric_path -> value }.
    For each (run_id, metric_path), returns the value with the highest step,
    or the step=null value if no non-null steps exist.
    """
    if not request.run_ids or not request.metric_paths:
        return {}

    # For each (run_id, attribute_path), get metrics with non-null steps
    # and find the max step
    metrics_with_steps = (
        db.query(
            Metric.run_id,
            Metric.attribute_path,
            Metric.step,
            Metric.float_value,
            Metric.int_value,
            Metric.string_value,
            Metric.bool_value,
        )
        .filter(
            Metric.run_id.in_(request.run_ids),
            Metric.attribute_path.in_(request.metric_paths),
            Metric.step.isnot(None),
        )
        .all()
    )

    # For summary metrics (step=null)
    summary_metrics = (
        db.query(
            Metric.run_id,
            Metric.attribute_path,
            Metric.step,
            Metric.float_value,
            Metric.int_value,
            Metric.string_value,
            Metric.bool_value,
        )
        .filter(
            Metric.run_id.in_(request.run_ids),
            Metric.attribute_path.in_(request.metric_paths),
            Metric.step.is_(None),
        )
        .all()
    )

    # Build result dict
    result: dict[int, dict[str, float | int | str | bool | None]] = {
        run_id: {} for run_id in request.run_ids
    }

    # Track max step per (run_id, attribute_path) from non-null steps
    max_steps: dict[tuple, int] = {}
    max_step_metrics: dict[tuple, tuple] = {}

    # First pass: find max step metrics with non-null steps
    for m in metrics_with_steps:
        key = (m.run_id, m.attribute_path)
        if key not in max_steps or m.step > max_steps[key]:
            max_steps[key] = m.step
            max_step_metrics[key] = m

    # Second pass: add summary metrics (step=null) if no non-null step exists
    for m in summary_metrics:
        key = (m.run_id, m.attribute_path)
        if key not in max_step_metrics:
            max_step_metrics[key] = m

    # Extract values
    for key, metric in max_step_metrics.items():
        run_id, attr_path = key
        result[run_id][attr_path] = extract_metric_value(metric)

    # Convert int keys to string keys for JSON compatibility
    return {str(run_id): metrics_dict for run_id, metrics_dict in result.items()}


@router.get("/runs/{run_id}", response_model=list[MetricInfo])
def list_metrics(run_id: int, db: Session = Depends(get_db)):
    """List all metrics for a run with their attribute types."""
    get_run_or_404(run_id, db)

    metrics = (
        db.query(Metric.attribute_path, Metric.attribute_type)
        .filter(Metric.run_id == run_id)
        .distinct(Metric.attribute_path)
        .order_by(Metric.attribute_path)
        .all()
    )

    return [MetricInfo(path=m[0], attribute_type=m[1]) for m in metrics]


@router.get(
    "/runs/{run_id}/metric/{metric_path:path}", response_model=MetricValuesResponse
)
def get_metric_values(
    run_id: int,
    metric_path: str,
    limit: int = 1000,
    offset: int = 0,
    step_min: Optional[int] = None,
    step_max: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get time-series values for a specific metric.
    """
    get_run_or_404(run_id, db)

    query = db.query(Metric).filter(
        Metric.run_id == run_id,
        Metric.attribute_path == metric_path,
    )

    if step_min is not None:
        query = query.filter(Metric.step >= step_min)
    if step_max is not None:
        query = query.filter(Metric.step <= step_max)

    total = query.count()
    metrics = query.order_by(Metric.step).limit(limit).offset(offset).all()

    data = []
    attribute_type = None
    for m in metrics:
        value = extract_metric_value(m)
        if value is not None:
            attribute_type = m.attribute_type
        else:
            continue

        data.append(
            MetricValue(
                step=m.step,
                timestamp=m.timestamp,
                value=value,
                attribute_type=m.attribute_type,
            )
        )

    has_more = (offset + limit) < total

    return MetricValuesResponse(
        data=data, has_more=has_more, attribute_type=attribute_type
    )
