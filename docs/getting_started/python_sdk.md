# Python SDK

## Overview

Dalva's Python API lets you log experiments:

- `dalva.init()` - Initialize a new run, resume, or fork an existing one
- `run.log()` - Log metrics with steps
- `run.get()` - Retrieve a specific metric
- `run.remove()` - Remove a metric (required before overwriting)
- `run.log_config()` - Add config keys after init
- `run.get_config()` - Retrieve a config key
- `run.remove_config()` - Remove a config key
- `run.create_table()` - Create a table linked to the run
- `run.finish()` - Complete the run and all linked tables
- `dalva.table()` - Initialize a standalone table (not linked to a run)
- `table.log()` - Log a DataFrame to the table
- `table.finish()` - Complete the table

## Quick Index

| Topic | File |
|-------|------|
| [Initialize a Run](runs.md) | `dalva.init()`, `resume_from`, `fork_from`, nested config |
| [Log Metrics](metrics.md) | `run.log()`, nested dicts, series vs. scalar |
| [Get / Remove / Re-log](metrics.md#getting-metrics-and-config) | `run.get()`, `run.remove()`, `run.get_config()`, `run.remove_config()` |
| [Tables](tables.md) | `dalva.table()`, log modes, DataFrames |
| [Config vs Metrics](metrics.md#when-to-use-config-vs-metrics) | When to use each |

## Examples

A complete working example is available at [`examples/nested_metrics_and_config.py`](https://github.com/tuliosouza99/Dalva/tree/main/examples/nested_metrics_and_config.py). |
