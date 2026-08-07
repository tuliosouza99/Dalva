# Remote Training

Track experiments on clusters, GPUs, and spot instances without running a Dalva
server on the training machine.

## How It Works

1. Each experiment writes a durable local journal.
2. Closed, immutable segments are uploaded asynchronously to object storage.
3. `finish()` waits for remote acknowledgement and retains local copies on failure.

## Setup

### 1. Install the S3 transport

```bash
uv add "dalva[s3]"
```

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
    sync="s3://my-experiments/dalva",
    durability="strict",
)

for step in range(10000):
    loss = train_step(step)
    run.log({"train": {"loss": loss}}, step=step)

run.finish()
```

`log()` returns after the event is journaled locally. Segments are rotated every
500 ms or 256 KiB and uploaded in the background. Use `run.sync()` for an
explicit remote durability barrier.

### 3. View remotely replicated runs

```bash
aws s3 sync s3://my-experiments/dalva ~/.dalva/runs
dalva ui
```

For MinIO, R2, or another S3-compatible service, configure its CLI endpoint and
set `DALVA_S3_ENDPOINT_URL` on the training machine.

## Crash Recovery

Finalized segments and the active journal remain on local disk until the machine
is removed. Restart or resume the run with the same ID to continue from them:

```python
run = dalva.init(
    project="vit-finetune",
    resume_from="RUN-...",
    sync="s3://my-experiments/dalva",
)
run.sync()
```

For spot instances, use `durability="strict"` and short segment intervals. A
machine can still lose events that have not yet received remote acknowledgement;
call `sync()` at checkpoints when that boundary matters.

## Troubleshooting

### Missing remote runs

- Confirm the SDK credentials can write to the bucket.
- Call `run.sync()` and inspect any returned synchronization errors.
- Confirm both `manifest.json` and `events/*.jsonl` were downloaded.

Repeated segment uploads and UI imports are idempotent. Segment filenames include
their SHA-256 checksum, and the materializer tracks `(resource_id, sequence)`.
