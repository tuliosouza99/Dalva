# Remote Training

Track experiments running on remote machines (clusters, GPUs, cloud instances) by running Dalva directly on the remote machine and syncing data back to your local database when training finishes.

## How It Works

1. Run `dalva server start` on the remote machine
2. Train your model, logging metrics to `localhost` as usual
3. After training, export the database to an NDJSON stream
4. Import the stream into your local Dalva database

## Setup

### 1. Start Dalva Server (Remote Machine)

```bash
dalva server start
```

The server listens on `http://localhost:8000` by default.

### 2. Run Training (Remote Machine)

```python
import dalva

run = dalva.init(
    project="vit-finetune",
    name="gpu-experiment",
    config={
        "learning_rate": 0.001,
        "batch_size": 64,
        "epochs": 100,
    },
    server_url="http://localhost:8000",
)

for step in range(10000):
    loss = train_step(step)
    run.log({"train": {"loss": loss}}, step=step)

run.finish()
```

All metrics are written to the local DuckDB on the remote machine — no network traffic leaves the machine during training.

### 3. Sync Back to Local Machine

After training finishes, export the data and import it locally.

**Option A: One-liner via SSH pipe**

```bash
ssh gpu-server "dalva db export --project vit-finetune" | dalva db import -
```

This streams the NDJSON export directly over SSH into your local database. No temporary files needed.

**Option B: Export to file, transfer, then import**

```bash
# On the remote machine
dalva db export --output /tmp/vit-export.ndjson --project vit-finetune

# Transfer to local machine
scp gpu-server:/tmp/vit-export.ndjson .

# Import into local database
dalva db import vit-export.ndjson
```

**Option C: Compressed transfer (recommended for large exports)**

```bash
ssh gpu-server "dalva db export --project vit-finetune | gzip" | gunzip | dalva db import -
```

## CLI Reference

### Export

```bash
dalva db export                          # Export entire database to stdout
dalva db export --output dump.ndjson     # Export to file
dalva db export --project my-project     # Export only one project
```

### Import

```bash
dalva db import dump.ndjson              # Import from file
dalva db import -                        # Import from stdin (for piping)
dalva db import dump.ndjson --fail-on-conflict  # Error on duplicates
```

### Merge Behavior

By default, `dalva db import` **skips** records that already exist locally:

- Projects with the same name are reused
- Runs with the same `(project, run_id)` are skipped (along with their metrics/configs)
- Tables with the same `(project, table_id)` are skipped
- Individual configs and metrics that conflict are silently ignored

Use `--fail-on-conflict` to error instead of skipping if you want strict import behavior.

## Crash Recovery

When training on a remote machine, Dalva's write-ahead log (WAL) protects against crashes during training. If the training process crashes:

```bash
# On the remote machine — replay unsent operations to the local server
dalva sync
```

Then export/import as usual.

## Troubleshooting

### Empty Export

- Verify the remote Dalva server was running during training
- Check that runs completed successfully: `dalva query runs` on the remote machine

### Import Conflicts

- Use `dalva db info` on the local machine to inspect existing data
- Re-importing the same export is safe (duplicate records are skipped)

### Large Exports

For projects with millions of metric rows, use the compressed transfer option:

```bash
ssh gpu-server "dalva db export | gzip" | gunzip | dalva db import -
```
