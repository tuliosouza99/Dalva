# Metrics and Value Types

Dalva supports different value types that are rendered differently in the web interface.

## Supported Value Types

| Python Type | `attribute_type` | Storage Column | Notes |
|-------------|-----------------|----------------|-------|
| `float` | `float` | `float_value` | Summary metrics (step=None) |
| `int` | `int` | `int_value` | Summary metrics (step=None) |
| `str` | `string` | `string_value` | Summary metrics (step=None) |
| `bool` | `bool` | `bool_value` | Summary metrics (step=None) |
| `float` | `float_series` | `float_value` | Time-series metrics (step=int) |
| `int` | `int_series` | `int_value` | Time-series metrics (step=int) |
| `str` | `string_series` | `string_value` | Time-series metrics (step=int) |
| `bool` | `bool_series` | `bool_value` | Time-series metrics (step=int) |

## Series vs Scalar Types

The `step` parameter determines whether a metric is stored as a **scalar** or **series**:

- **`step=None`** → Scalar types (`float`, `int`, `string`, `bool`)
  - Single values stored without a step index
  - Displayed as a **single value card** in the UI
  - Use for: final metrics, summary statistics, best model performance

- **`step=<int>`** → Series types (`float_series`, `int_series`, `string_series`, `bool_series`)
  - Values stored with a step index (e.g., step=0, step=1, step=2)
  - Displayed as an **interactive chart** in the UI
  - Use for: training curves, epoch-level metrics, iteration metrics

## How Step Determines Type

The type is automatically determined by the `step` parameter:

```python
# step=None → scalar type
run.log({"best_accuracy": 0.95})  # attribute_type="float"

# step=0 → series type
run.log({"accuracy": 0.85}, step=0)  # attribute_type="float_series"
run.log({"accuracy": 0.87}, step=1)  # attribute_type="float_series"
run.log({"accuracy": 0.89}, step=2)  # attribute_type="float_series"
```

## Example: Logging Training Metrics

```python
import dalva

run = dalva.init(project="my-project", name="experiment-1")

# Log training metrics at each epoch (series type → chart)
for epoch in range(100):
    train_loss = 1.0 / (epoch + 1)
    train_acc = min(0.99, epoch / 100)
    run.log({
        "train/loss": train_loss,
        "train/accuracy": train_acc
    }, step=epoch)

# Log summary metrics (scalar type → value card)
run.log({
    "best_model/accuracy": 0.95,
    "best_model/epoch": 87,
    "training_completed": True
})  # step=None by default

run.finish()
```

## Type Enforcement

Once a metric key is used for a run, it **must remain consistent**:

```python
run = dalva.init(project="my-project", name="experiment")

# First log with step=0 → float_series
run.log({"loss": 0.5}, step=0)

# Later, log without step → float (ERROR! Type mismatch)
run.log({"loss": 0.1})  # Raises ValueError: attribute_type mismatch
```

This prevents accidental type mismatches where you forget to add `step`.

## Frontend Rendering

### Scalar Metrics (step=None)

Scalar metrics are displayed as **value cards** in the run's Overview tab:

| Metric | Value |
|--------|-------|
| best_model/accuracy | 0.9523 |
| best_model/hter | 0.0821 |
| training_completed | true |
| best_optimizer | adamw |

### Numeric Series (float_series, int_series)

Numeric series are displayed as **interactive line charts** in the run's Metrics tab. The chart shows the metric value over steps, with hover tooltips for exact values.

### Bool Series (bool_series)

Bool series are displayed as **stacked area charts** with two areas (`true` / `false`) showing cumulative counts over steps.

**Use case — tracking binary states:**

```python
for step in range(50):
    run.log({
        "phase/is_training": step % 10 != 7,
        "phase/is_converged": step >= 30,
    }, step=step)
```

This lets you visualize when a flag flips — for example, when training switches to validation, or when a model converges.

### String Series (string_series)

String series are displayed as **stacked area charts** showing cumulative counts per category over steps. By default the top 3 categories (by total count) are shown as separate areas, with remaining categories grouped under "Other". You can increase the number of visible categories up to `min(10, nunique)` using the selector below the chart.

**Use case — tracking categorical values:**

```python
optimizers = ["adam", "adam", "sgd", "adam", "rmsprop", ...]
for step in range(50):
    run.log({
        "hyperparams/optimizer": optimizers[step],
        "phase/name": "train" if step % 8 != 7 else "validate",
    }, step=step)
```

Common scenarios for string series:

| Scenario | Example metric | Categories |
|----------|---------------|------------|
| Training phase | `phase/name` | `train`, `validate`, `test` |
| Optimizer sweep | `hyperparams/optimizer` | `adam`, `sgd`, `rmsprop` |
| Data source region | `infra/region` | `us-east`, `eu-west`, `ap-south` |
| Learning rate schedule | `lr/schedule` | `cosine`, `step`, `constant` |
| Model selection | `model/variant` | `base`, `large`, `xl` |

### Compare Runs View

When comparing multiple runs, categorical metrics display **side-by-side stacked area charts** — one per run — so you can see how category distributions differ across experiments.

## Common Patterns

### Pattern 1: Training Loop with Summary

```python
run = dalva.init(project="my-project", name="training")

best_val_acc = 0.0
for epoch in range(100):
    # Training
    train_loss = compute_loss()
    run.log({"train/loss": train_loss}, step=epoch)
    
    # Validation
    val_acc = evaluate()
    run.log({"val/accuracy": val_acc}, step=epoch)
    
    if val_acc > best_val_acc:
        best_val_acc = val_acc

# Summary metrics (no step)
run.log({
    "best_val_accuracy": best_val_acc,
    "final_epoch": epoch
})

run.finish()
```

### Pattern 2: Hyperparameters as Config

```python
run = dalva.init(
    project="my-project",
    name="experiment-1",
    config={
        "model": "resnet50",
        "lr": 0.001,
        "batch_size": 32,
        "optimizer": "adam"
    }
)
# Config is stored separately from metrics and displayed in the "Config" tab
```

## Metric Naming Conventions

While not required, a common convention uses path-like names:

| Prefix | Usage | Example |
|--------|-------|---------|
| `train/` | Training metrics | `train/loss`, `train/accuracy` |
| `val/` | Validation metrics | `val/loss`, `val/accuracy` |
| `test/` | Test metrics | `test/accuracy`, `test/f1` |
| `best_model/` | Final/best model metrics | `best_model/accuracy` |
| `sys/` | System info | `sys/hostname`, `sys/running_time` |
