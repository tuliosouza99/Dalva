# Setup Reference

How to set up Dalva for experiment tracking, from installation to wiring it into a training script.

## Installation and Server

Dalva is installed as a Python package. Once installed, the `dalva` CLI is available.

```bash
pip install dalva          # or: uv add dalva
```

### Starting the Server

The Dalva server is a local FastAPI app backed by DuckDB. Start it before running experiments:

```bash
dalva server start              # production: serves frontend + API on one port
dalva server start --port 8080  # custom port
dalva server start --no-reload  # disable auto-reload

dalva server dev                # development: separate frontend/backend with hot reload
```

Default port is 8000 (auto-detected if occupied). The server creates the database at `~/.dalva/dalva.duckdb` on first use.

### Configuration

```bash
dalva config show   # view current config, file location, env var overrides
```

Config file: `~/.dalva/config.json`. Override DB path with `DALVA_DB_PATH` env var. Override server URL for query commands with `DALVA_SERVER_URL` env var.

### Database Management

```bash
dalva db info      # path, file size, row counts per table
dalva db backup    # copy DB to timestamped backup
dalva db reset     # delete DB (confirmation required)
```

## Wiring Dalva Into a Training Script

### Basic: Track a Run with Metrics and Config

```python
from dalva.sdk import Run

run = Run(
    project="my-project",
    name="baseline-v1",
    config={
        "lr": 0.001,
        "batch_size": 64,
        "epochs": 100,
        "optimizer": "adam",
    },
)

for epoch in range(100):
    train_loss = train_one_epoch(model, dataloader)
    val_loss = evaluate(model, val_dataloader)

    run.log({"train_loss": train_loss, "val_loss": val_loss}, step=epoch)

    if epoch % 10 == 0:
        print(f"Epoch {epoch}: train={train_loss:.4f} val={val_loss:.4f}")

run.finish()
```

### With Tabular Data (Tables)

Tables are for structured row data — predictions, per-layer stats, sweep results, etc.

```python
from dalva.sdk import Run
from dalva.sdk.schema import DalvaSchema
from typing import Optional

class PredictionSchema(DalvaSchema):
    epoch: int
    sample_id: str
    prediction: float
    target: float
    correct: bool

run = Run(project="my-project", name="with-predictions")
table = run.create_table(PredictionSchema, name="predictions")

for epoch in range(10):
    train_loss = train_one_epoch(model, dataloader)

    for sample_id, pred, target in get_predictions(model, val_data):
        table.log_row({
            "epoch": epoch,
            "sample_id": sample_id,
            "prediction": pred,
            "target": target,
            "correct": abs(pred - target) < 0.5,
        })

run.log({"train_loss": train_loss}, step=epoch)

table.finish()
run.finish()
```

### Nested Metrics

Metrics can be nested — they're flattened with `/` as separator:

```python
run.log({
    "train/loss": 0.5,
    "train/accuracy": 0.95,
    "val/loss": 0.6,
    "val/accuracy": 0.92,
}, step=epoch)
```

Query as: `dalva query metric <run_id> train/loss`

### Forking a Run

To create a variant of an existing run (copies configs and metrics):

```python
run2 = Run(
    project="my-project",
    name="higher-lr",
    fork_from="<run_id_of_original>",
    config={"lr": 0.01},  # overrides forked config
)
```

### Resuming a Run

To continue logging to an existing run after a restart:

```python
run = Run(
    project="my-project",
    resume_from="<run_id>",
)
```

## WAL (Write-Ahead Log) and Crash Recovery

Dalva's SDK is asynchronous — `log()` returns immediately and operations are sent in the background. If the process crashes or times out, unsent operations are saved to disk as WAL files in `~/.dalva/outbox/`.

### Recovery Flow

```bash
# Check if there are unsent operations
dalva sync --status

# Preview what would be sent
dalva sync --dry-run

# Replay all pending operations
dalva sync
```

The typical crash recovery pattern:
1. Training script crashes (OOM, SIGKILL, power loss)
2. WAL files survive on disk with unsent metric log requests
3. Restart the server: `dalva server start`
4. Replay: `dalva sync`
5. All data is recovered

### When WAL is Written

- **Normal operation**: Worker appends to WAL before sending HTTP. On successful `finish()`, WAL is deleted
- **Timeout**: If `finish()` or `flush()` times out, remaining queue items are dumped to WAL
- **Crash**: Items already appended to WAL survive. Items still in the in-memory queue (~0.2s window) are lost

## SDK Run API Quick Reference

| Method | Sync/Async | Description |
|--------|-----------|-------------|
| `Run(project, name?, config?, ...)` | Sync | Create a new run |
| `run.log(metrics, step?)` | Async (returns immediately) | Log metrics |
| `run.log_config(config)` | Sync | Add config keys |
| `run.get(key, default?, step?)` | Sync | Get a metric value |
| `run.get_config(key, default?)` | Sync | Get a config value |
| `run.remove(metric, step?)` | Sync | Remove metric(s) |
| `run.flush(timeout?)` | Sync | Drain the send queue |
| `run.finish(on_error?, timeout?)` | Sync | Finish the run |
| `run.create_table(schema, name?, config?)` | Sync | Create a linked table |

## SDK Table API Quick Reference

| Method | Sync/Async | Description |
|--------|-----------|-------------|
| `Table(project, schema?, name?, ...)` | Sync | Create or resume a table |
| `table.log_row(row)` | Async (returns immediately) | Log a single row |
| `table.log_rows(rows)` | Async (returns immediately) | Log multiple rows |
| `table.get_table(stream?)` | Sync | Get all rows |
| `table.remove_table()` | Sync | Remove all rows |
| `table.finish(on_error?, timeout?)` | Sync | Finish the table |

## DalvaSchema

Tables require a schema — a Pydantic `BaseModel` subclass that defines columns:

```python
from dalva.sdk.schema import DalvaSchema
from typing import Optional

class MySchema(DalvaSchema):
    epoch: int
    loss: float
    label: str
    active: bool
    notes: Optional[str] = None
```

Allowed types: `int`, `float`, `str`, `bool`, `None`, `list`, `dict`, `Optional[X]`.

## Server Architecture

- Backend: FastAPI on Uvicorn, DuckDB for storage (single file at `~/.dalva/dalva.duckdb`)
- Frontend: React 19 + TypeScript + Vite, served from `static/` in production
- API prefix: `/api/` — all query commands hit these endpoints
- SPA serving: non-`/api` paths return `index.html` for the web UI
- DuckDB uses `NullPool` — connection is opened and closed per operation, no long-held write locks
