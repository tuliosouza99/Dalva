# CLI Usage

## Installation

The `dalva` CLI is included when you install the backend dependencies:

```bash
cd backend && uv sync
dalva --help
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
