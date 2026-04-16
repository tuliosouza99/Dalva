# Dalva

> A lightweight, self-hosted experiment tracker for deep learning

Dalva provides a simple Python API for logging experiments and a clean web interface for visualizing and comparing results.

For more information on using Dalva, please refer to the [documentation](https://tuliosouza99.github.io/Dalva/).

## Features

- **Simple Python API** - Easy-to-use Python interface
- **Self-Hosted** - All data stored locally in DuckDB
- **Flexible Metrics** - Log any metrics without predefined schemas
- **Tabular Data** - Track structured rows alongside runs with `DalvaSchema` + `dalva.table()`
- **Real-time Visualization** - Interactive charts with Plotly.js
- **Run Comparison** - Compare metrics across multiple experiments
- **Resume Support** - Continue logging to existing runs
- **Crash Recovery** - Automatic WAL persistence + `dalva sync` for replaying lost operations
- **CLI Query Tools** - Read-only CLI commands for monitoring experiments (`dalva query`)
- **Agent-Friendly** - JSON output by default, designed for LLM agent consumption
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

### Running the App

**Option 1: Using the CLI (Recommended)**

```bash
# Start the server (serves both backend and frontend)
dalva server start
```

The server will automatically find an available port and display the URL.

**Option 2: Development Mode (for active development)**

```bash
# Start backend and frontend separately with hot reload
dalva server dev
```

**Option 3: Manual Setup (advanced)**

**Terminal 1 - Start the Backend:**
```bash
cd backend
uv run uvicorn dalva.api.main:app --reload
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
import dalva

# Initialize a run
run = dalva.init(
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

    run.log({
        "train/loss": train_loss,
        "val/accuracy": val_acc
    }, step=epoch)

# Finish the run
run.finish()
```

### Tabular Data

Define a schema and log structured rows:

```python
import dalva

class PredictionSchema(dalva.DalvaSchema):
    sample_id: int
    label: str
    confidence: float

run = dalva.init(project="image-classification", name="resnet-eval")
table = run.create_table(schema=PredictionSchema, name="predictions")

table.log_row({"sample_id": 1, "label": "cat", "confidence": 0.95})
table.log_rows([
    {"sample_id": 2, "label": "dog", "confidence": 0.87},
    {"sample_id": 3, "label": "bird", "confidence": 0.72},
])

run.finish()  # auto-finishes the table
```

### Resuming Runs

```python
import dalva

# Resume an existing run
run = dalva.init(
    project="image-classification",
    resume_from="resnet50-experiment"  # Pass run_id or run name to resume
)

# Continue logging
run.log({"loss": 0.1}, step=100)
run.finish()
```

## Web Interface

The Dalva web interface provides:

- **Projects Dashboard** - Overview of all projects with run statistics
- **Runs Table** - Filterable, sortable table of all experiments
- **Run Details** - Detailed view of individual runs with all metrics
- **Metric Charts** - Interactive visualizations with zoom, pan, and hover
- **Categorical Charts** - Stacked area charts for bool and string series
- **Run Comparison** - Side-by-side comparison of multiple experiments
- **Tables View** - Browse tabular data linked to runs with a "Load to Python" code snippet

## CLI Query Tools

Monitor experiments from the terminal or give an LLM agent visibility into training:

```bash
dalva query projects                    # list projects with run counts
dalva query runs --state running        # filter running experiments
dalva query run <run_id>                # run summary (metrics + config)
dalva query metric <run_id> loss        # full metric timeseries
dalva query config <run_id>             # run hyperparameters
dalva query tables --run-id <run_id>    # list tables for a run
dalva query table-data <table_id>       # inspect table rows
dalva query table-stats <table_id>      # per-column statistics
```

All commands output JSON by default (for scripts and agents). Use `--format table` for human-readable output.

See [`dalva skill install`](docs/getting_started/experiment_monitoring.md) for giving an LLM agent autonomous monitoring capabilities.

## Development

### Tech Stack

**Backend:**
- FastAPI - Web framework
- SQLAlchemy - ORM
- DuckDB - Database
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
npm run build:check  # TypeScript type-check (no test runner)
```

### Project Structure

```
Dalva/
├── backend/
│   ├── src/dalva/
│   │   ├── __init__.py       # Public Python API (init, table, DalvaSchema)
│   │   ├── api/              # FastAPI routes + Pydantic models
│   │   ├── cli/              # Click CLI commands
│   │   ├── db/               # Database schema & connection
│   │   ├── sdk/              # Client SDK
│   │   │   ├── run.py        # Run class
│   │   │   ├── table.py      # Table class
│   │   │   ├── schema.py     # DalvaSchema base class
│   │   │   ├── worker.py     # Background SyncWorker thread
│   │   │   └── wal.py        # Write-ahead log manager
│   │   ├── services/         # Business logic
│   │   └── static/           # Frontend build output
│   ├── examples/             # Example scripts
│   └── tests/                # Unit + integration tests
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

# Resume run example
uv run python backend/examples/resume_run.py

# Categorical metrics example (bool & string series)
uv run python backend/examples/categorical_demo.py

# Tabular data with DalvaSchema
uv run python backend/examples/linked_table.py

# Fork runs with tables
uv run python backend/examples/fork_run_full.py

# Crash recovery with WAL
uv run python backend/examples/crash_recovery.py
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
