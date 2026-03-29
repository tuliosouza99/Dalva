# AGENTS.md

This file provides guidance to Agents when working with code in this repository.

## Project Overview

Dalva is a lightweight experiment tracker for deep learning. It consists of a FastAPI backend with a React/TypeScript frontend for visualizing experiments.

## Development Commands

### CLI Installation

Dalva provides a CLI tool for managing the server and database:

```bash
# Install dependencies (includes CLI)
cd backend && uv sync

# The `dalva` command is now available
dalva --help
```

### First-Time Setup

No setup wizard required. The database (`~/.dalva/dalva.duckdb`) is created automatically the first time you start the server or log an experiment.

### Quick Start (Production Mode)

Dalva serves both backend and frontend from a single port in production:

```bash
# Start everything (automatically finds available port starting from 8000)
dalva server start

# Or specify a port
dalva server start --port 8080

# Disable auto-reload
dalva server start --no-reload
```

This command:
- Finds the first available port starting from 8000 (if not specified)
- Builds the frontend
- Serves everything from the backend on the selected port

### Development Mode (with Hot Reload)

For active frontend development with hot reload:

```bash
# Run backend and frontend separately
dalva server dev

# Or specify custom ports
dalva server dev --backend-port 8001 --frontend-port 5174
```

This command:
- Finds available ports for both backend (starting from 8000) and frontend (starting from 5173)
- Starts backend and frontend on the selected ports
- Frontend automatically proxies `/api` requests to the backend
- Displays URLs for both servers

**Note**: The old `start.sh` and `dev.sh` scripts are deprecated. Use the `dalva` CLI instead.

### Backend (Python/FastAPI)

The backend uses **uv** for Python dependency management. Always use uv commands:

```bash
# Install dependencies
cd backend && uv sync

# Run the server
cd backend && uv run uvicorn dalva.api.main:app --reload

# Run example scripts
cd backend && uv run python examples/simple_experiment.py
```

### Frontend (React/TypeScript/Vite)

```bash
# Install dependencies
cd frontend && npm install

# Run development server (default: http://localhost:5173)
cd frontend && npm run dev

# Build for production (outputs to ../static)
cd frontend && npm run build

# Build with type checking
cd frontend && npm run build:check

# Lint code
cd frontend && npm run lint
```

## Architecture Overview

### Backend Architecture

**Framework**: FastAPI with SQLAlchemy ORM

**Database**:
- DuckDB database stored at `~/.dalva/dalva.duckdb` (centralized location)
- Can be overridden via `DALVA_DB_PATH` environment variable
- Tables: `projects`, `runs`, `metrics`, `configs`, `custom_views`
- Metrics use EAV (Entity-Attribute-Value) model for flexibility

**Key Components**:
- `src/dalva/__init__.py` - Public API (`init()`)
- `src/dalva/run.py` - HTTP client for the REST API
- `src/dalva/services/logger.py` - Plain functions for database operations
- `src/dalva/api/main.py` - FastAPI app entry point
- `src/dalva/api/routes/` - API route handlers (projects, runs, metrics)
- `src/dalva/db/schema.py` - SQLAlchemy table definitions
- `src/dalva/db/connection.py` - Database connection and initialization

**Python API**:
```python
import dalva

# Requires dalva server running: dalva server start
# server_url defaults to http://localhost:8000

run = dalva.init(
    project="my-project",
    name="my-run",
    config={"lr": 0.01}
)
run.log({"loss": 0.5}, step=0)
run.finish()

# Resume an existing run
run = dalva.init(project="my-project", resume="RUN-1")
run.log({"loss": 0.3}, step=100)
run.finish()
```

### Frontend Architecture

**Framework**: React 19 with TypeScript, Vite build tool

**Key Libraries**:
- React Router v7 - Client-side routing
- TanStack Query (React Query) v5 - Data fetching and caching
- TanStack Virtual - Virtualized tables for performance
- Plotly.js - Interactive charts
- Tailwind CSS v4 - Styling
- React Grid Layout - Dashboard widget layout

**Directory Structure**:
- `src/api/client.ts` - Axios API client and React Query hooks
- `src/pages/` - Page components (ProjectsPage, RunsPage, RunDetailPage, CompareRunsPage)
- `src/components/` - Reusable components
  - `Layout.tsx` - Main app layout with navigation
  - `RunsTable/` - Virtualized table for runs list
  - `Charts/` - Metric visualization components

**Routing**:
- `/projects` - List all projects
- `/projects/:projectId/runs` - List runs for a project
- `/projects/:projectId/dashboard` - Project dashboard
- `/runs/:runId` - Run detail page with metrics
- `/compare` - Compare runs side-by-side

**Data Flow**:
- React Query hooks (defined in `client.ts`) handle all API calls
- 30-second stale time, no refetch on window focus
- Virtualized tables for efficient rendering of large datasets

### API Endpoints

**Projects**:
- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project with summary stats
- `DELETE /api/projects/{project_id}` - Delete project

**Runs**:
- `GET /api/runs` - List runs (supports filters, pagination, sorting)
- `GET /api/runs/{run_id}` - Get run details
- `GET /api/runs/{run_id}/summary` - Get run summary with metrics
- `GET /api/runs/{run_id}/config` - Get run configuration
- `POST /api/runs/init` - Initialize a new run (SDK-facing)
- `POST /api/runs/{run_id}/log` - Log metrics for a run
- `POST /api/runs/{run_id}/finish` - Mark run complete
- `DELETE /api/runs/{run_id}` - Delete run

**Metrics**:
- `GET /api/metrics/runs/{run_id}` - List all metric names for a run
- `GET /api/metrics/runs/{run_id}/metric/{metric_path}` - Get metric values

## Database Management

**Check statistics**:
```bash
dalva db info
```

**Backup**:
```bash
dalva db backup --output ~/backups/dalva-backup.duckdb
```

**Reset (deletes all data)**:
```bash
dalva db reset
```

## Development Workflow

### Production Mode (Single Port)

Run everything from a single command:

```bash
dalva server start
```

The backend serves the built frontend from the `/static` directory. The CLI automatically finds an available port starting from 8000 and displays the URL.

### Development Mode (Hot Reload)

For active development with frontend hot reload:

```bash
dalva server dev
```

The CLI automatically finds available ports for both servers:
- Backend: starts from port 8000
- Frontend: starts from port 5173
- Frontend automatically proxies `/api` requests to the backend's port

### Adding New Features

**Backend**:
1. Update `db/schema.py` if database changes are needed
2. Add route handlers in `api/routes/`
3. Register router in `api/main.py`
4. Add/update service methods in `services/`

**Frontend**:
1. Add API functions and hooks to `api/client.ts`
2. Create page components in `pages/`
3. Add reusable components in `components/`
4. Update routing in `App.tsx`

## Key Design Decisions

- **Database Engine**: Uses DuckDB instead of SQLite for better analytics performance
- **Metrics Storage**: Uses EAV model to support arbitrary metric structures without schema changes
- **Database Location**: Centralized at `~/.dalva/dalva.duckdb` to access experiments from any project
- **CLI Management**: Unified `dalva` CLI command for server management, database operations, and configuration
- **Frontend Performance**: Virtualized tables and React Query caching for handling large datasets
- **Resume Support**: Runs can be resumed using `resume="allow"` or `resume="must"` modes
- **Client-Server Architecture**: SDK is a thin HTTP client; all data flows through the REST API to the server
