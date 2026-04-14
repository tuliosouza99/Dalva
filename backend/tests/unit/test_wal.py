"""Tests for WAL (write-ahead log) manager for queue persistence."""

import json
import queue

import pytest

from dalva.sdk.wal import WALManager


@pytest.fixture
def outbox_dir(tmp_path):
    d = tmp_path / "outbox"
    d.mkdir()
    return d


@pytest.fixture
def wal(outbox_dir):
    return WALManager("run", 42, outbox_dir=outbox_dir)


def _make_request(seq=1, **overrides):
    from dalva.sdk.worker import PendingRequest

    defaults = {
        "method": "POST",
        "url": "/api/runs/1/log",
        "payload": {"metrics": {"loss": 0.5}, "step": seq},
        "batch_key": "run:1",
    }
    defaults.update(overrides)
    return PendingRequest(**defaults)


class TestWALCreate:
    def test_creates_file_on_first_append(self, wal, outbox_dir):
        req = _make_request()
        wal.append(req)
        expected = outbox_dir / "run_42.jsonl"
        assert expected.exists()

    def test_file_name_format(self, outbox_dir):
        w = WALManager("table", 7, outbox_dir=outbox_dir)
        assert w.path == outbox_dir / "table_7.jsonl"

    def test_path_property_before_append(self, wal, outbox_dir):
        assert wal.path == outbox_dir / "run_42.jsonl"
        assert not wal.path.exists()

    def test_creates_outbox_dir_if_missing(self, tmp_path):
        missing_dir = tmp_path / "deep" / "outbox"
        wal = WALManager("run", 1, outbox_dir=missing_dir)
        req = _make_request()
        wal.append(req)
        assert missing_dir.exists()
        assert (missing_dir / "run_1.jsonl").exists()


class TestWALAppend:
    def test_append_single_entry(self, wal, outbox_dir):
        req = _make_request()
        wal.append(req)

        lines = (wal.path).read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["method"] == "POST"
        assert entry["url"] == "/api/runs/1/log"
        assert entry["payload"] == {"metrics": {"loss": 0.5}, "step": 1}
        assert entry["batch_key"] == "run:1"
        assert entry["seq"] == 1

    def test_append_multiple_entries_sequential(self, wal):
        for i in range(5):
            wal.append(_make_request(seq=i))

        lines = wal.path.read_text().strip().split("\n")
        assert len(lines) == 5
        for i, line in enumerate(lines):
            entry = json.loads(line)
            assert entry["seq"] == i + 1

    def test_append_with_custom_headers(self, wal):
        req = _make_request(
            headers={"Content-Type": "application/json"},
            payload='{"rows":[1,2]}',
        )
        wal.append(req)

        entry = json.loads(wal.path.read_text().strip())
        assert entry["headers"] == {"Content-Type": "application/json"}

    def test_append_with_no_batch_key(self, wal):
        req = _make_request(batch_key=None)
        wal.append(req)

        entry = json.loads(wal.path.read_text().strip())
        assert entry["batch_key"] is None

    def test_append_finish_request(self, wal):
        from dalva.sdk.worker import PendingRequest

        req = PendingRequest(method="POST", url="/api/runs/42/finish")
        wal.append(req)

        entry = json.loads(wal.path.read_text().strip())
        assert entry["url"] == "/api/runs/42/finish"
        assert entry["payload"] is None


class TestWALRead:
    def test_read_empty_file(self, wal):
        wal.path.touch()
        entries = WALManager.read(wal.path)
        assert entries == []

    def test_read_nonexistent_file(self, outbox_dir):
        entries = WALManager.read(outbox_dir / "nope.jsonl")
        assert entries == []

    def test_read_roundtrip(self, wal):
        req1 = _make_request(seq=0, payload={"metrics": {"loss": 0.5}, "step": 0})
        req2 = _make_request(seq=1, payload={"metrics": {"acc": 0.9}, "step": 1})
        wal.append(req1)
        wal.append(req2)

        entries = WALManager.read(wal.path)
        assert len(entries) == 2
        assert entries[0]["method"] == "POST"
        assert entries[0]["url"] == "/api/runs/1/log"
        assert entries[0]["payload"] == {"metrics": {"loss": 0.5}, "step": 0}
        assert entries[0]["batch_key"] == "run:1"
        assert entries[0]["seq"] == 1
        assert entries[1]["seq"] == 2

    def test_read_preserves_headers(self, wal):
        req = _make_request(
            headers={"Content-Type": "application/json"},
            payload='{"data":1}',
        )
        wal.append(req)

        entries = WALManager.read(wal.path)
        assert entries[0]["headers"] == {"Content-Type": "application/json"}


class TestWALDelete:
    def test_delete_removes_file(self, wal):
        wal.append(_make_request())
        assert wal.path.exists()

        wal.delete()
        assert not wal.path.exists()

    def test_delete_nonexistent_is_noop(self, wal):
        wal.delete()
        assert not wal.path.exists()

    def test_delete_idempotent(self, wal):
        wal.append(_make_request())
        wal.delete()
        wal.delete()
        assert not wal.path.exists()


class TestWALDumpQueue:
    def test_dump_drains_queue_to_file(self, wal):
        q = queue.Queue()
        for i in range(5):
            q.put(_make_request(seq=i))

        count = wal.dump_queue(q)
        assert count == 5
        assert q.empty()

        entries = WALManager.read(wal.path)
        assert len(entries) == 5

    def test_dump_empty_queue(self, wal):
        q = queue.Queue()
        count = wal.dump_queue(q)
        assert count == 0
        assert not wal.path.exists()

    def test_dump_appends_to_existing(self, wal):
        wal.append(_make_request(seq=0))

        q = queue.Queue()
        q.put(_make_request(seq=1))
        q.put(_make_request(seq=2))

        count = wal.dump_queue(q)
        assert count == 2

        entries = WALManager.read(wal.path)
        assert len(entries) == 3
        assert entries[0]["seq"] == 1
        assert entries[1]["seq"] == 2
        assert entries[2]["seq"] == 3

    def test_dump_handles_none_sentinel(self, wal):
        q = queue.Queue()
        q.put(_make_request())
        q.put(None)
        q.put(_make_request())

        count = wal.dump_queue(q)
        assert count == 2

        entries = WALManager.read(wal.path)
        assert len(entries) == 2

    def test_dump_continues_sequential_numbering(self, wal):
        for i in range(3):
            wal.append(_make_request(seq=i))

        q = queue.Queue()
        q.put(_make_request(seq=3))

        wal.dump_queue(q)
        entries = WALManager.read(wal.path)
        assert [e["seq"] for e in entries] == [1, 2, 3, 4]


class TestWALListPending:
    def test_list_empty_dir(self, outbox_dir):
        result = WALManager.list_pending(outbox_dir)
        assert result == []

    def test_list_finds_wal_files(self, outbox_dir):
        for i in range(3):
            w = WALManager("run", i, outbox_dir=outbox_dir)
            w.append(_make_request())

        result = WALManager.list_pending(outbox_dir)
        assert len(result) == 3
        names = {r.path.name for r in result}
        assert names == {"run_0.jsonl", "run_1.jsonl", "run_2.jsonl"}

    def test_list_returns_entry_counts(self, outbox_dir):
        w = WALManager("run", 1, outbox_dir=outbox_dir)
        for i in range(5):
            w.append(_make_request(seq=i))

        w2 = WALManager("table", 2, outbox_dir=outbox_dir)
        w2.append(_make_request())

        result = WALManager.list_pending(outbox_dir)
        by_name = {r.path.name: r for r in result}
        assert by_name["run_1.jsonl"].entry_count == 5
        assert by_name["table_2.jsonl"].entry_count == 1

    def test_list_excludes_empty_files(self, outbox_dir):
        (outbox_dir / "run_99.jsonl").touch()
        result = WALManager.list_pending(outbox_dir)
        assert result == []

    def test_list_excludes_non_jsonl(self, outbox_dir):
        (outbox_dir / "notes.txt").write_text("hello")
        result = WALManager.list_pending(outbox_dir)
        assert result == []

    def test_list_returns_resource_info(self, outbox_dir):
        w = WALManager("run", 42, outbox_dir=outbox_dir)
        w.append(_make_request())

        result = WALManager.list_pending(outbox_dir)
        assert len(result) == 1
        info = result[0]
        assert info.resource_type == "run"
        assert info.resource_id == 42

    def test_list_uses_default_dir(self, tmp_path, monkeypatch):
        outbox = tmp_path / ".dalva" / "outbox"
        monkeypatch.setattr("dalva.sdk.wal._default_outbox_dir", lambda: outbox)

        w = WALManager("run", 1)
        w.append(_make_request())

        result = WALManager.list_pending()
        assert len(result) == 1


class TestWALRewrite:
    def test_rewrite_keeps_only_specified_entries(self, wal):
        for i in range(5):
            wal.append(_make_request(seq=i))

        entries = WALManager.read(wal.path)
        WALManager.rewrite(wal.path, [entries[1], entries[3]])

        remaining = WALManager.read(wal.path)
        assert len(remaining) == 2
        assert remaining[0]["payload"]["step"] == 1
        assert remaining[1]["payload"]["step"] == 3

    def test_rewrite_renumbers_seqs(self, wal):
        for i in range(5):
            wal.append(_make_request(seq=i))

        entries = WALManager.read(wal.path)
        WALManager.rewrite(wal.path, [entries[2], entries[4]])

        remaining = WALManager.read(wal.path)
        assert [e["seq"] for e in remaining] == [1, 2]

    def test_rewrite_empty_deletes_file(self, wal):
        wal.append(_make_request())
        WALManager.rewrite(wal.path, [])
        assert not wal.path.exists()

    def test_rewrite_nonexistent_is_noop(self, outbox_dir):
        WALManager.rewrite(outbox_dir / "nope.jsonl", [])


class TestWALExists:
    def test_exists_false_initially(self, wal):
        assert wal.exists is False

    def test_exists_true_after_append(self, wal):
        wal.append(_make_request())
        assert wal.exists is True

    def test_exists_false_after_delete(self, wal):
        wal.append(_make_request())
        wal.delete()
        assert wal.exists is False
