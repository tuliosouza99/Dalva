"""Main CLI entry point for Dalva."""

import click

from dalva.cli.config import config
from dalva.cli.database import db
from dalva.cli.server import server
from dalva.cli.sync import sync


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Dalva - Lightweight experiment tracker for deep learning."""
    pass


# Register commands and command groups
cli.add_command(server)
cli.add_command(db)
cli.add_command(config)
cli.add_command(sync)


if __name__ == "__main__":
    cli()
