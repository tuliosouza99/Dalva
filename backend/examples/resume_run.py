"""
Example demonstrating run resumption.

Shows how to resume an existing run to continue logging metrics.
"""

import trackai

# First, create a run
print("=== Creating initial run ===")
run1 = trackai.init(
    project="example-project",
    name="resumable-run",
    config={"initial_lr": 0.01},
)

run1.log({"loss": 1.0, "step": 0}, step=0)
run1.log({"loss": 0.8, "step": 1}, step=1)
print(f"Logged 2 steps. Run ID: {run1.run_id}")
run1.finish()

# Now resume the same run using its run_id
print(f"\n=== Resuming run {run1.run_id} ===")
run2 = trackai.init(
    project="example-project",
    resume=run1.run_id,  # Pass the run_id to resume
)

run2.log({"loss": 0.6, "step": 2}, step=2)
run2.log({"loss": 0.4, "step": 3}, step=3)
print("Logged 2 more steps")
run2.finish()

print("\nRun resumed successfully!")
print(f"All metrics are now part of run: {run2.run_id}")
