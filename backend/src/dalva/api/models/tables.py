"""API models for table endpoints."""

from datetime import datetime
from typing import Any, Literal, Optional, Union

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


class ColumnFilter(BaseModel):
    """A single column filter."""

    column: str
    op: Literal["between", "contains", "eq"]
    min: Optional[float] = None
    max: Optional[float] = None
    value: Optional[Any] = None


class TableDataRequest(BaseModel):
    """Request for table data with pagination/sort/filter."""

    version: Optional[int] = None
    limit: int = 100
    offset: int = 0
    sort_by: Optional[str] = None
    sort_order: str = "asc"
    filters: Optional[list[ColumnFilter]] = None


class TableDataResponse(BaseModel):
    """Response with table data."""

    rows: list[dict[str, Any]]
    total: int
    column_schema: list[ColumnSchema]
    has_more: bool


class NumericStats(BaseModel):
    """Statistics for numeric columns (int/float)."""

    type: Literal["numeric"] = "numeric"
    min: Optional[float] = None
    max: Optional[float] = None
    bins: list[dict[str, Any]] = []
    null_count: int = 0


class BoolStats(BaseModel):
    """Statistics for boolean columns."""

    type: Literal["bool"] = "bool"
    counts: dict[str, int] = {"true": 0, "false": 0}
    null_count: int = 0


class StringStats(BaseModel):
    """Statistics for string columns."""

    type: Literal["string"] = "string"
    top_values: list[dict[str, Any]] = []
    unique_count: int = 0
    null_count: int = 0


class SkippedStats(BaseModel):
    """Placeholder stats for date/list/dict columns."""

    type: str
    null_count: int = 0


ColumnStats = Union[NumericStats, BoolStats, StringStats, SkippedStats]


class TableStatsResponse(BaseModel):
    """Response with per-column statistics."""

    columns: dict[str, ColumnStats] = {}


class FinishTableResponse(BaseModel):
    """Response from finishing a table."""

    state: str = "finished"
