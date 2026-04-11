from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ConfigCreate(BaseModel):
    run_id: int
    key: str
    value: str


class ConfigResponse(BaseModel):
    id: int
    run_id: int
    key: str
    value: str

    class Config:
        from_attributes = True


class FileCreate(BaseModel):
    run_id: int
    file_type: str
    file_path: str
    file_hash: Optional[str] = None
    size: Optional[int] = None
    file_metadata: Optional[str] = None


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


class DashboardCreate(BaseModel):
    project_id: int
    name: str
    widgets: Optional[str] = None
    layout: Optional[str] = None


class DashboardResponse(BaseModel):
    id: int
    project_id: int
    name: str
    widgets: Optional[str] = None
    layout: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
