# Quick Start

Get up and running with TrackAI in 5 minutes.

## 1. Install TrackAI

```bash
git clone https://github.com/tuliosouza99/TrackAI.git
cd TrackAI/backend
uv sync
```

## 2. Start the Server

```bash
trackai server start
```

The server will automatically find an available port and display the URL.

## 3. Log Your First Experiment

Create a new file `my_experiment.py`:

```python
import trackai

# Initialize a run
run = trackai.init(
    project="quickstart",
    name="first-experiment",
    config={
        "learning_rate": 0.001,
        "batch_size": 32,
        "optimizer": "adam"
    }
)

# Log metrics during training
for step in range(100):
    loss = 1.0 / (step + 1)
    accuracy = min(0.95, step / 100)

    run.log({
        "train/loss": loss,
        "train/accuracy": accuracy
    }, step=step)

run.finish()
print("✅ Experiment logged successfully!")
```

Run the experiment:

```bash
python my_experiment.py
```

## 4. View Results

Open your browser to http://localhost:8000 to see your experiment.
