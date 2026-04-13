"""Nested metrics, config, get/remove/relog patterns.

Run this after starting the Dalva server:

    dalva server start

Then:

    python examples/nested_metrics_and_config.py
"""

import dalva

run = dalva.init(
    project="nested-metrics-demo",
    name="nested-example",
    config={
        "optimizer": {
            "name": "adam",
            "lr": 0.001,
            "betas": [0.9, 0.999],
        },
        "model": {
            "backbone": "resnet50",
            "pretrained": True,
        },
        "epochs": 50,
        "batch_size": 32,
    },
)


# ── Nested metrics ──────────────────────────────────────────────────
#
# Nested dicts are flattened with '/' as separator.
# These two calls are equivalent (only run ONE of them — duplicate keys raise 409):
#
#   run.log({"train/loss": 0.8, "train/acc": 0.6}, step=0)
#   run.log({"train": {"loss": 0.8, "acc": 0.6}}, step=0)  # same keys
#
# We'll use the nested form:

run.log({"train": {"loss": 0.8, "acc": 0.6}}, step=0)

# Deep nesting works too:
run.log({"model": {"encoder": {"loss": 0.5}}}, step=0)
# → creates key "model/encoder/loss"

# Flat and nested keys can be mixed in the same call:
run.log({"val/loss": 0.9, "val": {"acc": 0.5}}, step=0)


# ── Getting metrics ─────────────────────────────────────────────────

result = run.get("train/loss", step=0)
print(
    f"train/loss at step 0: {result}"
)  # {"key": "train/loss", "value": 0.8, "step": 0}

result = run.get("train/acc")
print(
    f"train/acc (latest):   {result}"
)  # {"key": "train/acc", "value": 0.6, "step": 0}

# Missing keys return None or your default:
print(f"missing key:          {run.get('nonexistent')}")  # None
print(f"missing with default: {run.get('nonexistent', default=-1)}")  # -1


# ── Getting config ──────────────────────────────────────────────────

cfg = run.get_config("optimizer/lr")
print(f"optimizer/lr: {cfg}")  # {"key": "optimizer/lr", "value": 0.001}

cfg = run.get_config("model/backbone")
print(f"model/backbone: {cfg}")  # {"key": "model/backbone", "value": "resnet50"}

# Lists are stored as-is:
cfg = run.get_config("optimizer/betas")
print(f"optimizer/betas: {cfg}")  # {"key": "optimizer/betas", "value": [0.9, 0.999]}

print(f"missing config: {run.get_config('nonexistent', default='N/A')}")  # N/A


# ── Remove + re-log pattern ────────────────────────────────────────
#
# Logging is strict: duplicate keys raise ValueError (409 Conflict).
# To overwrite, remove first, then log again.

# Overwrite a metric at a specific step:
run.remove("train/loss", step=0)
run.log({"train": {"loss": 0.4}}, step=0)  # new value at step 0

# Overwrite a scalar (no step):
run.log({"best_accuracy": 0.85})
run.remove("best_accuracy")
run.log({"best_accuracy": 0.92})

# Overwrite a nested config key:
run.remove_config("optimizer/lr")
run.log_config({"optimizer": {"lr": 0.01}})

# Verify:
print(
    f"new optimizer/lr: {run.get_config('optimizer/lr')}"
)  # {"key": "optimizer/lr", "value": 0.01}


# ── Simulated training loop with nested metrics ─────────────────────

for step in range(1, 6):
    train_loss = 0.8 / (step + 1)
    train_acc = min(0.95, 0.6 + step * 0.07)
    val_loss = train_loss * 1.1
    val_acc = train_acc - 0.02

    run.log(
        {
            "train": {"loss": train_loss, "accuracy": train_acc},
            "val": {"loss": val_loss, "accuracy": val_acc},
        },
        step=step,
    )

# Get latest val accuracy:
latest = run.get("val/accuracy")
print(f"\nLatest val/accuracy: {latest}")


run.finish()
print("\nDone! Open http://localhost:8000 to see the results.")
