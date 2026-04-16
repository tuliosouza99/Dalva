"""Sync command — replay pending WAL operations from disk."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import click
import httpx

from dalva.sdk.wal import WALManager


def _send_entry(client: httpx.Client, entry: dict) -> tuple[bool, str]:
    method = entry["method"]
    url = entry["url"]
    payload = entry.get("payload")
    headers = entry.get("headers")

    try:
        if method == "POST":
            if headers:
                resp = client.post(url, content=payload, headers=headers)
            else:
                resp = client.post(url, json=payload)
        elif method == "DELETE":
            resp = client.delete(url, params=payload)
        else:
            return False, f"Unsupported method: {method}"
        resp.raise_for_status()
        return True, ""
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 409:
            return True, "already applied"
        return False, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
    except httpx.HTTPError as e:
        return False, str(e)


def _replay_file(
    client: httpx.Client,
    file_info,
    dry_run: bool = False,
) -> tuple[int, int, list[dict]]:
    entries = WALManager.read(file_info.path)
    if not entries:
        return 0, 0, []

    if dry_run:
        return len(entries), 0, entries

    succeeded = 0
    failed: list[dict] = []

    batch_groups: dict[str, list[dict]] = defaultdict(list)
    non_batch: list[dict] = []

    for entry in entries:
        bk = entry.get("batch_key")
        if bk:
            batch_groups[bk].append(entry)
        else:
            non_batch.append(entry)

    for batch_key, batch_entries in batch_groups.items():
        items = batch_entries[:]
        finish_entries = [e for e in items if "/finish" in e["url"]]
        log_entries = [e for e in items if "/finish" not in e["url"]]

        if log_entries:
            batch_payload = {"entries": [e["payload"] for e in log_entries]}
            first_url = log_entries[0]["url"]
            batch_url = first_url.replace("/log", "/log/batch")
            ok, msg = _send_entry(
                client,
                {"method": "POST", "url": batch_url, "payload": batch_payload},
            )
            if ok:
                succeeded += len(log_entries)
            else:
                failed.extend(log_entries)

        for entry in finish_entries:
            ok, msg = _send_entry(client, entry)
            if ok:
                succeeded += 1
            else:
                failed.append(entry)

    for entry in non_batch:
        ok, msg = _send_entry(client, entry)
        if ok:
            succeeded += 1
        else:
            failed.append(entry)
    if not failed:
        WALManager.rewrite(file_info.path, [])
    else:
        WALManager.rewrite(file_info.path, failed)

    return succeeded, len(entries) - succeeded, failed


@click.command()
@click.option("--status", is_flag=True, help="Show pending operations without syncing.")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be sent without sending."
)
@click.option(
    "--outbox",
    type=click.Path(),
    default=None,
    help="Path to outbox directory (default: ~/.dalva/outbox).",
)
def sync(status, dry_run, outbox):
    """Sync pending operations from disk to the server.

    Replays WAL (write-ahead log) files that were saved when operations
    could not be delivered (e.g., network timeout, process crash).

    \b
    dalva sync           # Replay all pending operations
    dalva sync --status  # Show what's pending
    dalva sync --dry-run # Preview without sending
    """
    outbox_dir = Path(outbox) if outbox else None

    pending = WALManager.list_pending(outbox_dir=outbox_dir)

    if not pending:
        click.echo(click.style("No pending operations found.", fg="green"))
        return

    if status:
        click.echo(click.style("Pending operations:", fg="blue", bold=True))
        click.echo()
        for info in pending:
            label = f"{info.resource_type}_{info.resource_id}.jsonl"
            click.echo(f"  {label}: {info.entry_count} operation(s)")
        click.echo()
        total = sum(i.entry_count for i in pending)
        click.echo(f"  Total: {total} operation(s) across {len(pending)} file(s)")
        return

    if dry_run:
        click.echo(click.style("Would sync:", fg="blue", bold=True))
        click.echo()
        for info in pending:
            entries = WALManager.read(info.path)
            label = f"{info.resource_type}_{info.resource_id}.jsonl"
            click.echo(f"  {label}: {len(entries)} operation(s)")
            for entry in entries:
                url = entry.get("url", "?")
                click.echo(f"    {entry.get('method', '?')} {url}")
        return

    total_ok = 0
    total_fail = 0
    total_skipped = 0

    import os

    server_url = os.getenv("DALVA_SERVER_URL", "http://localhost:8000")

    try:
        with httpx.Client(base_url=server_url, timeout=30) as client:
            try:
                client.get("/api/health").raise_for_status()
            except Exception:
                click.echo(
                    click.style(
                        f"Error: Cannot reach Dalva server at {server_url}",
                        fg="red",
                    )
                )
                click.echo("Start the server with: dalva server start")
                return

            for info in pending:
                label = f"{info.resource_type}_{info.resource_id}.jsonl"
                ok, fail, _failed_entries = _replay_file(client, info, dry_run=False)
                total_ok += ok
                total_fail += fail
                if fail > 0:
                    click.echo(f"  {label}: Synced {ok}/{ok + fail} ({fail} failed)")
                else:
                    skipped = info.entry_count - ok
                    total_skipped += skipped
                    if skipped:
                        click.echo(
                            f"  {label}: Synced {ok}/{info.entry_count} ({skipped} already applied)"
                        )
                    else:
                        click.echo(f"  {label}: Synced {ok}/{ok} ✓")
    except Exception as e:
        click.echo(click.style(f"Error: {e}", fg="red"))
        return

    click.echo()
    parts = [f"synced {total_ok}"]
    if total_skipped:
        parts.append(f"{total_skipped} already applied")
    if total_fail:
        parts.append(f"{total_fail} failed")
    click.echo(click.style(f"Done: {', '.join(parts)}.", fg="green"))
