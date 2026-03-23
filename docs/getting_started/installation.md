# Installation

## Requirements

- **Python**: >= 3.10 and <= 3.14
- **OS**: macOS, Linux, or Windows

## Install

```bash
git clone https://github.com/tuliosouza99/Dalva.git
cd Dalva/backend
uv sync
```

Verify:

```bash
dalva --version
```

## Start the Server

```bash
dalva server start
```

The server runs on http://localhost:8000

## Database

Data is stored at: `~/.dalva/dalva.duckdb`
