"""Query commands — read-only access to experiments via the API server."""

from __future__ import annotations

import json
import os
from typing import Any

import click
import httpx


def _server_url(ctx: click.Context) -> str:
    return os.getenv("DALVA_SERVER_URL", "http://localhost:8000")


def _make_request(
    method: str,
    path: str,
    server_url: str,
    params: dict[str, Any] | None = None,
) -> Any:
    url = f"{server_url}{path}"
    try:
        with httpx.Client(timeout=30) as client:
            resp = client.request(method, url, params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.ConnectError:
        raise click.ClickException(
            f"Cannot reach Dalva server at {server_url}. "
            "Start it with: dalva server start"
        )
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise click.ClickException(f"Not found: {path}")
        raise click.ClickException(
            f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        )
    except httpx.HTTPError as e:
        raise click.ClickException(str(e))


def _output(data: Any, fmt: str) -> None:
    if fmt == "json":
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        _print_table(data)


def _print_table(data: Any) -> None:
    if isinstance(data, list):
        _print_rows(data)
    elif isinstance(data, dict):
        if "runs" in data and isinstance(data["runs"], list):
            click.echo(
                f"Total: {data.get('total', len(data['runs']))}  "
                f"has_more: {data.get('has_more', False)}"
            )
            click.echo()
            _print_rows(data["runs"])
        elif "tables" in data and isinstance(data["tables"], list):
            click.echo(
                f"Total: {data.get('total', len(data['tables']))}  "
                f"has_more: {data.get('has_more', False)}"
            )
            click.echo()
            _print_rows(data["tables"])
        elif "data" in data and isinstance(data["data"], list):
            click.echo(f"has_more: {data.get('has_more', False)}")
            click.echo()
            _print_rows(data["data"])
        elif "rows" in data and isinstance(data["rows"], list):
            click.echo(
                f"Total: {data.get('total', len(data['rows']))}  "
                f"has_more: {data.get('has_more', False)}"
            )
            click.echo()
            _print_rows(data["rows"])
        elif "columns" in data and isinstance(data["columns"], dict):
            _print_stats(data)
        else:
            for k, v in data.items():
                click.echo(f"  {k}: {v}")
    else:
        click.echo(data)


def _print_rows(rows: list[dict]) -> None:
    if not rows:
        click.echo("(no results)")
        return

    def _flatten(d: dict, parent_key: str = "", sep: str = ".") -> dict:
        items: list[tuple[str, Any]] = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(_flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    flat = [_flatten(r) for r in rows]
    all_keys: list[str] = []
    seen: set[str] = set()
    for r in flat:
        for k in r:
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    widths = {k: max(len(k), *(len(str(r.get(k, ""))) for r in flat)) for k in all_keys}

    header = "  ".join(k.ljust(widths[k]) for k in all_keys)
    click.echo(header)
    click.echo("  ".join("-" * widths[k] for k in all_keys))
    for r in flat:
        row = "  ".join(str(r.get(k, "")).ljust(widths[k]) for k in all_keys)
        click.echo(row)


def _print_stats(data: dict) -> None:
    columns = data.get("columns", {})
    for col_name, stats in columns.items():
        click.echo(click.style(f"\n{col_name}", fg="blue", bold=True))
        stat_type = stats.get("type", "unknown")
        click.echo(f"  type:       {stat_type}")
        click.echo(f"  null_count: {stats.get('null_count', 0)}")
        if stat_type == "numeric":
            click.echo(f"  min:        {stats.get('min')}")
            click.echo(f"  max:        {stats.get('max')}")
            bins = stats.get("bins", [])
            if bins:
                click.echo(f"  histogram:  {len(bins)} bins")
                for b in bins:
                    click.echo(f"    [{b['start']:.4g}, {b['end']:.4g}): {b['count']}")
        elif stat_type == "bool":
            counts = stats.get("counts", {})
            click.echo(f"  true:       {counts.get('true', 0)}")
            click.echo(f"  false:      {counts.get('false', 0)}")
        elif stat_type == "string":
            click.echo(f"  unique:     {stats.get('unique_count', 0)}")
            for tv in stats.get("top_values", []):
                click.echo(f"    {tv['value']}: {tv['count']}")


@click.group()
def query():
    """Query experiments from the Dalva server (read-only)."""
    pass


@query.command()
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def projects(fmt, server_url):
    """List all projects with run counts."""
    base = server_url or _server_url(click.get_current_context())
    data = _make_request("GET", "/api/projects/", base)
    _output(data, fmt)


@query.command("runs")
@click.option("--project-id", type=int, default=None, help="Filter by project DB id.")
@click.option(
    "--state", type=click.Choice(["running", "completed", "failed"]), default=None
)
@click.option("--search", default=None, help="Search run names.")
@click.option("--tags", default=None, help="Comma-separated tags to filter by.")
@click.option("--limit", type=int, default=100)
@click.option("--offset", type=int, default=0)
@click.option("--sort-by", default="created_at", help="Field to sort by.")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), default="desc")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def runs_list(
    project_id, state, search, tags, limit, offset, sort_by, sort_order, fmt, server_url
):
    """List and filter runs."""
    base = server_url or _server_url(click.get_current_context())
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "sort_by": sort_by,
        "sort_order": sort_order,
    }
    if project_id is not None:
        params["project_id"] = project_id
    if state:
        params["state"] = state
    if search:
        params["search"] = search
    if tags:
        params["tags"] = tags
    data = _make_request("GET", "/api/runs/", base, params=params)
    _output(data, fmt)


@query.command("run")
@click.argument("run_id")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def run_detail(run_id, fmt, server_url):
    """Get run summary (metadata + latest metrics + config)."""
    base = server_url or _server_url(click.get_current_context())
    data = _make_request("GET", f"/api/runs/{run_id}/summary", base)
    _output(data, fmt)


@query.command("metrics")
@click.argument("run_id")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def metrics_list(run_id, fmt, server_url):
    """List available metric keys for a run."""
    base = server_url or _server_url(click.get_current_context())
    data = _make_request("GET", f"/api/metrics/runs/{run_id}", base)
    _output(data, fmt)


@query.command("metric")
@click.argument("run_id")
@click.argument("metric_path")
@click.option("--step-min", type=int, default=None, help="Minimum step (inclusive).")
@click.option("--step-max", type=int, default=None, help="Maximum step (inclusive).")
@click.option("--limit", type=int, default=1000)
@click.option("--offset", type=int, default=0)
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def metric_history(
    run_id, metric_path, step_min, step_max, limit, offset, fmt, server_url
):
    """Get full history of a metric (timeseries)."""
    base = server_url or _server_url(click.get_current_context())
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if step_min is not None:
        params["step_min"] = step_min
    if step_max is not None:
        params["step_max"] = step_max
    data = _make_request(
        "GET", f"/api/metrics/runs/{run_id}/metric/{metric_path}", base, params=params
    )
    _output(data, fmt)


@query.command("config")
@click.argument("run_id")
@click.argument("key", required=False, default=None)
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def run_config(run_id, key, fmt, server_url):
    """Get run config (all keys, or a specific key)."""
    base = server_url or _server_url(click.get_current_context())
    if key:
        data = _make_request("GET", f"/api/runs/{run_id}/config/{key}", base)
    else:
        data = _make_request("GET", f"/api/runs/{run_id}/config", base)
    _output(data, fmt)


@query.command("tables")
@click.option("--run-id", type=int, default=None, help="Filter by run DB id.")
@click.option("--project-id", type=int, default=None, help="Filter by project DB id.")
@click.option("--limit", type=int, default=100)
@click.option("--offset", type=int, default=0)
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def tables_list(run_id, project_id, limit, offset, fmt, server_url):
    """List tables."""
    base = server_url or _server_url(click.get_current_context())
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if run_id is not None:
        params["run_id"] = run_id
    if project_id is not None:
        params["project_id"] = project_id
    data = _make_request("GET", "/api/tables/", base, params=params)
    _output(data, fmt)


@query.command("table")
@click.argument("table_id")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def table_detail(table_id, fmt, server_url):
    """Get table metadata and schema."""
    base = server_url or _server_url(click.get_current_context())
    data = _make_request("GET", f"/api/tables/{table_id}", base)
    _output(data, fmt)


@query.command("table-data")
@click.argument("table_id")
@click.option("--limit", type=int, default=100)
@click.option("--offset", type=int, default=0)
@click.option("--sort-by", default=None, help="Column to sort by.")
@click.option("--sort-order", type=click.Choice(["asc", "desc"]), default="asc")
@click.option("--filters", default=None, help="JSON array of column filters.")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def table_data(table_id, limit, offset, sort_by, sort_order, filters, fmt, server_url):
    """Get table rows with optional sorting and filtering."""
    base = server_url or _server_url(click.get_current_context())
    params: dict[str, Any] = {
        "limit": limit,
        "offset": offset,
        "sort_order": sort_order,
    }
    if sort_by:
        params["sort_by"] = sort_by
    if filters:
        params["filters"] = filters
    data = _make_request("GET", f"/api/tables/{table_id}/data", base, params=params)
    _output(data, fmt)


@query.command("table-stats")
@click.argument("table_id")
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.option("--server-url", default=None)
def table_stats(table_id, fmt, server_url):
    """Get per-column statistics for a table."""
    base = server_url or _server_url(click.get_current_context())
    data = _make_request("GET", f"/api/tables/{table_id}/stats", base)
    _output(data, fmt)
