# Quick Start

Get up and running with TrackAI in 5 minutes.

## 1. Install TrackAI

```bash
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI/backend
uv sync
```

## 2. Start the Server

```bash
trackai server start
```

The server will automatically find an available port and display the URL:

```
🚀 Starting TrackAI server on port 8000...
📊 Access the web interface at http://localhost:8000
```

## 3. Log Your First Experiment

Create a new file `my_experiment.py`:

```python
import trackai
import time
import random

# Initialize a run
with trackai.init(
    project="quickstart",
    name="first-experiment",
    config={
        "learning_rate": 0.001,
        "batch_size": 32,
        "optimizer": "adam"
    }
) as run:
    # Simulate training loop
    for step in range(100):
        # Simulate training metrics
        loss = 1.0 / (step + 1) + random.uniform(-0.1, 0.1)
        accuracy = min(0.95, step / 100 + random.uniform(-0.05, 0.05))

        # Log training metrics
        trackai.log({
            "train/loss": loss,
            "train/accuracy": accuracy
        }, step=step)

        # Log system metrics every 10 steps
        if step % 10 == 0:
            trackai.log_system({
                "gpu_utilization": random.uniform(0.8, 1.0),
                "memory_used_gb": random.uniform(4.0, 8.0)
            })

        time.sleep(0.1)  # Simulate work

print("✅ Experiment logged successfully!")
```

Run the experiment:

```bash
python my_experiment.py
```

## 4. View Results in Web Interface

1. Open your browser to http://localhost:8000
2. Click on the **quickstart** project
3. You'll see your **first-experiment** run in the table
4. Click on the run to view detailed metrics and charts

## 5. Explore the Interface

### Projects Dashboard

The home page shows all your projects with statistics:

- Total number of runs
- Completed, running, and failed runs
- Recent activity

### Runs Table

Click on a project to see all runs with:

- Run name, group, and state
- Configuration parameters
- Creation date
- Sortable and filterable columns

### Run Detail Page

Click on a run to see:

- **Configuration** - All hyperparameters
- **Metrics Charts** - Interactive Plotly visualizations
- **System Metrics** - GPU utilization, memory usage
- **Metadata** - Run ID, timestamps, state

### Comparing Runs

Select multiple runs (checkbox in runs table) and click "Compare" to see:

- Side-by-side configuration comparison
- Overlaid metric charts
- Performance differences

## 6. Try More Features

### Resume a Run

```python
import trackai

# Resume the same run and log more data
with trackai.init(
    project="quickstart",
    name="first-experiment",
    resume="allow"  # Resume if exists, create if not
) as run:
    for step in range(100, 200):  # Continue from step 100
        trackai.log({"train/loss": 0.5}, step=step)
```

### Log Different Metric Types

```python
import trackai

with trackai.init(project="quickstart") as run:
    # Nested metrics (creates grouped charts)
    trackai.log({
        "train/loss": 0.5,
        "train/accuracy": 0.8,
        "val/loss": 0.6,
        "val/accuracy": 0.75
    }, step=0)

    # System metrics (timestamp-based)
    trackai.log_system({
        "cpu_percent": 45.2,
        "memory_percent": 62.1,
        "disk_usage_gb": 128.5
    })
```

### Use Groups to Organize Runs

```python
import trackai

# Group related experiments
with trackai.init(
    project="quickstart",
    group="hyperparameter-search",  # Group name
    config={"lr": 0.01, "batch_size": 64}
) as run:
    trackai.log({"loss": 0.4}, step=0)
```

## 7. Database Management

Check database statistics:

```bash
trackai db info
```

Backup your data:

```bash
trackai db backup --output ~/backups/trackai-backup.duckdb
```

## Next Steps

Now that you've logged your first experiment, explore:

- [Python SDK Guide](python_sdk.md) - Learn all SDK features
- [Logging Metrics](logging_metrics.md) - Best practices for metrics
- [CLI Usage](cli_usage.md) - Server and database commands
- [S3 Storage](s3_storage.md) - Configure cloud storage
- [REST API](rest_api.md) - Integrate with other tools
