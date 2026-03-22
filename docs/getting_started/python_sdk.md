# Python SDK

## Overview

TrackAI provides a simple Python API:

- `trackai.init()` - Initialize a new run
- `run.log()` - Log metrics with steps
- `run.finish()` - Complete the run

## Initialize a Run

```python
import trackai

run = trackai.init(
    project="my-project",
    name="experiment-1",
    config={"lr": 0.001, "batch_size": 32}
)
```

- `project` (required) - Project name
- `name` (optional) - Human-readable run name
- `config` (optional) - Configuration dictionary

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

## Example

```python
import trackai

run = trackai.init(
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
