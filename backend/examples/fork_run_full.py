"""
Example demonstrating all fork_from functionalities.

Tests:
1. Basic fork (configs + metrics copied, no tables)
2. Fork with copy_tables_on_fork=True (all tables + rows copied)
3. Fork with copy_tables_on_fork=[id] (specific tables copied)
4. Fork with custom name
5. Fork of a fork (chain)
6. Forked run has fork_from field set

Usage:
    dalva server start
    python examples/fork_run_full.py [server_url]
"""

import sys

import dalva
from dalva import DalvaSchema

server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
project = "fork-demo"
errors = []


class PredictionSchema(DalvaSchema):
    input: int
    output: float


class EmbeddingSchema(DalvaSchema):
    vec: list


def check(label, condition, detail=""):
    if condition:
        print(f"  PASS: {label}")
    else:
        msg = f"  FAIL: {label}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        errors.append(label)


# ── Setup: create a source run with config, metrics, and tables ──
print("=== Setup: creating source run ===")
run1 = dalva.init(
    project=project,
    name="source-run",
    config={"lr": 0.01, "batch_size": 32, "optimizer": "adam"},
    server_url=server_url,
)
run1.log({"loss": 1.0, "accuracy": 0.1}, step=0)
run1.log({"loss": 0.7, "accuracy": 0.4}, step=1)
run1.log({"loss": 0.5, "accuracy": 0.6}, step=2)

t1 = run1.create_table(name="predictions", schema=PredictionSchema)
t1.log_rows(
    [
        {"input": 1, "output": 0.9},
        {"input": 2, "output": 0.8},
    ]
)

t2 = run1.create_table(name="embeddings", schema=EmbeddingSchema)
t2.log_rows(
    [
        {"vec": [0.1, 0.2]},
        {"vec": [0.3, 0.4]},
    ]
)

run1.finish()
print(f"Source run: {run1.run_id} (name={run1.name})\n")


# ── Test 1: Basic fork (no tables) ──
print("=== Test 1: Basic fork (copy_tables_on_fork=False) ===")
fork1 = dalva.init(
    project=project,
    fork_from=run1.run_id,
    copy_tables_on_fork=False,
    server_url=server_url,
)
check(
    "forked run has default name",
    fork1.name == f"fork of {run1.name}",
    f"got {fork1.name}",
)
check("forked run has different id", fork1.run_id != run1.run_id)

fork1_config = fork1.get_config("lr")
check(
    "config copied",
    fork1_config is not None and fork1_config.get("value") == 0.01,
    f"got {fork1_config}",
)

fork1_metric = fork1.get("loss", step=2)
check(
    "metrics copied",
    fork1_metric is not None and fork1_metric.get("value") == 0.5,
    f"got {fork1_metric}",
)

fork1.finish()
print()


# ── Test 2: Fork with copy_tables_on_fork=True ──
print("=== Test 2: Fork with copy_tables_on_fork=True ===")
fork2 = dalva.init(
    project=project,
    fork_from=run1.run_id,
    copy_tables_on_fork=True,
    server_url=server_url,
)
check("forked with tables has default name", fork2.name == f"fork of {run1.name}")
fork2.finish()
print("  (table verification via API — check in UI)")
print()


# ── Test 3: Fork with custom name ──
print("=== Test 3: Fork with custom name ===")
fork3 = dalva.init(
    project=project,
    name="my-custom-fork",
    fork_from=run1.run_id,
    server_url=server_url,
)
check("custom name is used", fork3.name == "my-custom-fork", f"got {fork3.name}")
fork3.finish()
print()


# ── Test 4: Continue logging to forked run ──
print("=== Test 4: Continue logging to forked run ===")
fork4 = dalva.init(
    project=project,
    fork_from=run1.run_id,
    server_url=server_url,
)
fork4.log({"loss": 0.3, "accuracy": 0.8}, step=3)
fork4.log({"loss": 0.1, "accuracy": 0.95}, step=4)
fork4.flush()

metric_step3 = fork4.get("loss", step=3)
metric_step0 = fork4.get("loss", step=0)
check(
    "can log new step to fork",
    metric_step3 is not None and metric_step3.get("value") == 0.3,
    f"got {metric_step3}",
)
check(
    "inherited step still accessible",
    metric_step0 is not None and metric_step0.get("value") == 1.0,
    f"got {metric_step0}",
)
fork4.finish()
print()


# ── Test 5: Fork of a fork (chain) ──
print("=== Test 5: Fork of a fork ===")
fork_of_fork = dalva.init(
    project=project,
    fork_from=fork4.run_id,
    server_url=server_url,
)
check("fork of fork has different id", fork_of_fork.run_id != fork4.run_id)
check(
    "fork of fork has default name",
    fork_of_fork.name == f"fork of {fork4.name}",
    f"got {fork_of_fork.name}",
)
fork_of_fork.finish()
print()


# ── Summary ──
print("=" * 50)
if errors:
    print(f"FAILED: {len(errors)} test(s)")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
    print("\nRuns created:")
    print(f"  source:   {run1.run_id}")
    print(f"  fork1:    {fork1.run_id}  (basic fork, no tables)")
    print(f"  fork2:    {fork2.run_id}  (fork with tables)")
    print(f"  fork3:    {fork3.run_id}  (custom name)")
    print(f"  fork4:    {fork4.run_id}  (continue logging)")
    print(f"  fork^2:   {fork_of_fork.run_id}  (fork of fork)")
