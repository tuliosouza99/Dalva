# CLI Usage

## Installation

The `dalva` CLI is included when you install the backend dependencies:

```bash
# uv
uv add dalva

# pip
pip install dalva
```

## Server Commands

### `dalva server start`

Start production server (builds frontend, serves from single port):

```bash
dalva server start              # Auto-detect port starting from 8000
dalva server start --port 8080  # Specify port
dalva server start --no-reload   # Disable auto-reload
```

### `dalva server dev`

Start development mode with hot reload (separate ports):

```bash
dalva server dev                    # Auto-detect ports
dalva server dev --backend-port 8001 --frontend-port 5174
```

Use this when working on frontend React components with hot reload enabled.

## Database Commands

```bash
dalva db info      # Show statistics
dalva db backup    # Create backup
dalva db reset     # Delete all data (requires confirmation)
dalva config show  # View current configuration
```

## Sync Command

Replay pending WAL operations from disk. These are operations that were saved when the server was unreachable (network timeout, process crash, etc.).

```bash
dalva sync              # Replay all pending operations
dalva sync --status     # Show pending operations without sending
dalva sync --dry-run    # Preview what would be sent without sending
```

WAL files are stored in `~/.dalva/outbox/` (one `.jsonl` file per run/table). The sync command:

- Groups batchable log entries and sends them as batch requests
- Treats 409 Conflict (already applied) as success
- On partial failure, keeps only failed entries in the WAL for retry
- Deletes the WAL file when all operations succeed

```bash
# Check what's pending
$ dalva sync --status
Pending operations:

  run_42.jsonl: 15 operation(s)

  Total: 15 operation(s) across 1 file(s)

# Replay
$ dalva sync
  run_42.jsonl: Synced 15/15 ✓

Done: synced 15.
```

## Query Commands

Read-only commands that query the Dalva API server. All commands output JSON by default — use `--format table` for human-readable output. Override the server URL with `--server-url` or the `DALVA_SERVER_URL` environment variable.

### `dalva query projects`

List all projects with run counts:

```bash
dalva query projects
dalva query projects --format table
```

Returns: project `id`, `name`, `project_id`, `total_runs`, `running_runs`, `completed_runs`, `failed_runs`.

### `dalva query runs`

List and filter runs:

```bash
dalva query runs                                        # all runs
dalva query runs --state running                        # only active runs
dalva query runs --project-id 1                         # filter by project
dalva query runs --search "baseline"                    # search by name
dalva query runs --tags "tag1,tag2"                     # filter by tags
dalva query runs --limit 10 --sort-by created_at        # pagination + sorting
```

Options: `--project-id`, `--state` (`running`/`completed`/`failed`), `--search`, `--tags`, `--limit`, `--offset`, `--sort-by`, `--sort-order`.

### `dalva query run <run_id>`

Get a run summary including latest metrics and config:

```bash
dalva query run 1
```

Returns: all run metadata plus `metrics` (dict of latest values) and `config` (dict of all keys).

### `dalva query metrics <run_id>`

List available metric keys for a run:

```bash
dalva query metrics 1
```

Returns: list of `{"path": "...", "attribute_type": "..."}` entries.

### `dalva query metric <run_id> <metric_path>`

Get the full timeseries history for a metric:

```bash
dalva query metric 1 loss                       # all steps
dalva query metric 1 loss --step-min 50         # from step 50
dalva query metric 1 loss --step-min 0 --step-max 100  # range
dalva query metric 1 loss --limit 100 --offset 200     # paginate
```

Returns: `{"data": [{"step": N, "value": V, "timestamp": "..."}], "has_more": bool}`.

### `dalva query config <run_id> [key]`

Get run configuration:

```bash
dalva query config 1           # all config keys
dalva query config 1 lr        # specific key
```

### `dalva query tables`

List tables, optionally filtered:

```bash
dalva query tables                        # all tables
dalva query tables --run-id 1             # tables for a specific run
dalva query tables --project-id 1         # tables for a project
```

### `dalva query table <table_id>`

Get table metadata and column schema:

```bash
dalva query table 1
```

### `dalva query table-data <table_id>`

Get table rows with optional sorting and filtering:

```bash
dalva query table-data 1                              # all rows
dalva query table-data 1 --sort-by epoch --sort-order desc   # sorted
dalva query table-data 1 --limit 50 --offset 100             # paginate
dalva query table-data 1 --filters '[{"column":"loss","op":"between","min":0,"max":0.5}]'
```

### `dalva query table-stats <table_id>`

Get per-column statistics (min/max/histogram for numeric, top values for strings, etc.):

```bash
dalva query table-stats 1
```
