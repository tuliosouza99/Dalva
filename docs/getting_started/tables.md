# Tables

Tables let you track **tabular data** alongside your runs. While metrics are time-series values (loss over steps), tables store structured rows like predictions, evaluation results, or dataset statistics.

## Define a Schema

Tables require a `DalvaSchema` subclass that defines columns and types:

```python
import dalva

class PredictionSchema(dalva.DalvaSchema):
    sample_id: int
    label: str
    confidence: float
    correct: bool
```

### Supported Column Types

| Type | Python Type | Example |
|------|-------------|---------|
| `int` | `int` | `42` |
| `float` | `float` | `0.95` |
| `bool` | `bool` | `True` |
| `str` | `str` | `"cat"` |
| `list` | `list` | `[1, 2, 3]` |
| `dict` | `dict` | `{"key": "val"}` |
| `null` | `None` | `None` (via `Optional[X]`) |

### Optional Fields

Use `Optional[X]` or `X | None` for nullable columns:

```python
from typing import Optional

class EvalSchema(dalva.DalvaSchema):
    sample_id: int
    label: str
    score: float
    notes: str | None = None
```

## Initialize a Table

### Standalone Table

```python
table = dalva.table(
    project="my-project",
    schema=PredictionSchema,
    name="predictions",
    server_url="http://localhost:8000"
)
```

**Parameters:**

- `project` (required) - Project name
- `schema` (required for new tables) - A `DalvaSchema` subclass defining the table columns
- `name` (optional) - Human-readable table name
- `config` (optional) - Configuration dictionary
- `run_id` (optional) - Run ID string to link this table to a run
- `resume_from` (optional) - Table ID to resume an existing table (schema not needed)
- `server_url` (required) - URL of the Dalva server

### Linked to a Run

The recommended way to link a table to a run is `run.create_table()`:

```python
run = dalva.init(project="my-project", name="training-run")

table = run.create_table(schema=PredictionSchema, name="predictions")
table.log_row({"sample_id": 1, "label": "cat", "confidence": 0.95, "correct": True})

run.finish()  # auto-finishes the table too
```

## Log Rows

### Single Row

```python
table.log_row({
    "sample_id": 1,
    "label": "cat",
    "confidence": 0.95,
    "correct": True,
})
```

`log_row()` is **async** — it enqueues the row and returns immediately.

### Multiple Rows

```python
table.log_rows([
    {"sample_id": 1, "label": "cat", "confidence": 0.95, "correct": True},
    {"sample_id": 2, "label": "dog", "confidence": 0.87, "correct": True},
    {"sample_id": 3, "label": "bird", "confidence": 0.72, "correct": False},
])
```

`log_rows()` is also **async** and batches rows into a single HTTP request.

### Validation

Rows are validated against the schema before enqueueing. Extra fields or wrong types raise a `ValueError`:

```python
table.log_row({"sample_id": 1, "label": "cat", "confidence": "high"})
# ValueError: Input should be a valid number, unable to parse string as a number
```

## Get Table Data

Retrieve all rows from the server:

```python
rows = table.get_table()
for row in rows:
    print(row)
```

For large tables, use streaming to avoid loading all rows into memory:

```python
for row in table.get_table(stream=True):
    process(row)
```

`get_table()` is **synchronous** — it drains the worker queue first to ensure all pending rows are sent.

## Remove All Rows

Remove all rows while keeping the table metadata and schema:

```python
table.remove_table()
```

## Finish a Table

For tables created via `run.create_table()`, calling `run.finish()` will automatically finish the table. You can also finish a table explicitly:

```python
table.finish()
```

Calling `finish()` multiple times is safe — it's a no-op after the first call.

### Error Handling

```python
table.finish(on_error="raise")  # raise DalvaError on accumulated errors
table.finish(on_error="warn")   # print warnings (default)
table.finish(timeout=60)        # custom timeout in seconds
```

## Table Object

The `Table` object has these properties:

- `table_id` - System-generated unique identifier (e.g., "ABC-T1")
- `name` - User-defined display name
- `project` - Project name

See the [Table Class API documentation](../api_documentation/table_class.md) for the full reference.

## Resuming Tables

Resume an existing table by passing `resume_from` with the table ID. No schema is needed — it's loaded from the server:

```python
table = dalva.table(
    project="my-project",
    resume_from="ABC-T1"
)
table.log_rows(new_data)
table.finish()
```

## Complete Example

```python
import dalva

class PredictionSchema(dalva.DalvaSchema):
    sample_id: int
    label: str
    confidence: float
    correct: bool

run = dalva.init(project="image-classification", name="resnet-eval")

table = run.create_table(schema=PredictionSchema, name="predictions")

for batch in eval_dataloader:
    for sample_id, pred, label in evaluate(batch):
        table.log_row({
            "sample_id": sample_id,
            "label": pred,
            "confidence": pred.confidence,
            "correct": pred == label,
        })

run.finish()

rows = table.get_table()
print(f"Accuracy: {sum(r['correct'] for r in rows) / len(rows):.2%}")
```
