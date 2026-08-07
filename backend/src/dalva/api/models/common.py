from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    message: str


class ConfigCreate(BaseModel):
    run_id: int
    key: str
    value: str


class ConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    key: str
    value: str


class FileCreate(BaseModel):
    run_id: int
    file_type: str
    file_path: str
    file_hash: str | None = None
    size: int | None = None
    file_metadata: str | None = None


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    file_type: str
    file_path: str
    file_hash: str | None = None
    size: int | None = None
    file_metadata: str | None = None


class DashboardCreate(BaseModel):
    project_id: int
    name: str
    widgets: str | None = None
    layout: str | None = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    widgets: str | None = None
    layout: str | None = None
    created_at: datetime
