# S3 Storage

Guide to configuring and using S3 storage for TrackAI experiments.

## Overview

TrackAI supports storing experiments in Amazon S3 with a **local-first architecture**:

- **SDK (logging)**: Writes directly to `~/.trackai/trackai.duckdb`. Pass `pull=True` to download from S3 before starting and `push=True` to upload to S3 after finishing.
- **Server (dashboard)**: Always reads from `~/.trackai/trackai.duckdb` — metrics are visible in real time during runs.
- **Manual sync**: Use `trackai db pull` / `trackai db push` from the CLI whenever you need to sync.

**Benefits**:
- ✅ Mid-run visibility — dashboard reads the same local DB that the SDK writes to
- ✅ Explicit sync — no magic auto-sync, you decide when to pull and push
- ✅ Fast logging — zero S3 latency during training
- ✅ Simple server — never touches S3 directly, instant startup and clean shutdown

## Quick Start

### 1. Set AWS Credentials

Add to `~/.bashrc` or `~/.zshrc`:

```bash
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

Then source the file:

```bash
source ~/.bashrc  # or ~/.zshrc
```

### 2. Configure TrackAI for S3

```bash
trackai config s3 \
  --bucket my-trackai-experiments \
  --key trackai.duckdb \
  --region us-east-1
```

### 3. Start the Dashboard

```bash
trackai server start
```

The dashboard reads from `~/.trackai/trackai.duckdb`.

### 4. Log Experiments

```python
import trackai

# pull=True downloads from S3 before starting (picks up runs from other machines)
# push=True uploads to S3 after finishing
run = trackai.init(project="training", pull=True, push=True)
for epoch in range(100):
    run.log({"loss": 0.5}, step=epoch)
run.finish()
# Database uploaded to S3 after finish() (because push=True)
```

### 5. Sync Manually (CLI)

```bash
trackai db pull   # Download S3 → ~/.trackai/trackai.duckdb
trackai db push   # Upload ~/.trackai/trackai.duckdb → S3
```

## Architecture

### How It Works

#### SDK (Python logging)

The SDK always writes to `~/.trackai/trackai.duckdb`. S3 sync is opt-in per run:

- **`pull=True`** (on `init()`): Downloads the database from S3 before the run starts, so you pick up any runs logged elsewhere.
- **`push=True`** (on `finish()`): Uploads the database to S3 after the run finishes.
- Both default to `False` — no S3 interaction unless you ask for it.

```python
# No S3 interaction (default)
run = trackai.init(project="p")
run.finish()

# Pull before, push after
run = trackai.init(project="p", pull=True, push=True)
run.finish()

# Pull before only (read shared data, keep local)
run = trackai.init(project="p", pull=True)
run.finish()

# Push after only (write shared data, no pull)
run = trackai.init(project="p", push=True)
run.finish()
    ...
```

#### Dashboard (visualization server)

The dashboard always reads from `~/.trackai/trackai.duckdb`:

- Mid-run results are visible in real time — the server reads the same file the SDK writes to
- The server never touches S3 — instant startup and clean shutdown
- Run `trackai db pull` to fetch completed runs from S3 that were logged on other machines

### Why Local-First?

The alternative (server reads S3 directly via DuckDB ATTACH) can't show in-progress runs because the SDK writes locally and only syncs to S3 on `finish()`. With local-first, the server reads the same local file, so metrics appear live.

## Configuration

### S3 Setup

#### Create S3 Bucket (if needed)

```bash
aws s3 mb s3://my-trackai-experiments --region us-east-1
```

#### Set Bucket Permissions

Ensure your AWS credentials have these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::my-trackai-experiments",
        "arn:aws:s3:::my-trackai-experiments/*"
      ]
    }
  ]
}
```

#### Configure TrackAI

```bash
trackai config s3 \
  --bucket my-trackai-experiments \
  --key trackai.duckdb \
  --region us-east-1
```

This creates/updates `~/.trackai/config.json`:

```json
{
  "database": {
    "db_path": "~/.trackai/trackai.duckdb",
    "s3_bucket": "my-trackai-experiments",
    "s3_key": "trackai.duckdb",
    "s3_region": "us-east-1"
  }
}
```

### Verify Configuration

```bash
trackai config show
```

## Usage

### Logging Experiments

```python
import trackai

# Minimal — no S3 interaction
run = trackai.init(project="training", config={"lr": 0.001})
for epoch in range(100):
    run.log({"loss": 0.5}, step=epoch)
run.finish()

# With explicit S3 sync
run = trackai.init(project="training", config={"lr": 0.001}, pull=True, push=True)
for epoch in range(100):
    run.log({"loss": 0.5}, step=epoch)
run.finish()
```

### Viewing Experiments

Start the server:

```bash
trackai server start
```

To get the latest runs from S3 first:

```bash
trackai db pull && trackai server start
```

### Manual CLI Sync

```bash
trackai db pull   # Download S3 → ~/.trackai/trackai.duckdb
trackai db push   # Upload ~/.trackai/trackai.duckdb → S3
```

**When to `pull`**:
- Before starting a session to pick up runs from teammates
- To restore from S3 after a local issue

**When to `push`**:
- Manual backup
- Share a set of local runs with the team without starting a new experiment

## Migrating to S3

### From Local to S3

```bash
# 1. Backup local database
trackai db backup --output ~/backups/local-backup.duckdb

# 2. Configure S3
trackai config s3 \
  --bucket my-trackai-experiments \
  --key trackai.duckdb \
  --region us-east-1

# 3. Push to S3
trackai db push

# 4. Verify
trackai db info
```

### From S3 to Local

```bash
# 1. Pull from S3
trackai db pull

# 2. Remove S3 config — edit ~/.trackai/config.json and delete the s3_* fields:
{
  "database": {
    "db_path": "~/.trackai/trackai.duckdb"
  }
}

# 3. Verify
trackai db info
```

## Best Practices

1. **Use `pull=True` when collaborating** — Pick up teammates' runs before starting:
   ```python
   with trackai.init(project="p", pull=True, push=True) as run:
       ...
   ```

2. **Use `push=False` for exploratory runs** — Don't pollute shared S3 with every local experiment:
   ```python
   with trackai.init(project="p") as run:  # no push
       ...
   ```

3. **Set AWS credentials in shell config** — Add to `~/.bashrc`/`~/.zshrc`:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

4. **Backup before migration** — Always backup before switching storage modes.

## Troubleshooting

### S3 Push/Pull Fails

**Check AWS credentials**:

```bash
aws sts get-caller-identity
```

**Check bucket permissions**:

```bash
aws s3 ls s3://my-trackai-experiments/
```

### Database Not Found in S3

Push your local database first:

```bash
trackai db push
```

**Verify upload**:

```bash
aws s3 ls s3://my-trackai-experiments/trackai.duckdb
```

### Dashboard Shows Stale Data

Pull the latest from S3:

```bash
trackai db pull
```

### Database Missing Locally

Pull from S3:

```bash
trackai db pull
```

### Concurrent Upload Conflicts

If multiple machines push simultaneously, last-write-wins. To avoid data loss, use separate S3 keys per machine:

```bash
# Machine A
trackai config s3 --bucket my-bucket --key machine-a.duckdb --region us-east-1

# Machine B
trackai config s3 --bucket my-bucket --key machine-b.duckdb --region us-east-1
```

## Cost Estimation

**Storage costs** (typical):
- DuckDB file: ~10-50 MB for 1000 runs
- S3 Standard: $0.023 per GB/month
- Monthly cost: ~$0.001-$0.002 (negligible)

**Request costs**:
- 1 PUT per `push` (run or CLI)
- 1 GET per `pull` (run or CLI)
- Typical monthly cost: < $0.01

**Total**: Usually under $1/month for active use.

## Next Steps

- [CLI Usage](cli_usage.md) - Full CLI reference including `pull` and `push`
- [Python SDK](python_sdk.md) - Using SDK with S3
