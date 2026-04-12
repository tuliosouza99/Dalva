# Quick Start

Get up and running with Dalva in 5 minutes.

## 1. Install Dalva

```bash
git clone https://github.com/tuliosouza99/Dalva.git
cd Dalva/backend
uv sync
```

## 2. Start the Server

```bash
dalva server start
```

The server will automatically find an available port and display the URL.

!!! important
    The Dalva server must be running before you can log experiments. The Python SDK communicates with the server via HTTP.

## 3. Log Your First Experiment

Create a new file `my_experiment.py`:

```python
import dalva

# Initialize a run with nested config
run = dalva.init(
    project="quickstart",
    name="first-experiment",
    config={
        "optimizer": {"name": "adam", "lr": 0.001},
        "batch_size": 32,
        "epochs": 100,
    },
    server_url="http://localhost:8000"
)

# Log metrics during training — nested dicts are flattened with '/' separator
for step in range(100):
    loss = 1.0 / (step + 1)
    accuracy = min(0.95, step / 100)

    run.log({"train": {"loss": loss, "accuracy": accuracy}}, step=step)
    # Equivalent to: run.log({"train/loss": loss, "train/accuracy": accuracy}, step=step)

# Retrieve metrics:
run.get("train/loss", step=0)   # {"key": "train/loss", "value": 1.0, "step": 0}
run.get("train/accuracy")       # latest step value

# Retrieve config:
run.get_config("optimizer/lr")  # {"key": "optimizer/lr", "value": 0.001}

# To overwrite a value, remove it first then re-log:
run.remove("train/loss", step=0)
run.log({"train": {"loss": 0.9}}, step=0)

run.finish()
print("Experiment logged successfully!")
```

Run the experiment:

```bash
python my_experiment.py
```

## 4. View Results

Open your browser to [http://localhost:8000](http://localhost:8000) to see your experiment.

## 5. More Examples

See [`examples/nested_metrics_and_config.py`](https://github.com/tuliosouza99/Dalva/tree/main/examples/nested_metrics_and_config.py) for a complete walkthrough covering nested metrics, get/remove/relog patterns, and nested config.
