"""FastAPI application for Dalva."""

from contextlib import asynccontextmanager

import os

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dalva.api.routes import (
    metrics,
    projects,
    run_configs,
    run_metrics,
    runs,
    tables,
    views,
)
from dalva.db.connection import init_db
from dalva.utils.paths import get_static_dir

# Get static directory (works in both dev and installed modes)
try:
    STATIC_DIR = get_static_dir()
except FileNotFoundError as e:
    print(f"WARNING: {e}")
    STATIC_DIR = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    # Initialize database
    init_db()

    yield

    print("Server shutdown complete")


app = FastAPI(
    title="Dalva",
    description="Lightweight experiment tracker for deep learning",
    version="0.1.0",
    lifespan=lifespan,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if os.getenv("DALVA_DEBUG"):
        detail = f"{type(exc).__name__}: {exc}"
    else:
        detail = "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"detail": detail},
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins since we're serving the frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Register routers
app.include_router(projects.router, prefix="/api/projects", tags=["projects"])
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(run_metrics.router, prefix="/api/runs", tags=["run-metrics"])
app.include_router(run_configs.router, prefix="/api/runs", tags=["run-configs"])
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(tables.router, prefix="/api/tables", tags=["tables"])
app.include_router(views.router, prefix="/api/views", tags=["views"])


# Serve frontend static files if available
if STATIC_DIR and STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve the frontend SPA - return index.html for all non-API routes.

        API routes must NOT fall through to here: when the router has no route
        for a path (e.g. '/api/projects' without trailing slash) FastAPI would
        otherwise match this catch-all and return HTML instead of a 404/redirect,
        breaking every API call that omits the trailing slash.
        """
        if full_path.startswith("api"):
            raise HTTPException(status_code=404, detail="Not found")
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:
    print("WARNING: Static files not found. Frontend will not be served.")


if __name__ == "__main__":
    uvicorn.run("dalva.api.main:app", host="0.0.0.0", port=8000, reload=True)
