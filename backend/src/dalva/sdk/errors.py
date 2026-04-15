"""Shared exceptions for the Dalva SDK."""

from __future__ import annotations

from .worker import PendingRequest


class DalvaError(Exception):
    def __init__(
        self, message: str, errors: list[tuple[PendingRequest, Exception]] | None = None
    ) -> None:
        super().__init__(message)
        self.errors: list[tuple[PendingRequest, Exception]] = errors or []
