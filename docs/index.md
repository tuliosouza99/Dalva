# TrackAI Documentation

> A lightweight, self-hosted experiment tracker for deep learning

TrackAI is a minimal alternative to tools like Weights & Biases and Neptune.ai. It provides a simple Python API for logging experiments and a clean web interface for visualizing and comparing results.

## Features

- **Simple Python API** - trackio-compatible interface for easy migration from Neptune.ai
- **Self-Hosted** - All data stored locally in DuckDB or S3
- **Flexible Metrics** - Log any metrics without predefined schemas
- **Real-time Visualization** - Interactive charts with Plotly.js
- **Run Comparison** - Compare metrics across multiple experiments
- **Resume Support** - Continue logging to existing runs with flexible resume modes
- **S3 Storage** - Optional S3 backend with split architecture for performance
- **Lightweight** - No complex setup or external dependencies
- **Project Organization** - Group experiments by project, groups, and tags
- **CLI Management** - Unified `trackai` command for server and database operations

## Installation

### Using uv (Recommended)

```bash
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI
cd backend && uv sync
```

### Using pip

```bash
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI/backend
pip install -e .
```

### Optional Documentation Dependencies

To build documentation locally:

```bash
cd backend && uv sync --group docs
```

## Quick Start

### Start the Server

```bash
# Production mode (auto-finds available port starting from 8000)
trackai server start

# Or specify a port
trackai server start --port 8080

# Development mode with hot reload (separate backend and frontend ports)
trackai server dev
```

### Log Your First Experiment

```python
import trackai

# Initialize a run
with trackai.init(project="my-project", config={"lr": 0.001}) as run:
    for step in range(100):
        # Log training metrics
        trackai.log({"loss": 0.5, "accuracy": 0.8}, step=step)

        # Log system metrics (GPU, memory, etc.)
        trackai.log_system({"gpu_util": 0.95, "memory_gb": 8.2})
```

### View in Web Interface

Open your browser to the URL shown by `trackai server start` (default: http://localhost:8000) to view:

- **Projects Dashboard** - Overview of all projects
- **Runs Table** - Filterable, sortable experiments
- **Run Details** - Metrics with interactive charts
- **Run Comparison** - Side-by-side comparisons

## What's Next?

### Getting Started Guides

- [Installation](getting_started/installation.md) - Detailed installation instructions
- [Quick Start](getting_started/quickstart.md) - 5-minute tutorial
- [Python SDK](getting_started/python_sdk.md) - Complete SDK guide
- [CLI Usage](getting_started/cli_usage.md) - Server and database commands
- [S3 Storage](getting_started/s3_storage.md) - Configure cloud storage

### API Documentation

- [Python SDK Reference](api_documentation/python_sdk/init.md) - Auto-generated API docs
- [REST API](getting_started/rest_api.md) - HTTP endpoints guide
- [CLI Reference](api_documentation/cli/server.md) - Command-line interface

### Migration

- [Migration from Neptune.ai](getting_started/migration_from_neptune.md) - Switch from Neptune

## Key Concepts

### Database Storage

TrackAI uses **DuckDB** for efficient analytics on experiment data. The database is stored at:

```
~/.trackai/trackai.duckdb
```

This centralized location allows you to access experiments from any project directory.

### Metrics Model

TrackAI uses an **EAV (Entity-Attribute-Value)** model for metrics, allowing you to log any metric structure without predefined schemas:

- **Step-based metrics**: Training metrics (loss, accuracy) with step numbers
- **Timestamp-based metrics**: System metrics (GPU, memory) with timestamps

### Resume Modes

Runs support three resume modes for checkpoint recovery:

- `resume="never"` - Always create a new run (default)
- `resume="allow"` - Resume if exists, otherwise create new
- `resume="must"` - Must resume existing run or fail

### S3 Split Architecture

When S3 storage is configured, TrackAI uses a unique split architecture:

- **SDK (logging)**: Downloads database on `init()`, uploads on `finish()` for fast local writes
- **Server (visualization)**: Uses DuckDB ATTACH for read-only S3 access (no downloads, instant startup)

## Architecture

### Backend

- **FastAPI** - Modern Python web framework
- **DuckDB** - High-performance analytics database
- **SQLAlchemy** - ORM for database operations
- **Pydantic** - Data validation
- **Click** - CLI framework

### Frontend

- **React 19** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool
- **TanStack Query** - Data fetching
- **Plotly.js** - Interactive charts
- **Tailwind CSS v4** - Styling

## Community & Support

- **GitHub**: [tuliosouza99/TrackAI](https://github.com/tuliosouza99/TrackAI)
- **Issues**: [Report bugs or request features](https://github.com/tuliosouza99/TrackAI/issues)
- **Examples**: Check `backend/examples/` for complete code examples

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/tuliosouza99/TrackAI/blob/main/LICENSE) file for details.
