"""API routes for custom views."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from dalva.api.models.views import CustomViewCreate, CustomViewResponse
from dalva.api.routes._helpers import get_project_or_404
from dalva.db.connection import get_db, next_id
from dalva.db.schema import CustomView

router = APIRouter()


@router.get("/projects/{project_id}/views", response_model=list[CustomViewResponse])
def list_custom_views(project_id: int, db: Session = Depends(get_db)):
    """
    List all custom views for a project.

    Args:
        project_id: Project ID
        db: Database session

    Returns:
        List of custom views
    """
    get_project_or_404(project_id, db)

    views = (
        db.query(CustomView)
        .filter(CustomView.project_id == project_id)
        .order_by(CustomView.created_at.desc())
        .all()
    )

    return views


@router.post("/projects/{project_id}/views", response_model=CustomViewResponse)
def create_custom_view(
    project_id: int, view: CustomViewCreate, db: Session = Depends(get_db)
):
    """
    Create a new custom view.

    Args:
        project_id: Project ID
        view: Custom view data
        db: Database session

    Returns:
        Created custom view
    """
    get_project_or_404(project_id, db)

    existing = (
        db.query(CustomView)
        .filter(CustomView.project_id == project_id, CustomView.name == view.name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A view with this name already exists for this project",
        )

    db_view = CustomView(
        id=next_id(db, "custom_views"),
        project_id=project_id,
        name=view.name,
        filters=view.filters,
        columns=view.columns,
        sort_by=view.sort_by,
    )
    db.add(db_view)
    db.commit()
    db.refresh(db_view)
    return db_view


@router.get("/views/{view_id}", response_model=CustomViewResponse)
def get_custom_view(view_id: int, db: Session = Depends(get_db)):
    """
    Get a custom view by ID.

    Args:
        view_id: Custom view ID
        db: Database session

    Returns:
        Custom view details
    """
    view = db.query(CustomView).filter(CustomView.id == view_id).first()
    if not view:
        raise HTTPException(status_code=404, detail="Custom view not found")
    return view


@router.put("/views/{view_id}", response_model=CustomViewResponse)
def update_custom_view(
    view_id: int, view: CustomViewCreate, db: Session = Depends(get_db)
):
    """
    Update an existing custom view.

    Args:
        view_id: Custom view ID
        view: Updated view data
        db: Database session

    Returns:
        Updated custom view
    """
    db_view = db.query(CustomView).filter(CustomView.id == view_id).first()
    if not db_view:
        raise HTTPException(status_code=404, detail="Custom view not found")

    # Check if trying to rename to an existing view name
    if view.name != db_view.name:
        existing = (
            db.query(CustomView)
            .filter(
                CustomView.project_id == db_view.project_id,
                CustomView.name == view.name,
                CustomView.id != view_id,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A view with this name already exists for this project",
            )

    # Update fields
    db_view.name = view.name
    db_view.filters = view.filters
    db_view.columns = view.columns
    db_view.sort_by = view.sort_by

    db.commit()
    db.refresh(db_view)
    return db_view


@router.delete("/views/{view_id}")
def delete_custom_view(view_id: int, db: Session = Depends(get_db)):
    """
    Delete a custom view.

    Args:
        view_id: Custom view ID
        db: Database session

    Returns:
        Success message
    """
    view = db.query(CustomView).filter(CustomView.id == view_id).first()
    if not view:
        raise HTTPException(status_code=404, detail="Custom view not found")

    db.delete(view)
    db.commit()
    return {"message": "Custom view deleted successfully"}
