"""
Example: Linked run and table.

Creates a run and a table linked to it via run.create_table(),
logs rows using the new DalvaSchema system, then finishes with
a single run.finish() call. Demonstrates streaming data back.

Usage:
    dalva server start
    python examples/linked_table.py
"""

import dalva
from dalva import DalvaSchema
import random
import sys

server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


class PredictionSchema(DalvaSchema):
    sample_id: int
    label: str
    confidence: float
    correct: bool


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

table = run.create_table(schema=PredictionSchema, name="Predictions")

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

for i, label in enumerate(labels):
    table.log_row(
        {
            "sample_id": i,
            "label": label,
            "confidence": round(0.5 + i * 0.02 + random.uniform(-0.05, 0.05), 3),
            "correct": random.random() > 0.3,
        }
    )

table.flush()
print(f"[Dalva] Logged {len(labels)} rows to table {table.table_id}")

run.finish()

print(f"\nRun: {run.run_id}  |  Table: {table.table_id}")

print("Streaming rows back from table:")
for row in table.get_table(stream=True):
    print(f"  {row}")

print(f"\nView at: {server_url}")
