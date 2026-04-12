"""
Example: Linked run and table.

Creates a run and a table linked to it via run.create_table(),
logs data to both, then finishes with a single run.finish() call.

Usage:
    dalva server start
    python examples/linked_table.py
"""

import dalva
import pandas as pd
import random
import sys

server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

run = dalva.init(
    project="link-test",
    name="Training Run",
    server_url=server_url,
    config={
        "model": "resnet50",
        "lr": 0.001,
        "epochs": 10,
    },
)

for step in range(10):
    loss = 1.0 - step * 0.08 + random.uniform(-0.02, 0.02)
    run.log(
        {"train/loss": loss, "train/accuracy": min(0.99, 0.5 + step * 0.05)}, step=step
    )

table = run.create_table(name="Predictions", log_mode="IMMUTABLE")

labels = [
    "cat",
    "dog",
    "bird",
    "fish",
    "horse",
    "rabbit",
    "snake",
    "turtle",
    "frog",
    "lizard",
    "cat",
    "dog",
    "bird",
    "horse",
    "rabbit",
    "snake",
    "turtle",
    "cat",
    "dog",
    "fish",
    "frog",
    "lizard",
    "cat",
    "horse",
    "rabbit",
]

df = pd.DataFrame(
    {
        "sample_id": range(25),
        "label": labels,
        "confidence": [
            round(0.5 + i * 0.02 + random.uniform(-0.05, 0.05), 3) for i in range(25)
        ],
        "score": [round(random.uniform(0, 100), 1) for _ in range(25)],
        "correct": [random.random() > 0.3 for _ in range(25)],
    }
)
table.log(df)

run.finish()

print(f"\nRun: {run.run_id}  |  Table: {table.table_id}")
print(f"View at: {server_url}")
