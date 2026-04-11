# 🌠 Dalva

> A lightweight, self-hosted experiment tracker for deep learning

Dalva provides a simple Python API for logging experiments and a clean web interface for visualizing and comparing results.

For more information on using Dalva, please refer to the [documentation](https://tuliosouza99.github.io/Dalva/).

## Features

- **Simple Python API** - Easy-to-use Python interface
- **Self-Hosted** - All data stored locally in DuckDB
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
npm test
```

### Project Structure

```
Dalva/
├── backend/
│   ├── src/dalva/
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

# Resume run example
uv run python backend/examples/resume_run.py

# Categorical metrics example (bool & string series)
uv run python backend/examples/categorical_demo.py
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
