"""Crash-safe, segmented event journal used by daemonless SDK resources."""

from __future__ import annotations

import json
import os
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from .transport import SegmentTransport, create_transport, sha256_file, write_ack

Durability = Literal["balanced", "strict"]


def default_runs_dir() -> Path:
    return Path.home() / ".dalva" / "runs"


def new_resource_id(prefix: str) -> str:
    """Return a sortable, process-safe resource identifier."""
    import uuid

    millis = int(time.time() * 1000)
    return f"{prefix}-{millis:013d}-{uuid.uuid4().hex[:12]}"


class SegmentUploader:
    """Retrying background uploader for already-finalized segments."""

    def __init__(
        self,
        transport: SegmentTransport,
        root: Path,
        ack_dir: Path,
        *,
        max_retries: int = 5,
        base_backoff: float = 0.25,
    ):
        self._transport = transport
        self._root = root
        self._ack_dir = ack_dir
        self._max_retries = max_retries
        self._base_backoff = base_backoff
        self._queue: queue.Queue[Path | None] = queue.Queue()
        self._pending = 0
        self._condition = threading.Condition()
        self._errors: list[tuple[Path, Exception]] = []
        self._queued: set[Path] = set()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _ack_path(self, segment: Path) -> Path:
        return self._ack_dir / f"{segment.name}.json"

    def enqueue(self, segment: Path) -> None:
        ack = self._ack_path(segment)
        if ack.exists():
            try:
                acknowledged = json.loads(ack.read_text()).get("sha256")
                if acknowledged == sha256_file(segment):
                    return
            except (OSError, json.JSONDecodeError):
                pass
        with self._condition:
            if segment in self._queued:
                return
            self._queued.add(segment)
            self._pending += 1
        self._queue.put(segment)

    def _run(self) -> None:
        while True:
            segment = self._queue.get()
            if segment is None:
                return
            last_error: Exception | None = None
            checksum = sha256_file(segment)
            for attempt in range(self._max_retries + 1):
                try:
                    relative = segment.relative_to(self._root)
                    self._transport.put(relative, segment, checksum)
                    write_ack(self._ack_path(segment), checksum)
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    if attempt < self._max_retries:
                        time.sleep(self._base_backoff * (2**attempt))

            with self._condition:
                self._queued.discard(segment)
                self._pending -= 1
                if last_error is not None:
                    self._errors.append((segment, last_error))
                self._condition.notify_all()

    def drain(self, timeout: float | None = None) -> bool:
        with self._condition:
            deadline = None if timeout is None else time.monotonic() + timeout
            while self._pending:
                if deadline is None:
                    self._condition.wait()
                    continue
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True

    def errors(self) -> list[tuple[Path, Exception]]:
        with self._condition:
            return list(self._errors)

    def retry_failed(self) -> None:
        with self._condition:
            failed = [path for path, _ in self._errors]
            self._errors.clear()
        for path in failed:
            self.enqueue(path)

    def stop(self) -> None:
        self._queue.put(None)
        self._thread.join()


class SegmentedJournal:
    """Append-only journal with atomic immutable segment rotation."""

    def __init__(
        self,
        resource_dir: Path,
        *,
        root: Path,
        sync_target: str | Path | SegmentTransport | None = None,
        durability: Durability = "balanced",
        segment_bytes: int = 256 * 1024,
        segment_interval: float = 0.5,
    ):
        if durability not in ("balanced", "strict"):
            raise ValueError("durability must be 'balanced' or 'strict'")
        self.resource_dir = resource_dir
        self.root = root
        self.events_dir = resource_dir / "events"
        self.ack_dir = resource_dir / ".synced"
        self.active_path = self.events_dir / ".active.jsonl"
        self._durability = durability
        self._segment_bytes = segment_bytes
        self._segment_interval = segment_interval
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._closed = False
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self._seq = self._discover_last_sequence()
        self._segment_start = self._active_start_sequence()
        self._opened_at = time.monotonic()
        self._stream = self.active_path.open("a", encoding="utf-8")

        transport = create_transport(sync_target)
        self.transport = transport
        self._uploader = (
            SegmentUploader(transport, root, self.ack_dir) if transport else None
        )
        if self._uploader:
            for segment in sorted(self.events_dir.glob("*.jsonl")):
                if segment.name != self.active_path.name:
                    self._uploader.enqueue(segment)
            self.replicate_manifest()

        self._rotator = threading.Thread(target=self._rotation_loop, daemon=True)
        self._rotator.start()

    def _discover_last_sequence(self) -> int:
        last = 0
        for event in self.iter_events():
            last = max(last, int(event.get("seq", 0)))
        return last

    def _active_start_sequence(self) -> int | None:
        if not self.active_path.exists():
            return None
        with self.active_path.open(encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    return int(json.loads(line)["seq"])
        return None

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> int:
        with self._lock:
            self._seq += 1
            if self._segment_start is None:
                self._segment_start = self._seq
            event = {
                "version": 1,
                "seq": self._seq,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                "payload": payload or {},
            }
            self._stream.write(json.dumps(event, separators=(",", ":")) + "\n")
            self._stream.flush()
            if self._durability == "strict":
                os.fsync(self._stream.fileno())
            if self.active_path.stat().st_size >= self._segment_bytes:
                self._rotate_locked()
            return self._seq

    def _rotation_loop(self) -> None:
        poll_interval = min(max(self._segment_interval / 4, 0.05), 0.25)
        while not self._stop_event.wait(poll_interval):
            with self._lock:
                if (
                    self._segment_start is not None
                    and time.monotonic() - self._opened_at >= self._segment_interval
                ):
                    self._rotate_locked()

    def _rotate_locked(self) -> Path | None:
        if self._segment_start is None:
            return None
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._stream.close()
        checksum = sha256_file(self.active_path)
        segment = self.events_dir / (
            f"{self._segment_start:020d}-{self._seq:020d}-{checksum}.jsonl"
        )
        os.replace(self.active_path, segment)
        self._segment_start = None
        self._opened_at = time.monotonic()
        self._stream = self.active_path.open("a", encoding="utf-8")
        if self._uploader:
            self._uploader.enqueue(segment)
        return segment

    def flush(self) -> None:
        with self._lock:
            self._stream.flush()
            os.fsync(self._stream.fileno())

    def replicate_manifest(self) -> None:
        manifest = self.resource_dir / "manifest.json"
        if self._uploader and manifest.exists():
            self._uploader.enqueue(manifest)

    def sync(self, timeout: float | None = None) -> list[tuple[Path, Exception]]:
        with self._lock:
            self._rotate_locked()
        if not self._uploader:
            return []
        self.replicate_manifest()
        self._uploader.retry_failed()
        if not self._uploader.drain(timeout):
            raise TimeoutError("Timed out while synchronizing Dalva journal segments")
        return self._uploader.errors()

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._stop_event.set()
        self._rotator.join()
        with self._lock:
            self._rotate_locked()
            self._stream.close()
        if self._uploader:
            self._uploader.drain()
            self._uploader.stop()

    def iter_events(self):
        paths = (
            sorted(self.events_dir.glob("*.jsonl")) if self.events_dir.exists() else []
        )
        if self.active_path.exists():
            paths.append(self.active_path)
        for path in paths:
            with path.open(encoding="utf-8") as stream:
                for line in stream:
                    if line.strip():
                        yield json.loads(line)


def write_manifest(path: Path, data: dict[str, Any]) -> None:
    """Atomically write and fsync a resource manifest."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
