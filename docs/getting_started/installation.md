# Installation

This guide covers installing TrackAI and its dependencies.

## System Requirements

- **Python**: >= 3.11
- **Node.js**: >= 18 (for frontend development)
- **Operating System**: macOS, Linux, or Windows

## Backend Installation

### Using uv (Recommended)

[uv](https://docs.astral.sh/uv/) is a fast Python package manager that handles dependencies efficiently.

```bash
# Clone the repository
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI

# Install backend dependencies
cd backend
uv sync
```

The `trackai` CLI command is now available:

```bash
trackai --help
```

### Using pip

```bash
# Clone the repository
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI/backend

# Install in editable mode
pip install -e .
```

### Optional Dependencies

#### Documentation

To build documentation locally:

```bash
cd backend
uv sync --group docs
```

#### Development

For running tests and development tools:

```bash
cd backend
uv sync --group dev
```

## Frontend Installation (Optional)

The frontend is only needed for development. In production mode, `trackai server start` automatically builds and serves the frontend.

```bash
cd frontend
npm install
```

## Verify Installation

Check that TrackAI is installed correctly:

```bash
trackai --version
```

Start the server to verify everything works:

```bash
trackai server start
```

You should see output indicating the server is running:

```
🚀 Starting TrackAI server on port 8000...
📊 Access the web interface at http://localhost:8000
```

## Database Location

TrackAI stores all experiment data in a centralized DuckDB database:

```
~/.trackai/trackai.duckdb
```

The database is created automatically on first run. This centralized location allows you to access experiments from any project directory.

### Custom Database Location

To override the default database location, set the `TRACKAI_DB_PATH` environment variable:

```bash
export TRACKAI_DB_PATH=/path/to/custom/trackai.duckdb
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent.

## AWS Configuration (Optional)

For S3 storage support, configure AWS credentials:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

Then configure TrackAI to use S3:

```bash
trackai config s3 --bucket my-trackai-experiments --key trackai.duckdb --region us-east-1
```

See [S3 Storage](s3_storage.md) for more details.

## Troubleshooting

### Port Already in Use

The `trackai server start` command automatically finds an available port starting from 8000. If you need a specific port:

```bash
trackai server start --port 8080
```

### Permission Errors

If you encounter permission errors when creating the database directory:

```bash
mkdir -p ~/.trackai
chmod 755 ~/.trackai
```

### uv Not Found

If `uv` is not installed:

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or using pip
pip install uv
```

## Next Steps

- [Quick Start](quickstart.md) - 5-minute tutorial
- [Python SDK](python_sdk.md) - Learn the Python API
- [CLI Usage](cli_usage.md) - Server and database commands
