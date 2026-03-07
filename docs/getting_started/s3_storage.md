# S3 Storage

Guide to configuring and using S3 storage for TrackAI experiments.

## Overview

TrackAI supports storing experiments in Amazon S3 with a unique **split architecture**:

- **SDK (logging)**: Downloads database on `init()`, uploads on `finish()`
- **Server (visualization)**: Uses DuckDB ATTACH for read-only S3 access

**Benefits**:
- ✅ No slow startup/shutdown for server
- ✅ No manual sync commands needed
- ✅ Fast local writes during training
- ✅ Automatic S3 backup on experiment completion

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

### 3. Start Visualization Server

```bash
trackai server start
```

Server reads directly from S3 (no download required).

### 4. Log Experiments

```python
import trackai

# Automatically downloads DB from S3 on init()
with trackai.init(project="training") as run:
    trackai.log({"loss": 0.5}, step=0)
# Automatically uploads DB to S3 on context exit
```

## Split Architecture

### How It Works

TrackAI uses two different modes depending on the use case:

#### Logging Mode (Python SDK)

When running experiments with the Python SDK:

1. **On `init()`**:
   - Downloads database from S3 to temporary location
   - Uses local file for fast writes
   - No network latency during training

2. **During training**:
   - All `log()` calls write to local database
   - Maximum write performance
   - No S3 interaction

3. **On `finish()`**:
   - Uploads complete database back to S3
   - Atomic update of S3 object
   - Local temp file cleaned up

#### Visualization Mode (Server)

When viewing experiments in the web interface:

1. **On server start**:
   - No download from S3
   - Instant startup
   - Attaches to S3 using DuckDB HTTPFS extension

2. **During queries**:
   - Reads data directly from S3
   - No local cache (always up-to-date)
   - Read-only access

3. **On server shutdown**:
   - No upload required
   - No hanging or delays
   - Clean shutdown

### Why This Architecture?

**Traditional approach** (used by many tools):
- Download entire database on server start (slow)
- Upload entire database on server shutdown (slow, may fail)
- Local cache can become stale

**TrackAI's split approach**:
- SDK downloads/uploads only when logging (infrequent)
- Server never downloads/uploads (frequent startups/shutdowns)
- Server always sees latest data from S3

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
    "storage_type": "s3",
    "s3_bucket": "my-trackai-experiments",
    "s3_key": "trackai.duckdb",
    "s3_region": "us-east-1",
    "local_cache_path": "~/.trackai/trackai.duckdb"
  }
}
```

### Verify Configuration

```bash
trackai config show
```

## Usage

### Logging Experiments

No code changes needed! Use TrackAI normally:

```python
import trackai

# Automatically handles S3 download/upload
with trackai.init(project="training", config={"lr": 0.001}) as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)

# Database uploaded to S3 on context exit
```

**What happens**:
1. `init()` downloads database from S3
2. Training logs to local temp file (fast)
3. Context exit uploads to S3
4. Temp file cleaned up

### Viewing Experiments

Start the server to view experiments:

```bash
trackai server start
```

Server reads directly from S3 using DuckDB's HTTPFS extension.

### Multiple Concurrent Experiments

Each experiment downloads, logs locally, and uploads:

```python
# Experiment 1
with trackai.init(project="exp1") as run:
    trackai.log({"loss": 0.5}, step=0)
# Uploads to S3

# Experiment 2 (sees results from Experiment 1)
with trackai.init(project="exp2") as run:
    trackai.log({"loss": 0.4}, step=0)
# Uploads to S3
```

TrackAI handles concurrent uploads correctly.

## Manual Sync (Optional)

The SDK automatically syncs, but you can manually sync if needed:

### Upload to S3

```bash
trackai db sync --direction upload
```

### Download from S3

```bash
trackai db sync --direction download
```

### Sync Both Ways

```bash
trackai db sync --direction both
```

**When to use manual sync**:
- Backup/restore operations
- Migration between machines
- Emergency data recovery

**When NOT to use**:
- Normal SDK usage (automatic)
- Server operation (read-only from S3)

## Migrating to S3

### From Local to S3

```bash
# 1. Backup local database (safety)
trackai db backup --output ~/backups/local-backup.duckdb

# 2. Configure S3
trackai config s3 \
  --bucket my-trackai-experiments \
  --key trackai.duckdb \
  --region us-east-1

# 3. Upload local database to S3
trackai db sync --direction upload

# 4. Verify
trackai db info
```

### From S3 to Local

```bash
# 1. Download from S3
trackai db sync --direction download

# 2. Update config to use local storage
# Edit ~/.trackai/config.json:
{
  "database": {
    "storage_type": "local",
    "db_path": "~/.trackai/trackai.duckdb"
  }
}

# 3. Verify
trackai db info
```

## Best Practices

1. **Use context manager** - Ensures S3 upload happens:
   ```python
   with trackai.init(project="p") as run:
       trackai.log({"loss": 0.5}, step=0)
   # ✅ Upload guaranteed
   ```

2. **Set AWS credentials in shell config** - Add to `~/.bashrc`/`~/.zshrc`:
   ```bash
   export AWS_ACCESS_KEY_ID="your-key"
   export AWS_SECRET_ACCESS_KEY="your-secret"
   export AWS_DEFAULT_REGION="us-east-1"
   ```

3. **Use S3 for shared experiments** - Team members can all use same bucket

4. **Monitor S3 costs** - DuckDB files are small, but check usage:
   ```bash
   aws s3 ls s3://my-trackai-experiments/ --summarize
   ```

5. **Backup before migration** - Always backup before switching storage modes

## Troubleshooting

### S3 Upload Fails

**Check AWS credentials**:

```bash
aws sts get-caller-identity
```

Expected output:
```json
{
    "UserId": "AIDAXXXXXXXXX",
    "Account": "123456789012",
    "Arn": "arn:aws:iam::123456789012:user/your-user"
}
```

**Check bucket permissions**:

```bash
aws s3 ls s3://my-trackai-experiments/
```

### Database Not Found in S3

**First upload**:

```bash
trackai db sync --direction upload
```

**Verify upload**:

```bash
aws s3 ls s3://my-trackai-experiments/trackai.duckdb
```

### Server Can't Read from S3

**Check HTTPFS extension**:

Server uses DuckDB HTTPFS extension. If it fails:

1. Check AWS credentials are set
2. Check bucket/key are correct
3. Check bucket permissions allow `s3:GetObject`

**Test S3 access**:

```bash
aws s3 cp s3://my-trackai-experiments/trackai.duckdb /tmp/test.duckdb
```

### Concurrent Upload Conflicts

If multiple experiments finish simultaneously, last-write-wins. To avoid:

```python
# Use different run names
with trackai.init(project="p", name="unique-run-1") as run:
    trackai.log({"loss": 0.5}, step=0)

with trackai.init(project="p", name="unique-run-2") as run:
    trackai.log({"loss": 0.4}, step=0)
```

## Advanced: Multi-Region Setup

For team members in different AWS regions:

```bash
# US team
trackai config s3 --bucket trackai-us --key trackai.duckdb --region us-east-1

# EU team
trackai config s3 --bucket trackai-eu --key trackai.duckdb --region eu-west-1
```

Use S3 replication to sync buckets (outside TrackAI scope).

## Cost Estimation

**Storage costs** (typical):
- DuckDB file: ~10-50 MB for 1000 runs
- S3 Standard: $0.023 per GB/month
- Monthly cost: ~$0.001-$0.002 (negligible)

**Request costs**:
- SDK upload: 1 PUT per experiment
- Server reads: Multiple GETs per page load
- Typical monthly cost: < $0.01

**Total**: Usually under $1/month for active use.

## Next Steps

- [CLI Usage](cli_usage.md) - Database sync commands
- [Python SDK](python_sdk.md) - Using SDK with S3
- [Context Manager](context_manager.md) - Guaranteed S3 upload
