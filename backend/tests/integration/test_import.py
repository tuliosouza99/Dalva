"""Tests for database import functionality."""

import json
import os
from io import StringIO

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from dalva.db.connection import session_scope
from dalva.db.schema import Config, Metric
from dalva.services.import_db import import_db
from tests.conftest import _create_tables


def _make_ndjson(records):
    return StringIO("\n".join(json.dumps(r) for r in records))


class TestImportHeader:
    def test_rejects_unsupported_version(self, db_session):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 99, "exported_at": "2026-01-01T00:00:00"},
            ]
        )
        try:
            import_db(ndjson)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "version" in str(e).lower()

    def test_accepts_version_1(self, db_session):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
            ]
        )
        counts = import_db(ndjson)
        assert counts["projects_created"] == 0


class TestImportProjects:
    def test_creates_project(self, db_session):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "my-project",
                    "created_at": "2026-01-01T00:00:00",
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["projects_created"] == 1
        assert counts["projects_skipped"] == 0

        with session_scope() as session:
            rows = session.execute(
                text("SELECT name, project_id FROM projects")
            ).fetchall()
            assert len(rows) == 1
            assert rows[0].name == "my-project"
            assert rows[0].project_id == "pid1"

    def test_skips_existing_project(self, db_session, sample_project):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "different_id",
                    "name": "test-project",
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["projects_skipped"] == 1
        assert counts["projects_created"] == 0

    def test_fail_on_conflict(self, db_session, sample_project):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "different_id",
                    "name": "test-project",
                },
            ]
        )
        try:
            import_db(ndjson, fail_on_conflict=True)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "test-project" in str(e)


class TestImportRuns:
    def test_creates_run(self, db_session, sample_project):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "R1",
                    "state": "running",
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["runs_created"] == 1

        with session_scope() as session:
            rows = session.execute(text("SELECT run_id, state FROM runs")).fetchall()
            r1 = [r for r in rows if r.run_id == "R1"]
            assert len(r1) == 1
            assert r1[0].state == "running"

    def test_skips_existing_run(self, db_session, sample_project, sample_run):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "completed",
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["runs_skipped"] == 1
        assert counts["runs_created"] == 0


class TestImportConfigs:
    def test_imports_configs(self, db_session, sample_project, sample_run):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "running",
                },
                {
                    "type": "config",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "key": "lr",
                    "value": "0.001",
                },
                {
                    "type": "config",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "key": "epochs",
                    "value": "10",
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["configs_imported"] == 2

        with session_scope() as session:
            rows = session.execute(
                text("SELECT key, value FROM configs ORDER BY key")
            ).fetchall()
            assert len(rows) == 2
            assert rows[0].key == "epochs"
            assert rows[0].value == "10"
            assert rows[1].key == "lr"
            assert rows[1].value == "0.001"

    def test_skips_duplicate_config(self, db_session, sample_project, sample_run):
        cfg = Config(run_id=sample_run["id"], key="lr", value="0.001")
        db_session.add(cfg)
        db_session.commit()

        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "running",
                },
                {
                    "type": "config",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "key": "lr",
                    "value": "0.002",
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["configs_skipped"] == 1

        with session_scope() as session:
            rows = session.execute(
                text("SELECT value FROM configs WHERE key = 'lr'")
            ).fetchall()
            assert len(rows) == 1
            assert rows[0].value == "0.001"


class TestImportMetrics:
    def test_imports_metrics(self, db_session, sample_project, sample_run):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "running",
                },
                {
                    "type": "metric",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "attribute_path": "loss",
                    "attribute_type": "float_series",
                    "step": 0,
                    "float_value": 0.5,
                },
                {
                    "type": "metric",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "attribute_path": "loss",
                    "attribute_type": "float_series",
                    "step": 1,
                    "float_value": 0.3,
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["metrics_imported"] == 2

        with session_scope() as session:
            rows = session.execute(
                text(
                    "SELECT attribute_path, step, float_value FROM metrics ORDER BY step"
                )
            ).fetchall()
            assert len(rows) == 2
            assert rows[0].float_value == 0.5
            assert rows[1].float_value == 0.3

    def test_handles_on_conflict_do_nothing(
        self, db_session, sample_project, sample_run
    ):
        metric = Metric(
            run_id=sample_run["id"],
            attribute_path="loss",
            attribute_type="float",
            step=0,
            float_value=0.5,
        )
        db_session.add(metric)
        db_session.commit()

        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "running",
                },
                {
                    "type": "metric",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "attribute_path": "loss",
                    "attribute_type": "float",
                    "step": 0,
                    "float_value": 0.99,
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["metrics_imported"] == 1

        with session_scope() as session:
            rows = session.execute(
                text(
                    "SELECT float_value FROM metrics WHERE step = 0 AND attribute_path = 'loss'"
                )
            ).fetchall()
            assert len(rows) == 1
            assert rows[0].float_value == 0.5

    def test_scalar_metric_with_null_step(self, db_session, sample_project, sample_run):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "running",
                },
                {
                    "type": "metric",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "attribute_path": "final_accuracy",
                    "attribute_type": "float",
                    "float_value": 0.95,
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["metrics_imported"] == 1

        with session_scope() as session:
            rows = session.execute(
                text(
                    "SELECT step, float_value FROM metrics WHERE attribute_path = 'final_accuracy'"
                )
            ).fetchall()
            assert len(rows) == 1
            assert rows[0].step is None
            assert rows[0].float_value == 0.95

    def test_batches_large_metric_import(self, db_session, sample_project, sample_run):
        records = [
            {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
            {
                "type": "project",
                "project_id": "pid1",
                "name": "test-project",
            },
            {
                "type": "run",
                "project_name": "test-project",
                "run_id": "TST-1",
                "state": "running",
            },
        ]
        for i in range(2500):
            records.append(
                {
                    "type": "metric",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "attribute_path": "loss",
                    "attribute_type": "float_series",
                    "step": i,
                    "float_value": 1.0 / (i + 1),
                }
            )

        ndjson = _make_ndjson(records)
        counts = import_db(ndjson)
        assert counts["metrics_imported"] == 2500

        with session_scope() as session:
            total = session.execute(text("SELECT COUNT(*) FROM metrics")).scalar()
            assert total == 2500


class TestImportTables:
    def test_imports_table_with_rows(self, db_session, sample_project):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "table",
                    "project_name": "test-project",
                    "table_id": "T1",
                    "name": "Results",
                    "state": "finished",
                    "column_schema": '[{"name": "x", "type": "int"}]',
                },
                {
                    "type": "table_row",
                    "project_name": "test-project",
                    "table_id": "T1",
                    "version": 0,
                    "row_data": '{"x": 1}',
                },
                {
                    "type": "table_row",
                    "project_name": "test-project",
                    "table_id": "T1",
                    "version": 0,
                    "row_data": '{"x": 2}',
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["tables_created"] == 1
        assert counts["table_rows_imported"] == 2

        with session_scope() as session:
            tables = session.execute(
                text("SELECT table_id, name, state FROM dalva_tables")
            ).fetchall()
            assert len(tables) == 1
            assert tables[0].table_id == "T1"
            assert tables[0].name == "Results"

            rows = session.execute(
                text("SELECT row_data FROM dalva_table_rows ORDER BY id")
            ).fetchall()
            assert len(rows) == 2
            assert json.loads(rows[0].row_data) == {"x": 1}
            assert json.loads(rows[1].row_data) == {"x": 2}

    def test_table_with_linked_run(self, db_session, sample_project, sample_run):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "running",
                },
                {
                    "type": "table",
                    "project_name": "test-project",
                    "table_id": "T2",
                    "name": "Linked",
                    "run_id": "TST-1",
                    "state": "active",
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["tables_created"] == 1

        with session_scope() as session:
            tables = session.execute(
                text("SELECT table_id, run_id FROM dalva_tables WHERE table_id = 'T2'")
            ).fetchall()
            assert tables[0].run_id == sample_run["id"]


class TestRoundTrip:
    def test_export_then_import(
        self, db_session, sample_project, sample_run, sample_metrics, tmp_path
    ):
        from dalva.services.export import export_db

        output = StringIO()
        export_db(output)
        output.seek(0)
        ndjson_data = output.read()

        new_db_path = str(tmp_path / "roundtrip.duckdb")
        old_path = os.environ.get("DALVA_DB_PATH")
        try:
            os.environ["DALVA_DB_PATH"] = new_db_path
            new_engine = create_engine(f"duckdb:///{new_db_path}", poolclass=NullPool)
            _create_tables(new_engine)

            counts = import_db(StringIO(ndjson_data))
            assert counts["projects_created"] == 1
            assert counts["runs_created"] == 1
            assert counts["metrics_imported"] == 4

            with session_scope() as session:
                total = session.execute(text("SELECT COUNT(*) FROM metrics")).scalar()
                assert total == 4
        finally:
            os.environ["DALVA_DB_PATH"] = old_path or ""
            new_engine.dispose()

    def test_import_into_existing_data(self, db_session, sample_project, sample_run):
        ndjson = _make_ndjson(
            [
                {"type": "header", "version": 1, "exported_at": "2026-01-01T00:00:00"},
                {
                    "type": "project",
                    "project_id": "pid1",
                    "name": "test-project",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "TST-1",
                    "state": "completed",
                },
                {
                    "type": "run",
                    "project_name": "test-project",
                    "run_id": "NEW-1",
                    "state": "running",
                },
                {
                    "type": "metric",
                    "project_name": "test-project",
                    "run_id": "NEW-1",
                    "attribute_path": "loss",
                    "attribute_type": "float",
                    "float_value": 0.1,
                },
            ]
        )
        counts = import_db(ndjson)
        assert counts["projects_skipped"] == 1
        assert counts["runs_skipped"] == 1
        assert counts["runs_created"] == 1
        assert counts["metrics_imported"] == 1
