# Runs

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
- `fork_from` (optional) - Run ID to fork from (creates a copy with config/metrics)
- `copy_tables_on_fork` (optional) - `False` (default, no tables), `True` (all tables), or a list of table IDs. Only used with `fork_from`.
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

## Forking Runs

Pass the `run_id` to `fork_from` to create a **copy** of an existing run. The forked run starts with the same config and metrics as the source, but is an independent run you can continue logging to.

```python
import dalva

# Create the original run
run1 = dalva.init(
    project="my-project",
    name="baseline",
    config={"lr": 0.01, "batch_size": 32},
)
run1.log({"loss": 1.0}, step=0)
run1.log({"loss": 0.7}, step=1)
run1.finish()

# Fork it — creates a new run with copied config + metrics
run2 = dalva.init(
    project="my-project",
    fork_from=run1.run_id,
)
# run2 has the same config and metrics as run1, plus a new run_id
run2.log({"loss": 0.4}, step=2)  # continue logging
run2.finish()
```

### Custom Name

By default, the forked run is named `"fork of {source_name}"`. Override with `name`:

```python
run2 = dalva.init(
    project="my-project",
    name="tuned-lr",
    fork_from=run1.run_id,
)
```

### Copying Tables

Use `copy_tables_on_fork` to copy tables from the source run:

```python
# Copy all tables (including their rows)
run2 = dalva.init(
    project="my-project",
    fork_from=run1.run_id,
    copy_tables_on_fork=True,
)

# Copy only specific tables by their database IDs
run2 = dalva.init(
    project="my-project",
    fork_from=run1.run_id,
    copy_tables_on_fork=[5, 7],
)

# Don't copy any tables (default)
run2 = dalva.init(
    project="my-project",
    fork_from=run1.run_id,
    copy_tables_on_fork=False,
)
```

### Fork vs Resume

| | `resume_from` | `fork_from` |
|---|---|---|
| **Creates new run?** | No — continues the same run | Yes — creates a new independent run |
| **Config** | Must match existing | Copied from source |
| **Metrics** | Appended to same history | Copied to new run |
| **Tables** | Same tables | Optionally copied |
| **Use case** | Resuming interrupted training | Branching off a new experiment |

### Chained Forks

You can fork a forked run:

```python
run1 = dalva.init(project="my-project", config={"lr": 0.01})
run1.log({"loss": 1.0}, step=0)
run1.finish()

run2 = dalva.init(project="my-project", fork_from=run1.run_id)
run2.log({"loss": 0.5}, step=1)
run2.finish()

run3 = dalva.init(project="my-project", fork_from=run2.run_id)
# run3 inherits all config + metrics from both run1 and run2
```

## Finish the Run

```python
run.finish()
```

If you created tables via `run.create_table()`, they will be finished automatically before the run is marked complete. Calling `finish()` multiple times is safe.
