# AGENTS.md

This file provides guidance to Agents when working with code in this repository.

## Project Overview

TrackAI is a lightweight experiment tracker for deep learning. It consists of a FastAPI backend with a React/TypeScript frontend for visualizing experiments.

## Development Commands

### CLI Installation

TrackAI provides a CLI tool for managing the server and database:

```bash
# Install dependencies (includes CLI)
cd backend && uv sync

# The `trackai` command is now available
trackai --help
```

### First-Time Setup

No setup wizard required. The database (`~/.trackai/trackai.duckdb`) is created automatically the first time you start the server or log an experiment.

**Optional: configure S3 push/pull**:

```bash
trackai config s3 --bucket my-bucket --key trackai.duckdb --region us-east-1
```

This saves S3 coordinates to `~/.trackai/config.json`. Requires AWS credentials in the environment (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`).

### Quick Start (Production Mode)

TrackAI serves both backend and frontend from a single port in production:

```bash
# Start everything (automatically finds available port starting from 8000)
trackai server start

# Or specify a port
trackai server start --port 8080

# Disable auto-reload
trackai server start --no-reload
```

This command:
- Finds the first available port starting from 8000 (if not specified)
- Builds the frontend
- Serves everything from the backend on the selected port

### Development Mode (with Hot Reload)

For active frontend development with hot reload:

```bash
# Run backend and frontend separately
trackai server dev

# Or specify custom ports
trackai server dev --backend-port 8001 --frontend-port 5174
```

This command:
- Finds available ports for both backend (starting from 8000) and frontend (starting from 5173)
- Starts backend and frontend on the selected ports
- Frontend automatically proxies `/api` requests to the backend
- Displays URLs for both servers

**Note**: The old `start.sh` and `dev.sh` scripts are deprecated. Use the `trackai` CLI instead.

### Backend (Python/FastAPI)

The backend uses **uv** for Python dependency management. Always use uv commands:

```bash
# Install dependencies
cd backend && uv sync

# Run the server
cd backend && uv run uvicorn trackai.api.main:app --reload

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
- DuckDB database stored at `~/.trackai/trackai.duckdb` (centralized location)
- Supports both local and S3 storage modes
- Can be overridden via `TRACKAI_DB_PATH` environment variable
- Tables: `projects`, `runs`, `metrics`, `configs`, `files`, `custom_views`, `dashboards`
- Metrics use EAV (Entity-Attribute-Value) model for flexibility
- **S3 Support**: Local-first architecture - all reads/writes use `~/.trackai/trackai.duckdb`; use `pull=True`/`push=True` flags on `trackai.init()` for per-run S3 sync, or `trackai db pull/push` from the CLI

**Key Components**:
- `src/trackai/__init__.py` - Public API (`init()`)
- `src/trackai/run.py` - Run class that manages experiment lifecycle
- `src/trackai/services/logger.py` - LoggingService for database operations
- `src/trackai/api/main.py` - FastAPI app entry point
- `src/trackai/api/routes/` - API route handlers (projects, runs, metrics)
- `src/trackai/db/schema.py` - SQLAlchemy table definitions
- `src/trackai/db/connection.py` - Database connection and initialization

**Python API**:
```python
import trackai

# Create a new run
run = trackai.init(project="my-project", name="my-run", config={"lr": 0.01})
run.log({"loss": 0.5}, step=0)
run.finish()

# Resume an existing run
run = trackai.init(project="my-project", resume="RUN-1")
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
- `PATCH /api/runs/{run_id}/state` - Update run state
- `DELETE /api/runs/{run_id}` - Delete run

**Metrics**:
- `GET /api/metrics/runs/{run_id}` - List all metric names for a run
- `GET /api/metrics/runs/{run_id}/metric/{metric_path}` - Get metric values

## Database Management

**Check statistics**:
```bash
trackai db info
```

**Backup**:
```bash
trackai db backup --output ~/backups/trackai-backup.duckdb
```

**Reset (deletes all data)**:
```bash
trackai db reset
```

**S3 sync** (requires `trackai config s3` + AWS credentials):
```bash
trackai db pull   # Download S3 → ~/.trackai/trackai.duckdb
trackai db push   # Upload ~/.trackai/trackai.duckdb → S3
```

**S3 Configuration**:

TrackAI uses a **local-first architecture** — the database always lives at `~/.trackai/trackai.duckdb`. S3 sync is opt-in:

1. **Experiment Logging (Python SDK)**:
   - Always writes to `~/.trackai/trackai.duckdb` — zero S3 latency during training
   - Pass `pull=True` to `trackai.init()` to download from S3 before the run
   - Pass `push=True` to `trackai.init()` to upload to S3 after the run finishes
   - Both default to `False` — no S3 interaction unless explicitly requested

2. **Visualization Server (FastAPI)**:
   - Always reads from `~/.trackai/trackai.duckdb`
   - Mid-run metrics visible in real time (same file the SDK writes to)
   - Use `trackai db pull` to fetch runs logged on other machines

**Setup**:
```bash
# Set AWS credentials (add to ~/.bashrc or ~/.zshrc)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Configure S3 coordinates
trackai config s3 --bucket my-trackai-experiments --key trackai.duckdb --region us-east-1

# Start the dashboard
trackai server dev

# Log experiments (add pull=True/push=True to sync with S3)
python train.py  # Uses trackai.init() and trackai.finish()
```

**Manual sync**:
```bash
trackai db pull   # Download S3 → ~/.trackai/trackai.duckdb
trackai db push   # Upload ~/.trackai/trackai.duckdb → S3
trackai config show  # View current configuration
```

**Benefits**:
- ✅ **Mid-run visibility** - Dashboard reads local DB, metrics appear during training
- ✅ **Fast logging** - Local writes during training, no S3 latency
- ✅ **No hanging** - Server never touches S3 directly
- ✅ **Simple sync** - `pull` / `push` when you need to share or restore data

## Development Workflow

### Production Mode (Single Port)

Run everything from a single command:

```bash
trackai server start
```

The backend serves the built frontend from the `/static` directory. The CLI automatically finds an available port starting from 8000 and displays the URL.

### Development Mode (Hot Reload)

For active development with frontend hot reload:

```bash
trackai server dev
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

- **Database Engine**: Uses DuckDB instead of SQLite for better analytics performance and S3 support
- **Metrics Storage**: Uses EAV model to support arbitrary metric structures without schema changes
- **Database Location**: Centralized at `~/.trackai/trackai.duckdb` to access experiments from any project
- **S3 Storage**: Local-first architecture - all reads/writes use `~/.trackai/trackai.duckdb`; `pull=True`/`push=True` flags on `trackai.init()` for per-run S3 sync; `trackai db pull/push` for manual CLI sync; no `storage_type` flag needed
- **CLI Management**: Unified `trackai` CLI command for server management, database operations, and configuration
- **Frontend Performance**: Virtualized tables and React Query caching for handling large datasets
- **Resume Support**: Runs can be resumed using `resume="allow"` or `resume="must"` modes
