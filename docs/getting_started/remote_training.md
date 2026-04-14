# Remote Training

Track experiments running on remote machines (clusters, GPUs, cloud instances) by using an SSH reverse tunnel to connect to your local Dalva server.

## How It Works

When training on a remote machine, you can't directly reach your local server. By creating an SSH reverse tunnel, the remote machine can forward traffic to your local Dalva server.

## Setup

### 1. Start the Dalva Server (Local Machine)

On your local machine where you want to store the database:

```bash
dalva server start
```

Note the port number shown (e.g., `8000`).

### 2. Create SSH Reverse Tunnel (Remote Machine)

On your remote training machine, create an SSH tunnel:

```bash
ssh -R 8000:localhost:8000 user@your-local-machine
```

This forwards port `8000` on the remote machine to port `8000` on your local machine.

### 3. Run Training (Remote Machine)

On your remote machine, install Dalva and run your experiment:

```python
import dalva

run = dalva.init(
    project="remote-project",
    name="gpu-experiment",
    config={
        "learning_rate": 0.001,
        "batch_size": 64,
        "epochs": 100,
    },
    server_url="http://localhost:8000"
)

for step in range(100):
    loss = train_step(step)
    run.log({"train": {"loss": loss}}, step=step)

run.finish()
```

The `server_url="http://localhost:8000"` points to the SSH tunnel, which forwards traffic to your local Dalva server.

## SSH Tunnel Options

### Keep Tunnel Alive

Add this to your SSH command to prevent the tunnel from timing out:

```bash
ssh -R 8000:localhost:8000 -o ServerAliveInterval=60 user@your-local-machine
```

### Custom Port

If your local server is on a different port, adjust both the SSH tunnel and `server_url`:

```bash
# Local machine: dalva server start --port 9000
# Remote machine: ssh -R 8000:localhost:9000 user@your-local-machine

run = dalva.init(
    project="my-project",
    server_url="http://localhost:8000"  # Tunnel maps 8000 -> 9000
)
```

## Crash Recovery

When training on a remote machine, network issues or process crashes can cause metric data to be lost. Dalva provides automatic crash recovery via a **write-ahead log (WAL)**.

### How It Works

Every `run.log()` call is enqueued to a background worker thread. Before the worker sends each operation to the server, it appends it to a WAL file on disk (`~/.dalva/outbox/`).

```
run.log() → queue → worker appends to WAL → sends HTTP
                              ↓
  finish() times out  → dump remaining → WAL persists on disk
  finish() succeeds   → WAL deleted
  process crashes     → WAL survives   → dalva sync replays later
```

### Automatic Timeout Handling

If `finish()` or `flush()` times out (e.g., the server is unreachable), unsent operations are automatically saved to disk:

```
[Dalva] 7 operation(s) saved to disk. Run 'dalva sync' to replay.
```

### Manual Recovery with `dalva sync`

After a crash or timeout, use the CLI to replay pending operations:

```bash
dalva sync             # Replay all pending operations
dalva sync --status    # Show what's pending without sending
dalva sync --dry-run   # Preview what would be sent
```

Example output:

```
$ dalva sync --status
Pending operations:

  run_42.jsonl: 15 operation(s)
  table_7.jsonl: 3 operation(s)

  Total: 18 operation(s) across 2 file(s)

$ dalva sync
  run_42.jsonl: Synced 15/15 ✓
  table_7.jsonl: Synced 3/3 ✓

Done: synced 18.
```

### Example: Simulated Crash and Recovery

```python
import dalva

# Phase 1: Normal training — server is up
run = dalva.init(project="crash-demo", name="experiment-1")

for step in range(10):
    loss = train_step(step)
    run.log({"loss": loss}, step=step)

run.flush()  # Ensure metrics are sent

# Phase 2: Server goes down / network drops
# ... run.log() continues to enqueue, WAL persists to disk ...
# ... process crashes or finish() times out ...

# Phase 3: Server is back — recover from disk
# Run on the same machine where training happened:
#   $ dalva sync
# All pending metrics are replayed to the server.
```

## Troubleshooting

### Connection Refused

- Verify the SSH tunnel is active: `ssh -R 8000:localhost:8000 user@host` succeeded
- Check that your local Dalva server is still running
- Verify the `server_url` matches the tunnel port

### Tunnel Drops

- Use `ServerAliveInterval=60` to keep the connection alive
- Consider using `autossh` for automatic reconnection:

```bash
autossh -R 8000:localhost:8000 user@your-local-machine
```
