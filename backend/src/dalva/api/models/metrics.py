from datetime import datetime

from pydantic import BaseModel, ConfigDict, RootModel


class MetricBase(BaseModel):
    attribute_path: str
    attribute_type: str
    step: int | None = None
    timestamp: datetime | None = None


class MetricCreate(MetricBase):
    run_id: int
    float_value: float | None = None
    int_value: int | None = None
    string_value: str | None = None
    bool_value: bool | None = None


class MetricResponse(MetricBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    float_value: float | None = None
    int_value: int | None = None
    string_value: str | None = None
    bool_value: bool | None = None


class MetricValue(BaseModel):
    step: int | None = None
    timestamp: datetime | None = None
    value: float | int | str | bool
    attribute_type: str | None = None


class MetricInfo(BaseModel):
    path: str
    attribute_type: str


class MetricValuesResponse(BaseModel):
    data: list[MetricValue]
    has_more: bool
    attribute_type: str | None = None


class SummaryMetricsRequest(BaseModel):
    run_ids: list[int]
    metric_paths: list[str]


class SummaryMetricsResponse(
    RootModel[dict[str, dict[str, float | int | str | bool | None]]]
):
    pass
