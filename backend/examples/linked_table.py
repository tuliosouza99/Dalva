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

df = pd.DataFrame(
    {
        "sample_id": range(5),
        "label": ["cat", "dog", "bird", "cat", "dog"],
        "confidence": [0.95, 0.87, 0.72, 0.91, 0.83],
        "correct": [True, True, False, True, False],
    }
)
table.log(df)

run.finish()

print(f"\nRun: {run.run_id}  |  Table: {table.table_id}")
print(f"View at: {server_url}")
