# Metrics API

REST API endpoints for logging and retrieving metrics.

## Endpoints

### List Metrics

`GET /api/metrics/runs/{run_id}` - List all metric names for a run

### Get Metric Values

`GET /api/metrics/runs/{run_id}/metric/{metric_path}` - Get metric values

### Compare Metrics

`POST /api/metrics/compare` - Compare metrics across multiple runs

See the [REST API Guide](../../getting_started/rest_api.md) for complete examples.
