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
