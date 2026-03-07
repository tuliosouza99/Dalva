# System Metrics

Guide to logging system metrics (GPU, memory, CPU) in TrackAI.

## Overview

System metrics are **timestamp-based** metrics that track system resources during training. Unlike training metrics (which use steps), system metrics use timestamps for the x-axis.

Use `trackai.log_system()` for:
- GPU utilization and memory
- CPU usage
- System memory
- Disk I/O
- Network usage
- Temperature sensors

## Basic Usage

```python
import trackai

with trackai.init(project="monitoring") as run:
    # Log system metrics
    trackai.log_system({
        "gpu_utilization": 0.95,
        "gpu_memory_used_gb": 8.2,
        "cpu_percent": 45.2,
        "memory_used_gb": 16.5
    })
```

**Key difference from `trackai.log()`**:
- No `step` parameter
- Uses current timestamp for x-axis
- Appears in separate section in web UI

## GPU Metrics

### Using nvidia-smi

```python
import subprocess
import trackai

def get_gpu_metrics():
    """Get GPU metrics using nvidia-smi"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,temperature.gpu',
             '--format=csv,noheader,nounits'],
            capture_output=True,
            text=True
        )

        util, memory, temp = result.stdout.strip().split(', ')

        return {
            "gpu_utilization": float(util) / 100,  # 0-1 range
            "gpu_memory_used_mb": float(memory),
            "gpu_temperature": float(temp)
        }
    except Exception:
        return {}

with trackai.init(project="training") as run:
    for epoch in range(100):
        # Train model
        train_one_epoch()

        # Log GPU metrics
        trackai.log_system(get_gpu_metrics())
```

### Using pynvml

```python
import pynvml
import trackai

# Initialize NVML
pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # GPU 0

def get_gpu_metrics():
    """Get GPU metrics using pynvml"""
    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

    return {
        "gpu_utilization": util.gpu / 100,
        "gpu_memory_used_gb": memory.used / (1024**3),
        "gpu_memory_total_gb": memory.total / (1024**3),
        "gpu_temperature": temp
    }

with trackai.init(project="training") as run:
    for epoch in range(100):
        train_one_epoch()
        trackai.log_system(get_gpu_metrics())
```

### Using GPUtil

```python
import GPUtil
import trackai

def get_gpu_metrics():
    """Get GPU metrics using GPUtil"""
    gpus = GPUtil.getGPUs()
    if not gpus:
        return {}

    gpu = gpus[0]  # First GPU
    return {
        "gpu_utilization": gpu.load,  # 0-1
        "gpu_memory_used_gb": gpu.memoryUsed / 1024,
        "gpu_memory_percent": gpu.memoryUtil,  # 0-1
        "gpu_temperature": gpu.temperature
    }

with trackai.init(project="training") as run:
    for epoch in range(100):
        train_one_epoch()
        trackai.log_system(get_gpu_metrics())
```

## CPU and Memory Metrics

### Using psutil

```python
import psutil
import trackai

def get_system_metrics():
    """Get system metrics using psutil"""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)

    # Memory
    memory = psutil.virtual_memory()

    # Disk
    disk = psutil.disk_usage('/')

    return {
        "cpu_percent": cpu_percent,
        "memory_used_gb": memory.used / (1024**3),
        "memory_percent": memory.percent,
        "disk_used_gb": disk.used / (1024**3),
        "disk_percent": disk.percent
    }

with trackai.init(project="training") as run:
    for epoch in range(100):
        train_one_epoch()
        trackai.log_system(get_system_metrics())
```

## Combined GPU and System Metrics

```python
import pynvml
import psutil
import trackai

# Initialize GPU monitoring
pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

def get_all_metrics():
    """Get both GPU and system metrics"""
    # GPU metrics
    gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    gpu_memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
    gpu_temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

    # System metrics
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    return {
        # GPU
        "gpu/utilization": gpu_util.gpu / 100,
        "gpu/memory_used_gb": gpu_memory.used / (1024**3),
        "gpu/memory_percent": (gpu_memory.used / gpu_memory.total),
        "gpu/temperature": gpu_temp,

        # System
        "system/cpu_percent": cpu_percent,
        "system/memory_used_gb": memory.used / (1024**3),
        "system/memory_percent": memory.percent
    }

with trackai.init(project="training") as run:
    for epoch in range(100):
        train_one_epoch()
        trackai.log_system(get_all_metrics())
```

## Logging Frequency

### Every Epoch

Standard frequency for epoch-based training:

```python
with trackai.init(project="training") as run:
    for epoch in range(100):
        train_one_epoch()

        # Log system metrics after each epoch
        trackai.log_system(get_system_metrics())
```

### Every N Batches

For long epochs, log more frequently:

```python
with trackai.init(project="training") as run:
    for epoch in range(100):
        for batch_idx, batch in enumerate(dataloader):
            train_batch(batch)

            # Log system metrics every 100 batches
            if batch_idx % 100 == 0:
                trackai.log_system(get_system_metrics())
```

### Background Thread

Log continuously in the background:

```python
import threading
import time
import trackai

def monitor_system(stop_event):
    """Monitor system in background thread"""
    while not stop_event.is_set():
        trackai.log_system(get_system_metrics())
        time.sleep(10)  # Log every 10 seconds

# Start monitoring
stop_event = threading.Event()
monitor_thread = threading.Thread(target=monitor_system, args=(stop_event,))
monitor_thread.start()

try:
    with trackai.init(project="training") as run:
        for epoch in range(100):
            train_one_epoch()
finally:
    # Stop monitoring
    stop_event.set()
    monitor_thread.join()
```

## Per-GPU Metrics

For multi-GPU training:

```python
import pynvml
import trackai

pynvml.nvmlInit()
num_gpus = pynvml.nvmlDeviceGetCount()

def get_multi_gpu_metrics():
    """Get metrics for all GPUs"""
    metrics = {}

    for i in range(num_gpus):
        handle = pynvml.nvmlDeviceGetHandleByIndex(i)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)

        metrics[f"gpu_{i}/utilization"] = util.gpu / 100
        metrics[f"gpu_{i}/memory_used_gb"] = memory.used / (1024**3)
        metrics[f"gpu_{i}/temperature"] = temp

    return metrics

with trackai.init(project="multi-gpu-training") as run:
    for epoch in range(100):
        train_one_epoch()
        trackai.log_system(get_multi_gpu_metrics())
```

## Combining with Training Metrics

Log both training and system metrics:

```python
import trackai

with trackai.init(project="training") as run:
    for epoch in range(100):
        # Training
        train_loss = train_one_epoch()
        val_loss = validate()

        # Log training metrics (step-based)
        trackai.log({
            "train/loss": train_loss,
            "val/loss": val_loss
        }, step=epoch)

        # Log system metrics (timestamp-based)
        trackai.log_system({
            "gpu_util": get_gpu_util(),
            "memory_gb": get_memory_usage()
        })
```

**Important**: Keep them separate - training metrics use `log()`, system metrics use `log_system()`.

## Best Practices

1. **Use `log_system()` for system metrics** - Don't use `log()` with steps
2. **Use nested paths** - Group by resource type (`gpu/`, `system/`)
3. **Log at reasonable frequency** - Every epoch or every N batches
4. **Include units in metric names** - `memory_used_gb` vs `memory`
5. **Normalize to 0-1** - Use percentages for utilization (0.95 = 95%)
6. **Monitor all GPUs** - Track each GPU separately in multi-GPU setups
7. **Background monitoring** - Consider background thread for continuous monitoring

## Anti-Patterns

### Don't Use Steps for System Metrics

```python
# ❌ Bad - Using steps for system metrics
trackai.log({"gpu_util": 0.95}, step=epoch)

# ✅ Good - Use log_system()
trackai.log_system({"gpu_util": 0.95})
```

### Don't Log Too Frequently

```python
# ❌ Bad - Logging every batch (too many points)
for batch in dataloader:
    train_batch(batch)
    trackai.log_system(get_system_metrics())  # 10,000+ log calls!

# ✅ Good - Log every N batches
for batch_idx, batch in enumerate(dataloader):
    train_batch(batch)
    if batch_idx % 100 == 0:
        trackai.log_system(get_system_metrics())
```

### Don't Mix Metric Types

```python
# ❌ Bad - Mixing training and system metrics
trackai.log({
    "loss": 0.5,
    "gpu_util": 0.95  # Should use log_system()
}, step=epoch)

# ✅ Good - Separate calls
trackai.log({"loss": 0.5}, step=epoch)
trackai.log_system({"gpu_util": 0.95})
```

## Complete Example

```python
import trackai
import pynvml
import psutil
import time

# Initialize GPU monitoring
pynvml.nvmlInit()
gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)

def get_comprehensive_metrics():
    """Get all system metrics"""
    # GPU
    gpu_util = pynvml.nvmlDeviceGetUtilizationRates(gpu_handle)
    gpu_mem = pynvml.nvmlDeviceGetMemoryInfo(gpu_handle)
    gpu_temp = pynvml.nvmlDeviceGetTemperature(gpu_handle, pynvml.NVML_TEMPERATURE_GPU)

    # CPU/Memory
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()

    # Disk
    disk = psutil.disk_usage('/')

    return {
        # GPU metrics
        "gpu/utilization": gpu_util.gpu / 100,
        "gpu/memory_used_gb": gpu_mem.used / (1024**3),
        "gpu/memory_percent": gpu_mem.used / gpu_mem.total,
        "gpu/temperature": gpu_temp,

        # System metrics
        "system/cpu_percent": cpu_percent,
        "system/memory_used_gb": memory.used / (1024**3),
        "system/memory_percent": memory.percent,
        "system/disk_percent": disk.percent
    }

# Train with monitoring
with trackai.init(
    project="image-classification",
    config={"model": "resnet50", "lr": 0.001}
) as run:

    for epoch in range(100):
        # Training
        train_loss, train_acc = train_one_epoch()
        val_loss, val_acc = validate()

        # Log training metrics
        trackai.log({
            "train/loss": train_loss,
            "train/accuracy": train_acc,
            "val/loss": val_loss,
            "val/accuracy": val_acc
        }, step=epoch)

        # Log system metrics
        trackai.log_system(get_comprehensive_metrics())

print("✅ Training complete with full system monitoring!")
```

## Next Steps

- [Logging Metrics](logging_metrics.md) - Training metrics best practices
- [Python SDK](python_sdk.md) - Complete SDK guide
- [Web Interface](web_interface.md) - Viewing system metrics in UI
