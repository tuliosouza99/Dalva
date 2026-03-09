---
name: TrackAI Skill
description: A guide to using TrackAI for experiment tracking in machine learning projects.
---

# TrackAI Skill

A guide to using TrackAI for experiment tracking in machine learning projects.

## When to Use This Skill

Use this skill when working with:
- Experiment tracking for deep learning models
- Setting up TrackAI servers and databases
- Configuring S3 storage for experiments
- Troubleshooting TrackAI installations
- Migrating from Neptune.ai or Weights & Biases
- Comparing model training runs
- Logging metrics, hyperparameters, and system resources

## Quick Reference

### Server Management

```bash
# Start production server (auto-finds port, builds frontend)
trackai server start

# Start with specific port
trackai server start --port 8080

# Development mode with hot reload (separate backend/frontend)
trackai server dev

# Custom ports for dev mode
trackai server dev --backend-port 8001 --frontend-port 5174
```

**Production vs Development**:
- **Production** (`trackai server start`): Single port, builds frontend first, serves static files
- **Development** (`trackai server dev`): Separate ports, hot reload for both backend and frontend

### Python SDK Usage

```python
import trackai

# Basic usage
run = trackai.init(
    project="my-project",
    name="experiment-1",  # Optional, auto-generated if not provided
    config={"lr": 0.001, "batch_size": 32}
)

# Log training metrics (step-based)
trackai.log({"train/loss": 0.5, "train/acc": 0.8}, step=0)

# Log system metrics (timestamp-based)
trackai.log_system({"gpu_util": 0.95, "memory_gb": 8.2})

# Finish the run
trackai.finish()
```

**Context manager (recommended)**:
```python
with trackai.init(project="my-project") as run:
    for step in range(100):
        trackai.log({"loss": 0.5}, step=step)
    # Run automatically finished on context exit
```

**S3 sync flags** (requires `trackai config s3` and valid AWS credentials):
```python
# Pull from S3 before starting, push to S3 after finishing
with trackai.init(project="my-project", pull=True, push=True) as run:
    ...

# Pull only (read shared data, keep local)
with trackai.init(project="my-project", pull=True) as run:
    ...

# Push only (write shared data, no pull)
with trackai.init(project="my-project", push=True) as run:
    ...
```

**Resume modes**:
```python
# Resume if exists, create if not
trackai.init(project="p", name="long-run", resume="allow")

# Must resume existing run or fail
trackai.init(project="p", name="checkpoint-run", resume="must")

# Always create new run (default)
trackai.init(project="p", name="new-run", resume="never")
```

### Database Management

```bash
# Check database info and statistics
trackai db info

# Backup database
trackai db backup --output ~/backups/trackai-backup.duckdb

# Reset database (deletes all data - be careful!)
trackai db reset

# Migrate from SQLite to DuckDB
trackai db migrate --sqlite-path ~/.trackai/trackai.db --duckdb-path ~/.trackai/trackai.duckdb --yes

# S3 sync (requires 'trackai config s3' + valid AWS credentials)
trackai db pull   # Download S3 → ~/.trackai/trackai.duckdb
trackai db push   # Upload ~/.trackai/trackai.duckdb → S3
```

### S3 Configuration

```bash
# Set AWS credentials (add to ~/.bashrc or ~/.zshrc)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"

# Configure TrackAI for S3
trackai config s3 --bucket my-trackai-experiments --key trackai.duckdb --region us-east-1

# Push existing local database to S3 (first-time setup)
trackai db push

# Pull latest data from S3
trackai db pull

# View current configuration
trackai config show
```

## Key Concepts

### Local-First S3 Architecture

TrackAI uses a local-first architecture for S3 storage. All reads and writes go to `~/.trackai/trackai.duckdb`. S3 sync is opt-in.

**SDK (Python logging)**:
- Always writes to `~/.trackai/trackai.duckdb` — zero S3 latency during training
- `pull=True` on `trackai.init()` — downloads from S3 before the run starts
- `push=True` on `trackai.init()` — uploads to S3 after the run finishes
- Both default to `False` — no S3 interaction unless explicitly requested

**Server (dashboard)**:
- Always reads from `~/.trackai/trackai.duckdb`
- Mid-run metrics visible in real time — same file the SDK writes to
- Never touches S3 — instant startup and clean shutdown

**CLI sync**:
- `trackai db pull` — download S3 → `~/.trackai/trackai.duckdb`
- `trackai db push` — upload `~/.trackai/trackai.duckdb` → S3

**Benefits**:
- ✅ Mid-run visibility — dashboard shows live metrics during training
- ✅ Zero S3 latency during training
- ✅ Simple server — no S3 ATTACH, no hanging on shutdown
- ✅ Explicit sync — no magic auto-sync, you control when to pull/push

### Resume Modes

Three resume modes for checkpoint recovery:

- `resume="never"` - Always create new run (default)
- `resume="allow"` - Resume if exists, create if not (recommended for checkpoints)
- `resume="must"` - Must resume existing run or fail (strict mode)

### Metric Types

**Step-based metrics** (use `trackai.log()`):
- Training loss, accuracy, learning rate
- X-axis: Step/epoch number
- Example: `trackai.log({"train/loss": 0.5}, step=epoch)`

**Timestamp-based metrics** (use `trackai.log_system()`):
- GPU utilization, memory usage, temperature
- X-axis: Timestamp
- Example: `trackai.log_system({"gpu_util": 0.95})`

**Nested paths**:
- Use `/` to group metrics: `train/loss`, `val/loss`, `test/loss`
- Automatically grouped in web UI charts

### Database Storage

- **Engine**: DuckDB (not SQLite) for better analytics performance
- **Location**: `~/.trackai/trackai.duckdb` (centralized, accessible from any project)
- **Override**: `export TRACKAI_DB_PATH=/custom/path/trackai.duckdb`
- **Storage modes**: Local (file) or S3 (cloud)

## Project Structure

```
TrackAI/
├── backend/
│   └── src/trackai/
│       ├── __init__.py          # Public API (init, log, finish)
│       ├── run.py               # Run class
│       ├── api/                 # FastAPI routes
│       │   ├── main.py          # FastAPI app
│       │   ├── models.py        # Pydantic models
│       │   └── routes/          # Endpoint handlers
│       ├── cli/                 # CLI commands
│       │   ├── server.py        # Server commands
│       │   ├── database.py      # DB commands
│       │   └── config.py        # Config commands
│       ├── db/                  # Database
│       │   ├── schema.py        # Table definitions
│       │   └── connection.py    # DB connection
│       ├── services/            # Business logic
│       │   └── logger.py        # LoggingService
│       ├── s3/                  # S3 integration
│       │   └── sync.py          # S3 sync functions
│       └── config.py            # Configuration management
└── frontend/
    └── src/                     # React UI
```

## Common Tasks

### Installing Dependencies

```bash
# Backend (use uv - recommended)
cd backend && uv sync

# Backend (alternative - use pip)
cd backend && pip install -e .

# Frontend
cd frontend && npm install

# Documentation (optional)
cd backend && uv sync --group docs
```

### Running Examples

```bash
cd backend

# Simple experiment
uv run python examples/simple_experiment.py

# Context manager example
uv run python examples/context_manager.py

# Resume run example
uv run python examples/resume_run.py
```

### Building Frontend

```bash
cd frontend

# Development mode (hot reload)
npm run dev

# Production build (outputs to ../static)
npm run build

# Build with type checking
npm run build:check
```

### Database Location

**Default**: `~/.trackai/trackai.duckdb`

**Custom location**:
```bash
export TRACKAI_DB_PATH=/path/to/custom.duckdb
```

**Check current location**:
```bash
trackai db info
```

## Troubleshooting

### Port Already in Use

The CLI automatically finds available ports:

```bash
# Auto-detect from 8000
trackai server start

# Or specify port
trackai server start --port 8080
```

### S3 Push/Pull Fails

**Check AWS credentials**:
```bash
aws sts get-caller-identity
```

**Re-configure S3**:
```bash
trackai config s3 --bucket my-bucket --key trackai.duckdb --region us-east-1
```

### Database Migration

**From SQLite to DuckDB**:
```bash
trackai db migrate \
  --sqlite-path ~/.trackai/trackai.db \
  --duckdb-path ~/.trackai/trackai.duckdb \
  --yes
```

### Frontend Build Fails

**Install dependencies**:
```bash
cd frontend
npm install
```

### Context Manager Not Uploading to S3

**Problem**: Exception before context exit prevents upload

**Solution**: Ensure `finish()` is called or use try/finally:
```python
with trackai.init(project="p") as run:
    try:
        train_model()
    except Exception as e:
        trackai.log({"error": str(e)}, step=0)
        raise  # Re-raise to mark run as failed
# Upload happens on context exit regardless
```

## API Compatibility

TrackAI is **trackio-compatible** for easy migration from Neptune.ai:

**Neptune.ai**:
```python
import neptune

run = neptune.init_run(project="workspace/project", api_token="TOKEN")
run["train/loss"].log(0.5)
run.stop()
```

**TrackAI**:
```python
import trackai

run = trackai.init(project="project")
trackai.log({"train/loss": 0.5}, step=0)
trackai.finish()
```

**Key differences**:
- No cloud account or API token needed
- Dict-based logging instead of object-based
- Explicit step numbers recommended
- Context manager pattern preferred

## Best Practices

1. **Use context manager** - Ensures runs are always finished:
   ```python
   with trackai.init(project="p") as run:
       trackai.log({"loss": 0.5}, step=0)
   ```

2. **Use nested metric paths** - Group related metrics:
   ```python
   trackai.log({
       "train/loss": 0.5,
       "train/acc": 0.8,
       "val/loss": 0.6,
       "val/acc": 0.75
   }, step=epoch)
   ```

3. **Separate training and system metrics**:
   ```python
   trackai.log({"loss": 0.5}, step=epoch)  # Training metrics
   trackai.log_system({"gpu_util": 0.95})  # System metrics
   ```

4. **Include configuration** - Always pass config dict:
   ```python
   trackai.init(project="p", config={"lr": 0.001, "batch_size": 32})
   ```

5. **Use groups for experiments** - Organize related runs:
   ```python
   trackai.init(project="p", group="hyperparameter-sweep", config={...})
   ```

6. **Resume for checkpoints** - Use `resume="allow"`:
   ```python
   trackai.init(project="p", name="long-run", resume="allow")
   ```

## Resources

- **GitHub**: [tuliosouza99/TrackAI](https://github.com/tuliosouza99/TrackAI)
- **Example Scripts**: `backend/examples/` directory
- **Config Location**: `~/.trackai/config.json`
- **Database Location**: `~/.trackai/trackai.duckdb`
