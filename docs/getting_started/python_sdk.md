# Python SDK

## Overview

Dalva's Python API lets you log experiments:

- `dalva.init()` - Initialize a new run or resume an existing one
- `run.log()` - Log metrics with steps
- `run.finish()` - Complete the run
- `dalva.table()` - Initialize a new table for tabular data
- `table.log()` - Log a DataFrame to the table
- `table.finish()` - Complete the table

## Initialize a Run

```python
import dalva

run = dalva.init(
    project="my-project",
    name="experiment-1",
    config={"lr": 0.001, "batch_size": 32},
    server_url="http://localhost:8000"
)
```

**Parameters:**

- `project` (required) - Project name
- `name` (optional) - Human-readable run name
- `config` (optional) - Configuration dictionary
- `resume_from` (optional) - Run ID to resume an existing run
- `server_url` (required) - URL of the Dalva server (e.g., `http://localhost:8000`)

## The Config Parameter

The `config` parameter stores **hyperparameters** that remain constant throughout the run. Unlike metrics (which can be logged multiple times), config is set once at initialization.

### What to Put in Config

```python
run = dalva.init(
    project="my-project",
    name="resnet50-experiment",
    config={
        # Model architecture
        "model": "resnet50",
        "num_classes": 1000,
        "pretrained": True,
        
        # Data settings
        "dataset": "imagenet",
        "image_size": 224,
        "augmentation": ["flip", "crop", "color_jitter"],
        
        # Training hyperparameters
        "optimizer": "adam",
        "lr": 0.001,
        "batch_size": 32,
        "epochs": 100,
        "weight_decay": 0.0001,
        
        # Hardware
        "num_workers": 4,
        "device": "cuda",
        
        # Reproducibility
        "seed": 42,
    },
    server_url="http://localhost:8000"
)
```

### Nested Config

Config supports nested dictionaries:

```python
run = dalva.init(
    project="my-project",
    config={
        "model": {
            "backbone": "vit_base",
            "head": "mlp",
            "pretrained": True,
        },
        "optimizer": {
            "name": "adam",
            "lr": 0.001,
            "betas": [0.9, 0.999],
        },
        "data": {
            "train": {"path": "/data/train", "size": 50000},
            "val": {"path": "/data/val", "size": 10000},
        }
    },
    server_url="http://localhost:8000"
)
# Stored as flat keys: model/backbone, optimizer/lr, data/train/path, etc.
```

## Log Metrics

```python
run.log({"loss": 0.5, "accuracy": 0.8}, step=0)
run.log({"loss": 0.3, "accuracy": 0.9}, step=1)
```

You can log multiple metrics at once:

```python
run.log({
    "train/loss": 0.5,
    "train/accuracy": 0.85,
    "val/loss": 0.6,
    "val/accuracy": 0.80
}, step=epoch)
```

### What to Put in Metrics

Metrics track values that change during the run, such as training loss, validation accuracy, or any value you'd want to visualize as a chart over time.

```python
run = dalva.init(project="my-project", name="resnet50-experiment")

best_val_acc = 0.0
for epoch in range(100):
    # Training metrics (logged at each epoch)
    train_loss = compute_loss()
    train_acc = compute_accuracy()
    run.log({
        "train/loss": train_loss,
        "train/accuracy": train_acc
    }, step=epoch)
    
    # Validation metrics (logged at each epoch)
    val_loss = compute_val_loss()
    val_acc = compute_val_accuracy()
    run.log({
        "val/loss": val_loss,
        "val/accuracy": val_acc
    }, step=epoch)
    
    if val_acc > best_val_acc:
        best_val_acc = val_acc

# Summary metrics (logged once, without step)
run.log({
    "best_val_accuracy": best_val_acc,
    "final_epoch": epoch,
    "training_completed": True
})

run.finish()
```

### Metric Types

Metrics can be logged as:

| Type | When to Use | Example |
|------|-------------|---------|
| **Series** (with `step`) | Values that change over time | `run.log({"loss": 0.5}, step=0)` |
| **Scalar** (without `step`) | Final/summary values | `run.log({"best_accuracy": 0.95})` |

### Logging Categorical Metrics

In addition to numeric types (`float`, `int`), you can log `bool` and `str` values to track categorical changes over time. These render as **stacked area charts** instead of line charts.

**Bool series** — track binary flags like training phase, convergence, or early stopping:

```python
for step in range(100):
    run.log({
        "train/loss": train_loss,
        "phase/is_training": step % 10 != 7,
        "phase/is_converged": step >= 50,
    }, step=step)
```

**String series** — track categorical values like optimizer, data source, or phase name:

```python
for step in range(100):
    run.log({
        "train/loss": train_loss,
        "hyperparams/optimizer": current_optimizer,
        "phase/name": "train" if step % 10 != 7 else "validate",
    }, step=step)
```

By default, string series show the top 3 categories as separate areas with the rest grouped as "Other". You can adjust this up to 10 in the chart UI.

See [Metrics & Value Types](../getting_started/metrics_and_types.md) for details on how different types are rendered.

## Why Use Config vs Metrics?

| Aspect | Config | Metrics |
|--------|--------|---------|
| When set | Once at init | Multiple times during run |
| Use case | Hyperparameters | Values that change over time |
| Examples | `lr=0.001`, `model=resnet50` | `loss=0.5`, `accuracy=0.87` |
| Display | Config tab | Overview tab + Charts |

## Finish the Run

```python
run.finish()
```

## Run Object

The `Run` object has these properties:

- `run_id` - System-generated unique identifier (e.g., "ABC-1")
- `name` - User-defined display name
- `project` - Project name
- `state` - Run state (running, finished, etc.)

See the [Run Class API documentation](../api_documentation/run_class.md) for the full reference.

### Understanding run_id

When you create a run, Dalva generates a unique `run_id` for you:

```
ABC-1
```

This ID is:
- **Unique** - No two runs share the same ID
- **Human-readable** - Uses a short prefix and incrementing number (e.g., "ABC-1", "ABC-2")
- **Persistent** - Once assigned, a run's ID never changes

**Where to find your run_id:**

1. **Python** - Access it via the Run object:
   ```python
   run = dalva.init(project="my-project")
   print(f"Run ID: {run.run_id}")  # ABC-1
   ```

2. **Console output** - When you initialize a run, Dalva prints the run ID:
   ```
   Run created: ABC-1
   ```

3. **Frontend** - The run ID is displayed in the run's overview page in the web interface

## Resuming Runs

Pass the `run_id` to `resume_from` to continue a previous run:

```python
import dalva

# Resume an existing run
run = dalva.init(
    project="my-project",
    resume_from="ABC-1"  # The run_id to resume
)

run.log({"loss": 0.2}, step=2)
run.finish()
```

Example continuing a run:

```python
# First run
run1 = dalva.init(project="training", name="my-experiment")
run1.log({"loss": 1.0}, step=0)
run1.log({"loss": 0.8}, step=1)
run1.finish()

print(f"Run ID: {run1.run_id}")  # e.g., "ABC-1"

# Later, resume the same run
run2 = dalva.init(
    project="training",
    resume_from="ABC-1"
)
run2.log({"loss": 0.6}, step=2)
run2.log({"loss": 0.4}, step=3)
run2.finish()
```

## Tables

Tables let you track **tabular data** alongside your runs. While metrics are time-series values (loss over steps), tables store structured rows like predictions, evaluation results, or dataset statistics.

### Initialize a Table

```python
import dalva
import pandas as pd

table = dalva.table(
    project="my-project",
    name="predictions",
    log_mode="IMMUTABLE",
    server_url="http://localhost:8000"
)
```

**Parameters:**

- `project` (required) - Project name
- `name` (optional) - Human-readable table name
- `config` (optional) - Configuration dictionary
- `run_id` (optional) - Run ID string to link this table to a run
- `resume_from` (optional) - Table ID to resume an existing table
- `server_url` (required) - URL of the Dalva server
- `log_mode` (optional) - One of `IMMUTABLE`, `MUTABLE`, or `INCREMENTAL` (default: `IMMUTABLE`)

### Log a DataFrame

```python
df = pd.DataFrame({
    "sample_id": [1, 2, 3],
    "label": ["cat", "dog", "bird"],
    "confidence": [0.95, 0.87, 0.72],
    "correct": [True, True, False],
})

table.log(df)
```

### Supported Column Types

| Type | Python/pandas dtype | Example |
|------|---------------------|---------|
| `int` | `int64`, `int32`, `Int64`, etc. | `42` |
| `float` | `float64`, `float32` | `0.95` |
| `bool` | `bool` | `True` |
| `str` | `object` (string) | `"cat"` |
| `date` | `datetime64` | `"2025-01-15"` |
| `list` | list values | `[1, 2, 3]` |
| `dict` | dict values | `{"key": "val"}` |

Mixed types within a single column are not allowed. All values in a column must be the same type.

### Log Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `IMMUTABLE` | Log exactly once. Re-logging raises an error. | Final evaluation results |
| `MUTABLE` | Each log creates a new version. Only latest shown. | Updating predictions over epochs |
| `INCREMENTAL` | Each log appends rows. Column types must match. | Streaming predictions batch by batch |

```python
# IMMUTABLE - log once
table = dalva.table(project="my-project", name="final-results", log_mode="IMMUTABLE")
table.log(df)
table.finish()

# MUTABLE - re-log creates new version
table = dalva.table(project="my-project", name="epoch-predictions", log_mode="MUTABLE")
table.log(df_epoch_1)  # version 1
table.log(df_epoch_2)  # version 2 (replaces v1 in UI)
table.finish()

# INCREMENTAL - appends rows
table = dalva.table(project="my-project", name="all-predictions", log_mode="INCREMENTAL")
table.log(df_batch_1)  # rows appended
table.log(df_batch_2)  # more rows appended
table.finish()
```

### Link a Table to a Run

Pass the `run_id` to associate a table with a run. The link is visible in both the run detail and table detail pages.

```python
run = dalva.init(project="my-project", name="training-run")
# ... log metrics to run ...

table = dalva.table(
    project="my-project",
    name="predictions",
    run_id=run.run_id,  # link to the run
)

table.log(predictions_df)
table.finish()
run.finish()
```

### Finish a Table

```python
table.finish()
```

### Table Object

The `Table` object has these properties:

- `table_id` - System-generated unique identifier (e.g., "ABC-T1")
- `name` - User-defined display name
- `project` - Project name

See the [Table Class API documentation](../api_documentation/table_class.md) for the full reference.

### Resuming Tables

MUTABLE and INCREMENTAL tables can be resumed. IMMUTABLE tables cannot.

```python
# Resume a MUTABLE or INCREMENTAL table
table = dalva.table(
    project="my-project",
    resume_from="ABC-T1"
)
table.log(new_data)
table.finish()
```
