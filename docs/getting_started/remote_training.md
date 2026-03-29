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
    run.log({"loss": loss}, step=step)

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
