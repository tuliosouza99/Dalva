"""
Simple example showing how to use TrackAI for experiment tracking.

This example demonstrates:
- Initializing a run with configuration
- Logging metrics at different steps
- Finishing a run
"""

import trackai
import random

# Initialize a new run
run = trackai.init(
    project="example-project",
    name="simple-experiment",
    config={
        "learning_rate": 0.001,
        "batch_size": 32,
        "optimizer": "adam",
    },
)

print(f"Started run: {run}")

# Simulate training loop
for step in range(10):
    loss = 1.0 - (step * 0.08) + random.uniform(-0.05, 0.05)
    accuracy = 0.5 + (step * 0.04) + random.uniform(-0.02, 0.02)

    run.log(
        {
            "train/loss": loss,
            "train/accuracy": accuracy,
        },
        step=step,
    )

    print(f"Step {step}: loss={loss:.4f}, accuracy={accuracy:.4f}")

# Log validation metrics
run.log(
    {
        "val/loss": 0.25,
        "val/accuracy": 0.92,
    }
)

print("\nTraining complete!")
run.finish()
print("Run finished successfully!")
