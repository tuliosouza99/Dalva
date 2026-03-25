# Python SDK

## Overview

Dalva's Python API lets you log experiments:

- `dalva.init()` - Initialize a new run or resume an existing one
- `run.log()` - Log metrics with steps
- `run.finish()` - Complete the run

## Initialize a Run

```python
import dalva

run = dalva.init(
    project="my-project",
    name="experiment-1",
    config={"lr": 0.001, "batch_size": 32}
)
```

**Parameters:**
- `project` (required) - Project name
- `name` (optional) - Human-readable run name
- `config` (optional) - Configuration dictionary
- `resume` (optional) - Run ID to resume an existing run

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

## Finish the Run

```python
run.finish()
```

## Run Object

The `Run` object returned by `init()` has these properties:

- `run_id` - System-generated unique identifier (e.g., "ABC-1")
- `name` - User-defined display name
- `project` - Project name
- `state` - Run state (running, finished, etc.)

## Resuming Runs

Pass the `run_id` to `resume` to continue a previous run:

```python
import dalva

# Resume an existing run
run = dalva.init(
    project="my-project",
    resume="ABC-1"  # The run_id to resume
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
    resume="ABC-1"
)
run2.log({"loss": 0.6}, step=2)
run2.log({"loss": 0.4}, step=3)
run2.finish()
```

## Example

```python
import dalva

run = dalva.init(
    project="image-classification",
    name="resnet50-exp",
    config={"model": "resnet50", "lr": 0.001}
)

for epoch in range(100):
    loss = 1.0 / (epoch + 1)
    accuracy = min(0.95, epoch / 100)

    run.log({
        "train/loss": loss,
        "train/accuracy": accuracy
    }, step=epoch)

run.finish()
```
