# TrackAI Backend

Lightweight experiment tracker backend built with FastAPI.

## Setup

### Install dependencies

```bash
uv sync
```

### Run the server

```bash
uv run python src/trackai/api/main.py
```

Or with uvicorn directly:

```bash
uv run uvicorn trackai.api.main:app --reload
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

The SQLite database is stored at:
```
~/.trackai/trackai.db
```

This centralized location allows you to access experiments from any project directory.

### Custom Location

Override the default location using the `TRACKAI_DB_PATH` environment variable:

```bash
export TRACKAI_DB_PATH=/path/to/custom/database.db
uv run python train.py
```

Or set it in your Python code before importing trackai:

```python
import os
os.environ['TRACKAI_DB_PATH'] = './project_specific.db'
import trackai
```

### Database Management

**Check statistics:**
```bash
sqlite3 ~/.trackai/trackai.db "SELECT
  (SELECT COUNT(*) FROM projects) as projects,
  (SELECT COUNT(*) FROM runs) as runs,
  (SELECT COUNT(*) FROM metrics) as metrics;"
```

**Backup:**
```bash
cp ~/.trackai/trackai.db ~/backups/trackai-backup.db
```

**Reset (warning: deletes all data):**
```bash
rm ~/.trackai/trackai.db
```

## Python Logging API

TrackAI provides a simple Python API for logging experiments directly from your Python code.

### Basic Usage

```python
import trackai

# Initialize a run
run = trackai.init(
    project="my-project",
    name="experiment-1",
    config={"learning_rate": 0.001, "batch_size": 32}
)

# Log training metrics
for step in range(100):
    trackai.log({"loss": 0.5, "accuracy": 0.8}, step=step)

# Log system metrics (without step)
trackai.log_system({"gpu_util": 0.95, "memory_gb": 8.2})

# Finish the run
trackai.finish()
```

### Using Context Manager (Recommended)

```python
import trackai

with trackai.init(project="my-project", config={"lr": 0.001}) as run:
    trackai.log({"loss": 0.5}, step=0)
    # Run automatically finished when context exits
```

### Resume Existing Run

```python
import trackai

# Resume a run to continue logging
run = trackai.init(
    project="my-project",
    name="long-running-experiment",
    resume="allow"  # "allow" or "must"
)

trackai.log({"loss": 0.3}, step=100)
trackai.finish()
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
