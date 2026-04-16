from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, RootModel


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
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    float_value: Optional[float] = None
    int_value: Optional[int] = None
    string_value: Optional[str] = None
    bool_value: Optional[bool] = None


class MetricValue(BaseModel):
    step: Optional[int] = None
    timestamp: Optional[datetime] = None
    value: float | int | str | bool
    attribute_type: Optional[str] = None


class MetricInfo(BaseModel):
    path: str
    attribute_type: str


class MetricValuesResponse(BaseModel):
    data: list[MetricValue]
    has_more: bool
    attribute_type: Optional[str] = None


class SummaryMetricsRequest(BaseModel):
    run_ids: list[int]
    metric_paths: list[str]


class SummaryMetricsResponse(
    RootModel[dict[str, dict[str, float | int | str | bool | None]]]
):
    pass
