"""API routes for metrics."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import distinct
from sqlalchemy.orm import Session

from trackai.api.models import MetricValue, MetricValuesResponse
from trackai.db.connection import get_db
from trackai.db.schema import Metric, Run

router = APIRouter()


@router.get("/runs/{run_id}")
def list_metrics(run_id: int, db: Session = Depends(get_db)):
    """
    List all metric names for a run.
    """
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    metrics = (
        db.query(distinct(Metric.attribute_path))
        .filter(Metric.run_id == run_id)
        .order_by(Metric.attribute_path)
        .all()
    )

    return [m[0] for m in metrics]


@router.get("/runs/{run_id}/metric/{metric_path:path}", response_model=MetricValuesResponse)
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
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

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
    for m in metrics:
        value = None
        if m.float_value is not None:
            value = m.float_value
        elif m.int_value is not None:
            value = m.int_value
        elif m.string_value is not None:
            value = m.string_value
        elif m.bool_value is not None:
            value = m.bool_value

        if value is None:
            continue

        data.append(MetricValue(step=m.step, timestamp=m.timestamp, value=value))

    has_more = (offset + limit) < total

    return MetricValuesResponse(data=data, has_more=has_more)
