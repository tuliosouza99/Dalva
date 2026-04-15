# Python SDK

## Overview

Dalva's Python API lets you log experiments:

- `dalva.init()` - Initialize a new run, resume, or fork an existing one
- `run.log()` - Log metrics with steps (**async** — enqueued to background worker)
- `run.flush()` - Drain pending operations to the server (blocking)
- `run.get()` - Retrieve a specific metric
- `run.remove()` - Remove a metric (required before overwriting)
- `run.log_config()` - Add config keys after init
- `run.get_config()` - Retrieve a config key
- `run.remove_config()` - Remove a config key
- `run.create_table()` - Create a table linked to the run (requires a `DalvaSchema`)
- `run.finish()` - Complete the run and all linked tables
- `dalva.table()` - Initialize a standalone table (not linked to a run)
- `dalva.DalvaSchema` - Base class for defining table column schemas
- `table.log_row()` - Log a single row to the table (**async**)
- `table.log_rows()` - Log multiple rows to the table (**async**)
- `table.get_table()` - Retrieve all rows (synchronous, with optional streaming)
- `table.remove_table()` - Remove all rows from the table
- `table.finish()` - Complete the table

### Async Logging

`run.log()`, `table.log_row()`, and `table.log_rows()` are **asynchronous** — they enqueue operations to a background worker thread and return immediately. This means your training loop is never blocked by network I/O.

The background worker:

- Batches up to 50 operations per HTTP request
- Retries on transient failures (5xx, network errors) with exponential backoff
- Persists unsent operations to a write-ahead log (WAL) for crash recovery

```python
for step in range(1000):
    loss = train_step(step)
    run.log({"loss": loss}, step=step)  # Returns immediately

# Ensure all metrics are sent before finishing
run.finish(timeout=120)  # Drains queue, sends finish, marks complete
```

If `finish()` times out or the process crashes, pending operations are saved to disk. Run `dalva sync` to recover them later. See [Remote Training](remote_training.md#crash-recovery) for details.

## Quick Index

| Topic | File |
|-------|------|
| [Initialize a Run](runs.md) | `dalva.init()`, `resume_from`, `fork_from`, nested config |
| [Log Metrics](metrics.md) | `run.log()`, nested dicts, series vs. scalar |
| [Get / Remove / Re-log](metrics.md#getting-metrics-and-config) | `run.get()`, `run.remove()`, `run.get_config()`, `run.remove_config()` |
| [Tables](tables.md) | `DalvaSchema`, `dalva.table()`, `log_row`, `log_rows` |
| [Config vs Metrics](metrics.md#when-to-use-config-vs-metrics) | When to use each |

## Examples

A complete working example is available at [`examples/nested_metrics_and_config.py`](https://github.com/tuliosouza99/Dalva/tree/main/examples/nested_metrics_and_config.py). |
