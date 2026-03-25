# Dalva Backend

Lightweight experiment tracker backend built with FastAPI.

## Setup

### Install dependencies

```bash
uv sync
```

### Run the server

```bash
uv run python src/dalva/api/main.py
```

Or with uvicorn directly:

```bash
uv run uvicorn dalva.api.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Projects
- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project with summary
- `POST /api/projects` - Create new project
- `DELETE /api/projects/{project_id}` - Delete project

### Runs
- `GET /api/runs` - List runs (with filters, pagination, sorting)
- `GET /api/runs/{run_id}` - Get run details
- `GET /api/runs/{run_id}/summary` - Get run summary with metrics
- `GET /api/runs/{run_id}/config` - Get run configuration
- `POST /api/runs` - Create new run
- `PATCH /api/runs/{run_id}/state` - Update run state
- `DELETE /api/runs/{run_id}` - Delete run

### Metrics
- `GET /api/metrics/runs/{run_id}` - List all metric names
- `GET /api/metrics/runs/{run_id}/metric/{metric_path}` - Get metric values
- `POST /api/metrics/compare` - Compare metrics across runs

## Database

### Location

The DuckDB database is stored at:
```
~/.dalva/dalva.duckdb
```

This centralized location allows you to access experiments from any project directory.

### Custom Location

Override the default location using the `DALVA_DB_PATH` environment variable:

```bash
export DALVA_DB_PATH=/path/to/custom/database.db
uv run python train.py
```

Or set it in your Python code before importing dalva:

```python
import os
os.environ['DALVA_DB_PATH'] = './project_specific.db'
import dalva
```

### Database Management

**Check statistics:**
```bash
dalva db info
```

**Backup:**
```bash
dalva db backup --output ~/backups/dalva-backup.duckdb
```

**Reset (warning: deletes all data):**
```bash
dalva db reset
```

## Python Logging API

Dalva provides a simple Python API for logging experiments directly from your Python code.

### Basic Usage

```python
import dalva

# Initialize a run
run = dalva.init(
    project="my-project",
    name="experiment-1",
    config={"learning_rate": 0.001, "batch_size": 32}
)

# Log training metrics
for step in range(100):
    dalva.log({"loss": 0.5, "accuracy": 0.8}, step=step)

# Log system metrics (without step)
dalva.log_system({"gpu_util": 0.95, "memory_gb": 8.2})

# Finish the run
dalva.finish()
```

### Resume Existing Run

```python
import dalva

# Resume a run to continue logging
run = dalva.init(
    project="my-project",
    name="long-running-experiment",
    resume="allow"  # "allow" or "must"
)

dalva.log({"loss": 0.3}, step=100)
dalva.finish()
```

### Examples

See the `examples/` directory for complete examples:
- `simple_experiment.py` - Basic logging
- `context_manager.py` - Using with statement
- `resume_run.py` - Resuming runs

Run examples:
```bash
uv run python examples/simple_experiment.py
```
ng
- `context_manager.py` - Using with statement
- `resume_run.py` - Resuming runs

Run examples:
```bash
uv run python examples/simple_experiment.py
```
