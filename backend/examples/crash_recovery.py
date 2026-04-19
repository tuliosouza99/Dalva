"""
Crash recovery demo — WAL persistence + dalva sync.

This script demonstrates the queue persistence and crash recovery mechanism:
1. A training run that simulates a server crash mid-training
2. WAL (write-ahead log) persists unsent operations to disk
3. The `dalva sync` CLI replays the pending operations

Prerequisites:
    dalva server start    # in another terminal

Usage:
    python examples/crash_recovery.py
"""

import random
import shutil
import sys
import tempfile
from pathlib import Path

import dalva
import httpx
from dalva.cli.sync import _replay_file
from dalva.sdk.wal import WALManager
from dalva.sdk.worker import PendingRequest

server_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
outbox_dir = Path(tempfile.mkdtemp(prefix="dalva_demo_")) / "outbox"

print("=" * 60)
print("Dalva Crash Recovery Demo")
print("=" * 60)

# --- Phase 1: Normal training (server up) ---
print("\n--- Phase 1: Normal training ---")
run = dalva.init(
    project="crash-demo",
    name="resilient-run",
    server_url=server_url,
    config={"model": "mlp", "lr": 0.01, "epochs": 30},
    outbox_dir=outbox_dir,
)

for step in range(10):
    loss = 1.0 - step * 0.08 + random.uniform(-0.02, 0.02)
    run.log({"train/loss": loss}, step=step)

run.flush(timeout=10)
print("  Flushed 10 metrics to server")

# --- Phase 2: Simulate crash — write WAL directly ---
print("\n--- Phase 2: Simulating crash (server unreachable) ---")
db_id = run._db_id

wal = WALManager("run", db_id, outbox_dir=outbox_dir)
for step in range(10, 20):
    loss = 1.0 - step * 0.08 + random.uniform(-0.02, 0.02)
    wal.append(
        PendingRequest(
            method="POST",
            url=f"/api/runs/{db_id}/log",
            payload={"metrics": {"train/loss": loss}, "step": step},
            batch_key=f"run:{db_id}",
        )
    )
wal.append(
    PendingRequest(
        method="POST",
        url=f"/api/runs/{db_id}/finish",
    )
)

pending = WALManager.list_pending(outbox_dir=outbox_dir)
print(f"  WAL written: {pending[0].entry_count} operations in {pending[0].path.name}")

# --- Phase 3: Sync (replay from disk) ---
print("\n--- Phase 3: Replaying with dalva sync ---")

client = httpx.Client(base_url=server_url)
client.get("/api/health").raise_for_status()

total_ok = 0
for info in pending:
    ok, fail, _ = _replay_file(client, info)
    total_ok += ok
    print(f"  {info.path.name}: synced {ok} operations")
client.close()

print(f"\n  Total recovered: {total_ok} operations")

# --- Verify ---
print("\n--- Verification ---")
remaining = WALManager.list_pending(outbox_dir=outbox_dir)
print(f"  Pending WAL files: {len(remaining)}")
print(f"  WAL file exists: {wal.exists}")
print(f"\n  Run ID: {run.run_id}")
print(f"  Server URL: {server_url}")

# Cleanup
run._worker = None
shutil.rmtree(outbox_dir.parent, ignore_errors=True)
print("\nDone!")
