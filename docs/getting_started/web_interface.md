# Web Interface

Guide to using the TrackAI web interface for visualizing and comparing experiments.

## Overview

The TrackAI web interface provides:

- **Projects Dashboard** - Overview of all projects
- **Runs Table** - Filterable, sortable list of experiments
- **Run Detail Page** - Detailed metrics and charts for individual runs
- **Compare Runs** - Side-by-side comparison of multiple experiments
- **Custom Dashboards** - Create custom layouts with metric widgets

## Accessing the Interface

Start the server:

```bash
trackai server start
```

Open your browser to the displayed URL (default: http://localhost:8000).

## Projects Dashboard

The home page shows all your projects.

### Project Cards

Each project card displays:

- **Project name**
- **Total runs count**
- **Completed runs** (green)
- **Running runs** (blue)
- **Failed runs** (red)
- **Last updated** timestamp

### Actions

- **Click on a project** - View all runs in that project
- **Create new project** - Automatically created when logging first run

## Runs Table

Click on a project to see all runs in a sortable, filterable table.

### Table Columns

Default columns:

- **Run Name** - Clickable to view details
- **Group** - Group name (if set)
- **State** - running / completed / failed
- **Config** - Hyperparameters preview
- **Created** - Creation timestamp
- **Duration** - Time elapsed

### Sorting

Click column headers to sort:

- **Name** - Alphabetical
- **Created** - Chronological (newest/oldest first)
- **Duration** - Longest/shortest first
- **State** - grouped by status

**Multi-column sort**: Hold Shift and click multiple columns.

### Filtering

Use the filter bar above the table:

- **Search by name** - Type run name or partial match
- **Filter by group** - Select specific group
- **Filter by state** - Show only running/completed/failed
- **Filter by tags** - Select runs with specific tags

**Example filters**:
```
Search: "resnet"
Group: "baseline-experiments"
State: "completed"
```

### Selecting Runs

- **Checkbox column** - Select multiple runs
- **Select all** - Checkbox in header
- **Compare button** - Click to compare selected runs (2+ required)

### Virtualized Table

For projects with thousands of runs:

- Only visible rows rendered (fast performance)
- Smooth scrolling
- No lag with large datasets

## Run Detail Page

Click on a run name to view detailed information.

### Configuration Section

View all hyperparameters:

```
learning_rate: 0.001
batch_size: 32
optimizer: "adam"
weight_decay: 0.0001
```

### Metrics Section

Interactive charts for all logged metrics.

#### Chart Features

- **Zoom** - Drag to select area, double-click to reset
- **Pan** - Click and drag while zoomed
- **Hover** - See exact values
- **Legend** - Click to hide/show metrics
- **Download** - Save chart as PNG

#### Grouped Metrics

Metrics with nested paths are grouped:

**train/** group:
- train/loss
- train/accuracy
- train/f1_score

**val/** group:
- val/loss
- val/accuracy
- val/f1_score

Each group has its own chart section.

### System Metrics Section

If `log_system()` was used, view timestamp-based metrics:

- GPU utilization over time
- Memory usage over time
- CPU usage over time
- Temperature over time

**X-axis**: Timestamp (not step number)

### Metadata Section

View run metadata:

- **Run ID** - Unique identifier
- **Project** - Parent project name
- **Group** - Group name (if set)
- **State** - Current state
- **Created** - Creation timestamp
- **Updated** - Last update timestamp
- **Duration** - Total time elapsed

## Compare Runs

Compare multiple runs side-by-side.

### How to Compare

1. Go to runs table
2. Select 2+ runs using checkboxes
3. Click "Compare" button

### Comparison View

#### Configuration Comparison

Table showing all configs side-by-side:

| Parameter    | Run 1  | Run 2  | Run 3  |
|--------------|--------|--------|--------|
| learning_rate| 0.001  | 0.01   | 0.1    |
| batch_size   | 32     | 32     | 64     |
| optimizer    | adam   | adam   | sgd    |

**Differences highlighted** - Values that differ across runs are highlighted.

#### Metrics Charts

Overlaid charts for each metric:

**train/loss**:
- Run 1 (blue line)
- Run 2 (red line)
- Run 3 (green line)

Each run has a different color and shows up in the legend.

**Interactive features**:
- Hide/show specific runs
- Zoom to specific step range
- Hover to see all values at a step

### Use Cases

**Hyperparameter sweeps**:
```python
for lr in [0.001, 0.01, 0.1]:
    with trackai.init(
        project="tuning",
        group="lr-sweep",
        config={"lr": lr}
    ) as run:
        train_model(lr)

# Compare all runs in web interface
```

**Architecture comparison**:
```python
for model in ["resnet50", "efficientnet", "vit"]:
    with trackai.init(
        project="models",
        group="architecture-comparison",
        config={"model": model}
    ) as run:
        train_model(model)
```

**Ablation studies**:
```python
configs = [
    {"use_dropout": True, "use_bn": True},
    {"use_dropout": False, "use_bn": True},
    {"use_dropout": True, "use_bn": False},
]

for config in configs:
    with trackai.init(project="ablation", config=config) as run:
        train_model(config)
```

## Custom Dashboards

Create custom dashboard layouts with metric widgets.

### Creating a Dashboard

1. Click "Dashboards" in navigation
2. Click "Create New Dashboard"
3. Enter dashboard name
4. Add widgets

### Widget Types

**Metric Chart Widget**:
- Select run(s)
- Select metric
- Choose chart type (line, scatter)

**Comparison Widget**:
- Select multiple runs
- Select metric to compare
- Overlaid chart

**Configuration Table Widget**:
- Select runs
- Display config comparison

### Dashboard Layout

Drag and drop widgets to arrange:

- Resize widgets
- Reorder widgets
- Delete widgets
- Save layout

### Sharing Dashboards

Dashboards are saved per-project and can be accessed by anyone viewing the project.

## Keyboard Shortcuts

- **`/`** - Focus search box
- **`Esc`** - Clear filters
- **`↑` / `↓`** - Navigate runs table
- **`Enter`** - Open selected run

## Performance Features

### Virtualized Tables

For large datasets (10,000+ runs):

- Only render visible rows
- Smooth scrolling
- No performance degradation

### Data Caching

React Query caches data for 30 seconds:

- Instant navigation
- Reduced backend load
- Configurable stale time

### Lazy Loading

Charts only load when visible:

- Fast initial page load
- Scroll to load more charts

## Best Practices

1. **Use groups** - Organize related experiments for easy filtering
2. **Descriptive run names** - Easy to identify in table
3. **Consistent config keys** - Makes comparison easier
4. **Use nested metric paths** - Automatic chart grouping
5. **Add tags** - Additional metadata for filtering

## Troubleshooting

### Charts Not Loading

**Check**:
- Backend server is running
- No console errors (F12 developer tools)
- Metrics were logged with `trackai.log()`

### Table Slow with Many Runs

**Solutions**:
- Use filters to reduce visible runs
- Virtualized table should handle 10,000+ runs
- Check browser console for errors

### Data Not Updating

**Force refresh**:
- Hard refresh: Ctrl+F5 (Windows/Linux) or Cmd+Shift+R (Mac)
- Clear browser cache
- Restart server

## Next Steps

- [Python SDK](python_sdk.md) - Log metrics for visualization
- [Logging Metrics](logging_metrics.md) - Best practices for charts
- [Compare Runs](../api_documentation/rest_api/metrics.md) - Compare API
