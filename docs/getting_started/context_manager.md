# Context Manager

Guide to using TrackAI's context manager pattern for automatic run management.

## Overview

The context manager pattern (`with` statement) automatically handles run lifecycle:

```python
import trackai

with trackai.init(project="my-project") as run:
    trackai.log({"loss": 0.5}, step=0)
# Run automatically finished on context exit
```

**Benefits**:
- Automatic `finish()` on successful completion
- Automatic failure marking on exceptions
- Guaranteed S3 upload (if configured)
- Cleaner, more Pythonic code

## Basic Usage

### Standard Pattern

```python
import trackai

with trackai.init(
    project="image-classification",
    config={"lr": 0.001, "batch_size": 32}
) as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)
```

When the `with` block exits:
1. `trackai.finish()` is called automatically
2. Run is marked as "completed"
3. Database is synced to S3 (if configured)

### Equivalent Manual Pattern

```python
import trackai

run = trackai.init(project="image-classification", config={"lr": 0.001})
try:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)
finally:
    trackai.finish()
```

**Use context manager** - it's cleaner and less error-prone.

## Automatic Success Handling

The run is marked as "completed" when context exits normally:

```python
import trackai

with trackai.init(project="training") as run:
    for epoch in range(100):
        train_loss = train_one_epoch()
        trackai.log({"train/loss": train_loss}, step=epoch)

    print("Training finished!")
# ✅ Run marked as "completed"
```

## Automatic Failure Handling

If an exception occurs, the run is marked as "failed":

```python
import trackai

with trackai.init(project="training") as run:
    for epoch in range(100):
        if epoch == 50:
            raise ValueError("Training diverged!")
        trackai.log({"loss": 0.5}, step=epoch)
# ❌ Run marked as "failed"
```

The exception is re-raised after marking the run as failed, so you can catch it:

```python
import trackai

try:
    with trackai.init(project="training") as run:
        for epoch in range(100):
            if epoch == 50:
                raise ValueError("Training diverged!")
            trackai.log({"loss": 0.5}, step=epoch)
except ValueError as e:
    print(f"Training failed: {e}")
    # Run is already marked as "failed"
```

## Guaranteed Cleanup

Context managers guarantee cleanup even if exceptions occur:

```python
import trackai

with trackai.init(project="training") as run:
    # Start training
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)

        # Even if KeyboardInterrupt (Ctrl+C) happens here...
        if user_stopped:
            break

# ...the run is still properly finished and synced
```

**Guaranteed actions on exit**:
- Run state updated (completed/failed)
- S3 upload triggered (if configured)
- Database session closed
- Resources cleaned up

## S3 Upload

For S3-configured setups, the context manager ensures upload happens:

```python
import trackai

# S3 is configured via: trackai config s3 --bucket my-bucket ...

with trackai.init(project="training") as run:
    for epoch in range(1000):  # Long training
        trackai.log({"loss": 0.5}, step=epoch)

# ✅ Database automatically uploaded to S3 on exit
```

Without context manager, you must remember to call `finish()`:

```python
run = trackai.init(project="training")
for epoch in range(1000):
    trackai.log({"loss": 0.5}, step=epoch)
# ❌ If program crashes here, S3 upload never happens!

trackai.finish()  # Must remember to call this
```

## Nested Contexts

You can nest TrackAI contexts, but each `init()` creates a new run:

```python
import trackai

# Outer run
with trackai.init(project="main-experiment") as run1:
    trackai.log({"main_loss": 0.5}, step=0)

    # Inner run (separate run!)
    with trackai.init(project="sub-experiment") as run2:
        trackai.log({"sub_loss": 0.3}, step=0)
    # run2 finished

    trackai.log({"main_loss": 0.4}, step=1)
# run1 finished
```

**Note**: Inner `init()` overwrites the global run. Better to use instance methods:

```python
import trackai

with trackai.init(project="main") as run1:
    run1.log({"main_loss": 0.5}, step=0)

    with trackai.init(project="sub") as run2:
        run2.log({"sub_loss": 0.3}, step=0)

    run1.log({"main_loss": 0.4}, step=1)
```

## Early Exit

You can exit the context early with `return` or `break`:

```python
import trackai

def train_model():
    with trackai.init(project="training") as run:
        for epoch in range(100):
            loss = train_one_epoch()
            trackai.log({"loss": loss}, step=epoch)

            # Early stopping
            if loss < 0.01:
                print("Converged!")
                return  # Context exits here, run finished
    # Never reached

train_model()
```

## Exception Handling Patterns

### Catch Specific Exceptions

```python
import trackai

with trackai.init(project="training") as run:
    try:
        for epoch in range(100):
            loss = train_one_epoch()
            trackai.log({"loss": loss}, step=epoch)
    except RuntimeError as e:
        # Log error metric
        trackai.log({"error_message": str(e)}, step=epoch)
        raise  # Re-raise to mark run as failed
```

### Continue on Error

If you catch and don't re-raise, the run is marked as "completed":

```python
import trackai

with trackai.init(project="training") as run:
    for epoch in range(100):
        try:
            loss = train_one_epoch()
            trackai.log({"loss": loss}, step=epoch)
        except RuntimeError:
            print("Epoch failed, continuing...")
            continue  # Run continues as "running"

# ✅ Run marked as "completed" (no exception escaped context)
```

### Manual Failure Marking

Mark run as failed without raising exception:

```python
import trackai

with trackai.init(project="training") as run:
    for epoch in range(100):
        loss = train_one_epoch()
        trackai.log({"loss": loss}, step=epoch)

        if loss > 10.0:  # Training diverged
            # This just logs state, doesn't mark as failed
            trackai.log({"diverged": True}, step=epoch)
            break

# Run still marked as "completed"
```

To manually mark as failed, you need to raise an exception or use a workaround.

## Resume with Context Manager

Use `resume="allow"` to continue existing runs:

```python
import trackai

# First run
with trackai.init(project="long-training", name="week-long", resume="allow") as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)

# Later, resume the same run
with trackai.init(project="long-training", name="week-long", resume="allow") as run:
    for epoch in range(100, 200):  # Continue from epoch 100
        trackai.log({"loss": 0.4}, step=epoch)
```

See [Resuming Runs](resuming_runs.md) for more details.

## Best Practices

1. **Always use context manager** - Guarantees proper cleanup
2. **Let exceptions propagate** - Don't catch-all unless necessary
3. **Use early returns** - Exit context when done, don't set flags
4. **Log errors before re-raising** - Capture error state in metrics
5. **Don't nest contexts** - Each context creates a new run

## Anti-Patterns

### Forgetting to Use Context Manager

```python
# ❌ Bad - Manual finish() easy to forget
run = trackai.init(project="training")
for epoch in range(100):
    trackai.log({"loss": 0.5}, step=epoch)
trackai.finish()  # What if exception happens before this?

# ✅ Good - Context manager guarantees finish
with trackai.init(project="training") as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)
```

### Catching All Exceptions

```python
# ❌ Bad - Swallows all exceptions, run marked as "completed" even on errors
with trackai.init(project="training") as run:
    try:
        for epoch in range(100):
            trackai.log({"loss": 0.5}, step=epoch)
    except Exception:
        pass  # Swallows exception, run appears successful!

# ✅ Good - Let exceptions propagate
with trackai.init(project="training") as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)
# Exceptions automatically mark run as failed
```

### Manually Calling finish()

```python
# ❌ Bad - Calling finish() explicitly in context manager
with trackai.init(project="training") as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)
    trackai.finish()  # Redundant! Context manager does this
# finish() called again on context exit!

# ✅ Good - Let context manager handle it
with trackai.init(project="training") as run:
    for epoch in range(100):
        trackai.log({"loss": 0.5}, step=epoch)
```

## Complete Example

```python
import trackai
import time

def train_model(config):
    """Train a model with automatic run management"""

    with trackai.init(
        project="image-classification",
        name=f"resnet-lr-{config['lr']}",
        group="lr-sweep",
        config=config
    ) as run:

        best_val_loss = float('inf')

        for epoch in range(config['epochs']):
            # Training
            train_loss, train_acc = train_one_epoch(config)

            # Validation
            val_loss, val_acc = validate(config)

            # Log metrics
            trackai.log({
                "train/loss": train_loss,
                "train/accuracy": train_acc,
                "val/loss": val_loss,
                "val/accuracy": val_acc,
                "learning_rate": get_current_lr()
            }, step=epoch)

            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= 10:
                print(f"Early stopping at epoch {epoch}")
                trackai.log({"early_stopped": True}, step=epoch)
                return best_val_loss  # Context exits, run finished

        return best_val_loss

# Train multiple models
configs = [
    {"lr": 0.001, "epochs": 100},
    {"lr": 0.01, "epochs": 100},
    {"lr": 0.1, "epochs": 100}
]

for config in configs:
    try:
        best_loss = train_model(config)
        print(f"Config {config} achieved {best_loss:.4f}")
    except Exception as e:
        print(f"Config {config} failed: {e}")
        # Run automatically marked as failed
```

## Next Steps

- [Python SDK](python_sdk.md) - Complete SDK guide
- [Resuming Runs](resuming_runs.md) - Resume runs with context manager
- [S3 Storage](s3_storage.md) - Automatic S3 upload on context exit
