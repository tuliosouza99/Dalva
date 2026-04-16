"""API routes for projects."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from dalva.api.models.common import MessageResponse
from dalva.api.models.projects import ProjectCreate, ProjectResponse, ProjectSummary
from dalva.api.routes._helpers import get_project_or_404
from dalva.db.connection import get_db, next_id
from dalva.db.schema import Metric, Project, Run

router = APIRouter()


@router.get("/", response_model=list[ProjectSummary])
def list_projects(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """
    List all projects with pagination and summary statistics.

    Args:
        limit: Maximum number of projects to return
        offset: Number of projects to skip
        db: Database session

    Returns:
        List of projects with run statistics
    """
    projects = (
        db.query(Project)
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    from sqlalchemy import case, func

    project_ids = [p.id for p in projects]

    if not project_ids:
        return []

    counts_raw = (
        db.query(
            Run.project_id,
            func.count(Run.id).label("total"),
            func.sum(case((Run.state == "running", 1), else_=0)).label("running"),
            func.sum(case((Run.state == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Run.state == "failed", 1), else_=0)).label("failed"),
        )
        .filter(Run.project_id.in_(project_ids))
        .group_by(Run.project_id)
        .all()
    )

    counts_map: dict[int, dict[str, int]] = {
        pid: {"total": 0, "running": 0, "completed": 0, "failed": 0}
        for pid in project_ids
    }
    for row in counts_raw:
        counts_map[row[0]] = {
            "total": row[1],
            "running": int(row[2] or 0),
            "completed": int(row[3] or 0),
            "failed": int(row[4] or 0),
        }
    for row in counts_raw:
        counts_map[row[0]] = {
            "total": row[1],
            "running": row[2],
            "completed": row[3],
            "failed": row[4],
        }

    result = []
    for project in projects:
        c = counts_map.get(
            project.id, {"total": 0, "running": 0, "completed": 0, "failed": 0}
        )
        result.append(
            ProjectSummary(
                id=project.id,
                name=project.name,
                project_id=project.project_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                total_runs=c["total"],
                running_runs=c["running"],
                completed_runs=c["completed"],
                failed_runs=c["failed"],
            )
        )

    return result


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """Get project details with summary statistics."""
    project = get_project_or_404(project_id, db)

    from sqlalchemy import case, func

    row = (
        db.query(
            func.count(Run.id).label("total"),
            func.sum(case((Run.state == "running", 1), else_=0)).label("running"),
            func.sum(case((Run.state == "completed", 1), else_=0)).label("completed"),
            func.sum(case((Run.state == "failed", 1), else_=0)).label("failed"),
        )
        .filter(Run.project_id == project_id)
        .one()
    )

    return ProjectSummary(
        id=project.id,
        name=project.name,
        project_id=project.project_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        total_runs=row[0],
        running_runs=int(row[1] or 0),
        completed_runs=int(row[2] or 0),
        failed_runs=int(row[3] or 0),
    )


@router.get("/{project_id}/tags", response_model=list[str])
def get_project_tags(project_id: int, db: Session = Depends(get_db)):
    """Get all unique tags for a project."""
    get_project_or_404(project_id, db)

    # Get all runs with tags
    runs = (
        db.query(Run).filter(Run.project_id == project_id, Run.tags.isnot(None)).all()
    )

    # Collect all unique tags
    tags_set = set()
    for run in runs:
        if run.tags:
            tags = [tag.strip() for tag in run.tags.split(",")]
            tags_set.update(tags)

    return sorted(list(tags_set))


@router.get("/{project_id}/available-columns", response_model=list[str])
def get_available_columns(project_id: int, db: Session = Depends(get_db)):
    """Get available metric columns for the runs table."""
    get_project_or_404(project_id, db)

    metrics = (
        db.query(Metric.attribute_path)
        .join(Run, Metric.run_id == Run.id)
        .filter(
            Run.project_id == project_id,
            Metric.step.is_(None),
            Metric.attribute_type.notin_(
                [
                    "bool",
                    "bool_series",
                    "string",
                    "string_series",
                ]
            ),
        )
        .distinct()
        .all()
    )

    paths = sorted([m[0] for m in metrics])
    return paths


@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """
    Create a new project.

    Args:
        project: Project data
        db: Database session

    Returns:
        Created project
    """
    # Check if project with same name or project_id already exists
    existing = (
        db.query(Project)
        .filter(
            (Project.name == project.name) | (Project.project_id == project.project_id)
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Project with this name or ID already exists"
        )

    db_project = Project(id=next_id(db, "projects"), **project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.delete("/{project_id}", response_model=MessageResponse)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """Delete a project and all associated runs."""
    project = get_project_or_404(project_id, db)

    db.delete(project)
    db.commit()
    return MessageResponse(message="Project deleted successfully")
