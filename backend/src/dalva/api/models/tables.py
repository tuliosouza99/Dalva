"""API models for table endpoints."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ColumnSchema(BaseModel):
    """Schema for a single column."""

    name: str
    type: str  # int, float, bool, str, date, list, dict


class InitTableRequest(BaseModel):
    """Request to initialize a new table."""

    project: str
    name: Optional[str] = None
    config: Optional[dict] = None
    run_id: Optional[int] = None
    log_mode: Optional[str] = Field(
        default="IMMUTABLE", pattern="^(IMMUTABLE|MUTABLE|INCREMENTAL)$"
    )
    resume_from: Optional[str] = None


class InitTableResponse(BaseModel):
    """Response from table initialization."""

    id: int
    table_id: str
    name: Optional[str]
    log_mode: str
    version: int = 0


class LogTableRequest(BaseModel):
    """Request to log rows to a table."""

    rows: list[dict[str, Any]]
    column_schema: list[ColumnSchema]


class LogTableResponse(BaseModel):
    """Response from logging rows."""

    success: bool = True
    version: int
    rows_added: int


class TableResponse(BaseModel):
    """Response with full table metadata."""

    id: int
    project_id: int
    table_id: str
    name: Optional[str]
    run_id: Optional[int]
    log_mode: str
    version: int
    row_count: int
    column_schema: str  # JSON string
    config: Optional[str]  # JSON string
    state: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TableListResponse(BaseModel):
    """Response for listing tables."""

    tables: list[TableResponse]
    total: int
    has_more: bool


class TableDataRequest(BaseModel):
    """Request for table data with pagination/sort/filter."""

    version: Optional[int] = None
    limit: int = 100
    offset: int = 0
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    filters: Optional[dict[str, Any]] = None


class TableDataResponse(BaseModel):
    """Response with table data."""

    rows: list[dict[str, Any]]
    total: int
    column_schema: list[ColumnSchema]
    has_more: bool


class FinishTableResponse(BaseModel):
    """Response from finishing a table."""

    state: str = "finished"
