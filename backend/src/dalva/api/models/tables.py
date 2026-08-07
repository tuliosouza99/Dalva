"""API models for table endpoints."""

import re
from collections.abc import Mapping
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

from ...types import InputValue, SingleElement

_COLUMN_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,127}$")


class ColumnSchema(BaseModel):
    """Schema for a single column."""

    name: str
    type: str

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        if not _COLUMN_NAME_RE.match(v):
            raise ValueError(
                f"Invalid column name '{v}': must start with a letter or underscore "
                "and contain only letters, digits, and underscores (max 128 chars)"
            )
        return v


class InitTableRequest(BaseModel):
    """Request to initialize a new table."""

    project: str
    name: str | None = None
    config: Mapping[str, InputValue] | None = None
    run_id: int | None = None
    column_schema: list[ColumnSchema] | None = None
    resume_from: str | None = None


class InitTableResponse(BaseModel):
    """Response from table initialization."""

    id: int
    table_id: str
    name: str | None
    version: int = 0


class LogTableRequest(BaseModel):
    """Request to log rows to a table."""

    rows: list[dict[str, InputValue]]


class BatchLogTableRequest(BaseModel):
    """Request to batch-log rows to a table."""

    entries: list[LogTableRequest]


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
    name: str | None
    run_id: int | None
    version: int
    row_count: int
    column_schema: str
    config: str | None
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
    min: float | None = None
    max: float | None = None
    value: SingleElement | None = None


class TableDataRequest(BaseModel):
    """Request for table data with pagination/sort/filter."""

    version: int | None = None
    limit: int = 100
    offset: int = 0
    sort_by: str | None = None
    sort_order: str = "asc"
    filters: list[ColumnFilter] | None = None


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
    min: float | None = None
    max: float | None = None
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
    """Placeholder stats for list/dict columns."""

    type: str
    null_count: int = 0


ColumnStats = NumericStats | BoolStats | StringStats | SkippedStats


class TableStatsResponse(BaseModel):
    """Response with per-column statistics."""

    columns: dict[str, ColumnStats] = {}


class FinishTableResponse(BaseModel):
    """Response from finishing a table."""

    state: str = "finished"
