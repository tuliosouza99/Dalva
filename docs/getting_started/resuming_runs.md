# Resuming Runs

Guide to resuming runs for checkpoint recovery and continuing experiments.

## Overview

TrackAI supports three resume modes for handling existing runs:

- `resume="never"` - Always create a new run (default)
- `resume="allow"` - Resume if run exists, otherwise create new
- `resume="must"` - Must resume existing run, fail if doesn't exist

## Resume Modes

### never (Default)

Always creates a new run, even if one with the same name exists:

```python
import trackai

# First call - creates run
run1 = trackai.init(project="training", name="experiment-1")
trackai.log({"loss": 0.5}, step=0)
trackai.finish()

# Second call - creates a NEW run with same name
run2 = trackai.init(project="training", name="experiment-1", resume="never")
trackai.log({"loss": 0.4}, step=0)
trackai.finish()

# Result: Two separate runs, both named "experiment-1"
```

**When to use**:
- Starting fresh experiments
- Don't want to accidentally overwrite existing runs
- Default safe behavior

### allow

Resumes run if it exists, creates new if it doesn't:

```python
import trackai

# First call - no run exists, creates new
run1 = trackai.init(project="training", name="long-run", resume="allow")
trackai.log({"loss": 0.5}, step=0)
trackai.finish()

# Second call - run exists, resumes it
run2 = trackai.init(project="training", name="long-run", resume="allow")
trackai.log({"loss": 0.4}, step=1)  # Continues from step 1
trackai.finish()

# Result: One run with metrics at steps 0 and 1
```

**When to use**:
- Checkpoint recovery (resume if training was interrupted)
- Long training jobs that may need restarts
- Flexible resume behavior

### must

Must resume existing run, fails if run doesn't exist:

```python
import trackai

# No run exists yet
try:
    run = trackai.init(project="training", name="nonexistent", resume="must")
except RuntimeError as e:
    print(f"Error: {e}")  # "Run 'nonexistent' not found and resume='must'"

# Create run first
run1 = trackai.init(project="training", name="checkpoint-run")
trackai.log({"loss": 0.5}, step=0)
trackai.finish()

# Now resume works
run2 = trackai.init(project="training", name="checkpoint-run", resume="must")
trackai.log({"loss": 0.4}, step=1)
trackai.finish()
```

**When to use**:
- Strict checkpoint recovery
- Ensure you're continuing specific run
- Fail fast if run doesn't exist

## Checkpoint Recovery Pattern

### Basic Pattern

```python
import trackai
import os

# Training configuration
config = {
    "lr": 0.001,
    "batch_size": 32,
    "epochs": 100
}

# Resume or create run
with trackai.init(
    project="image-classification",
    name="resnet50-main",
    config=config,
    resume="allow"  # Resume if exists
) as run:

    # Determine starting epoch
    checkpoint_path = "checkpoint.pt"
    if os.path.exists(checkpoint_path):
        checkpoint = torch.load(checkpoint_path)
        start_epoch = checkpoint['epoch'] + 1
        model.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        print(f"Resuming from epoch {start_epoch}")
    else:
        start_epoch = 0
        print("Starting from scratch")

    # Train from start_epoch
    for epoch in range(start_epoch, config['epochs']):
        train_loss = train_one_epoch(model, optimizer)
        val_loss = validate(model)

        # Log metrics
        trackai.log({
            "train/loss": train_loss,
            "val/loss": val_loss
        }, step=epoch)

        # Save checkpoint
        torch.save({
            'epoch': epoch,
            'model_state_dict': model.state_dict(),
            'optimizer_state_dict': optimizer.state_dict()
        }, checkpoint_path)
```

### With Automatic Checkpoint Detection

```python
import trackai
import torch
import os

def train_with_resume(config):
    """Train model with automatic checkpoint resume"""

    checkpoint_dir = "checkpoints"
    os.makedirs(checkpoint_dir, exist_ok=True)

    with trackai.init(
        project="training",
        name=config["run_name"],
        config=config,
        resume="allow"
    ) as run:

        # Load checkpoint if exists
        checkpoint_path = os.path.join(checkpoint_dir, f"{config['run_name']}.pt")

        if os.path.exists(checkpoint_path):
            print(f"Loading checkpoint from {checkpoint_path}")
            checkpoint = torch.load(checkpoint_path)
            start_epoch = checkpoint['epoch'] + 1
            model.load_state_dict(checkpoint['model_state_dict'])
            optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        else:
            print("No checkpoint found, starting fresh")
            start_epoch = 0
            model = create_model(config)
            optimizer = create_optimizer(model, config)

        # Training loop
        for epoch in range(start_epoch, config['epochs']):
            train_loss = train_one_epoch(model, optimizer)
            val_loss = validate(model)

            trackai.log({
                "train/loss": train_loss,
                "val/loss": val_loss
            }, step=epoch)

            # Save checkpoint
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss
            }, checkpoint_path)

            print(f"Epoch {epoch}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}")

# Train
config = {"run_name": "resnet-baseline", "lr": 0.001, "epochs": 100}
train_with_resume(config)
```

## Handling Interrupted Training

### Detecting Interruptions

Check if run already exists before starting:

```python
import trackai

run_name = "long-training-job"

# Try to resume
with trackai.init(
    project="training",
    name=run_name,
    resume="allow"
) as run:

    # Check if this is a resume (implement custom logic)
    # TrackAI doesn't expose this directly, so use checkpoints

    checkpoint_path = f"{run_name}.pt"
    if os.path.exists(checkpoint_path):
        print("📦 Resuming from checkpoint")
        checkpoint = torch.load(checkpoint_path)
        start_epoch = checkpoint['epoch'] + 1
    else:
        print("🆕 Starting new training")
        start_epoch = 0

    # Continue training...
```

### Handling Failures

Resume after failures:

```python
import trackai

def train_with_retry(config, max_retries=3):
    """Train with automatic retry on failure"""

    for attempt in range(max_retries):
        try:
            with trackai.init(
                project="training",
                name=config["run_name"],
                config=config,
                resume="allow"  # Resume on retry
            ) as run:

                # Load checkpoint if exists
                start_epoch = load_checkpoint_if_exists()

                # Train
                for epoch in range(start_epoch, config['epochs']):
                    train_loss = train_one_epoch()
                    trackai.log({"loss": train_loss}, step=epoch)
                    save_checkpoint(epoch)

                # Success!
                return True

        except RuntimeError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print("Retrying...")
                time.sleep(10)  # Wait before retry
            else:
                print("Max retries reached")
                return False

# Train with retry
train_with_retry({"run_name": "robust-training", "epochs": 100})
```

## Multiple Resume Sessions

Log to the same run across multiple sessions:

```python
import trackai

# Session 1 - Train epochs 0-50
with trackai.init(project="training", name="multi-session", resume="allow") as run:
    for epoch in range(0, 50):
        trackai.log({"loss": 0.5}, step=epoch)

# Session 2 - Continue epochs 50-100
with trackai.init(project="training", name="multi-session", resume="allow") as run:
    for epoch in range(50, 100):
        trackai.log({"loss": 0.4}, step=epoch)

# Result: One run with 100 steps
```

## Step Management

When resuming, manage steps carefully:

```python
import trackai

# First session
with trackai.init(project="training", name="my-run", resume="allow") as run:
    for step in range(0, 1000):
        trackai.log({"loss": 0.5}, step=step)

# Second session - continue from step 1000
with trackai.init(project="training", name="my-run", resume="allow") as run:
    for step in range(1000, 2000):  # Continue from 1000, not 0!
        trackai.log({"loss": 0.4}, step=step)
```

**Important**: TrackAI doesn't track the last step automatically. You must manage step numbers yourself.

## Best Practices

1. **Use `resume="allow"` for checkpoints** - Flexible and safe
2. **Save checkpoints with epoch/step** - Track where to resume from
3. **Match checkpoint and run names** - Use same name for checkpoint file and run
4. **Continue step numbering** - Don't restart from 0 when resuming
5. **Include resume info in logs** - Log whether resumed or started fresh
6. **Test resume logic** - Ensure checkpoints work before long training

## Anti-Patterns

### Forgetting to Continue Step Numbers

```python
# ❌ Bad - Steps restart from 0 on resume
with trackai.init(project="p", name="r", resume="allow") as run:
    for step in range(0, 1000):  # First session: steps 0-999
        trackai.log({"loss": 0.5}, step=step)

with trackai.init(project="p", name="r", resume="allow") as run:
    for step in range(0, 1000):  # Second session: steps 0-999 again!
        trackai.log({"loss": 0.4}, step=step)  # Overwrites previous data!

# ✅ Good - Continue step numbers
with trackai.init(project="p", name="r", resume="allow") as run:
    for step in range(0, 1000):
        trackai.log({"loss": 0.5}, step=step)

with trackai.init(project="p", name="r", resume="allow") as run:
    for step in range(1000, 2000):  # Continue from 1000
        trackai.log({"loss": 0.4}, step=step)
```

### Using `resume="must"` Without Checking

```python
# ❌ Bad - Crashes if run doesn't exist
with trackai.init(project="p", name="r", resume="must") as run:
    # RuntimeError if "r" doesn't exist!
    trackai.log({"loss": 0.5}, step=0)

# ✅ Good - Use "allow" or handle exception
with trackai.init(project="p", name="r", resume="allow") as run:
    trackai.log({"loss": 0.5}, step=0)
```

### Not Saving Checkpoints

```python
# ❌ Bad - Resume run but no checkpoint (model restarts from scratch)
with trackai.init(project="p", name="r", resume="allow") as run:
    model = create_model()  # Always starts from scratch!
    for epoch in range(100):
        train_loss = train_one_epoch(model)
        trackai.log({"loss": train_loss}, step=epoch)
    # No checkpoint saved!

# ✅ Good - Save checkpoints
with trackai.init(project="p", name="r", resume="allow") as run:
    if os.path.exists("checkpoint.pt"):
        model.load_state_dict(torch.load("checkpoint.pt"))
        start_epoch = 50
    else:
        model = create_model()
        start_epoch = 0

    for epoch in range(start_epoch, 100):
        train_loss = train_one_epoch(model)
        trackai.log({"loss": train_loss}, step=epoch)
        torch.save(model.state_dict(), "checkpoint.pt")
```

## Complete Example

```python
import trackai
import torch
import os

def train_with_full_resume(config):
    """Complete training with checkpoint and run resume"""

    checkpoint_path = f"checkpoints/{config['run_name']}.pt"
    os.makedirs("checkpoints", exist_ok=True)

    with trackai.init(
        project=config['project'],
        name=config['run_name'],
        group=config.get('group'),
        config=config,
        resume="allow"  # Allow resume
    ) as run:

        # Initialize model and optimizer
        model = create_model(config)
        optimizer = create_optimizer(model, config)

        # Load checkpoint if exists
        if os.path.exists(checkpoint_path):
            print(f"📦 Resuming from {checkpoint_path}")
            checkpoint = torch.load(checkpoint_path)

            model.load_state_dict(checkpoint['model'])
            optimizer.load_state_dict(checkpoint['optimizer'])
            start_epoch = checkpoint['epoch'] + 1
            best_val_loss = checkpoint['best_val_loss']

            print(f"   Continuing from epoch {start_epoch}")
            print(f"   Best val loss so far: {best_val_loss:.4f}")
        else:
            print("🆕 Starting new training")
            start_epoch = 0
            best_val_loss = float('inf')

        # Training loop
        for epoch in range(start_epoch, config['epochs']):
            # Train
            train_loss, train_acc = train_one_epoch(model, optimizer)

            # Validate
            val_loss, val_acc = validate(model)

            # Log metrics
            trackai.log({
                "train/loss": train_loss,
                "train/accuracy": train_acc,
                "val/loss": val_loss,
                "val/accuracy": val_acc,
                "learning_rate": optimizer.param_groups[0]['lr']
            }, step=epoch)

            # Update best model
            is_best = val_loss < best_val_loss
            if is_best:
                best_val_loss = val_loss

            # Save checkpoint
            torch.save({
                'epoch': epoch,
                'model': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'best_val_loss': best_val_loss,
                'config': config
            }, checkpoint_path)

            print(f"Epoch {epoch}: train={train_loss:.4f}, val={val_loss:.4f} {'⭐' if is_best else ''}")

        print(f"✅ Training complete! Best val loss: {best_val_loss:.4f}")
        return best_val_loss

# Usage
config = {
    "project": "image-classification",
    "run_name": "resnet50-baseline",
    "group": "baseline-experiments",
    "lr": 0.001,
    "batch_size": 32,
    "epochs": 100
}

train_with_full_resume(config)
```

## Next Steps

- [Context Manager](context_manager.md) - Using resume with context manager
- [Python SDK](python_sdk.md) - Complete SDK guide
- [CLI Usage](cli_usage.md) - Database backup for checkpoint recovery
