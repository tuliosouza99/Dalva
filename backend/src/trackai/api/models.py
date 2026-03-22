"""Pydantic models for API request/response validation."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# Project models
class ProjectBase(BaseModel):
    name: str
    project_id: str


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectSummary(ProjectResponse):
    total_runs: int
    running_runs: int
    completed_runs: int
    failed_runs: int


# Run models
class RunBase(BaseModel):
    run_id: str
    name: Optional[str] = None
    group_name: Optional[str] = None
    tags: Optional[str] = None  # Comma-separated tags
    state: str = "running"


class RunCreate(RunBase):
    project_id: int


class RunResponse(RunBase):
    id: int
    project_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RunSummary(RunResponse):
    metrics: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)


class RunsListResponse(BaseModel):
    runs: list[RunResponse]
    total: int
    has_more: bool


# Metric models
class MetricBase(BaseModel):
    attribute_path: str
    attribute_type: str
    step: Optional[int] = None
    timestamp: Optional[datetime] = None


class MetricCreate(MetricBase):
    run_id: int
    float_value: Optional[float] = None
    int_value: Optional[int] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None


class MetricResponse(MetricBase):
    id: int
    run_id: int
    float_value: Optional[float] = None
    int_value: Optional[int] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None

    class Config:
        from_attributes = True


class MetricValue(BaseModel):
    step: Optional[int] = None
    timestamp: Optional[datetime] = None
    value: float | int | str | bool


class MetricValuesResponse(BaseModel):
    data: list[MetricValue]
    has_more: bool


# Config models
class ConfigCreate(BaseModel):
    run_id: int
    key: str
    value: str  # JSON-encoded


class ConfigResponse(BaseModel):
    id: int
    run_id: int
    key: str
    value: str

    class Config:
        from_attributes = True


# File models
class FileCreate(BaseModel):
    run_id: int
    file_type: str
    file_path: str
    file_hash: Optional[str] = None
    size: Optional[int] = None
    file_metadata: Optional[str] = None  # JSON


class FileResponse(BaseModel):
    id: int
    run_id: int
    file_type: str
    file_path: str
    file_hash: Optional[str] = None
    size: Optional[int] = None
    file_metadata: Optional[str] = None

    class Config:
        from_attributes = True


# Custom View models
class CustomViewCreate(BaseModel):
    name: str
    filters: Optional[str] = None  # JSON
    columns: Optional[str] = None  # JSON
    sort_by: Optional[str] = None  # JSON


class CustomViewResponse(BaseModel):
    id: int
    project_id: int
    name: str
    filters: Optional[str] = None
    columns: Optional[str] = None
    sort_by: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# Dashboard models
class DashboardCreate(BaseModel):
    project_id: int
    name: str
    widgets: Optional[str] = None  # JSON
    layout: Optional[str] = None  # JSON


class DashboardResponse(BaseModel):
    id: int
    project_id: int
    name: str
    widgets: Optional[str] = None
    layout: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
