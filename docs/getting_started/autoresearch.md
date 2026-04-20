# AutoResearch with LLM Agents

Dalva provides a bundled skill called **dalva-autoresearch** that gives LLM agents (like Claude Code, Cursor, etc.) full visibility into your training experiments. With this skill installed, an agent can autonomously monitor training progress, detect problems, compare runs, and suggest adjustments.

## How It Works

1. Your training script logs metrics, configs, and tabular data to Dalva via the Python SDK (same as normal)
2. The agent uses `dalva query` CLI commands to read that data in real time
3. Based on what it sees (loss curves, configs, table statistics), the agent decides what to do next — continue, adjust hyperparameters, stop early, or try a different approach

The training script doesn't need any special integration — it just logs to Dalva as it normally would.

## Install the Skill

```bash
dalva skill install                  # install into .agents/skills/ (default)
dalva skill install --target claude  # install into .claude/skills/
dalva skill install --cwd /path      # specify a different project directory
```

This copies the `dalva-autoresearch` skill into the chosen skills directory. Agents that read skills from these locations will automatically pick it up.

```
your-project/
├── .agents/skills/dalva-autoresearch/    # installed by `dalva skill install`
│   ├── SKILL.md                         # skill instructions for the agent
│   └── references/setup.md              # SDK setup reference
├── train.py                             # your training script (logs to Dalva)
└── ...
```

## Wire Dalva Into Your Training Script

Add a few lines to log metrics during training:

```python
from dalva.sdk import Run

run = Run(
    project="my-project",
    name="experiment-1",
    config={
        "lr": 0.001,
        "batch_size": 64,
        "epochs": 100,
    },
)

for epoch in range(100):
    train_loss = train_one_epoch(model, dataloader)
    val_loss = evaluate(model, val_dataloader)

    run.log({"train_loss": train_loss, "val_loss": val_loss}, step=epoch)

run.finish()
```

See [Python SDK](python_sdk.md) for full API reference.

## Start the Server

```bash
dalva server start
```

The agent will query this server via `dalva query` commands.

## What the Agent Can Do

Once the skill is installed and the server is running, the agent has access to these tools:

| Command | What it shows the agent |
|---|---|
| `dalva query projects` | All projects with run counts |
| `dalva query runs --state running` | Active experiments |
| `dalva query run <id>` | Run summary: state + latest metrics + config |
| `dalva query metric <id> loss` | Full loss trajectory (timeseries) |
| `dalva query config <id>` | All hyperparameters for a run |
| `dalva query tables --run-id <id>` | Tabular data linked to a run |
| `dalva query table-stats <id>` | Column statistics (histograms, distributions) |

All commands output JSON by default, making them easy for agents to parse.

## Autonomous Training Loop Pattern

The skill enables an autonomous loop where the agent:

1. **Observes**: polls metrics during or after training via `dalva query`
2. **Analyzes**: looks at loss curves, compares train vs validation, checks configs
3. **Decides**: determines whether training is converging, overfitting, or diverging
4. **Acts**: suggests or makes changes (new run with different hyperparameters, early stop, etc.)
5. **Repeats**: continues monitoring across multiple experiments

This pattern works with any training framework — PyTorch, JAX, TensorFlow — since Dalva is framework-agnostic. The agent doesn't modify your training code; it reads the data your code already logs.

## Example: Monitoring a Single Run

```bash
# See what's running
dalva query runs --state running

# Get a summary
dalva query run 1
# → {"state": "running", "metrics": {"train_loss": 0.23, "val_loss": 0.31}, ...}

# Check the loss trajectory
dalva query metric 1 train_loss
# → {"data": [{"step": 0, "value": 0.8}, {"step": 1, "value": 0.5}, ...]}

# See what config was used
dalva query config 1
# → {"lr": 0.001, "batch_size": 64, "epochs": 100}
```

## Crash Recovery

If the training process crashes, the agent can recover unsent data:

```bash
dalva sync --status    # check for pending operations
dalva sync             # replay them to the server
```

## Remote Training

When training runs on a remote GPU machine, use export/import to sync results back:

```bash
# Sync from remote to local in one command
ssh gpu-server "dalva db export --project my-project" | dalva db import -
```

See [Remote Training](remote_training.md) for the full guide.

See [CLI Usage](cli_usage.md) for the full command reference.
