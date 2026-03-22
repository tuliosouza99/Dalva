# S3 Storage

TrackAI uses a **local-first architecture** — the database lives at `~/.trackai/trackai.duckdb`, and S3 sync is opt-in.

## How It Works

| Component | Behavior |
|-----------|----------|
| SDK (logging) | Writes to local `~/.trackai/trackai.duckdb`. Use `pull=True`/`push=True` on `init()` for S3 sync. |
| Server (dashboard) | Always reads from local `~/.trackai/trackai.duckdb`. Mid-run metrics visible in real time. |
| CLI | `trackai db pull` / `trackai db push` for manual sync. |

## Setup

1. **Set AWS credentials** in your environment:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

2. **Configure TrackAI**:

```bash
trackai config s3 --bucket my-bucket --key trackai.duckdb --region us-east-1
```

## Logging with S3 Sync

```python
import trackai

# Pull from S3 before run, push to S3 after
run = trackai.init(project="training", pull=True, push=True)

for epoch in range(100):
    run.log({"loss": 0.5}, step=epoch)

run.finish()  # Database uploaded to S3 (because push=True)
```

## CLI Sync

```bash
trackai db pull   # Download S3 → ~/.trackai/trackai.duckdb
trackai db push   # Upload ~/.trackai/trackai.duckdb → S3
trackai config show
```

## Benefits

- **Mid-run visibility** — dashboard reads the same local DB the SDK writes to
- **Fast logging** — zero S3 latency during training
- **Simple** — server never touches S3 directly
