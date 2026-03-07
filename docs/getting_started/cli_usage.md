# CLI Usage

Complete guide to the `trackai` command-line interface.

## Overview

TrackAI provides a unified CLI for server management, database operations, and configuration:

```bash
trackai --help
```

## Server Commands

### `trackai server start`

Start production server (builds frontend, serves from single port):

```bash
# Auto-detect available port starting from 8000
trackai server start

# Specify port
trackai server start --port 8080

# Specify host
trackai server start --host 0.0.0.0

# Disable auto-reload
trackai server start --no-reload
```

**What it does**:
1. Builds the frontend (`npm run build`)
2. Starts the FastAPI backend
3. Serves frontend from `/static`
4. Auto-detects available port if not specified

**Output**:
```
Starting TrackAI...

Building frontend...
Frontend built successfully!

Starting backend server on port 8000...

TrackAI is running!
Access the app at: http://localhost:8000

Press Ctrl+C to stop the server
```

### `trackai server dev`

Start development mode with hot reload (separate ports for backend and frontend):

```bash
# Auto-detect available ports
trackai server dev

# Specify custom ports
trackai server dev --backend-port 8001 --frontend-port 5174
```

**What it does**:
1. Starts FastAPI backend on backend-port (default: 8000)
2. Starts Vite dev server on frontend-port (default: 5173)
3. Frontend auto-proxies `/api` requests to backend
4. Both servers have hot reload enabled

**Output**:
```
Starting TrackAI in development mode...

Backend starting on port 8000...
Frontend starting on port 5173...

✓ Backend ready at http://localhost:8000
✓ Frontend ready at http://localhost:5173

Press Ctrl+C to stop both servers
```

**When to use**:
- Frontend development with hot reload
- Working on React components
- Iterating on UI changes

## Database Commands

### `trackai db info`

Show database statistics:

```bash
trackai db info
```

**Output**:
```
Database Information

Storage Type: local
Mode: auto
Database Path: /Users/you/.trackai/trackai.duckdb
File Size: 12.45 MB

Table Statistics:
  projects       :       15 rows
  runs           :      234 rows
  configs        :      234 rows
  metrics        :   45,678 rows
  files          :        0 rows
  custom_views   :        3 rows
  dashboards     :        1 rows
```

### `trackai db backup`

Backup database to a file:

```bash
# Backup to specific file
trackai db backup --output ~/backups/trackai-backup.duckdb

# Backup with timestamp
trackai db backup --output ~/backups/trackai-$(date +%Y%m%d).duckdb
```

**What it does**:
- Copies database file to specified location
- Preserves all data (projects, runs, metrics)

### `trackai db reset`

Delete all data (warning: irreversible):

```bash
trackai db reset
```

**Interactive prompt**:
```
⚠️  WARNING: This will delete all experiment data!

Database: /Users/you/.trackai/trackai.duckdb

Are you sure? (y/N):
```

Type `y` to confirm deletion.

**What it deletes**:
- All projects
- All runs
- All metrics
- All configurations
- All custom views and dashboards

### `trackai db migrate`

Migrate from SQLite to DuckDB:

```bash
trackai db migrate \
  --sqlite-path ~/.trackai/trackai.db \
  --duckdb-path ~/.trackai/trackai.duckdb \
  --yes
```

**Options**:
- `--sqlite-path`: Path to source SQLite database
- `--duckdb-path`: Path to destination DuckDB database
- `--yes`: Skip confirmation prompt

**What it does**:
- Reads all data from SQLite database
- Creates new DuckDB database
- Migrates all tables (projects, runs, metrics, etc.)
- Preserves all data and relationships

### `trackai db sync`

Sync database with S3:

```bash
# Upload to S3 (default)
trackai db sync

# Explicitly specify direction
trackai db sync --direction upload

# Download from S3
trackai db sync --direction download

# Sync both ways
trackai db sync --direction both
```

**Requirements**:
- S3 storage must be configured (`trackai config s3`)
- AWS credentials must be set

**When to use**:
- Manual backup to S3
- Restore from S3
- Sync after batch updates

**Note**: SDK automatically downloads on `init()` and uploads on `finish()`, so manual sync is usually not needed.

## Configuration Commands

### `trackai config s3`

Configure S3 storage:

```bash
trackai config s3 \
  --bucket my-trackai-experiments \
  --key trackai.duckdb \
  --region us-east-1
```

**Options**:
- `--bucket`: S3 bucket name
- `--key`: S3 object key (filename in bucket)
- `--region`: AWS region

**Prerequisites**:
```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

**What it does**:
- Updates TrackAI configuration
- Saves to `~/.trackai/config.json`
- Future runs will use S3 storage

### `trackai config show`

Display current configuration:

```bash
trackai config show
```

**Output**:
```
TrackAI Configuration

Database:
  Storage Type: s3
  Mode: auto
  Local DB Path: /Users/you/.trackai/trackai.duckdb

S3 Settings:
  Bucket: my-trackai-experiments
  Key: trackai.duckdb
  Region: us-east-1
  Local Cache: /Users/you/.trackai/trackai.duckdb
```

## Init Command

### `trackai init`

Initialize TrackAI (first-time setup):

```bash
trackai init
```

**What it does**:
- Creates `~/.trackai/` directory
- Initializes configuration file
- Sets up database location
- Validates installation

## Common Workflows

### Starting for Production

```bash
trackai server start
```

Single command to build and serve everything.

### Development Workflow

```bash
# Terminal 1: Start servers
trackai server dev

# Terminal 2: Make changes to code
# Changes auto-reload in both backend and frontend
```

### Backing Up Before Experiment

```bash
# Backup current state
trackai db backup --output ~/backups/before-experiment.duckdb

# Run experiments
python my_experiment.py

# If something goes wrong, restore backup
cp ~/backups/before-experiment.duckdb ~/.trackai/trackai.duckdb
```

### Migrating to S3

```bash
# 1. Set AWS credentials
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-east-1"

# 2. Create S3 bucket (optional, if not exists)
aws s3 mb s3://my-trackai-experiments

# 3. Configure TrackAI
trackai config s3 \
  --bucket my-trackai-experiments \
  --key trackai.duckdb \
  --region us-east-1

# 4. Upload current database
trackai db sync --direction upload

# 5. Verify configuration
trackai config show
```

### Checking Database Health

```bash
# View statistics
trackai db info

# Check for issues
trackai db info | grep "Error"
```

## Environment Variables

Override default behavior with environment variables:

```bash
# Custom database location
export TRACKAI_DB_PATH=/path/to/custom/trackai.duckdb

# AWS credentials (for S3)
export AWS_ACCESS_KEY_ID="your-key"
export AWS_SECRET_ACCESS_KEY="your-secret"
export AWS_DEFAULT_REGION="us-east-1"
```

Add to `~/.bashrc` or `~/.zshrc` to make permanent.

## Troubleshooting

### Port Already in Use

CLI automatically finds available ports:

```bash
# Auto-detect from 8000
trackai server start

# Or specify different port
trackai server start --port 8080
```

### Database Not Found

Initialize TrackAI:

```bash
trackai init
```

### S3 Upload Fails

Check AWS credentials:

```bash
# Verify credentials work
aws sts get-caller-identity

# Re-configure S3
trackai config s3 --bucket my-bucket --key trackai.duckdb --region us-east-1
```

### Frontend Build Fails

Install frontend dependencies:

```bash
cd frontend
npm install
```

## Next Steps

- [S3 Storage](s3_storage.md) - Configure cloud storage
- [Python SDK](python_sdk.md) - Use SDK with CLI
- [Installation](installation.md) - Installation guide
