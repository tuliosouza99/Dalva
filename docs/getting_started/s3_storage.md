# S3 Storage

Dalva uses a **local-first architecture** — the database lives at `~/.dalva/dalva.duckdb`, and S3 sync is opt-in.

## How It Works

| Component | Behavior |
|-----------|----------|
| SDK (logging) | Writes to local `~/.dalva/dalva.duckdb`. Use `pull=True`/`push=True` on `init()` for S3 sync. |
| Server (dashboard) | Always reads from local `~/.dalva/dalva.duckdb`. Mid-run metrics visible in real time. |
| CLI | `dalva db pull` / `dalva db push` for manual sync. |

## Setup

1. **Set AWS credentials** in your environment:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

2. **Configure Dalva**:

```bash
dalva config s3 --bucket my-bucket --key dalva.duckdb --region us-east-1
```

## Logging with S3 Sync

```python
import dalva

# Pull from S3 before run, push to S3 after
run = dalva.init(project="training", pull=True, push=True)

for epoch in range(100):
    run.log({"loss": 0.5}, step=epoch)

run.finish()  # Database uploaded to S3 (because push=True)
```

## CLI Sync

```bash
dalva db pull   # Download S3 → ~/.dalva/dalva.duckdb
dalva db push   # Upload ~/.dalva/dalva.duckdb → S3
dalva config show
```

## Benefits

- **Mid-run visibility** — dashboard reads the same local DB the SDK writes to
- **Fast logging** — zero S3 latency during training
- **Simple** — server never touches S3 directly
