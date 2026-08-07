<img src="assets/logo.svg" alt="Dalva Logo" width="64" height="64" align="left" style="margin-right: 12px;" />

# Dalva

> A lightweight, self-hosted experiment tracker for deep learning

Dalva provides a simple Python API for logging experiments and a web interface for visualizing results.

## Installation

```bash
# uv
uv add dalva

# pip
pip install dalva
```

## Quick Start

```python
import dalva

# Initialize a daemonless run
run = dalva.init(
    project="my-project",
    name="experiment-1",
    config={"lr": 0.001},
)

# Log metrics
run.log({"loss": 0.5, "accuracy": 0.8}, step=0)
run.log({"loss": 0.3, "accuracy": 0.9}, step=1)

# Finish the run
run.finish()
```

## Features

- **Simple API** - Just `init()`, `log()`, and `finish()`
- **Daemonless Logging** - Durable per-run journals require no server
- **Self-Hosted** - Journals and the DuckDB read model remain local
- **Flexible Metrics** - Log any metrics without schemas
- **Tabular Data** - Track DataFrames alongside runs with `dalva.table()`
- **Web Interface** - Start an on-demand viewer with `dalva ui`
- **Crash Recovery** - Every event is journaled before `log()` returns

## View Experiments

```bash
dalva ui
```

The viewer materializes journal events into DuckDB while it is running. Training
processes never need to connect to it.
