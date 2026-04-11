from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RunBase(BaseModel):
    run_id: str
    name: Optional[str] = None
    group_name: Optional[str] = None
    tags: Optional[str] = None
    state: str = "running"


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


class InitRunRequest(BaseModel):
    project: str
    name: Optional[str] = None
    config: Optional[dict] = None
    resume_from: Optional[str] = None


class InitRunResponse(BaseModel):
    id: int
    run_id: str
    name: Optional[str]


class LogMetricsRequest(BaseModel):
    metrics: dict[str, bool | int | float | str]
    step: Optional[int] = None
    timestamp: Optional[datetime] = None


class LogResponse(BaseModel):
    success: bool = True


class FinishResponse(BaseModel):
    state: str
