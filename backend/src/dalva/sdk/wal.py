"""Write-ahead log (WAL) manager for persisting pending SDK operations to disk."""

from __future__ import annotations

import json
import queue
from dataclasses import dataclass
from pathlib import Path


def _default_outbox_dir() -> Path:
    return Path.home() / ".dalva" / "outbox"


@dataclass
class WALFileInfo:
    path: Path
    resource_type: str
    resource_id: int
    entry_count: int


class WALManager:
    def __init__(
        self,
        resource_type: str,
        resource_id: int,
        outbox_dir: Path | None = None,
    ) -> None:
        self.resource_type = resource_type
        self.resource_id = resource_id
        self._outbox_dir = outbox_dir or _default_outbox_dir()
        self._path = self._outbox_dir / f"{resource_type}_{resource_id}.jsonl"
        self._seq = 0

    @property
    def path(self) -> Path:
        return self._path

    @property
    def exists(self) -> bool:
        return self._path.exists() and self._path.stat().st_size > 0

    def append(self, request) -> None:
        self._outbox_dir.mkdir(parents=True, exist_ok=True)
        self._seq += 1
        entry = {
            "seq": self._seq,
            "method": request.method,
            "url": request.url,
            "payload": request.payload,
            "headers": request.headers,
            "batch_key": request.batch_key,
            "batch_count": request.batch_count,
        }
        with open(self._path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")
            f.flush()

    def delete(self) -> None:
        try:
            self._path.unlink()
        except FileNotFoundError:
            pass

    def dump_queue(self, q: queue.Queue) -> int:
        items = []
        while True:
            try:
                item = q.get_nowait()
            except queue.Empty:
                break
            if item is not None:
                items.append(item)

        if not items:
            return 0

        self._outbox_dir.mkdir(parents=True, exist_ok=True)
        with open(self._path, "a") as f:
            for item in items:
                self._seq += 1
                entry = {
                    "seq": self._seq,
                    "method": item.method,
                    "url": item.url,
                    "payload": item.payload,
                    "headers": item.headers,
                    "batch_key": item.batch_key,
                    "batch_count": item.batch_count,
                }
                f.write(json.dumps(entry, default=str) + "\n")
            f.flush()
        return len(items)

    @staticmethod
    def read(filepath: Path) -> list[dict]:
        if not filepath.exists():
            return []
        text = filepath.read_text().strip()
        if not text:
            return []
        entries = []
        for line in text.split("\n"):
            line = line.strip()
            if line:
                entries.append(json.loads(line))
        return entries

    @staticmethod
    def rewrite(filepath: Path, entries: list[dict]) -> None:
        if not entries:
            try:
                filepath.unlink()
            except FileNotFoundError:
                pass
            return
        rewritten = []
        for i, entry in enumerate(entries, 1):
            entry = dict(entry)
            entry["seq"] = i
            rewritten.append(json.dumps(entry, default=str))
        with open(filepath, "w") as f:
            f.write("\n".join(rewritten) + "\n")
            f.flush()

    @staticmethod
    def list_pending(outbox_dir: Path | None = None) -> list[WALFileInfo]:
        outbox = outbox_dir or _default_outbox_dir()
        if not outbox.exists():
            return []
        results = []
        for p in sorted(outbox.glob("*.jsonl")):
            entries = WALManager.read(p)
            if not entries:
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass
                continue
            parts = p.stem.split("_", 1)
            if len(parts) != 2:
                continue
            resource_type, id_str = parts
            try:
                resource_id = int(id_str)
            except ValueError:
                continue
            results.append(
                WALFileInfo(
                    path=p,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    entry_count=len(entries),
                )
            )
        return results
