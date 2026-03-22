# Installation

## Requirements

- **Python**: >= 3.10 and <= 3.14
- **OS**: macOS, Linux, or Windows

## Install

```bash
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI/backend
uv sync
```

Verify:

```bash
trackai --version
```

## Start the Server

```bash
trackai server start
```

The server runs on http://localhost:8000

## Database

Data is stored at: `~/.trackai/trackai.duckdb`
