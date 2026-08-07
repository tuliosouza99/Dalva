from collections.abc import Mapping
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, RootModel

from ...types import ConfigOutputDict, InputValue, OutputDict, SingleElement


class DeleteMetricResponse(BaseModel):
    message: str
    count: int


class RunConfigResponse(RootModel[ConfigOutputDict]):
    pass


class RunBase(BaseModel):
    run_id: str
    name: str | None = None
    group_name: str | None = None
    tags: str | None = None
    state: str = "running"


class RunResponse(RunBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    fork_from: int | None = None
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
    name: str | None = None
    config: Mapping[str, InputValue] | None = None
    resume_from: str | None = None
    fork_from: str | None = None
    copy_tables_on_fork: bool | list[int] = False


class InitRunResponse(BaseModel):
    id: int
    run_id: str
    name: str | None


class LogMetricsRequest(BaseModel):
    metrics: Mapping[str, InputValue]
    step: int | None = None
    timestamp: datetime | None = None


class BatchLogEntry(BaseModel):
    metrics: Mapping[str, InputValue]
    step: int | None = None


class BatchLogMetricsRequest(BaseModel):
    entries: list[BatchLogEntry]


class LogResponse(BaseModel):
    success: bool = True


class FinishResponse(BaseModel):
    state: str


class MetricGetResponse(BaseModel):
    key: str
    value: SingleElement = None
    step: int | None = None


class ConfigGetResponse(BaseModel):
    key: str
    value: InputValue = None


class LogConfigRequest(BaseModel):
    config: Mapping[str, InputValue]
