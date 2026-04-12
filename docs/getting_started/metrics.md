# Metrics

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

### How Step Determines Type

The type is automatically determined by the `step` parameter:

```python
# step=None → scalar type
run.log({"best_accuracy": 0.95})  # attribute_type="float"

# step=0 → series type
run.log({"accuracy": 0.85}, step=0)  # attribute_type="float_series"
run.log({"accuracy": 0.87}, step=1)  # attribute_type="float_series"
run.log({"accuracy": 0.89}, step=2)  # attribute_type="float_series"
```

### Supported Value Types

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

## When to use Config vs Metrics?

| Aspect | Config | Metrics |
|--------|--------|---------|
| When set | Once at init | Multiple times during run |
| Use case | Hyperparameters | Values that change over time |
| Examples | `lr=0.001`, `model=resnet50` | `loss=0.5`, `accuracy=0.87` |
| Display | Config tab | Overview tab + Charts |

## Repeated Keys (Strict Insert — No Overwrites)

Logging a metric or config with a key that already exists raises a **409 Conflict** error. To overwrite a value, you must explicitly remove it first.

This is intentional: overwrites can silently lose data in concurrent scenarios and make run history unreliable. Every logged value is permanent.

### Metrics

Metric keys are unique per run **per step**. Logging the same metric at the same step raises 409:

```python
run.log({"loss": 0.5}, step=0)   # OK
run.log({"loss": 0.3}, step=0)   # 409 Conflict — use remove() first
run.log({"loss": 0.1}, step=1)   # OK — different step, new row created
```

To overwrite:

```python
run.remove("loss", step=0)        # remove specific step
run.log({"loss": 0.3}, step=0)   # now log the new value
```

### Config

Config keys are unique per run. Adding a duplicate key raises a 409 error. Use `run.log_config()` to add new keys after run creation, or `run.remove_config()` to delete a key before overwriting:

```python
run = dalva.init(project="my-project", config={"lr": 0.001})

# Add more config later:
run.log_config({"batch_size": 32, "epochs": 100})

# Overwrite an existing key — must remove first:
run.remove_config("lr")
run.log_config({"lr": 0.01})        # now succeeds
```

Nested dicts are flattened with `/` as separator:

```python
run.log_config({"optimizer": {"lr": 0.001, "betas": [0.9, 0.999]}})
# Creates keys: optimizer/lr, optimizer/betas
```

### Type Consistency

Once a metric key is logged with a type, it cannot be changed. int and float are treated as distinct types:

```python
run.log({"m": 5}, step=0)       # OK — int_series
run.log({"m": 5.5}, step=0)    # 409 Conflict — cannot change to float_series
```

### Scalar vs Series

You cannot mix scalar (step=NULL) and series (step!=NULL) values for the same key:

```python
run.log({"acc": 0.5})            # OK — scalar
run.log({"acc": 0.9}, step=0)   # 409 Conflict — acc already has scalar values
```

### Removing Metrics and Config

```python
run.remove("loss")              # removes ALL loss entries (all steps)
run.remove("loss", step=5)       # removes only step 5
run.remove_config("lr")         # removes the lr config key
run.log_config({"lr": 0.01})   # log new value after removal
```


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

#### Compare Runs View

When comparing multiple runs, categorical metrics display **side-by-side stacked area charts** — one per run — so you can see how category distributions differ across experiments.
