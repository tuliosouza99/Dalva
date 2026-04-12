from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CustomViewCreate(BaseModel):
    name: str
    filters: Optional[str] = None
    columns: Optional[str] = None
    sort_by: Optional[str] = None


class CustomViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    filters: Optional[str] = None
    columns: Optional[str] = None
    sort_by: Optional[str] = None
    created_at: datetime
