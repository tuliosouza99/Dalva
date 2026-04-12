"""API routes for tables."""

import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from dalva.api.models.tables import (
    ColumnSchema,
    ColumnFilter,
    FinishTableResponse,
    InitTableRequest,
    InitTableResponse,
    LogTableRequest,
    LogTableResponse,
    TableDataResponse,
    TableListResponse,
    TableResponse,
    TableStatsResponse,
)
from dalva.db.connection import get_db
from dalva.db.schema import DalvaTable, DalvaTableRow, Project
from dalva.services.tables import (
    add_table_rows,
    create_table,
    delete_table,
    finish_table,
    get_table_data,
    get_table_stats,
    get_tables_for_project,
    get_tables_for_run,
)

router = APIRouter()


@router.get("/", response_model=TableListResponse)
def list_tables(
    project_id: Optional[int] = None,
    run_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """List tables with optional filtering."""
    if not project_id and not run_id:
        raise HTTPException(status_code=400, detail="project_id or run_id required")

    if run_id:
        tables = get_tables_for_run(run_id)
        return TableListResponse(
            tables=[TableResponse.model_validate(t) for t in tables],
            total=len(tables),
            has_more=False,
        )

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        tables = []
        total = 0
    else:
        tables, total = get_tables_for_project(project_id, limit, offset)

    has_more = (offset + limit) < total
    return TableListResponse(
        tables=[TableResponse.model_validate(t) for t in tables],
        total=total,
        has_more=has_more,
    )


@router.get("/{table_id}", response_model=TableResponse)
def get_table(table_id: int, db: Session = Depends(get_db)):
    """Get table metadata."""
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    table.row_count = (
        db.query(func.count(DalvaTableRow.id))
        .filter(DalvaTableRow.table_id == table_id)
        .scalar()
        or 0
    )
    return table


@router.get("/{table_id}/data", response_model=TableDataResponse)
def get_table_data_endpoint(
    table_id: int,
    version: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    filters: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get table data with pagination, sorting, and filtering."""
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    parsed_filters = None
    if filters:
        try:
            raw = json.loads(filters)
            validated = [ColumnFilter(**f) for f in raw]
            parsed_filters = [f.model_dump() for f in validated]
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid filters: {e}")

    try:
        rows, total, column_schema = get_table_data(
            table_db_id=table_id,
            version=version,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
            filters=parsed_filters,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    has_more = (offset + limit) < total
    return TableDataResponse(
        rows=rows,
        total=total,
        column_schema=[ColumnSchema(**c) for c in column_schema],
        has_more=has_more,
    )


@router.get("/{table_id}/stats", response_model=TableStatsResponse)
def get_table_stats_endpoint(
    table_id: int,
    version: Optional[int] = None,
    filters: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get per-column statistics for a table."""
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    parsed_filters = None
    if filters:
        try:
            raw = json.loads(filters)
            validated = [ColumnFilter(**f) for f in raw]
            parsed_filters = [f.model_dump() for f in validated]
        except (json.JSONDecodeError, ValueError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid filters: {e}")

    try:
        stats = get_table_stats(
            table_db_id=table_id,
            version=version,
            filters=parsed_filters,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return TableStatsResponse(columns=stats)


@router.post("/init", response_model=InitTableResponse)
def init_table(request: InitTableRequest):
    """Initialize a new table."""
    try:
        db_id, table_id, name, log_mode = create_table(
            project_name=request.project,
            name=request.name,
            config=request.config,
            run_id=request.run_id,
            log_mode=request.log_mode or "IMMUTABLE",
            resume_from=request.resume_from,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return InitTableResponse(
        id=db_id,
        table_id=table_id,
        name=name,
        log_mode=log_mode,
        version=0,
    )


@router.post("/{table_id}/log", response_model=LogTableResponse)
def log_table_rows(
    table_id: int,
    request: LogTableRequest,
    db: Session = Depends(get_db),
):
    """Log rows to a table."""
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if table.state == "finished":
        raise HTTPException(status_code=400, detail="Table is already finished")

    current_version = table.version
    log_mode = table.log_mode

    try:
        new_version, rows_added = add_table_rows(
            table_db_id=table_id,
            rows=request.rows,
            column_schema=[c.model_dump() for c in request.column_schema],
            log_mode=log_mode,
            current_version=current_version,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return LogTableResponse(
        success=True,
        version=new_version,
        rows_added=rows_added,
    )


@router.post("/{table_id}/finish", response_model=FinishTableResponse)
def finish_table_endpoint(table_id: int, db: Session = Depends(get_db)):
    """Mark a table as finished."""
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        state = finish_table(table_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return FinishTableResponse(state=state)


@router.patch("/{table_id}/state", response_model=FinishTableResponse)
def update_table_state(
    table_id: int,
    state: str = Query(..., pattern="^(active|finished)$"),
    db: Session = Depends(get_db),
):
    """Update table state."""
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    table.state = state
    table.updated_at = datetime.now(timezone.utc)
    db.commit()
    return FinishTableResponse(state=state)


@router.delete("/{table_id}")
def delete_table_endpoint(table_id: int, db: Session = Depends(get_db)):
    """Delete a table and all its rows."""
    table = db.query(DalvaTable).filter(DalvaTable.id == table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        delete_table(table_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "Table deleted successfully"}
