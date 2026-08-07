"""Tests for daemonless segmented journals and replication transports."""

from __future__ import annotations

import json
from pathlib import Path

import dalva
import pytest
from dalva.sdk.journal import SegmentedJournal, SegmentUploader
from dalva.sdk.local import JournalRun, JournalTable
from dalva.sdk.schema import DalvaSchema
from dalva.sdk.transport import FileTransport, S3Transport, sha256_file


class _Prediction(DalvaSchema):
    label: str
    score: float


class _RecordingTransport:
    def __init__(self, failures: int = 0):
        self.failures = failures
        self.calls: list[tuple[Path, bytes, str]] = []

    def put(self, relative_path: Path, source: Path, checksum: str) -> None:
        if self.failures:
            self.failures -= 1
            raise ConnectionError("temporary failure")
        self.calls.append((relative_path, source.read_bytes(), checksum))


def test_journal_rotates_and_replicates_immutable_segment(tmp_path):
    local = tmp_path / "local"
    remote = tmp_path / "remote"
    journal = SegmentedJournal(
        local / "RUN-1",
        root=local,
        sync_target=remote,
        durability="strict",
        segment_bytes=1,
        segment_interval=60,
    )

    journal.append("metrics_logged", {"metrics": {"loss": 0.5}, "step": 1})
    assert journal.sync(timeout=2) == []
    journal.close()

    local_segments = [
        path
        for path in (local / "RUN-1" / "events").glob("*.jsonl")
        if not path.name.startswith(".")
    ]
    remote_segments = list((remote / "RUN-1" / "events").glob("*.jsonl"))
    assert len(local_segments) == 1
    assert len(remote_segments) == 1
    assert local_segments[0].name == remote_segments[0].name
    assert sha256_file(local_segments[0]) == sha256_file(remote_segments[0])


def test_uploader_retries_and_writes_ack(tmp_path):
    root = tmp_path / "root"
    segment = root / "RUN-1" / "events" / "1-1-hash.jsonl"
    segment.parent.mkdir(parents=True)
    segment.write_text('{"seq":1}\n')
    transport = _RecordingTransport(failures=1)
    uploader = SegmentUploader(
        transport,
        root,
        root / "RUN-1" / ".synced",
        max_retries=1,
        base_backoff=0,
    )

    uploader.enqueue(segment)
    assert uploader.drain(timeout=2) is True
    uploader.stop()

    assert len(transport.calls) == 1
    assert list((root / "RUN-1" / ".synced").glob("*.json"))


def test_uploader_keeps_local_segment_after_permanent_failure(tmp_path):
    root = tmp_path / "root"
    segment = root / "RUN-1" / "events" / "1-1-hash.jsonl"
    segment.parent.mkdir(parents=True)
    segment.write_text('{"seq":1}\n')
    uploader = SegmentUploader(
        _RecordingTransport(failures=10),
        root,
        root / "RUN-1" / ".synced",
        max_retries=0,
    )

    uploader.enqueue(segment)
    assert uploader.drain(timeout=2) is True
    errors = uploader.errors()
    uploader.stop()

    assert segment.exists()
    assert len(errors) == 1
    assert not list((root / "RUN-1" / ".synced").glob("*.json"))


def test_file_transport_is_idempotent(tmp_path):
    source = tmp_path / "source.jsonl"
    source.write_text("first\n")
    checksum = sha256_file(source)
    transport = FileTransport(tmp_path / "destination")

    transport.put(Path("runs/segment.jsonl"), source, checksum)
    transport.put(Path("runs/segment.jsonl"), source, checksum)

    assert (tmp_path / "destination" / "runs" / "segment.jsonl").read_text() == (
        "first\n"
    )


class _FakeS3:
    def __init__(self):
        self.objects = {}

    def head_object(self, *, Bucket, Key):
        del Bucket
        if Key not in self.objects:
            error = RuntimeError("missing")
            error.response = {"ResponseMetadata": {"HTTPStatusCode": 404}}
            raise error
        return {"Metadata": self.objects[Key]["Metadata"]}

    def put_object(self, *, Bucket, Key, Body, Metadata, ContentType):
        del Bucket, ContentType
        self.objects[Key] = {"Body": Body.read(), "Metadata": Metadata}


def test_s3_transport_uses_content_checksum_for_idempotency(tmp_path):
    source = tmp_path / "segment.jsonl"
    source.write_text('{"seq":1}\n')
    checksum = sha256_file(source)
    client = _FakeS3()
    transport = S3Transport("bucket", "dalva", client=client)

    transport.put(Path("RUN-1/events/segment.jsonl"), source, checksum)
    transport.put(Path("RUN-1/events/segment.jsonl"), source, checksum)

    stored = client.objects["dalva/RUN-1/events/segment.jsonl"]
    assert stored["Body"] == source.read_bytes()
    assert stored["Metadata"] == {"sha256": checksum}


def test_public_init_is_daemonless_and_resumable(tmp_path, monkeypatch):
    monkeypatch.delenv("DALVA_SERVER_URL", raising=False)
    run = dalva.init(
        project="vision",
        config={"model": {"lr": 0.01}},
        runs_dir=tmp_path / "runs",
        durability="strict",
    )
    assert isinstance(run, JournalRun)
    run.log({"train": {"loss": 0.5}}, step=0)
    run.log({"train": {"loss": 0.3}}, step=1)
    run.flush()
    run_id = run.run_id
    run.finish()

    resumed = dalva.init(
        project="vision", resume_from=run_id, runs_dir=tmp_path / "runs"
    )
    assert resumed.get("train/loss") == {
        "key": "train/loss",
        "value": 0.3,
        "step": 1,
    }
    assert resumed.get_config("model/lr") == {"key": "model/lr", "value": 0.01}
    resumed.finish()

    manifest = json.loads((tmp_path / "runs" / run_id / "manifest.json").read_text())
    assert manifest["state"] == "completed"


def test_journal_run_replication_and_table_roundtrip(tmp_path):
    run = JournalRun(
        project="vision",
        runs_dir=tmp_path / "runs",
        sync=tmp_path / "remote",
        segment_bytes=1,
    )
    table = run.create_table(_Prediction, name="predictions")
    assert isinstance(table, JournalTable)
    table.log_rows(
        [
            {"label": "cat", "score": 0.9},
            {"label": "dog", "score": 0.8},
        ]
    )
    assert table.get_table() == [
        {"label": "cat", "score": 0.9},
        {"label": "dog", "score": 0.8},
    ]
    run.finish(timeout=2)

    replicated = list((tmp_path / "remote" / run.run_id).rglob("*.jsonl"))
    assert replicated
    remote_manifest = tmp_path / "remote" / run.run_id / "manifest.json"
    assert json.loads(remote_manifest.read_text())["state"] == "completed"


def test_standalone_table_uses_scannable_runs_root(tmp_path, monkeypatch):
    monkeypatch.delenv("DALVA_SERVER_URL", raising=False)
    table = dalva.table(
        project="vision",
        schema=_Prediction,
        runs_dir=tmp_path / "runs",
    )
    table.log_row({"label": "cat", "score": 0.9})
    table.finish()

    manifest = tmp_path / "runs" / "_tables" / table.table_id / "manifest.json"
    assert manifest.exists()


def test_metric_conflicts_are_rejected_before_journaling(tmp_path):
    run = JournalRun(project="test", runs_dir=tmp_path / "runs")
    run.log({"loss": 1.0}, step=0)

    with pytest.raises(ValueError, match="already exists"):
        run.log({"loss": 0.5}, step=0)
    with pytest.raises(ValueError, match="different type"):
        run.log({"loss": "bad"}, step=1)

    run.finish()
