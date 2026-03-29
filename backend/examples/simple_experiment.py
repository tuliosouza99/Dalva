"""
Demo script for remote tracking via SSH tunnel.

This example demonstrates:
1. Starting the dalva server locally: dalva server start
2. SSH with port forwarding: ssh -R 8000:localhost:8000 user@local-machine
3. Running this script remotely with server_url pointing to localhost:8000

Usage:
    python examples/demo_remote_tracking.py [server_url]

Examples:
    python examples/demo_remote_tracking.py                        # Uses http://localhost:8000
    python examples/demo_remote_tracking.py http://localhost:8001 # Uses custom port
"""

import dalva
import random
import sys

# Get server URL from command line argument or default
server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

run = dalva.init(
    project="demo-project",
    name="demo-run",
    server_url=server_url,
    config={
        "model": "resnet50",
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 10,
        "optimizer": "adam",
    },
)

print(f"Started run: {run}")
print("Logging metrics...")

# Simulate training loop
for step in range(20):
    loss = 1.0 - (step * 0.04) + random.uniform(-0.02, 0.02)
    accuracy = 0.5 + (step * 0.02) + random.uniform(-0.01, 0.01)
    learning_rate = 0.001 * (0.95**step)

    run.log(
        {
            "train/loss": loss,
            "train/accuracy": accuracy,
            "train/learning_rate": learning_rate,
        },
        step=step,
    )

    if step % 5 == 0:
        print(f"Step {step}: loss={loss:.4f}, accuracy={accuracy:.4f}")

# Log validation metrics
run.log(
    {
        "val/loss": 0.15 + random.uniform(-0.02, 0.02),
        "val/accuracy": 0.95 + random.uniform(-0.01, 0.01),
    }
)

print("\nTraining complete!")
run.finish()
print("Run finished successfully!")
print(f"\nView results at: {server_url}")
