---
name: dalva-autoresearch
description: >
  Monitor, analyze, and guide deep learning training experiments using Dalva's CLI tools.
  Use this skill when the user is running or planning to run training experiments and needs
  to track metrics, inspect model performance, compare runs, read training configurations,
  analyze tabular data (predictions, hyperparameter sweeps, layer statistics), or make
  autonomous decisions about training adjustments. Triggers on: training monitoring,
  experiment tracking, loss curves, metric analysis, training loops, hyperparameter tuning,
  model convergence, overfitting detection, run comparison, experiment management, ML
  experiment dashboard, training progress, val loss, learning rate scheduling, checkpoint
  decisions, early stopping, autonomous research, auto-research, or any scenario where an
  agent needs visibility into what's happening inside a training run. Also use when the user
  mentions Dalva, dalva query, experiment observability, or wants an automated agent to
  watch and react to training.
---

# Dalva Autoresearch

This skill gives you, the agent, a complete set of tools to observe and reason about deep learning training experiments tracked by Dalva. The goal is to let you see what's happening inside training — metrics over time, configurations, tabular data — so you can make informed decisions about whether training is heading in the right direction and what to adjust.

## How Dalva Works

Dalva is a lightweight experiment tracker. A training script logs metrics, configs, and tabular data to a local Dalva server via the Python SDK. You query that data through CLI commands.

The server must be running for query commands to work. If it's not running, start it:

```bash
dalva server start              # production mode
dalva server dev                # dev mode (separate frontend/backend)
```

The server default is `http://localhost:8000`. Override with `--server-url` or the `DALVA_SERVER_URL` env var.

For detailed setup instructions (wiring Dalva into a training script, SDK usage, WAL recovery), read `references/setup.md`.

---

## Query Tools Reference

All query commands output JSON by default (optimized for agent consumption). Use `--format table` for human-readable output. All commands accept `--server-url` to override the server address.

### Projects

```bash
dalva query projects [--format table]
```

Returns a list of projects with `total_runs`, `running_runs`, `completed_runs`, `failed_runs`. Each project has an `id` (used in other commands), `name`, and `project_id`.

### Runs

```bash
dalva query runs [--project-id ID] [--state running|completed|failed] [--search QUERY] [--tags TAGS] [--limit N] [--offset N] [--sort-by FIELD] [--sort-order asc|desc]
```

Lists runs with filtering. Key fields per run: `id`, `run_id`, `name`, `state`, `group_name`, `tags`, `fork_from`, `created_at`, `updated_at`. The response wraps runs in `{"runs": [...], "total": N, "has_more": bool}`.

Filter by state to find active (`running`) or finished experiments. Use `--search` for name-based lookup.

### Run Summary

```bash
dalva query run <run_id>
```

Returns the full picture for a single run: metadata (`id`, `name`, `state`, `group_name`, `tags`) plus `metrics` (dict of latest values per metric key) and `config` (dict of all config keys). This is the single most useful command for understanding a run's current state.

### Available Metrics

```bash
dalva query metrics <run_id>
```

Lists all metric keys logged for a run. Each entry has `path` (the metric name, possibly nested with `/`) and `attribute_type` (`float`, `int`, `string`, `bool`). Use this to discover what metrics exist before querying history.

### Metric History (Timeseries)

```bash
dalva query metric <run_id> <metric_path> [--step-min N] [--step-max N] [--limit N] [--offset N]
```

Returns the full timeseries for a single metric: `{"data": [{"step": N, "value": V, "timestamp": "..."}], "has_more": bool, "attribute_type": "..."}`. This is how you see the trajectory — loss decreasing, accuracy increasing, etc.

Use `--step-min` / `--step-max` to zoom into a range of steps. Paginate with `--limit` / `--offset` if there are many data points (default limit is 1000).

### Config

```bash
dalva query config <run_id>              # all config keys
dalva query config <run_id> <key>        # specific key
```

Returns the run's configuration as a dict, or a single key's value. Configs are set at run init or via `log_config()`. Nested keys use `/` as separator (e.g., `optimizer/lr`).

### Tables

```bash
dalva query tables [--run-id ID] [--project-id ID] [--limit N]
```

Lists Dalva tables (tabular data tracked alongside metrics). Tables have a `column_schema` defining their columns. Tables are linked to runs via `run_id`.

### Table Detail

```bash
dalva query table <table_id>
```

Returns table metadata: `id`, `name`, `table_id`, `row_count`, `version`, `column_schema` (JSON string describing columns), `state`, `config`.

### Table Data (Rows)

```bash
dalva query table-data <table_id> [--limit N] [--sort-by COLUMN] [--sort-order asc|desc] [--filters JSON]
```

Returns rows: `{"rows": [...], "total": N, "column_schema": [...], "has_more": bool}`. Supports sorting and filtering (pass filters as a JSON array of `{"column": "...", "op": "between|contains|eq", "min": N, "max": N, "value": ...}`).

### Table Statistics

```bash
dalva query table-stats <table_id>
```

Returns per-column statistics: `{"columns": {"col_name": {...}}}`. For numeric columns: `min`, `max`, `null_count`, `bins` (histogram). For string columns: `unique_count`, `top_values`. For bool columns: `counts`. This is useful for quick data profiling without pulling all rows.

---

## Other CLI Commands

These aren't query commands but are important for managing the system.

### Database Info

```bash
dalva db info      # shows DB path, file size, row counts per table
dalva db backup    # creates a timestamped backup
dalva db reset     # deletes the database (requires confirmation)
```

### Configuration

```bash
dalva config show  # shows current config, file path, env var overrides
```

### Sync (WAL Recovery)

When the training process crashes or times out, unsent operations are persisted to disk as WAL (write-ahead log) files. Replay them to recover data:

```bash
dalva sync              # replay all pending operations
dalva sync --status     # show what's pending without syncing
dalva sync --dry-run    # preview what would be sent
```

### Health Check

```bash
curl http://localhost:8000/api/health   # returns {"status": "healthy"}
```

---

## Monitoring Patterns

### Getting Oriented

Start by understanding what's in the system:

```bash
dalva query projects
dalva query runs --state running
dalva query runs --state completed --limit 5
```

Then drill into a specific run:

```bash
dalva query run <run_id>          # see current metrics + config
dalva query metrics <run_id>      # see all metric keys
```

### Reading Training Progress

For any metric, get its trajectory:

```bash
dalva query metric <run_id> loss
dalva query metric <run_id> accuracy
dalva query metric <run_id> val_loss --step-min 50   # zoom into later training
```

Look for:
- **Steady decrease** in loss: training is learning
- **Plateau** in loss: might need learning rate adjustment
- **Increasing loss**: divergence — reduce learning rate, check data
- **Gap between train and val metrics**: overfitting — consider regularization, dropout, more data

### Comparing Runs

Compare multiple runs by querying their summaries and specific metric histories:

```bash
# Get summaries for all completed runs
dalva query runs --state completed

# Compare a specific metric across runs
dalva query metric <run_id_1> loss
dalva query metric <run_id_2> loss
```

Look at the configs to understand what changed:

```bash
dalva query config <run_id_1>
dalva query config <run_id_2>
```

### Analyzing Tabular Data

Tables often hold predictions, per-layer statistics, or hyperparameter sweep results:

```bash
dalva query tables --run-id <run_id>
dalva query table-stats <table_id>          # quick column overview
dalva query table-data <table_id> --limit 20
```

Use statistics to spot outliers, skewed distributions, or missing data without downloading everything.

---

## Decision-Making Guidance

### When Training Looks Good

- Loss decreasing steadily, validation metrics improving
- The run summary shows metrics converging toward expected targets
- Consider letting it continue, or checkpointing and trying a larger model

### When to Intervene

- **Loss not decreasing after many steps**: learning rate might be too low, or there's a bug in the data pipeline
- **Loss exploding (NaN or sudden spike)**: learning rate too high, gradient clipping needed, or numerical instability
- **Overfitting detected** (train loss keeps dropping but val loss rises): add regularization (dropout, weight decay), reduce model size, augment data, or early-stop
- **Validation metrics oscillating wildly**: batch size might be too small, or learning rate too high
- **Training extremely slow**: check batch size, consider mixed precision, verify data loading isn't bottlenecked

### Using Config to Understand What Changed

When comparing runs, the config tells you what hyperparameters were used. Common config keys to look at:
- `lr` or `learning_rate`: the most impactful single parameter
- `batch_size`: affects training dynamics and speed
- `optimizer`: Adam vs SGD vs others behave differently
- `weight_decay`, `dropout`: regularization strength
- `model_name` or `architecture`: what model variant is being used

### Efficient Monitoring for Long-Running Training

For training that runs for hours, poll periodically rather than querying constantly:

1. Check run state: `dalva query run <run_id>` — look at `state` and latest metrics
2. Check recent metric trajectory: `dalva query metric <run_id> loss --step-min <last_step_checked>`
3. If state changed to `completed` or `failed`, inspect full results

---

## Integration Patterns

### Pattern 1: Autonomous Training Agent

You can use these tools to build an autonomous training loop where you:

1. Start a training run (the training script initializes a Dalva `Run` and logs to it)
2. Periodically poll metrics to assess progress
3. Based on what you see, decide whether to continue, adjust hyperparameters (by starting a new run with modified config), or stop
4. Compare runs to decide which approach works best

The key insight: the training script logs data, and you observe it through these CLI tools. The training script doesn't need to know about your monitoring — it just logs to Dalva as normal.

### Pattern 2: Single Experiment Analysis

For a one-off experiment:

1. `dalva query run <run_id>` to get the overview
2. `dalva query metrics <run_id>` to see what was tracked
3. `dalva query metric <run_id> <key>` for detailed trajectories
4. `dalva query config <run_id>` for hyperparameters
5. `dalva query tables --run-id <run_id>` for any tabular data

### Pattern 3: Hyperparameter Sweep Analysis

When multiple runs test different hyperparameters:

1. `dalva query runs --state completed` to list all finished runs
2. For each run, get the config and the final metrics
3. Compare configs against metric outcomes to find the best configuration
4. Use table data if the sweep results are logged as a table

---

## Tips for Effective Use

- Default output is JSON — parse it with `json.loads()` or pipe to `jq` if you need to extract specific fields in bash
- Run IDs in query commands are the database ID (integer), not the run_id string. Both are shown in `dalva query runs` output — use the `id` field for subsequent queries
- The `--format table` option is useful for quick visual inspection when you're looking at output yourself
- Tables are a powerful way to log structured per-step or per-epoch data (predictions, gradients, layer statistics) alongside scalar metrics
- If the server is unreachable, check if it's running with `dalva db info` or `curl http://localhost:8000/api/health`
