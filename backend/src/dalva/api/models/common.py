from datetime import datetime
from typing import Optional

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
    file_hash: Optional[str] = None
    size: Optional[int] = None
    file_metadata: Optional[str] = None


class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: int
    file_type: str
    file_path: str
    file_hash: Optional[str] = None
    size: Optional[int] = None
    file_metadata: Optional[str] = None


class DashboardCreate(BaseModel):
    project_id: int
    name: str
    widgets: Optional[str] = None
    layout: Optional[str] = None


class DashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    widgets: Optional[str] = None
    layout: Optional[str] = None
    created_at: datetime
