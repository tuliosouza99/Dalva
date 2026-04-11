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
```

## Layout

```
backend/src/dalva/    # Python package (hatch builds from here)
  api/                # FastAPI app + routes + Pydantic models
  cli/                # Click CLI (entry: dalva.cli.main:cli)
  db/                 # SQLAlchemy schema + connection
  services/           # Business logic (logger.py, tables.py)
  static/             # Frontend build output bundled into wheel (gitignored)
  utils/
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
uv run pytest backend/tests/test_api.py -v         # single file
uv run pytest -m unit                              # by marker
```

Available markers (defined in `pyproject.toml`): `unit`, `integration`, `slow`, `db`, `api`.

Test fixtures in `conftest.py`: `db_engine`, `db_session`, `api_client` (TestClient with patched `get_db`), `sample_project`, `sample_run`, `sample_metrics`, `sample_table`.

## Architecture Notes

- **Config priority:** env vars > `~/.dalva/config.json` > defaults. Override DB path with `DALVA_DB_PATH`.
- **Frontend dev proxy:** Vite proxies `/api` to `VITE_BACKEND_URL` (default `http://localhost:8000`).
- **SPA serving:** In production, FastAPI serves built frontend from `static/`. A catch-all route returns `index.html` for non-`/api` paths.
- **Publishing:** `hatch_build.py` copies `static/` into `backend/src/dalva/static/` before wheel build. Frontend must be pre-built (`npm run build`).
- **Tables feature:** `DalvaTable` / `DalvaTableRow` support tabular data alongside metrics. Has its own API routes (`/api/tables`), service (`services/tables.py`), and frontend pages (`TablesPage`, `TableDetailPage`).
