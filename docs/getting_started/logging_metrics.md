# Logging Metrics

Best practices and patterns for logging training metrics in TrackAI.

## Metric Types

TrackAI supports two types of metrics:

### Step-Based Metrics (Training Metrics)

Use `trackai.log()` for metrics that correspond to training steps or epochs:

```python
trackai.log({"loss": 0.5, "accuracy": 0.8}, step=epoch)
```

**X-axis**: Step number
**Use for**: Loss, accuracy, learning rate, gradients, etc.

### Timestamp-Based Metrics (System Metrics)

Use `trackai.log_system()` for system monitoring metrics:

```python
trackai.log_system({"gpu_util": 0.95, "memory_gb": 8.2})
```

**X-axis**: Timestamp
**Use for**: GPU utilization, memory usage, temperature, etc.

See [System Metrics](system_metrics.md) for details.

## Nested Metric Paths

### Why Use Nested Paths?

Nested paths organize related metrics into groups:

```python
trackai.log({
    "train/loss": 0.5,
    "train/accuracy": 0.85,
    "val/loss": 0.6,
    "val/accuracy": 0.80
}, step=epoch)
```

**Benefits**:
- Grouped visualizations in web interface
- Easier to compare train vs validation
- Cleaner metric organization
- Standard convention (train/, val/, test/)

### Common Path Conventions

```python
trackai.log({
    # Training metrics
    "train/loss": 0.5,
    "train/accuracy": 0.85,
    "train/f1_score": 0.82,

    # Validation metrics
    "val/loss": 0.6,
    "val/accuracy": 0.80,
    "val/f1_score": 0.78,

    # Test metrics
    "test/loss": 0.65,
    "test/accuracy": 0.78,

    # Optimizer metrics
    "optimizer/learning_rate": 0.001,
    "optimizer/gradient_norm": 0.05,

    # Model metrics
    "model/num_parameters": 25_000_000,
    "model/sparsity": 0.3
}, step=epoch)
```

### Multi-Level Nesting

You can nest arbitrarily deep:

```python
trackai.log({
    "train/classification/accuracy": 0.85,
    "train/classification/f1": 0.82,
    "train/detection/mAP": 0.75,
    "train/detection/precision": 0.80,
    "val/classification/accuracy": 0.83,
    "val/detection/mAP": 0.73
}, step=epoch)
```

## Logging Frequency

### Every Step

For fine-grained tracking:

```python
for batch_idx in range(num_batches):
    loss = train_batch()
    trackai.log({"train/batch_loss": loss}, step=batch_idx)
```

**Pros**: Detailed view of training dynamics
**Cons**: Large number of data points, slower to visualize

### Every Epoch

Standard practice for epoch-based training:

```python
for epoch in range(num_epochs):
    train_loss = train_one_epoch()
    val_loss = validate()

    trackai.log({
        "train/loss": train_loss,
        "val/loss": val_loss
    }, step=epoch)
```

**Pros**: Clean charts, fast visualization
**Cons**: Less granular view

### Hybrid Approach

Log different metrics at different frequencies:

```python
global_step = 0

for epoch in range(num_epochs):
    for batch_idx, batch in enumerate(dataloader):
        loss = train_batch(batch)

        # Log batch loss every step
        trackai.log({"train/batch_loss": loss}, step=global_step)
        global_step += 1

    # Log epoch-level metrics
    val_loss = validate()
    trackai.log({
        "train/epoch_loss": epoch_loss,
        "val/loss": val_loss
    }, step=epoch)
```

## Auto-Incrementing Steps

If you don't provide a `step` parameter, TrackAI auto-increments:

```python
with trackai.init(project="training") as run:
    trackai.log({"loss": 0.5})  # step=0
    trackai.log({"loss": 0.4})  # step=1
    trackai.log({"loss": 0.3})  # step=2
```

**When to use**:
- Sequential logging without explicit step numbers
- Simple scripts where step doesn't matter

**When not to use**:
- Need specific step numbers
- Resuming runs (steps would restart from 0)
- Logging at different frequencies

## Metric Value Types

TrackAI supports multiple value types:

### Floats (Most Common)

```python
trackai.log({
    "loss": 0.5234,
    "accuracy": 0.8567,
    "learning_rate": 0.001
}, step=epoch)
```

### Integers

```python
trackai.log({
    "epoch": 10,
    "num_samples": 50000,
    "batch_size": 32
}, step=epoch)
```

### Booleans

```python
trackai.log({
    "early_stopping_triggered": True,
    "best_model_updated": False
}, step=epoch)
```

### Strings

```python
trackai.log({
    "checkpoint_path": "/models/checkpoint-epoch-10.pt",
    "status": "training"
}, step=epoch)
```

## Logging Patterns

### Classification Metrics

```python
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

# After validation
y_pred = model.predict(X_val)

trackai.log({
    "val/accuracy": accuracy_score(y_true, y_pred),
    "val/precision": precision_score(y_true, y_pred, average='weighted'),
    "val/recall": recall_score(y_true, y_pred, average='weighted'),
    "val/f1": f1_score(y_true, y_pred, average='weighted')
}, step=epoch)
```

### Object Detection Metrics

```python
trackai.log({
    "val/mAP": 0.75,
    "val/mAP_50": 0.85,
    "val/mAP_75": 0.70,
    "val/precision": 0.80,
    "val/recall": 0.75
}, step=epoch)
```

### Segmentation Metrics

```python
trackai.log({
    "val/iou": 0.65,
    "val/dice": 0.75,
    "val/pixel_accuracy": 0.90
}, step=epoch)
```

### NLP Metrics

```python
trackai.log({
    "val/bleu": 0.35,
    "val/rouge_1": 0.45,
    "val/rouge_2": 0.30,
    "val/rouge_l": 0.40,
    "val/perplexity": 15.2
}, step=epoch)
```

## Batch Logging

Log multiple metrics at once for atomic updates:

```python
# ✅ Good - Log all metrics together
trackai.log({
    "train/loss": 0.5,
    "train/accuracy": 0.85,
    "val/loss": 0.6,
    "val/accuracy": 0.80
}, step=epoch)

# ❌ Avoid - Separate log calls
trackai.log({"train/loss": 0.5}, step=epoch)
trackai.log({"train/accuracy": 0.85}, step=epoch)
trackai.log({"val/loss": 0.6}, step=epoch)
trackai.log({"val/accuracy": 0.80}, step=epoch)
```

**Why batch?**
- Atomic database transaction
- Consistent timestamps
- Better performance

## Learning Rate Schedules

Track learning rate changes:

```python
import torch

optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100)

for epoch in range(100):
    train_loss = train_one_epoch()

    # Get current learning rate
    current_lr = optimizer.param_groups[0]['lr']

    trackai.log({
        "train/loss": train_loss,
        "optimizer/lr": current_lr
    }, step=epoch)

    scheduler.step()
```

## Gradient Tracking

Monitor gradient norms:

```python
import torch

for epoch in range(100):
    optimizer.zero_grad()
    loss = model(inputs)
    loss.backward()

    # Compute gradient norm
    total_norm = 0
    for p in model.parameters():
        if p.grad is not None:
            total_norm += p.grad.data.norm(2).item() ** 2
    total_norm = total_norm ** 0.5

    trackai.log({
        "train/loss": loss.item(),
        "optimizer/gradient_norm": total_norm
    }, step=epoch)

    optimizer.step()
```

## Per-Class Metrics

Log metrics for each class:

```python
from sklearn.metrics import classification_report

# After validation
report = classification_report(y_true, y_pred, output_dict=True)

metrics = {}
for class_name, scores in report.items():
    if isinstance(scores, dict):
        metrics[f"val/class_{class_name}/precision"] = scores['precision']
        metrics[f"val/class_{class_name}/recall"] = scores['recall']
        metrics[f"val/class_{class_name}/f1"] = scores['f1-score']

trackai.log(metrics, step=epoch)
```

## Best Practices

1. **Use nested paths** - Group related metrics (`train/`, `val/`, `test/`)
2. **Batch log metrics** - Log all metrics for a step at once
3. **Consistent step numbers** - Use epoch or global_step consistently
4. **Include learning rate** - Always log LR for debugging
5. **Log validation metrics** - Track generalization, not just training
6. **Use descriptive names** - `train/cross_entropy_loss` vs `loss`
7. **Track important hyperparameters** - Log as metrics if they change

## Anti-Patterns

### Don't Mix Step Types

```python
# ❌ Bad - Mixing epoch and batch steps
trackai.log({"train/loss": 0.5}, step=epoch)  # epoch-based
trackai.log({"val/loss": 0.6}, step=global_step)  # batch-based
```

### Don't Log Too Frequently

```python
# ❌ Bad - Logging every iteration for long training
for i in range(1_000_000):
    trackai.log({"loss": 0.5}, step=i)  # 1M data points!
```

**Solution**: Log every N iterations or aggregate:

```python
# ✅ Good - Log every 100 iterations
for i in range(1_000_000):
    if i % 100 == 0:
        trackai.log({"loss": 0.5}, step=i)
```

### Don't Use Step for System Metrics

```python
# ❌ Bad - Using step for system metrics
trackai.log({"gpu_util": 0.95}, step=epoch)

# ✅ Good - Use log_system()
trackai.log_system({"gpu_util": 0.95})
```

## Next Steps

- [System Metrics](system_metrics.md) - GPU and memory monitoring
- [Python SDK](python_sdk.md) - Complete SDK reference
- [Web Interface](web_interface.md) - Visualizing metrics in the UI
