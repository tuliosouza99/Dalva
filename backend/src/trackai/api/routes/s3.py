"""S3 management API routes."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from trackai.config import load_config, update_s3_config
from trackai.s3.sync import sync_from_s3, sync_to_s3, validate_s3_credentials

router = APIRouter(prefix="/s3", tags=["s3"])


class S3Config(BaseModel):
    """S3 configuration."""

    bucket: Optional[str] = None
    key: str = "trackai.duckdb"
    region: str = "us-east-1"


class S3ConfigUpdate(BaseModel):
    """S3 configuration update request."""

    bucket: str
    key: str = "trackai.duckdb"
    region: str = "us-east-1"


class S3Status(BaseModel):
    """S3 status response."""

    configured: bool
    credentials_valid: bool
    bucket: Optional[str] = None
    key: Optional[str] = None
    region: Optional[str] = None


class OperationResult(BaseModel):
    """Operation result response."""

    success: bool
    message: str


@router.get("/status", response_model=S3Status)
async def get_s3_status():
    """Get S3 configuration status."""
    config = load_config()
    configured = config.database.s3_bucket is not None
    credentials_valid = validate_s3_credentials() if configured else False

    return S3Status(
        configured=configured,
        credentials_valid=credentials_valid,
        bucket=config.database.s3_bucket,
        key=config.database.s3_key if configured else None,
        region=config.database.s3_region if configured else None,
    )


@router.get("/config", response_model=S3Config)
async def get_s3_config():
    """Get current S3 configuration."""
    config = load_config()
    return S3Config(
        bucket=config.database.s3_bucket,
        key=config.database.s3_key,
        region=config.database.s3_region,
    )


@router.post("/config", response_model=OperationResult)
async def update_s3_config_route(config_update: S3ConfigUpdate):
    """Update S3 configuration."""
    try:
        # Validate credentials before saving
        if not validate_s3_credentials():
            raise HTTPException(
                status_code=400,
                detail="Invalid AWS credentials. Please check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
            )

        update_s3_config(
            bucket=config_update.bucket,
            key=config_update.key,
            region=config_update.region,
        )

        return OperationResult(
            success=True, message="S3 configuration updated successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pull", response_model=OperationResult)
async def pull_from_s3():
    """Pull database from S3 to local storage."""
    try:
        config = load_config()
        if not config.database.s3_bucket:
            raise HTTPException(
                status_code=400,
                detail="S3 not configured. Please configure S3 settings first.",
            )

        if not validate_s3_credentials():
            raise HTTPException(
                status_code=400,
                detail="Invalid AWS credentials. Please check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
            )

        sync_from_s3()
        return OperationResult(
            success=True, message="Database pulled from S3 successfully"
        )
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/push", response_model=OperationResult)
async def push_to_s3():
    """Push local database to S3."""
    try:
        config = load_config()
        if not config.database.s3_bucket:
            raise HTTPException(
                status_code=400,
                detail="S3 not configured. Please configure S3 settings first.",
            )

        if not validate_s3_credentials():
            raise HTTPException(
                status_code=400,
                detail="Invalid AWS credentials. Please check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables.",
            )

        sync_to_s3()
        return OperationResult(
            success=True, message="Database pushed to S3 successfully"
        )
    except HTTPException:
        raise
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
