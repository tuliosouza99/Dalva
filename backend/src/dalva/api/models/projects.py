from datetime import datetime

from pydantic import BaseModel


class ProjectBase(BaseModel):
    name: str
    project_id: str


class ProjectCreate(ProjectBase):
    pass


class ProjectResponse(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectSummary(ProjectResponse):
    total_runs: int
    running_runs: int
    completed_runs: int
    failed_runs: int
