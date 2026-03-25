# Dalva Examples

This directory contains example scripts demonstrating how to use Dalva for experiment tracking.

## Running Examples

All examples can be run from the backend directory:

```bash
uv run python examples/simple_experiment.py
uv run python examples/context_manager.py
uv run python examples/resume_run.py
```

## Examples Overview

### 1. simple_experiment.py
Basic usage showing:
- Initializing a run with configuration
- Logging training metrics at different steps
- Logging system metrics (GPU, memory)
- Finishing a run manually

```python
import dalva

run = dalva.init(
    project="my-project",
    config={"lr": 0.001}
)

dalva.log({"loss": 0.5, "accuracy": 0.8}, step=0)
dalva.finish()
```

### 2. resume_run.py
Resume an existing run:
- Continue logging to the same run
- Useful for interrupted training
- Supports "allow" and "must" modes

```python
import dalva

# First run
run = dalva.init(project="my-project", name="my-run")
dalva.log({"loss": 1.0}, step=0)
dalva.finish()

# Resume later
run = dalva.init(
    project="my-project",
    name="my-run",
    resume="allow"  # or "must"
)
dalva.log({"loss": 0.5}, step=1)
dalva.finish()
```

## API Reference

### dalva.init()
Initialize a new run or resume an existing one.

**Parameters:**
- `project` (str): Project name
- `name` (str, optional): Run name (auto-generated if not provided)
- `group` (str, optional): Group name for organizing runs
- `config` (dict, optional): Configuration dictionary
- `resume` (str): Resume mode - "never" (default), "allow", or "must"

**Returns:** Run object

### dalva.log()
Log metrics to the current run.

**Parameters:**
- `metrics` (dict): Dictionary of metric name -> value
- `step` (int, optional): Step number (auto-incremented if not provided)

### dalva.log_system()
Log system metrics (GPU, memory, etc.) without a step number.

**Parameters:**
- `metrics` (dict): Dictionary of system metrics

### dalva.finish()
Finish the current run and mark it as completed.

## Viewing Results

After running examples, you can view the results through the API:

```bash
# List all projects
curl http://localhost:8000/api/projects/

# List runs for a project
curl "http://localhost:8000/api/runs/?project_id=2"

# Get run summary
curl http://localhost:8000/api/runs/201/summary

# Get metrics for a run
curl http://localhost:8000/api/metrics/runs/201
```

Or access the API documentation at:
```
http://localhost:8000/docs
```

## Tips

1. **Log configuration** at the start of each run
2. **Use meaningful project and run names** for organization
3. **Group related runs** using the `group` parameter
4. **Log system metrics** periodically to track resource usage
