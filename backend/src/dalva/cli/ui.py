"""On-demand Dalva web UI command."""

import threading
import webbrowser

import click
import uvicorn

from dalva.cli.utils import find_available_port


@click.command()
@click.option("--port", type=int, default=None, help="Local UI port.")
@click.option("--host", default="127.0.0.1", help="Interface to bind.")
def ui(port: int | None, host: str) -> None:
    """Open the UI and materialize daemonless journals while it is running."""
    selected_port = port or find_available_port(8000)
    url = f"http://localhost:{selected_port}"
    click.echo(f"Opening Dalva at {url}")
    click.echo("Press Ctrl+C to close the UI.")

    opener = threading.Timer(0.75, webbrowser.open, args=(url,))
    opener.daemon = True
    opener.start()
    uvicorn.run(
        "dalva.api.main:app",
        host=host,
        port=selected_port,
        reload=False,
    )
