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

# Initialize a run (server must be running at the specified URL)
run = dalva.init(
    project="quickstart",
    name="first-experiment",
    config={
        "learning_rate": 0.001,
        "batch_size": 32,
        "optimizer": "adam"
    },
    server_url="http://localhost:8000"
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

Open your browser to [http://localhost:8000](http://localhost:8000) to see your experiment.
