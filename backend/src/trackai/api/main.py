"""FastAPI application for TrackAI."""

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from trackai.api.routes import mcp, metrics, projects, runs, views
from trackai.config import load_config
from trackai.db.connection import init_db
from trackai.utils.paths import get_static_dir

# Get static directory (works in both dev and installed modes)
try:
    STATIC_DIR = get_static_dir()
except FileNotFoundError as e:
    print(f"WARNING: {e}")
    STATIC_DIR = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application startup and shutdown."""
    config = load_config()

    if config.database.storage_type == "s3":
        print("S3 storage mode enabled - using READ-ONLY access")
        print(f"Reading from: s3://{config.database.s3_bucket}/{config.database.s3_key}")

    # Initialize database (will ATTACH S3 in read-only mode for visualization)
    init_db()

    yield

    # No sync needed in visualization mode
    print("Server shutdown complete")


app = FastAPI(
    title="TrackAI",
    description="Lightweight experiment tracker for deep learning",
    version="0.1.0",
    lifespan=lifespan,
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
app.include_router(metrics.router, prefix="/api/metrics", tags=["metrics"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
app.include_router(views.router, prefix="/api/views", tags=["views"])


# Serve frontend static files if available
if STATIC_DIR and STATIC_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Serve the frontend SPA - return index.html for all non-API routes."""
        file_path = STATIC_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(STATIC_DIR / "index.html")
else:
    print("WARNING: Static files not found. Frontend will not be served.")


if __name__ == "__main__":
    uvicorn.run("trackai.api.main:app", host="0.0.0.0", port=8000, reload=True)
