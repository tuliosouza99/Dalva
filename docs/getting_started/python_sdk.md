# Python SDK

Complete guide to using the TrackAI Python SDK for logging experiments.

See the [API Reference](../api_documentation/python_sdk/init.md) for detailed function signatures.

## Overview

TrackAI provides a simple Python API inspired by trackio (Neptune.ai SDK) for easy migration. The API consists of four main functions:

- `trackai.init()` - Initialize a new run
- `trackai.log()` - Log training metrics with steps
- `trackai.log_system()` - Log system metrics with timestamps
- `trackai.finish()` - Complete the run

## Basic Workflow

### Standard Pattern

```python
import trackai

# 1. Initialize a run
run = trackai.init(
    project="my-project",
    name="experiment-1",
    config={"lr": 0.001, "batch_size": 32}
)

# 2. Log metrics during training
for step in range(100):
    trackai.log({"loss": 0.5, "accuracy": 0.8}, step=step)

# 3. Finish the run
trackai.finish()
```

### Context Manager Pattern (Recommended)

The context manager pattern automatically calls `finish()` on exit:

```python
import trackai

with trackai.init(project="my-project") as run:
    for step in range(100):
        trackai.log({"loss": 0.5}, step=step)
    # Run automatically finished when context exits
```

Benefits:
- Automatic cleanup on success
- Automatic failure marking on exceptions
- S3 upload on context exit (if configured)

## Initializing Runs

### Basic Initialization

```python
import trackai

run = trackai.init(project="image-classification")
```

This creates a run with:
- Auto-generated run ID (e.g., `RUN20240101_123456`)
- Auto-generated run name (e.g., `run-1`)
- State: "running"

### With Custom Name and Config

```python
run = trackai.init(
    project="image-classification",
    name="resnet50-experiment",
    config={
        "model": "resnet50",
        "learning_rate": 0.001,
        "batch_size": 32,
        "optimizer": "adam",
        "weight_decay": 0.0001
    }
)
```

### With Groups

Use groups to organize related experiments (e.g., hyperparameter sweeps):

```python
run = trackai.init(
    project="image-classification",
    name="lr-0.01",
    group="learning-rate-sweep",
    config={"lr": 0.01}
)
```

## Logging Metrics

### Step-Based Metrics

Training metrics use steps for the x-axis:

```python
import trackai

with trackai.init(project="training") as run:
    for epoch in range(100):
        # Log multiple metrics at once
        trackai.log({
            "train/loss": 0.5,
            "train/accuracy": 0.85,
            "val/loss": 0.6,
            "val/accuracy": 0.80
        }, step=epoch)
```

### Auto-Incrementing Steps

If you don't provide a step number, TrackAI auto-increments:

```python
with trackai.init(project="training") as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5})  # step=0
        trackai.log({"loss": 0.4})  # step=1
        trackai.log({"loss": 0.3})  # step=2
```

### Nested Metric Paths

Use `/` to create nested metric groups:

```python
trackai.log({
    "train/loss": 0.5,
    "train/accuracy": 0.85,
    "train/f1_score": 0.82,
    "val/loss": 0.6,
    "val/accuracy": 0.80,
    "val/f1_score": 0.78
}, step=epoch)
```

In the web interface, these appear as grouped charts:
- `train/` metrics in one section
- `val/` metrics in another section

### Logging at Different Frequencies

```python
with trackai.init(project="training") as run:
    for step in range(1000):
        # Log training loss every step
        trackai.log({"train/loss": 0.5}, step=step)

        # Log validation metrics every 10 steps
        if step % 10 == 0:
            trackai.log({"val/accuracy": 0.8}, step=step)

        # Log test metrics every 100 steps
        if step % 100 == 0:
            trackai.log({"test/accuracy": 0.75}, step=step)
```

## Logging System Metrics

System metrics (GPU, CPU, memory) use timestamps instead of steps:

```python
import trackai

with trackai.init(project="monitoring") as run:
    # Log system metrics
    trackai.log_system({
        "gpu_utilization": 0.95,
        "gpu_memory_used_gb": 8.2,
        "gpu_temperature": 75,
        "cpu_percent": 45.2,
        "memory_used_gb": 16.5
    })
```

These metrics are plotted with time on the x-axis instead of steps.

### Combining Training and System Metrics

```python
with trackai.init(project="training") as run:
    for step in range(100):
        # Log training metrics
        trackai.log({"loss": 0.5}, step=step)

        # Log system metrics every 10 steps
        if step % 10 == 0:
            trackai.log_system({
                "gpu_util": 0.95,
                "memory_gb": 8.2
            })
```

## Finishing Runs

### Manual Finish

```python
import trackai

run = trackai.init(project="my-project")
trackai.log({"loss": 0.5}, step=0)
trackai.finish()  # Marks run as "completed"
```

### Automatic Finish (Context Manager)

```python
with trackai.init(project="my-project") as run:
    trackai.log({"loss": 0.5}, step=0)
# Automatically finished on context exit
```

### Finish with S3 Push

If S3 storage is configured, pass `push=True` to upload the database to S3 on finish:

```python
with trackai.init(project="my-project", push=True) as run:
    trackai.log({"loss": 0.5}, step=0)
# Context exit triggers S3 push (because push=True)
```

Use `pull=True` to download from S3 before the run starts:

```python
with trackai.init(project="my-project", pull=True, push=True) as run:
    trackai.log({"loss": 0.5}, step=0)
```

## Resume Support

See [Resuming Runs](resuming_runs.md) for detailed information on resume modes.

Quick example:

```python
# Resume existing run or create new
run = trackai.init(
    project="long-training",
    name="week-long-experiment",
    resume="allow"
)
```

## Global vs Instance Methods

TrackAI supports both global and instance methods:

### Global Methods (Default)

```python
import trackai

run = trackai.init(project="p1")
trackai.log({"loss": 0.5}, step=0)  # Logs to current run
trackai.finish()
```

### Instance Methods

```python
import trackai

run = trackai.init(project="p1")
run.log({"loss": 0.5}, step=0)  # Logs to this specific run
run.finish()
```

Both approaches work identically. Use whichever is more convenient for your workflow.

## Error Handling

### Catching Exceptions

```python
import trackai

try:
    with trackai.init(project="my-project") as run:
        for step in range(100):
            trackai.log({"loss": train()}, step=step)
            # If exception occurs, run is marked as "failed"
except Exception as e:
    print(f"Training failed: {e}")
    # Run is automatically marked as failed
```

### No Active Run Error

```python
import trackai

# This will raise an error
trackai.log({"loss": 0.5})  # RuntimeError: No active run

# Must call init() first
run = trackai.init(project="p1")
trackai.log({"loss": 0.5})  # ✅ Works
```

## Best Practices

1. **Use context managers** - Ensures runs are always finished, even on errors
2. **Use nested metric paths** - Groups related metrics in the UI (`train/loss`, `val/loss`)
3. **Log at consistent steps** - Makes charts easier to compare
4. **Include configuration** - Always pass `config` dict with hyperparameters
5. **Use groups** - Organize related experiments (sweeps, ablations)
6. **Separate system metrics** - Use `log_system()` for GPU/memory, not `log()`

## Complete Example

```python
import trackai
import time

# Training configuration
config = {
    "model": "resnet50",
    "lr": 0.001,
    "batch_size": 32,
    "optimizer": "adam",
    "epochs": 100
}

# Initialize run with context manager
with trackai.init(
    project="image-classification",
    name="resnet50-baseline",
    group="baseline-experiments",
    config=config
) as run:

    for epoch in range(config["epochs"]):
        # Training phase
        train_loss, train_acc = train_one_epoch()

        # Validation phase
        val_loss, val_acc = validate()

        # Log training metrics
        trackai.log({
            "train/loss": train_loss,
            "train/accuracy": train_acc,
            "val/loss": val_loss,
            "val/accuracy": val_acc,
            "learning_rate": get_current_lr()
        }, step=epoch)

        # Log system metrics every 10 epochs
        if epoch % 10 == 0:
            trackai.log_system({
                "gpu_utilization": get_gpu_util(),
                "memory_used_gb": get_memory_usage()
            })

print("✅ Training completed and logged!")
```

## Next Steps

- [Logging Metrics](logging_metrics.md) - Best practices for metrics
- [System Metrics](system_metrics.md) - GPU and memory monitoring
- [Context Manager](context_manager.md) - Deep dive on context managers
- [Resuming Runs](resuming_runs.md) - Continue logging to existing runs
