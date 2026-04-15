from datetime import datetime
from typing import Mapping, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from ...types import ConfigOutputDict, InputValue, OutputDict, SingleElement


class RunBase(BaseModel):
    run_id: str
    name: Optional[str] = None
    group_name: Optional[str] = None
    tags: Optional[str] = None
    state: str = "running"


class RunResponse(RunBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    fork_from: Optional[int] = None
    created_at: datetime
    updated_at: datetime


class RunSummary(RunResponse):
    metrics: OutputDict = Field(default_factory=dict)
    config: ConfigOutputDict = Field(default_factory=dict)


class RunsListResponse(BaseModel):
    runs: list[RunResponse]
    total: int
    has_more: bool


class InitRunRequest(BaseModel):
    project: str
    name: Optional[str] = None
    config: Optional[Mapping[str, InputValue]] = None
    resume_from: Optional[str] = None
    fork_from: Optional[str] = None
    copy_tables_on_fork: Union[bool, list[int]] = False


class InitRunResponse(BaseModel):
    id: int
    run_id: str
    name: Optional[str]


class LogMetricsRequest(BaseModel):
    metrics: Mapping[str, InputValue]
    step: Optional[int] = None
    timestamp: Optional[datetime] = None


class BatchLogEntry(BaseModel):
    metrics: Mapping[str, InputValue]
    step: Optional[int] = None


class BatchLogMetricsRequest(BaseModel):
    entries: list[BatchLogEntry]


class LogResponse(BaseModel):
    success: bool = True


class FinishResponse(BaseModel):
    state: str


class MetricGetResponse(BaseModel):
    key: str
    value: SingleElement = None
    step: Optional[int] = None


class ConfigGetResponse(BaseModel):
    key: str
    value: InputValue = None


class LogConfigRequest(BaseModel):
    config: Mapping[str, InputValue]
