"""
Example demonstrating run forking.

Shows how to fork an existing run to create a copy with the same
configs and metrics, then continue logging to the forked run.

Usage:
    dalva server start
    python examples/fork_run.py [server_url]
"""

import dalva
import sys

server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

# First, create a run with config and metrics
print("=== Creating initial run ===")
run1 = dalva.init(
    project="fork-example",
    name="original-run",
    config={"lr": 0.01, "batch_size": 32},
    server_url=server_url,
)

run1.log({"loss": 1.0, "accuracy": 0.1}, step=0)
run1.log({"loss": 0.8, "accuracy": 0.3}, step=1)
run1.log({"loss": 0.6, "accuracy": 0.5}, step=2)
print(f"Logged 3 steps. Run ID: {run1.run_id}")
run1.finish()

# Fork the run using its run_id string
print(f"\n=== Forking run {run1.run_id} ===")
run2 = dalva.init(
    project="fork-example",
    fork_from=run1.run_id,
    server_url=server_url,
)

print(f"Forked run ID: {run2.run_id}")
print(f"Forked run name: {run2.name}")

# Continue logging to the forked run
run2.log({"loss": 0.4, "accuracy": 0.7}, step=3)
run2.log({"loss": 0.2, "accuracy": 0.9}, step=4)
print("Logged 2 more steps to forked run")
run2.finish()

print(f"\nOriginal run: {run1.run_id} (3 steps)")
print(f"Forked run:   {run2.run_id} (5 steps — inherited 3 + 2 new)")
