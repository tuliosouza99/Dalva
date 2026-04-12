# Python SDK

## Overview

Dalva's Python API lets you log experiments:

- `dalva.init()` - Initialize a new run or resume an existing one
- `run.log()` - Log metrics with steps
- `run.create_table()` - Create a table linked to the run
- `run.finish()` - Complete the run and all linked tables
- `dalva.table()` - Initialize a standalone table (not linked to a run)
- `table.log()` - Log a DataFrame to the table
- `table.finish()` - Complete the table

## Quick Index

| Topic | File |
|-------|------|
| [Initialize a Run](runs.md) | `dalva.init()`, `resume_from`, config |
| [Log Metrics](metrics.md) | `run.log()`, series vs. scalar, upsert |
| [Tables](tables.md) | `dalva.table()`, log modes, DataFrames |
| [Config vs Metrics](metrics.md#when-to-use-config-vs-metrics) | When to use each |
