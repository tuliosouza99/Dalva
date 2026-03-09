"""Main CLI entry point for TrackAI."""

import click

from trackai.cli.config import config
from trackai.cli.database import db
from trackai.cli.server import server


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """TrackAI - Lightweight experiment tracker for deep learning."""
    pass

# Register commands and command groups
cli.add_command(server)
cli.add_command(db)
cli.add_command(config)


if __name__ == "__main__":
    cli()
