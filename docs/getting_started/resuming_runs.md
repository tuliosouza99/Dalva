# Resuming Runs

## Overview

To resume a run, pass the `run_id` to `resume` parameter when initializing:

```python
import trackai

# Resume an existing run
run = trackai.init(
    project="my-project",
    resume="ABC-1"  # The run_id to resume
)

# Continue logging
run.log({"loss": 0.2}, step=2)
run.finish()
```

## Key Concepts

- **run_id** - System-generated unique identifier (e.g., "ABC-1")
- **name** - User-defined display name (optional)

## Example

```python
import trackai

# First run
run1 = trackai.init(project="training", name="my-experiment")
run1.log({"loss": 1.0}, step=0)
run1.log({"loss": 0.8}, step=1)
run1.finish()

print(f"Run ID: {run1.run_id}")  # e.g., "ABC-1"

# Later, resume the same run
run2 = trackai.init(
    project="training",
    resume="ABC-1"  # Pass the run_id to resume
)
run2.log({"loss": 0.6}, step=2)
run2.log({"loss": 0.4}, step=3)
run2.finish()
```

All metrics will be in the same run.
