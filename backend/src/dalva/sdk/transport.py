"""Transports for replicating immutable Dalva journal segments."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Protocol
from urllib.parse import urlparse


class SegmentTransport(Protocol):
    """Destination for immutable, content-addressed journal segments."""

    def put(self, relative_path: Path, source: Path, checksum: str) -> None:
        """Persist *source* at *relative_path* and verify its checksum."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FileTransport:
    """Atomically replicate segments into another filesystem directory."""

    def __init__(self, root: Path):
        self.root = root.expanduser().resolve()

    def put(self, relative_path: Path, source: Path, checksum: str) -> None:
        destination = self.root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)

        if destination.exists() and sha256_file(destination) == checksum:
            return

        temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
        try:
            shutil.copyfile(source, temporary)
            if sha256_file(temporary) != checksum:
                raise OSError(f"Checksum mismatch while copying {source}")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)


class S3Transport:
    """Replicate segments to S3 or an S3-compatible object store.

    ``boto3`` is imported lazily so local-only users do not pay for the
    dependency. Configure compatible stores with ``endpoint_url``.
    """

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        *,
        endpoint_url: str | None = None,
        client=None,
    ):
        if client is None:
            try:
                import boto3
            except ImportError as exc:  # pragma: no cover - environment dependent
                raise RuntimeError(
                    "S3 synchronization requires the 's3' extra: "
                    "pip install 'dalva[s3]'"
                ) from exc
            client = boto3.client("s3", endpoint_url=endpoint_url)
        self._client = client
        self.bucket = bucket
        self.prefix = prefix.strip("/")

    def _key(self, relative_path: Path) -> str:
        relative = relative_path.as_posix().lstrip("/")
        return f"{self.prefix}/{relative}" if self.prefix else relative

    def put(self, relative_path: Path, source: Path, checksum: str) -> None:
        key = self._key(relative_path)
        try:
            existing = self._client.head_object(Bucket=self.bucket, Key=key)
            if existing.get("Metadata", {}).get("sha256") == checksum:
                return
        except Exception as exc:  # boto uses generated exception classes
            response = getattr(exc, "response", {})
            status = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if status not in (None, 404):
                raise

        with source.open("rb") as stream:
            self._client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=stream,
                Metadata={"sha256": checksum},
                ContentType=(
                    "application/json"
                    if source.name == "manifest.json"
                    else "application/x-ndjson"
                ),
            )

        uploaded = self._client.head_object(Bucket=self.bucket, Key=key)
        if uploaded.get("Metadata", {}).get("sha256") != checksum:
            raise OSError(
                f"Remote checksum verification failed for s3://{self.bucket}/{key}"
            )


def create_transport(
    target: str | Path | SegmentTransport | None,
) -> SegmentTransport | None:
    """Create a transport from a local path, ``file://`` URI, or ``s3://`` URI."""
    if target is None:
        return None
    if not isinstance(target, (str, Path)):
        return target
    if isinstance(target, Path):
        return FileTransport(target)

    parsed = urlparse(target)
    if parsed.scheme == "s3":
        if not parsed.netloc:
            raise ValueError("S3 sync target must include a bucket")
        endpoint_url = os.getenv("DALVA_S3_ENDPOINT_URL")
        return S3Transport(
            parsed.netloc,
            parsed.path.strip("/"),
            endpoint_url=endpoint_url,
        )
    if parsed.scheme == "file":
        return FileTransport(Path(parsed.path))
    if parsed.scheme:
        raise ValueError(f"Unsupported Dalva sync transport: {parsed.scheme}")
    return FileTransport(Path(target))


def write_ack(path: Path, checksum: str) -> None:
    """Atomically persist a local acknowledgement for a replicated segment."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps({"sha256": checksum}))
    os.replace(temporary, path)
