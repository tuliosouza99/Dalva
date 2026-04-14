<img src="assets/logo.svg" alt="Dalva Logo" width="64" height="64" align="left" style="margin-right: 12px;" />

# Dalva

> A lightweight, self-hosted experiment tracker for deep learning

Dalva provides a simple Python API for logging experiments and a web interface for visualizing results.

## Quick Start

```python
import dalva

# Initialize a run (server must be running)
run = dalva.init(
    project="my-project",
    name="experiment-1",
    config={"lr": 0.001},
    server_url="http://localhost:8000"
)

# Log metrics
run.log({"loss": 0.5, "accuracy": 0.8}, step=0)
run.log({"loss": 0.3, "accuracy": 0.9}, step=1)

# Finish the run
run.finish()
```

## Features

- **Simple API** - Just `init()`, `log()`, and `finish()`
- **Self-Hosted** - Data stored locally in DuckDB
- **Flexible Metrics** - Log any metrics without schemas
- **Tabular Data** - Track DataFrames alongside runs with `dalva.table()`
- **Web Interface** - View and compare experiments at `http://localhost:8000`
- **Crash Recovery** - Automatic WAL persistence + `dalva sync` for replaying lost operations

## Installation

```bash
git clone https://github.com/tuliosouza99/Dalva.git
cd Dalva/backend && uv sync
```

## Start the Server

```bash
dalva server start
```

Open [http://localhost:8000](http://localhost:8000) to access the web interface.

!!! important
    The Dalva server must be running before logging experiments. The Python SDK communicates with the server via HTTP at the specified `server_url`.
