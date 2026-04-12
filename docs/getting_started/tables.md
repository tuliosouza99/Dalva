# Tables

Tables let you track **tabular data** alongside your runs. While metrics are time-series values (loss over steps), tables store structured rows like predictions, evaluation results, or dataset statistics.

## Initialize a Table

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

## Log a DataFrame

```python
df = pd.DataFrame({
    "sample_id": [1, 2, 3],
    "label": ["cat", "dog", "bird"],
    "confidence": [0.95, 0.87, 0.72],
    "correct": [True, True, False],
})

table.log(df)
```

## Supported Column Types

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

## Log Modes

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

## Link a Table to a Run

The recommended way to link a table to a run is `run.create_table()`. The table is automatically associated with the same project and run, and `run.finish()` will finish the table too.

```python
run = dalva.init(project="my-project", name="training-run")
# ... log metrics to run ...

table = run.create_table(name="predictions", log_mode="IMMUTABLE")
table.log(predictions_df)

run.finish()  # auto-finishes the table too
```

You can also use `dalva.table()` with an explicit `run_id` for standalone tables:

```python
table = dalva.table(
    project="my-project",
    name="predictions",
    run_id=run.run_id,
)
table.log(predictions_df)
table.finish()
run.finish()
```

## Finish a Table

For tables created via `run.create_table()`, calling `run.finish()` will automatically finish the table. You can also finish a table explicitly:

```python
table.finish()
```

Calling `finish()` multiple times is safe — it's a no-op after the first call.

## Table Object

The `Table` object has these properties:

- `table_id` - System-generated unique identifier (e.g., "ABC-T1")
- `name` - User-defined display name
- `project` - Project name

See the [Table Class API documentation](../api_documentation/table_class.md) for the full reference.

## Resuming Tables

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
