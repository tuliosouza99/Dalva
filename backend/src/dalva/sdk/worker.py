"""Background worker for async HTTP request processing with batching."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
import warnings
from dataclasses import dataclass, field

import httpx

from .wal import WALManager

_logger = logging.getLogger("dalva.sdk")


@dataclass
class PendingRequest:
    method: str
    url: str
    payload: dict | list | str | bytes | None = None
    headers: dict | None = None
    max_retries: int = 5
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    batch_key: str | None = None
    batch_count: int = 0

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


class SyncWorker:
    def __init__(
        self,
        server_url: str,
        max_queue_size: int = 10_000,
        max_retries: int = 5,
        base_backoff: float = 1.0,
        max_backoff: float = 30.0,
        batch_size: int = 50,
        flush_interval: float = 0.2,
        wal_manager: WALManager | None = None,
        http_timeout: float | None = None,
    ) -> None:
        self._max_retries = max_retries
        self._base_backoff = base_backoff
        self._max_backoff = max_backoff
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._wal = wal_manager
        self._queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._errors: list[tuple[PendingRequest, Exception]] = []
        self._errors_lock = threading.Lock()
        self._pending = 0
        self._drain_cond = threading.Condition()
        self._client = httpx.Client(base_url=server_url, timeout=http_timeout)
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    @property
    def errors(self) -> list[tuple[PendingRequest, Exception]]:
        with self._errors_lock:
            return list(self._errors)

    def clear_errors(self) -> list[tuple[PendingRequest, Exception]]:
        with self._errors_lock:
            errs = self._errors
            self._errors = []
            return errs

    @property
    def queue_size(self) -> int:
        return self._queue.qsize()

    @property
    def pending(self) -> int:
        with self._drain_cond:
            return self._pending

    def enqueue(self, request: PendingRequest, timeout: float | None = None) -> None:
        try:
            self._queue.put(request, timeout=timeout)
        except queue.Full:
            raise ConnectionError(
                f"Worker queue full ({self._queue.maxsize}). "
                f"Server may be down. Call flush() to drain."
            ) from None
        with self._drain_cond:
            self._pending += 1
            self._drain_cond.notify()

    def drain(self, timeout: float | None = None) -> bool:
        with self._drain_cond:
            deadline = None if timeout is None else time.monotonic() + timeout
            while self._pending > 0:
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        return False
                    self._drain_cond.wait(timeout=remaining)
                else:
                    self._drain_cond.wait()
            return True

    def drain_with_progress(
        self, label: str = "Draining", timeout: float | None = None
    ) -> bool:
        with self._drain_cond:
            total = self._pending
            if total == 0:
                return True
            done = 0
            print(f"\r[Dalva] {label}: 0/{total}", end="", flush=True)
            deadline = None if timeout is None else time.monotonic() + timeout
            while self._pending > 0:
                if deadline is not None:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        print(f"\r[Dalva] {label}: {done}/{total} (timed out)")
                        return False
                    self._drain_cond.wait(timeout=remaining)
                else:
                    self._drain_cond.wait()
                new_done = total - self._pending
                if new_done > done:
                    done = new_done
                    print(f"\r[Dalva] {label}: {done}/{total}", end="", flush=True)
            print(f"\r[Dalva] {label}: {total}/{total} ✓")
            return True

    def dump_remaining(self) -> int:
        if self._wal is None:
            return 0
        return self._wal.dump_queue(self._queue)

    def wal_delete(self) -> None:
        if self._wal is not None:
            self._wal.delete()

    def stop(self, timeout: float | None = None) -> None:
        self._stop_event.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        with self._drain_cond:
            self._drain_cond.notify_all()
        self._thread.join(timeout=timeout)
        try:
            self._client.close()
        except Exception:
            pass

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                item = self._queue.get(timeout=self._flush_interval)
            except queue.Empty:
                continue
            if item is None:
                break
            if self._wal is not None:
                self._wal.append(item)
            if item.batch_key is not None:
                self._collect_and_send_batch(item)
            else:
                self._process_request(item)

    def _collect_and_send_batch(self, first: PendingRequest) -> None:
        items = [first]
        batch_key = first.batch_key
        batch_url = first.url

        while len(items) < self._batch_size:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                self._queue.put(None)
                break
            if item.batch_key == batch_key:
                if self._wal is not None:
                    self._wal.append(item)
                items.append(item)
            else:
                self._process_request(item)

        entries = []
        for it in items:
            entry = (
                json.loads(it.payload) if isinstance(it.payload, str) else it.payload
            )
            entries.append(entry)
        batch_payload = {"entries": entries}

        batch_req = PendingRequest(
            method="POST",
            url=batch_url.replace("/log", "/log/batch"),
            payload=batch_payload,
            batch_count=len(items),
        )
        self._process_batch_request(batch_req, count=len(items))

    def _process_batch_request(self, request: PendingRequest, count: int) -> None:
        try:
            response = self._send(request)
            response.raise_for_status()
            self._dec_pending_by(count)
        except httpx.HTTPStatusError as e:
            self._handle_batch_status_error(request, e, count)
        except httpx.HTTPError as e:
            self._handle_batch_network_error(request, e, count)
        except Exception as e:
            self._store_error(request, e)
            self._dec_pending_by(count)

    def _handle_batch_status_error(
        self, request: PendingRequest, exc: httpx.HTTPStatusError, count: int
    ) -> None:
        status = exc.response.status_code
        if status == 409:
            warnings.warn(
                f"Conflict (409) in batch for {request.url}: "
                f"dropping batch. This usually means duplicate metrics.",
                stacklevel=2,
            )
            self._dec_pending_by(count)
            return
        if status >= 500:
            self._retry_batch_or_store(request, exc, count)
            return
        self._store_error(request, exc)
        self._dec_pending_by(count)

    def _handle_batch_network_error(
        self, request: PendingRequest, exc: httpx.HTTPError, count: int
    ) -> None:
        if isinstance(exc, httpx.TimeoutException):
            _logger.warning(
                "Request to %s timed out — not retrying to avoid duplicates. "
                "The server may have already processed this request.",
                request.url,
            )
            self._store_error(request, exc)
            self._dec_pending_by(count)
            return
        self._retry_batch_or_store(request, exc, count)

    def _retry_batch_or_store(
        self, request: PendingRequest, exc: Exception, count: int
    ) -> None:
        if request.retry_count < self._max_retries:
            request.retry_count += 1
            delay = min(
                self._base_backoff * (2 ** (request.retry_count - 1)),
                self._max_backoff,
            )
            time.sleep(delay)
            try:
                self._queue.put_nowait(request)
            except queue.Full:
                self._store_error(request, exc)
                self._dec_pending_by(count)
        else:
            self._store_error(request, exc)
            self._dec_pending_by(count)

    def _process_request(self, request: PendingRequest) -> None:
        try:
            response = self._send(request)
            response.raise_for_status()
            if request.batch_count > 0:
                self._dec_pending_by(request.batch_count)
            else:
                self._dec_pending()
        except httpx.HTTPStatusError as e:
            self._handle_status_error(request, e)
        except httpx.HTTPError as e:
            self._handle_network_error(request, e)
        except Exception as e:
            self._store_error(request, e)
            if request.batch_count > 0:
                self._dec_pending_by(request.batch_count)
            else:
                self._dec_pending()

    def _send(self, request: PendingRequest) -> httpx.Response:
        if request.method == "POST":
            if request.headers:
                return self._client.post(
                    request.url,
                    content=request.payload,
                    headers=request.headers,
                )
            return self._client.post(request.url, json=request.payload)
        elif request.method == "DELETE":
            return self._client.delete(request.url, params=request.payload)
        elif request.method == "GET":
            return self._client.get(request.url, params=request.payload)
        else:
            raise ValueError(f"Unsupported HTTP method: {request.method}")

    def _handle_status_error(
        self, request: PendingRequest, exc: httpx.HTTPStatusError
    ) -> None:
        status = exc.response.status_code
        if status == 409:
            warnings.warn(
                f"Conflict (409) for {request.method} {request.url}: "
                f"dropping request. This usually means a duplicate metric/config.",
                stacklevel=2,
            )
            self._dec_pending()
            return
        if status >= 500:
            self._retry_or_store(request, exc)
            return
        self._store_error(request, exc)
        self._dec_pending()

    def _handle_network_error(
        self, request: PendingRequest, exc: httpx.HTTPError
    ) -> None:
        dec_by = request.batch_count if request.batch_count > 0 else 1
        if isinstance(exc, httpx.TimeoutException):
            _logger.warning(
                "Request to %s timed out — not retrying to avoid duplicates. "
                "The server may have already processed this request.",
                request.url,
            )
            self._store_error(request, exc)
            self._dec_pending_by(dec_by)
            return
        self._retry_or_store(request, exc)

    def _retry_or_store(self, request: PendingRequest, exc: Exception) -> None:
        dec_by = request.batch_count if request.batch_count > 0 else 1
        if request.retry_count < self._max_retries:
            request.retry_count += 1
            delay = min(
                self._base_backoff * (2 ** (request.retry_count - 1)),
                self._max_backoff,
            )
            time.sleep(delay)
            try:
                self._queue.put_nowait(request)
            except queue.Full:
                self._store_error(request, exc)
                self._dec_pending_by(dec_by)
        else:
            self._store_error(request, exc)
            self._dec_pending_by(dec_by)

    def _store_error(self, request: PendingRequest, exc: Exception) -> None:
        with self._errors_lock:
            self._errors.append((request, exc))

    def _dec_pending(self) -> None:
        self._dec_pending_by(1)

    def _dec_pending_by(self, n: int) -> None:
        with self._drain_cond:
            self._pending -= n
            self._drain_cond.notify_all()
