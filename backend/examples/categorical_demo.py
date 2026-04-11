"""
Demo script for categorical series (bool and string metrics).

Requires the dalva server running: dalva server start

Usage:
    cd backend && uv run python examples/categorical_demo.py
    cd backend && uv run python examples/categorical_demo.py http://localhost:8080
"""

import random
import sys

import dalva

server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# --- Run 1: Training phase tracker (bool series) ---
run1 = dalva.init(
    project="categorical-demo",
    name="phase-tracker",
    server_url=server_url,
    config={"model": "transformer", "lr": 0.001},
)

phases = [
    "train",
    "train",
    "train",
    "validate",
    "train",
    "train",
    "test",
    "train",
    "train",
    "validate",
    "train",
    "train",
    "train",
    "test",
    "train",
    "train",
    "validate",
    "train",
    "train",
    "test",
]

for step in range(20):
    phase = phases[step]
    is_training = phase == "train"
    is_converged = step >= 12
    loss = 1.0 - (step * 0.045) + random.uniform(-0.02, 0.02)

    run1.log(
        {
            "train/loss": loss,
            "phase/is_training": is_training,
            "phase/is_converged": is_converged,
            "phase/name": phase,
        },
        step=step,
    )

run1.finish()
print(f"Run 1 done: {run1.run_id}")


# --- Run 2: Optimizer sweep (string series) ---
optimizers = [
    "adam",
    "adam",
    "sgd",
    "adam",
    "rmsprop",
    "adam",
    "sgd",
    "sgd",
    "adam",
    "rmsprop",
    "adam",
    "adam",
    "sgd",
    "rmsprop",
    "adam",
    "adam",
    "adam",
    "sgd",
    "rmsprop",
    "adam",
]

run2 = dalva.init(
    project="categorical-demo",
    name="optimizer-sweep",
    server_url=server_url,
    config={"model": "resnet50", "lr": 0.01},
)

for step in range(20):
    opt = optimizers[step]
    loss = 1.0 - (step * 0.04) + random.uniform(-0.03, 0.03)
    acc = 0.5 + (step * 0.02) + random.uniform(-0.01, 0.01)

    run2.log(
        {
            "train/loss": loss,
            "train/accuracy": acc,
            "hyperparams/optimizer": opt,
            "hyperparams/lr_schedule": "cosine" if step < 10 else "step",
            "phase/is_training": opt != "rmsprop",
        },
        step=step,
    )

run2.finish()
print(f"Run 2 done: {run2.run_id}")


# --- Run 3: Many-category string series ---
regions = [
    "us-east",
    "us-west",
    "eu-west",
    "us-east",
    "ap-south",
    "us-east",
    "eu-west",
    "us-west",
    "ap-south",
    "us-east",
    "eu-central",
    "us-east",
    "us-west",
    "ap-south",
    "eu-west",
    "us-east",
    "eu-central",
    "us-east",
    "us-west",
    "ap-south",
    "us-east",
    "eu-west",
    "eu-central",
    "us-east",
    "us-west",
    "ap-south",
    "us-east",
    "eu-west",
    "us-east",
    "us-east",
]

run3 = dalva.init(
    project="categorical-demo",
    name="region-tracker",
    server_url=server_url,
    config={"model": "gpt2", "lr": 0.0005},
)

for step in range(30):
    region = regions[step]
    latency = 50 + random.uniform(-10, 10) + (5 if "eu" in region else 0)

    run3.log(
        {
            "infra/latency_ms": latency,
            "infra/region": region,
            "infra/spot_instance": random.random() > 0.3,
        },
        step=step,
    )

run3.finish()
print(f"Run 3 done: {run3.run_id}")


# --- Run 4: Scalar bool/string (not series) ---
run4 = dalva.init(
    project="categorical-demo",
    name="config-only",
    server_url=server_url,
    config={"model": "bert", "lr": 0.0001},
)

run4.log(
    {
        "summary/best_optimizer": "adamw",
        "summary/early_stopped": True,
        "summary/final_accuracy": 0.94,
        "summary/converged": True,
    }
)

run4.finish()
print(f"Run 4 done: {run4.run_id}")

print(f"\nAll done! View at: {server_url}")
print("Check the 'categorical-demo' project to see:")
print("  - bool series (is_training, is_converged, spot_instance)")
print("  - string series with few categories (optimizer, lr_schedule, phase)")
print("  - string series with many categories (region) - test top-N selector")
print("  - scalar bool/string values in config-only run")
