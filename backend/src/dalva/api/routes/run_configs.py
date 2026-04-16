"""API routes for run configs — log, get, delete."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from dalva.api.models.common import MessageResponse
from dalva.api.models.runs import (
    ConfigGetResponse,
    LogConfigRequest,
    LogResponse,
    RunConfigResponse,
)
from dalva.api.routes._helpers import get_run_or_404
from dalva.db.connection import get_db
from dalva.db.schema import Config
from dalva.services.logger import _log_config

router = APIRouter()


@router.get("/{run_id}/config", response_model=RunConfigResponse)
def get_run_config(run_id: int, db: Session = Depends(get_db)):
    """Get run configuration."""
    get_run_or_404(run_id, db)

    configs = db.query(Config).filter(Config.run_id == run_id).all()
    config_dict = {c.key: json.loads(c.value) if c.value else None for c in configs}

    return config_dict


@router.get(
    "/{run_id}/config/{key:path}",
    response_model=ConfigGetResponse,
    responses={404: {"description": "Run or config key not found"}},
)
def get_config(
    run_id: int,
    key: str,
    db: Session = Depends(get_db),
):
    """Get a specific config key from a run."""
    get_run_or_404(run_id, db)

    config = (
        db.query(Config)
        .filter(
            Config.run_id == run_id,
            Config.key == key,
        )
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Config key '{key}' not found for this run",
        )

    value = json.loads(config.value) if config.value else None

    return ConfigGetResponse(key=key, value=value)


@router.delete("/{run_id}/config/{key:path}", response_model=MessageResponse)
def remove_config(
    run_id: int,
    key: str,
    db: Session = Depends(get_db),
):
    """Remove a config key from a run."""
    get_run_or_404(run_id, db)

    config = (
        db.query(Config)
        .filter(
            Config.run_id == run_id,
            Config.key == key,
        )
        .first()
    )

    if not config:
        raise HTTPException(
            status_code=404,
            detail=f"Config key '{key}' not found for this run",
        )

    db.delete(config)
    db.commit()
    return {"message": f"Config key '{key}' removed"}


@router.post("/{run_id}/config", response_model=LogResponse)
def log_config_remote(
    run_id: int,
    request: LogConfigRequest,
    db: Session = Depends(get_db),
):
    """Add config key-value pairs to a run (strict insert — no overwrites).

    Raises 409 Conflict if any key already exists for the run.
    Use DELETE /api/runs/{run_id}/config/{key} to remove a key first.
    """
    get_run_or_404(run_id, db)

    try:
        _log_config(run_id, request.config, session=db)
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail={"message": "Config logging conflict(s)", "conflicts": [str(e)]},
        )

    db.commit()
    return LogResponse(success=True)
