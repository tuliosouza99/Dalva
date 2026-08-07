from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomViewCreate(BaseModel):
    name: str
    filters: str | None = None
    columns: str | None = None
    sort_by: str | None = None


class CustomViewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    filters: str | None = None
    columns: str | None = None
    sort_by: str | None = None
    created_at: datetime
