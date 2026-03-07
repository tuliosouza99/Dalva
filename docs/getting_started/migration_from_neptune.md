# Migration from Neptune.ai

Guide to migrating from Neptune.ai to TrackAI.

## Overview

TrackAI is designed to be **trackio-compatible**, making migration from Neptune.ai straightforward. Most Neptune code works with minimal changes.

## API Compatibility

### Initialization

**Neptune.ai**:
```python
import neptune

run = neptune.init_run(
    project="workspace/project",
    api_token="YOUR_API_TOKEN",
    name="experiment-1",
    tags=["baseline", "resnet50"]
)
```

**TrackAI**:
```python
import trackai

run = trackai.init(
    project="project",  # No workspace needed
    name="experiment-1",
    # No API token needed (local/S3)
    # Tags not yet supported
)
```

### Logging Metrics

**Neptune.ai**:
```python
run["train/loss"].log(0.5)
run["train/accuracy"].log(0.85)
```

**TrackAI**:
```python
trackai.log({"train/loss": 0.5, "train/accuracy": 0.85}, step=epoch)
```

### Logging System Metrics

**Neptune.ai**:
```python
run["sys/gpu/util"].log(0.95)
```

**TrackAI**:
```python
trackai.log_system({"gpu_util": 0.95})
```

### Stopping Run

**Neptune.ai**:
```python
run.stop()
```

**TrackAI**:
```python
trackai.finish()
```

### Context Manager

**Neptune.ai**:
```python
with neptune.init_run(project="workspace/project") as run:
    run["metrics/loss"].log(0.5)
```

**TrackAI**:
```python
with trackai.init(project="project") as run:
    trackai.log({"loss": 0.5}, step=0)
```

## Key Differences

### 1. No Cloud Service

**Neptune.ai**: Requires API token and cloud account

**TrackAI**: Self-hosted, uses local DuckDB or S3

```python
# Neptune - requires cloud account
run = neptune.init_run(
    project="workspace/project",
    api_token="YOUR_API_TOKEN"
)

# TrackAI - no account needed
run = trackai.init(project="project")
```

### 2. Simpler Metric Logging

**Neptune.ai**: Object-based API

```python
run["train/loss"].log(0.5)
run["train/accuracy"].log(0.85)
```

**TrackAI**: Dict-based API (batch logging)

```python
trackai.log({
    "train/loss": 0.5,
    "train/accuracy": 0.85
}, step=epoch)
```

### 3. Explicit Step Numbers

**Neptune.ai**: Auto-increments steps

```python
run["loss"].log(0.5)  # step=0
run["loss"].log(0.4)  # step=1
```

**TrackAI**: Explicit steps recommended

```python
trackai.log({"loss": 0.5}, step=0)
trackai.log({"loss": 0.4}, step=1)
```

### 4. Configuration Handling

**Neptune.ai**: Separate namespace

```python
run["parameters"] = {
    "lr": 0.001,
    "batch_size": 32
}
```

**TrackAI**: Pass to `init()`

```python
run = trackai.init(
    project="p",
    config={"lr": 0.001, "batch_size": 32}
)
```

### 5. Resume Support

**Neptune.ai**: Different API

```python
run = neptune.init_run(
    project="workspace/project",
    with_id="RUN-123",  # Resume specific run
    mode="read-only"
)
```

**TrackAI**: Resume modes

```python
run = trackai.init(
    project="project",
    name="experiment-1",
    resume="allow"  # or "must", "never"
)
```

## Migration Checklist

### 1. Export Neptune Data (Optional)

Download your Neptune experiments:

```python
import neptune

# Fetch run data
project = neptune.init_project(
    project="workspace/project",
    api_token="YOUR_API_TOKEN"
)

runs_table_df = project.fetch_runs_table().to_pandas()
runs_table_df.to_csv("neptune_export.csv")
```

### 2. Install TrackAI

```bash
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI/backend
uv sync
```

### 3. Start TrackAI Server

```bash
trackai server start
```

### 4. Update Python Code

**Before (Neptune)**:
```python
import neptune

run = neptune.init_run(
    project="workspace/my-project",
    api_token="YOUR_API_TOKEN",
    name="experiment-1"
)

run["parameters"] = {
    "lr": 0.001,
    "batch_size": 32
}

for epoch in range(100):
    train_loss = train_one_epoch()
    run["train/loss"].log(train_loss)
    run["train/accuracy"].log(train_acc)

run.stop()
```

**After (TrackAI)**:
```python
import trackai

run = trackai.init(
    project="my-project",
    name="experiment-1",
    config={
        "lr": 0.001,
        "batch_size": 32
    }
)

for epoch in range(100):
    train_loss = train_one_epoch()
    trackai.log({
        "train/loss": train_loss,
        "train/accuracy": train_acc
    }, step=epoch)

trackai.finish()
```

### 5. Import Existing Neptune Data (Optional)

TrackAI includes an import script for Neptune exports:

```bash
# 1. Export data from Neptune (download JSON files)

# 2. Place exports in backend/exports/

# 3. Run import script
cd backend
uv run python scripts/import_exports.py
```

## Feature Comparison

| Feature | Neptune.ai | TrackAI |
|---------|------------|---------|
| **Hosting** | Cloud | Self-hosted |
| **Cost** | Paid plans | Free |
| **Authentication** | API tokens | None (local) or AWS (S3) |
| **Metric Logging** | Object-based | Dict-based |
| **System Metrics** | Built-in | Manual (psutil, pynvml) |
| **File Uploads** | ✅ Yes | ⚠️ Planned |
| **Model Versioning** | ✅ Yes | ❌ No |
| **Collaboration** | ✅ Yes | Via S3 |
| **Custom Dashboards** | ✅ Yes | ✅ Yes |
| **Compare Runs** | ✅ Yes | ✅ Yes |
| **Data Export** | ✅ Yes | ✅ Yes (DuckDB) |
| **Resume Runs** | ✅ Yes | ✅ Yes |

## Migration Examples

### Simple Training Loop

**Neptune**:
```python
import neptune

run = neptune.init_run(project="workspace/project", api_token="TOKEN")
run["parameters"] = {"lr": 0.001}

for epoch in range(100):
    run["train/loss"].log(0.5)

run.stop()
```

**TrackAI**:
```python
import trackai

with trackai.init(project="project", config={"lr": 0.001}) as run:
    for epoch in range(100):
        trackai.log({"train/loss": 0.5}, step=epoch)
```

### PyTorch Integration

**Neptune**:
```python
import neptune
import torch

run = neptune.init_run(project="workspace/project", api_token="TOKEN")
run["parameters"] = {
    "lr": 0.001,
    "batch_size": 32
}

for epoch in range(100):
    train_loss = train(model, dataloader)
    val_loss = validate(model, val_dataloader)

    run["train/loss"].log(train_loss)
    run["val/loss"].log(val_loss)

run.stop()
```

**TrackAI**:
```python
import trackai
import torch

with trackai.init(
    project="project",
    config={"lr": 0.001, "batch_size": 32}
) as run:

    for epoch in range(100):
        train_loss = train(model, dataloader)
        val_loss = validate(model, val_dataloader)

        trackai.log({
            "train/loss": train_loss,
            "val/loss": val_loss
        }, step=epoch)
```

### Hyperparameter Sweeps

**Neptune**:
```python
import neptune

for lr in [0.001, 0.01, 0.1]:
    run = neptune.init_run(
        project="workspace/project",
        api_token="TOKEN",
        name=f"lr-{lr}",
        tags=["lr-sweep"]
    )
    run["parameters/lr"] = lr

    # Train...
    run.stop()
```

**TrackAI**:
```python
import trackai

for lr in [0.001, 0.01, 0.1]:
    with trackai.init(
        project="project",
        name=f"lr-{lr}",
        group="lr-sweep",  # Similar to tags
        config={"lr": lr}
    ) as run:
        # Train...
        pass
```

## Not Yet Supported

The following Neptune features are not yet supported in TrackAI:

### 1. File Uploads

**Neptune**:
```python
run["model/checkpoints"].upload("model.pt")
```

**TrackAI**: Not yet supported (planned)

### 2. Model Registry

**Neptune**: Full model versioning and registry

**TrackAI**: Not supported

### 3. Workspaces

**Neptune**: Multi-workspace organization

**TrackAI**: Single-level projects only

### 4. Tags

**Neptune**: Add/remove tags dynamically

**TrackAI**: Use `group` parameter instead

### 5. Monitoring

**Neptune**: Built-in monitoring dashboards

**TrackAI**: Manual with `log_system()`

### 6. Notebooks

**Neptune**: Jupyter notebook tracking

**TrackAI**: Not supported

## Benefits of TrackAI

**Why migrate**:

1. **Self-hosted** - Full data control, no cloud dependency
2. **Free** - No usage limits or paid plans
3. **Lightweight** - Minimal setup, no complex configuration
4. **Fast** - DuckDB for analytics, local writes
5. **S3 integration** - Optional cloud storage
6. **Open source** - Customize and extend

**When to stay with Neptune**:

- Need model versioning
- Need team collaboration features
- Need file upload support
- Prefer managed service over self-hosting

## Next Steps

- [Installation](installation.md) - Install TrackAI
- [Quick Start](quickstart.md) - Get started quickly
- [Python SDK](python_sdk.md) - Learn the API
- [CLI Usage](cli_usage.md) - Server and database commands
