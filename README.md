# TrackAI

> A lightweight, self-hosted experiment tracker for deep learning

TrackAI is a minimal alternative to tools like Weights & Biases and Neptune.ai. It provides a simple Python API for logging experiments and a clean web interface for visualizing and comparing results.

## Features

- **Simple Python API** - trackio-compatible interface for easy migration
- **Self-Hosted** - All data stored locally in SQLite
- **Flexible Metrics** - Log any metrics without predefined schemas
- **Real-time Visualization** - Interactive charts with Plotly.js
- **Run Comparison** - Compare metrics across multiple experiments
- **Resume Support** - Continue logging to existing runs
- **Lightweight** - No complex setup or external dependencies
- **Project Organization** - Group experiments by project and tags

## Quick Start

### Installation

**Backend:**
```bash
cd backend
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
```

### First-Time Setup

Before using TrackAI, run the setup wizard to configure your database:

```bash
trackai init
```

This interactive wizard will:
- Let you choose between local storage or S3 cloud storage
- Initialize the database at `~/.trackai/trackai.duckdb`
- Automatically detect and migrate existing SQLite databases
- For S3 storage: collect AWS credentials and configure cloud sync

**Note**: This is the recommended way to set up TrackAI. After running `trackai init`, you're ready to start the server and log experiments.

### Running the App

**Option 1: Using the CLI (Recommended)**

```bash
# Start the server (serves both backend and frontend)
trackai server start
```

The server will automatically find an available port and display the URL.

**Option 2: Development Mode (for active development)**

```bash
# Start backend and frontend separately with hot reload
trackai server dev
```

**Option 3: Manual Setup (advanced)**

**Terminal 1 - Start the Backend:**
```bash
cd backend
uv run uvicorn trackai.api.main:app --reload
```

**Terminal 2 - Start the Frontend:**
```bash
cd frontend
npm run dev
```

Access the web UI at `http://localhost:5173`

## Python API Usage

### Basic Example

```python
import trackai

# Initialize a run
run = trackai.init(
    project="image-classification",
    name="resnet50-experiment",
    config={
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 100
    }
)

# Log metrics during training
for epoch in range(100):
    train_loss = train_model()
    val_acc = validate_model()

    trackai.log({
        "train/loss": train_loss,
        "val/accuracy": val_acc
    }, step=epoch)

# Finish the run
trackai.finish()
```

### Using Context Manager (Recommended)

```python
import trackai

with trackai.init(project="my-project", config={"lr": 0.001}) as run:
    for step in range(100):
        trackai.log({"loss": 0.5, "accuracy": 0.8}, step=step)
    # Run automatically finished when context exits
```

### Logging System Metrics

```python
import trackai

run = trackai.init(project="my-project")

# Log GPU/system metrics (timestamp-based, not step-based)
trackai.log_system({
    "gpu_utilization": 0.95,
    "memory_used_gb": 8.2,
    "temperature": 75
})

trackai.finish()
```

### Resuming Runs

```python
import trackai

# Resume existing run or create new one
run = trackai.init(
    project="long-training",
    name="week-long-experiment",
    resume="allow"  # or "must" to require existing run
)

trackai.log({"loss": 0.3}, step=1000)
trackai.finish()
```

## REST API

TrackAI provides a comprehensive REST API for integrating with other tools.

### Projects

- `GET /api/projects` - List all projects
- `GET /api/projects/{project_id}` - Get project details
- `POST /api/projects` - Create new project
- `DELETE /api/projects/{project_id}` - Delete project

### Runs

- `GET /api/runs` - List runs (with filters, pagination, sorting)
- `GET /api/runs/{run_id}` - Get run details
- `GET /api/runs/{run_id}/summary` - Get run summary with metrics
- `POST /api/runs` - Create new run
- `PATCH /api/runs/{run_id}/state` - Update run state
- `DELETE /api/runs/{run_id}` - Delete run

### Metrics

- `GET /api/metrics/runs/{run_id}` - List all metric names
- `GET /api/metrics/runs/{run_id}/metric/{metric_path}` - Get metric values
- `POST /api/metrics/compare` - Compare metrics across runs

## Database

### Location

TrackAI stores all data in a centralized SQLite database:
```
~/.trackai/trackai.db
```

This allows you to access experiments from any project directory.

### Custom Database Location

Override the default location using an environment variable:

```bash
export TRACKAI_DB_PATH=/path/to/custom/database.db
```

Or in Python:
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
cp ~/.trackai/trackai.db ~/backups/trackai-$(date +%Y%m%d).db
```

**Reset (warning: deletes all data):**
```bash
rm ~/.trackai/trackai.db
```

## Web Interface

The TrackAI web interface provides:

- **Projects Dashboard** - Overview of all projects with run statistics
- **Runs Table** - Filterable, sortable table of all experiments
- **Run Details** - Detailed view of individual runs with all metrics
- **Metric Charts** - Interactive visualizations with zoom, pan, and hover
- **Run Comparison** - Side-by-side comparison of multiple experiments
- **Custom Dashboards** - Create custom layouts with metric widgets

## Development

### Tech Stack

**Backend:**
- FastAPI - Web framework
- SQLAlchemy - ORM
- SQLite - Database
- Pandas + PyArrow - Data processing
- Pydantic - Data validation

**Frontend:**
- React 19 + TypeScript
- Vite - Build tool
- TanStack Query - Data fetching
- Plotly.js - Charts
- Tailwind CSS - Styling
- React Router - Navigation

### Running Tests

**Backend:**
```bash
cd backend
uv run pytest
```

**Frontend:**
```bash
cd frontend
npm test
```

### Project Structure

```
TrackAI/
├── backend/
│   ├── src/trackai/
│   │   ├── __init__.py       # Public Python API
│   │   ├── run.py            # Run class
│   │   ├── api/              # FastAPI routes
│   │   ├── db/               # Database schema & connection
│   │   └── services/         # Business logic
│   ├── examples/             # Example scripts
│   └── scripts/              # Utility scripts
└── frontend/
    ├── src/
    │   ├── api/              # API client & hooks
    │   ├── components/       # React components
    │   ├── pages/            # Page components
    │   └── App.tsx           # Main app
    └── package.json
```

## Examples

Check the `backend/examples/` directory for complete examples:

```bash
# Simple logging example
uv run python backend/examples/simple_experiment.py

# Context manager example
uv run python backend/examples/context_manager.py

# Resume run example
uv run python backend/examples/resume_run.py
```

## Import Existing Data

TrackAI can import data from Neptune.ai exports:

```bash
# Place export files in backend/exports/
uv run python backend/scripts/import_exports.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
