"""API routes for projects."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from dalva.api.models.projects import ProjectCreate, ProjectResponse, ProjectSummary
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

    # Add run statistics for each project
    result = []
    for project in projects:
        total_runs = db.query(Run).filter(Run.project_id == project.id).count()
        running_runs = (
            db.query(Run)
            .filter(Run.project_id == project.id, Run.state == "running")
            .count()
        )
        completed_runs = (
            db.query(Run)
            .filter(Run.project_id == project.id, Run.state == "completed")
            .count()
        )
        failed_runs = (
            db.query(Run)
            .filter(Run.project_id == project.id, Run.state == "failed")
            .count()
        )

        result.append(
            ProjectSummary(
                id=project.id,
                name=project.name,
                project_id=project.project_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                total_runs=total_runs,
                running_runs=running_runs,
                completed_runs=completed_runs,
                failed_runs=failed_runs,
            )
        )

    return result


@router.get("/{project_id}", response_model=ProjectSummary)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    Get project details with summary statistics.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        Project details with run statistics
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get run statistics
    total_runs = db.query(Run).filter(Run.project_id == project_id).count()
    running_runs = (
        db.query(Run)
        .filter(Run.project_id == project_id, Run.state == "running")
        .count()
    )
    completed_runs = (
        db.query(Run)
        .filter(Run.project_id == project_id, Run.state == "completed")
        .count()
    )
    failed_runs = (
        db.query(Run)
        .filter(Run.project_id == project_id, Run.state == "failed")
        .count()
    )

    return ProjectSummary(
        id=project.id,
        name=project.name,
        project_id=project.project_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        total_runs=total_runs,
        running_runs=running_runs,
        completed_runs=completed_runs,
        failed_runs=failed_runs,
    )


@router.get("/{project_id}/tags", response_model=list[str])
def get_project_tags(project_id: int, db: Session = Depends(get_db)):
    """
    Get all unique tags for a project.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        List of unique tags
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
    """
    Get available metric columns for the runs table.

    Returns numeric (float/int) scalar metrics only. Bool and string metrics
    are excluded since the table renders numeric columns.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    """
    Delete a project and all associated runs.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        Success message
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()
    return {"message": "Project deleted successfully"}
