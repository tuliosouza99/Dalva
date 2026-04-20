"""Tests for database export functionality."""

import json
from datetime import datetime, timezone
from io import StringIO


from dalva.db.schema import (
    DalvaTable as DalvaTableSchema,
    DalvaTableRow,
)
from dalva.db.schema import Config, Metric, Project, Run
from dalva.services.export import EXPORT_VERSION, export_db


class TestExportHeader:
    def test_header_record(self, db_session):
        output = StringIO()
        export_db(output)
        output.seek(0)

        header = json.loads(output.readline())
        assert header["type"] == "header"
        assert header["version"] == EXPORT_VERSION
        assert "exported_at" in header

    def test_empty_database(self, db_session):
        output = StringIO()
        counts = export_db(output)
        output.seek(0)

        lines = output.readlines()
        assert len(lines) == 1
        assert counts["projects"] == 0


class TestExportProjects:
    def test_exports_project(self, db_session, sample_project):
        output = StringIO()
        counts = export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        projects = [rec for rec in lines if rec["type"] == "project"]
        assert len(projects) == 1
        assert projects[0]["name"] == "test-project"
        assert projects[0]["project_id"] == "test-project_abc123"
        assert counts["projects"] == 1

    def test_filter_by_project_name(self, db_session, sample_project):
        other = Project(
            name="other-project",
            project_id="other_xyz",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(other)
        db_session.commit()

        output = StringIO()
        counts = export_db(output, project_name="test-project")
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        projects = [rec for rec in lines if rec["type"] == "project"]
        assert len(projects) == 1
        assert projects[0]["name"] == "test-project"
        assert counts["projects"] == 1

    def test_filter_nonexistent_project(self, db_session, sample_project):
        output = StringIO()
        counts = export_db(output, project_name="nonexistent")
        assert counts["projects"] == 0


class TestExportRuns:
    def test_exports_run(self, db_session, sample_project, sample_run):
        output = StringIO()
        counts = export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        runs = [rec for rec in lines if rec["type"] == "run"]
        assert len(runs) == 1
        assert runs[0]["run_id"] == "TST-1"
        assert runs[0]["project_name"] == "test-project"
        assert runs[0]["state"] == "running"
        assert counts["runs"] == 1

    def test_run_with_optional_fields(self, db_session, sample_project):
        run = Run(
            project_id=sample_project["id"],
            run_id="TST-2",
            name="Named Run",
            group_name="group-a",
            tags="tag1,tag2",
            state="completed",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(run)
        db_session.commit()

        output = StringIO()
        export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        runs = [rec for rec in lines if rec["type"] == "run"]
        assert runs[0]["name"] == "Named Run"
        assert runs[0]["group_name"] == "group-a"
        assert runs[0]["tags"] == "tag1,tag2"
        assert runs[0]["state"] == "completed"


class TestExportConfigs:
    def test_exports_configs(self, db_session, sample_project, sample_run):
        for key, val in [("lr", "0.001"), ("epochs", "10")]:
            cfg = Config(run_id=sample_run["id"], key=key, value=val)
            db_session.add(cfg)
        db_session.commit()

        output = StringIO()
        counts = export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        configs = [rec for rec in lines if rec["type"] == "config"]
        assert len(configs) == 2
        assert configs[0]["key"] == "lr"
        assert configs[0]["value"] == "0.001"
        assert configs[0]["project_name"] == "test-project"
        assert configs[0]["run_id"] == "TST-1"
        assert counts["configs"] == 2


class TestExportMetrics:
    def test_exports_metrics(
        self, db_session, sample_project, sample_run, sample_metrics
    ):
        output = StringIO()
        counts = export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        metrics = [rec for rec in lines if rec["type"] == "metric"]
        assert len(metrics) == 4
        assert counts["metrics"] == 4

    def test_metric_has_correct_fields(
        self, db_session, sample_project, sample_run, sample_metrics
    ):
        output = StringIO()
        export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        metrics = [rec for rec in lines if rec["type"] == "metric"]
        m = metrics[0]
        assert m["project_name"] == "test-project"
        assert m["run_id"] == "TST-1"
        assert m["attribute_path"] in ("loss", "accuracy")
        assert m["attribute_type"] == "float"
        assert "step" in m
        assert "float_value" in m

    def test_omits_null_value_columns(self, db_session, sample_project, sample_run):
        metric = Metric(
            run_id=sample_run["id"],
            attribute_path="loss",
            attribute_type="float",
            step=0,
            timestamp=datetime.now(timezone.utc),
            float_value=0.5,
        )
        db_session.add(metric)
        db_session.commit()

        output = StringIO()
        export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        metrics = [rec for rec in lines if rec["type"] == "metric"]
        m = metrics[0]
        assert "float_value" in m
        assert "int_value" not in m
        assert "string_value" not in m
        assert "bool_value" not in m


class TestExportTables:
    def test_exports_table(self, db_session, sample_project, sample_table):
        row = DalvaTableRow(
            table_id=sample_table["id"],
            version=0,
            row_data='{"col1": 42, "col2": "hello"}',
        )
        db_session.add(row)
        db_session.commit()

        output = StringIO()
        counts = export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        tables = [rec for rec in lines if rec["type"] == "table"]
        assert len(tables) == 1
        assert tables[0]["table_id"] == "TST-T1"
        assert tables[0]["name"] == "Test Table"
        assert counts["tables"] == 1

        table_rows = [rec for rec in lines if rec["type"] == "table_row"]
        assert len(table_rows) == 1
        assert json.loads(table_rows[0]["row_data"]) == {"col1": 42, "col2": "hello"}
        assert counts["table_rows"] == 1

    def test_table_with_linked_run(self, db_session, sample_project, sample_run):
        table = DalvaTableSchema(
            project_id=sample_project["id"],
            table_id="TST-T2",
            name="Linked Table",
            run_id=sample_run["id"],
            version=0,
            row_count=0,
            state="active",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(table)
        db_session.commit()

        output = StringIO()
        export_db(output)
        output.seek(0)

        lines = [json.loads(line) for line in output if line.strip()]
        tables = [rec for rec in lines if rec["type"] == "table"]
        assert tables[0]["run_id"] == "TST-1"


class TestExportNDJSONFormat:
    def test_each_line_is_valid_json(
        self, db_session, sample_project, sample_run, sample_metrics
    ):
        output = StringIO()
        export_db(output)
        output.seek(0)

        for line in output:
            if line.strip():
                json.loads(line)

    def test_no_db_ids_in_output(
        self, db_session, sample_project, sample_run, sample_metrics
    ):
        output = StringIO()
        export_db(output)
        output.seek(0)

        content = output.read()
        lines = [json.loads(line) for line in content.splitlines() if line.strip()]
        for line in lines:
            assert "db_id" not in line
