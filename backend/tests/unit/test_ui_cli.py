"""Tests for the on-demand UI command."""

from unittest.mock import patch

from click.testing import CliRunner
from dalva.cli.main import cli


def test_ui_starts_single_non_reloading_process():
    runner = CliRunner()
    with (
        patch("dalva.cli.ui.uvicorn.run") as run,
        patch("dalva.cli.ui.threading.Timer") as timer,
    ):
        result = runner.invoke(cli, ["ui", "--port", "8123"])

    assert result.exit_code == 0
    run.assert_called_once_with(
        "dalva.api.main:app",
        host="127.0.0.1",
        port=8123,
        reload=False,
    )
    timer.return_value.start.assert_called_once()
