# REST API

Guide to using the TrackAI REST API for integrations and custom tools.

## Overview

TrackAI provides a comprehensive REST API for programmatic access:

- **Projects** - Manage projects
- **Runs** - Create, update, and query runs
- **Metrics** - Log and retrieve metrics
- **Custom Views** - Save custom table views

**Base URL**: `http://localhost:8000/api` (default)

## Quick Start

### Example: Create Run and Log Metrics

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Create a run
response = requests.post(f"{BASE_URL}/runs", json={
    "project_id": "my-project",
    "run_id": "experiment-1",
    "config": {"lr": 0.001, "batch_size": 32}
})
run_data = response.json()
run_id = run_data["id"]

# Log metrics
requests.post(f"{BASE_URL}/metrics", json={
    "run_id": run_id,
    "metrics": [
        {"path": "train/loss", "value": 0.5, "step": 0},
        {"path": "train/accuracy", "value": 0.85, "step": 0}
    ]
})

print(f"Logged metrics to run {run_id}")
```

## Projects API

### List Projects

```http
GET /api/projects
```

**Query parameters**:
- `limit` (int) - Max projects to return (default: 100)
- `offset` (int) - Skip first N projects (default: 0)

**Response**:
```json
[
  {
    "id": 1,
    "project_id": "image-classification",
    "total_runs": 150,
    "completed_runs": 120,
    "running_runs": 25,
    "failed_runs": 5,
    "created_at": "2024-01-01T12:00:00",
    "updated_at": "2024-01-15T10:30:00"
  }
]
```

### Get Project

```http
GET /api/projects/{project_id}
```

**Response**:
```json
{
  "id": 1,
  "project_id": "image-classification",
  "total_runs": 150,
  "completed_runs": 120,
  "running_runs": 25,
  "failed_runs": 5,
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

### Create Project

```http
POST /api/projects
```

**Request body**:
```json
{
  "project_id": "new-project"
}
```

**Response**: Same as Get Project

### Delete Project

```http
DELETE /api/projects/{project_id}
```

**Response**: `204 No Content`

## Runs API

### List Runs

```http
GET /api/runs
```

**Query parameters**:
- `project_id` (string) - Filter by project
- `group` (string) - Filter by group
- `state` (string) - Filter by state (running/completed/failed)
- `search` (string) - Search run names
- `tags` (string) - Filter by tags (comma-separated)
- `limit` (int) - Max runs to return (default: 100)
- `offset` (int) - Skip first N runs (default: 0)
- `sort_by` (string) - Sort field (created_at/updated_at/run_id)
- `sort_order` (string) - Sort order (asc/desc)

**Response**:
```json
{
  "runs": [
    {
      "id": 1,
      "run_id": "experiment-1",
      "project_id": "image-classification",
      "group_name": "baseline",
      "state": "completed",
      "created_at": "2024-01-01T12:00:00",
      "updated_at": "2024-01-01T14:00:00",
      "duration_seconds": 7200
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Get Run

```http
GET /api/runs/{run_id}
```

**Response**: Same as individual run in List Runs

### Get Run Summary

```http
GET /api/runs/{run_id}/summary
```

Includes metrics summary.

**Response**:
```json
{
  "id": 1,
  "run_id": "experiment-1",
  "project_id": "image-classification",
  "group_name": "baseline",
  "state": "completed",
  "config": {"lr": 0.001, "batch_size": 32},
  "created_at": "2024-01-01T12:00:00",
  "updated_at": "2024-01-01T14:00:00",
  "metrics": ["train/loss", "train/accuracy", "val/loss", "val/accuracy"]
}
```

### Get Run Config

```http
GET /api/runs/{run_id}/config
```

**Response**:
```json
{
  "lr": 0.001,
  "batch_size": 32,
  "optimizer": "adam",
  "epochs": 100
}
```

### Create Run

```http
POST /api/runs
```

**Request body**:
```json
{
  "project_id": "image-classification",
  "run_id": "experiment-1",
  "group_name": "baseline",
  "config": {"lr": 0.001}
}
```

**Response**: Same as Get Run

### Update Run State

```http
PATCH /api/runs/{run_id}/state
```

**Request body**:
```json
{
  "state": "completed"
}
```

**Valid states**: `running`, `completed`, `failed`

**Response**: Same as Get Run

### Delete Run

```http
DELETE /api/runs/{run_id}
```

**Response**: `204 No Content`

## Metrics API

### List Metrics for Run

```http
GET /api/metrics/runs/{run_id}
```

**Response**:
```json
{
  "run_id": "experiment-1",
  "metrics": [
    "train/loss",
    "train/accuracy",
    "val/loss",
    "val/accuracy"
  ]
}
```

### Get Metric Values

```http
GET /api/metrics/runs/{run_id}/metric/{metric_path}
```

**Query parameters**:
- `limit` (int) - Max values to return (default: 1000)
- `offset` (int) - Skip first N values (default: 0)
- `step_min` (int) - Min step (inclusive)
- `step_max` (int) - Max step (inclusive)

**Example**:
```http
GET /api/metrics/runs/experiment-1/metric/train%2Floss?limit=100&step_min=0&step_max=50
```

**Response**:
```json
{
  "run_id": "experiment-1",
  "metric_path": "train/loss",
  "values": [
    {"step": 0, "value": 1.5, "timestamp": "2024-01-01T12:00:00"},
    {"step": 1, "value": 1.2, "timestamp": "2024-01-01T12:01:00"},
    {"step": 2, "value": 0.9, "timestamp": "2024-01-01T12:02:00"}
  ],
  "total": 100,
  "limit": 100,
  "offset": 0
}
```

### Compare Metrics Across Runs

```http
POST /api/metrics/compare
```

**Request body**:
```json
{
  "run_ids": ["run-1", "run-2", "run-3"],
  "metric_path": "val/accuracy"
}
```

**Response**:
```json
{
  "metric_path": "val/accuracy",
  "runs": [
    {
      "run_id": "run-1",
      "values": [
        {"step": 0, "value": 0.75},
        {"step": 1, "value": 0.80}
      ]
    },
    {
      "run_id": "run-2",
      "values": [
        {"step": 0, "value": 0.70},
        {"step": 1, "value": 0.78}
      ]
    }
  ]
}
```

## Custom Views API

### List Custom Views

```http
GET /api/views
```

**Query parameters**:
- `project_id` (string) - Filter by project

**Response**:
```json
[
  {
    "id": 1,
    "name": "Top Performers",
    "project_id": "image-classification",
    "config": {
      "filters": {"state": "completed"},
      "sort_by": "val_accuracy",
      "sort_order": "desc"
    }
  }
]
```

### Create Custom View

```http
POST /api/views
```

**Request body**:
```json
{
  "name": "Top Performers",
  "project_id": "image-classification",
  "config": {
    "filters": {"state": "completed"},
    "sort_by": "val_accuracy",
    "sort_order": "desc"
  }
}
```

**Response**: Same as individual view

## MCP API

Model Context Protocol endpoints for AI integration.

See [MCP Documentation](../api_documentation/rest_api/mcp.md) for details.

## Authentication

Currently, TrackAI does not require authentication. For production deployments, consider:

- Adding API key authentication
- Using reverse proxy (nginx) with auth
- Network-level access control

## Rate Limiting

No rate limiting is currently enforced. For production:

- Consider adding rate limiting middleware
- Monitor for abuse
- Use caching for frequent queries

## Error Responses

All endpoints return standard HTTP status codes:

**Success codes**:
- `200 OK` - Request successful
- `201 Created` - Resource created
- `204 No Content` - Request successful, no content

**Error codes**:
- `400 Bad Request` - Invalid request body
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

**Error response format**:
```json
{
  "detail": "Run not found: experiment-xyz"
}
```

## Complete Example

### Python Client

```python
import requests
from typing import Dict, List

class TrackAIClient:
    """Simple TrackAI REST API client"""

    def __init__(self, base_url: str = "http://localhost:8000/api"):
        self.base_url = base_url

    def create_run(self, project_id: str, run_id: str, config: Dict) -> Dict:
        """Create a new run"""
        response = requests.post(
            f"{self.base_url}/runs",
            json={
                "project_id": project_id,
                "run_id": run_id,
                "config": config
            }
        )
        response.raise_for_status()
        return response.json()

    def log_metrics(self, run_id: str, metrics: Dict[str, float], step: int):
        """Log metrics for a run"""
        metric_list = [
            {"path": path, "value": value, "step": step}
            for path, value in metrics.items()
        ]

        response = requests.post(
            f"{self.base_url}/metrics",
            json={"run_id": run_id, "metrics": metric_list}
        )
        response.raise_for_status()

    def get_runs(self, project_id: str, limit: int = 100) -> List[Dict]:
        """Get all runs for a project"""
        response = requests.get(
            f"{self.base_url}/runs",
            params={"project_id": project_id, "limit": limit}
        )
        response.raise_for_status()
        return response.json()["runs"]

# Usage
client = TrackAIClient()

# Create run
run = client.create_run(
    project_id="api-example",
    run_id="test-run-1",
    config={"lr": 0.001, "batch_size": 32}
)

# Log metrics
for step in range(100):
    client.log_metrics(
        run_id="test-run-1",
        metrics={"train/loss": 0.5, "train/accuracy": 0.85},
        step=step
    )

# Get all runs
runs = client.get_runs(project_id="api-example")
print(f"Found {len(runs)} runs")
```

## Next Steps

- [API Reference](../api_documentation/rest_api/projects.md) - Detailed endpoint docs
- [Python SDK](python_sdk.md) - Python client (easier than REST API)
- [MCP Documentation](../api_documentation/rest_api/mcp.md) - AI integration
