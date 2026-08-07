"""End-to-end materialization tests for daemonless journals."""

import json

from dalva.db.connection import get_session
from dalva.db.schema import Config, DalvaTable, DalvaTableRow, Metric, Run
from dalva.sdk.local import JournalRun
from dalva.sdk.schema import DalvaSchema
from dalva.services.journal_import import import_journals_once


class _Prediction(DalvaSchema):
    label: str
    score: float


def test_journal_materializes_live_run_and_table_idempotently(db_engine, tmp_path):
    del db_engine
    runs_dir = tmp_path / "runs"
    run = JournalRun(
        project="daemonless",
        config={"optimizer": {"lr": 0.01}},
        runs_dir=runs_dir,
    )
    run.log({"train": {"loss": 0.8}}, step=0)
    run.flush()

    first_import = import_journals_once(runs_dir)
    assert first_import >= 2

    run.log({"train": {"loss": 0.4}}, step=1)
    table = run.create_table(_Prediction, name="predictions")
    table.log_row({"label": "cat", "score": 0.95})
    run.finish()

    second_import = import_journals_once(runs_dir)
    assert second_import > 0
    assert import_journals_once(runs_dir) == 0

    db = get_session()
    try:
        stored_run = db.query(Run).filter(Run.run_id == run.run_id).one()
        assert stored_run.state == "completed"
        assert db.query(Metric).filter(Metric.run_id == stored_run.id).count() == 2
        config = db.query(Config).filter(Config.run_id == stored_run.id).one()
        assert config.key == "optimizer/lr"
        assert json.loads(config.value) == 0.01

        stored_table = (
            db.query(DalvaTable).filter(DalvaTable.run_id == stored_run.id).one()
        )
        assert stored_table.state == "finished"
        assert stored_table.row_count == 1
        row = (
            db.query(DalvaTableRow)
            .filter(DalvaTableRow.table_id == stored_table.id)
            .one()
        )
        assert json.loads(row.row_data) == {"label": "cat", "score": 0.95}
    finally:
        db.close()
