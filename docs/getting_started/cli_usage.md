# CLI Usage

## Installation

The `trackai` CLI is included when you install the backend dependencies:

```bash
cd backend && uv sync
trackai --help
```

## Server Commands

### `trackai server start`

Start production server (builds frontend, serves from single port):

```bash
trackai server start              # Auto-detect port starting from 8000
trackai server start --port 8080  # Specify port
trackai server start --no-reload   # Disable auto-reload
```

### `trackai server dev`

Start development mode with hot reload (separate ports):

```bash
trackai server dev                    # Auto-detect ports
trackai server dev --backend-port 8001 --frontend-port 5174
```

Use this when working on frontend React components with hot reload enabled.

## Database Commands

```bash
trackai db info      # Show statistics
trackai db backup    # Create backup
trackai db reset     # Delete all data (requires confirmation)
```

## S3 Commands

Requires `trackai config s3 --bucket <bucket> --key <key> --region <region>` and AWS credentials in your environment.

```bash
trackai db pull      # Download S3 → ~/.trackai/trackai.duckdb
trackai db push      # Upload ~/.trackai/trackai.duckdb → S3
trackai config show  # View current configuration
```

## Configuration

```bash
# Set S3 configuration
trackai config s3 --bucket my-bucket --key trackai.duckdb --region us-east-1
```
