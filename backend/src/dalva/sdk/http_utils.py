"""Shared HTTP utilities for the SDK."""

from __future__ import annotations

import httpx


def _server_error(exc: httpx.HTTPStatusError) -> str:
    try:
        body = exc.response.json()
        detail = body.get("detail", str(exc))
    except Exception:
        detail = str(exc)
    return f"Server error {exc.response.status_code}: {detail}"
