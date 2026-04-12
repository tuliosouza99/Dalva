"""API models for table endpoints."""

from datetime import datetime
from typing import Literal, Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ...types import InputValue, SingleElement


class ColumnSchema(BaseModel):
    """Schema for a single column."""

    name: str
    type: str


class InitTableRequest(BaseModel):
    """Request to initialize a new table."""

    project: str
    name: Optional[str] = None
    config: Optional[Mapping[str, InputValue]] = None
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

    rows: list[dict[str, InputValue]]
    column_schema: list[ColumnSchema]


class LogTableResponse(BaseModel):
    """Response from logging rows."""

    success: bool = True
    version: int
    rows_added: int


class TableResponse(BaseModel):
    """Response with full table metadata."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    table_id: str
    name: Optional[str]
    run_id: Optional[int]
    log_mode: str
    version: int
    row_count: int
    column_schema: str
    config: Optional[str]
    state: str
    created_at: datetime
    updated_at: datetime


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
    value: Optional[SingleElement] = None


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

    rows: list[dict[str, InputValue]]
    total: int
    column_schema: list[ColumnSchema]
    has_more: bool


class Bin(BaseModel):
    """A histogram bin."""

    start: float
    end: float
    count: int


class TopValue(BaseModel):
    """A top value entry."""

    value: str
    count: int


class NumericStats(BaseModel):
    """Statistics for numeric columns (int/float)."""

    type: Literal["numeric"] = "numeric"
    min: Optional[float] = None
    max: Optional[float] = None
    bins: list[Bin] = []
    null_count: int = 0


class BoolStats(BaseModel):
    """Statistics for boolean columns."""

    type: Literal["bool"] = "bool"
    counts: dict[str, int] = {"true": 0, "false": 0}
    null_count: int = 0


class StringStats(BaseModel):
    """Statistics for string columns."""

    type: Literal["string"] = "string"
    top_values: list[TopValue] = []
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
