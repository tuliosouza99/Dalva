"""FastAPI application for TrackAI."""

from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from trackai.api.routes import mcp, metrics, projects, runs, s3, views
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

    if config.database.s3_bucket:
        db_path = Path(config.database.db_path).expanduser()
        print(f"S3 configured — dashboard reads from: {db_path}")
        print("Use 'trackai db pull' to fetch the latest data from S3.")

    # Initialize database
    init_db()

    yield

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
app.include_router(s3.router, prefix="/api", tags=["s3"])


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
    uvicorn.run("trackai.api.main:app", host="0.0.0.0", port=8000, reload=True)
