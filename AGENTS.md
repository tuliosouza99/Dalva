# AGENTS.md

## Commands

**Backend (from repo root, always use `uv`):**
```bash
uv sync                          # install deps
uv run pytest backend/tests/ -v  # run all tests
uv run ruff check                # lint
uv run ruff format --check       # check formatting
uv run uvicorn dalva.api.main:app --reload  # dev server
```

**Frontend (from `frontend/`):**
```bash
npm install        # install deps
npm run dev        # dev server (proxies /api to backend via VITE_BACKEND_URL, default localhost:8000)
npm run build      # production build → ../static
npm run build:check  # build with tsc type-check
npm run lint       # eslint
```

**Note:** `npm test` does not exist — there is no frontend test runner.

**CLI (after `uv sync`):**
```bash
dalva server start              # production: build frontend + serve on single port
dalva server dev                # dev: separate backend/frontend with hot reload
dalva db info / backup / reset  # database management
dalva sync                      # replay pending WAL operations from disk
dalva sync --status             # show pending operations without sending
dalva sync --dry-run            # preview what would be sent
```

## Layout

```
backend/src/dalva/    # Python package (hatch builds from here)
  api/                # FastAPI app + routes + Pydantic models
  cli/                # Click CLI (entry: dalva.cli.main:cli)
    sync.py           # dalva sync — WAL replay command
  db/                 # SQLAlchemy schema + connection
  sdk/                # Client SDK (Run, Table, Worker, WAL)
    run.py            # Run class — async log(), sync finish()/get()/remove()
    table.py          # Table class — async log(), sync finish()
    worker.py         # SyncWorker — background thread with batching + retry
    wal.py            # WALManager — write-ahead log for crash resilience
  services/           # Business logic (logger.py, tables.py)
  static/             # Frontend build output bundled into wheel (gitignored)
  utils/
backend/tests/
  conftest.py         # Shared fixtures (db_engine, api_client, sample_*)
  unit/               # Unit tests (no DB, mocked HTTP)
    test_wal.py       # WAL manager: append, read, rewrite, dump_queue
    test_worker.py    # SyncWorker: enqueue, drain, batch, retry, WAL integration
    test_sdk.py       # SDK Run/Table: mocked HTTP, WAL unit tests
    test_sync_cli.py  # CLI sync command: status, dry-run, replay (mocked)
    test_config.py    # Config file parsing, env var overrides
  integration/        # Integration tests (real DB + real API)
    test_sync_integration.py  # Crash → WAL → sync → data recovered (end-to-end)
    test_run_endpoints.py     # Run API endpoints: init, log, finish
    test_api.py               # Health, CORS, conformance
    test_get.py               # Get metric/config via API
    test_routes_*.py          # Full API route tests (runs, tables, metrics, projects)
    test_upsert.py            # Strict insert / remove semantics
backend/examples/
  crash_recovery.py   # Demo: crash → WAL → dalva sync
frontend/src/         # React 19 + TypeScript + Vite
  api/client.ts       # Axios + React Query hooks (all API calls go here)
  pages/              # Route pages
  components/         # Reusable components
  contexts/           # React contexts (ComparisonContext)
frontend/build → ../static  # Vite outputs here (hatch_build.py copies into package)
```

## Critical Gotchas

- **DuckDB + NullPool:** All engines use `NullPool` (not the default `QueuePool`). DuckDB allows only one writer at a time; connection pooling holds the write lock and blocks other processes. See `db/connection.py:266`.
- **No `Base.metadata.create_all()`:** DuckDB doesn't support `SERIAL`. Tables are created via raw SQL with explicit `CREATE SEQUENCE` + `DEFAULT nextval(...)` in `db/connection.py:_create_duckdb_tables()` and `tests/conftest.py:_create_tables()`. If you add a table, update **both**.
- **Schema changes = migration by ALTER:** The codebase uses `ALTER TABLE ... ADD COLUMN` wrapped in try/except for backward compatibility (see `connection.py:64`). There is no formal migration framework.
- **Test isolation:** `conftest.py` sets `DALVA_DB_PATH=""` at module level, then creates a temp DuckDB per test function. Tests never touch `~/.dalva/`.
- **CI builds frontend first:** The test workflow runs `npm install && npm run build` before `uv sync && pytest` because the hatch build hook needs static files.

## Testing

```bash
uv run pytest backend/tests/ -v                    # all tests
uv run pytest backend/tests/unit/ -v               # unit tests only (fast, no DB)
uv run pytest backend/tests/integration/ -v        # integration tests (real DB)
uv run pytest -m unit                              # by marker (unit)
uv run pytest -m integration                       # by marker (integration)
uv run pytest backend/tests/unit/test_worker.py -v # single file
```

Available markers (defined in `pyproject.toml`): `unit`, `integration`, `slow`, `db`, `api`.

Auto-marking: tests in `tests/unit/` get `@pytest.mark.unit`, tests in `tests/integration/` get `@pytest.mark.integration` + `@pytest.mark.db`.

Test fixtures in `conftest.py`: `db_engine`, `db_session`, `api_client` (TestClient with patched `get_db`), `sample_project`, `sample_run`, `sample_metrics`, `sample_table`.

## Architecture Notes

- **Config priority:** env vars > `~/.dalva/config.json` > defaults. Override DB path with `DALVA_DB_PATH`.
- **Frontend dev proxy:** Vite proxies `/api` to `VITE_BACKEND_URL` (default `http://localhost:8000`).
- **SPA serving:** In production, FastAPI serves built frontend from `static/`. A catch-all route returns `index.html` for non-`/api` paths.
- **Publishing:** `hatch_build.py` copies `static/` into `backend/src/dalva/static/` before wheel build. Frontend must be pre-built (`npm run build`).
- **Tables feature:** `DalvaTable` / `DalvaTableRow` support tabular data alongside metrics. Has its own API routes (`/api/tables`), service (`services/tables.py`), and frontend pages (`TablesPage`, `TableDetailPage`).

## SDK Worker + WAL Architecture

The SDK's `log()` is **async** — it enqueues operations to a background `SyncWorker` thread. The worker batches requests, retries on transient failures, and drains on `finish()`/`flush()`. A **WAL (write-ahead log)** persists unsent operations to `~/.dalva/outbox/` for crash recovery.

### Data Flow

```
Training loop          SyncWorker thread             Disk
─────────────          ─────────────────             ────
run.log() ──► queue ──► pick up item ──► append WAL ──► send HTTP
                  │                                      │
                  │   on success:   WAL stays (covers retries)
                  │   on finish():  WAL deleted
                  │   on timeout:   dump remaining queue → WAL
                  │   on crash:     WAL survives on disk
```

### Key Components

| Component | File | Purpose |
|-----------|------|---------|
| `SyncWorker` | `sdk/worker.py` | Daemon thread: queue → batch → HTTP with retry |
| `WALManager` | `sdk/wal.py` | Append/read/rewrite/delete JSONL files in `~/.dalva/outbox/` |
| `Run` | `sdk/run.py` | Creates `WALManager("run", db_id)`, passes to worker |
| `Table` | `sdk/table.py` | Creates `WALManager("table", db_id)`, passes to worker |
| `dalva sync` | `cli/sync.py` | Replays WAL files: batch, handle 409, partial failure |

### WAL Behavior

- **Normal operation**: Worker appends each item to WAL before sending. On successful `finish()`, WAL is deleted.
- **Timeout**: If `finish()` or `flush()` times out, remaining queue items are dumped to WAL. User sees: `"[Dalva] N operation(s) saved to disk. Run 'dalva sync' to replay."`
- **Crash**: If the process crashes (SIGKILL, OOM), items already appended to WAL survive. Items still in the in-memory queue but not yet picked up by the worker are lost (~0.2s window).
- **`dalva sync`**: Groups batchable entries by `batch_key`, sends as batch requests. Handles 409 Conflict (already applied) as success. On partial failure, rewrites WAL with only failed entries.

### Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `batch_size` | 50 | Max items per batch HTTP request |
| `flush_interval` | 0.2s | How often worker checks the queue |
| `max_retries` | 5 | Retry count for 5xx/network errors |
| `base_backoff` | 1.0s | Exponential backoff base (2^n) |
| `outbox_dir` | `~/.dalva/outbox/` | WAL file storage location |

### Finish Behavior

```python
run.finish(timeout=120)  # default: 2 min timeout
run.finish(on_error="raise")  # raise DalvaError on accumulated errors
run.finish(on_error="warn")   # print warnings (default)
```

- `_finished` is only set to `True` on success (not on failure/timeout)
- `finish()` is idempotent — calling it twice is safe
- `atexit` handler auto-calls `finish(timeout=30)` on process exit
