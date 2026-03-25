"""Configuration management commands."""

import json
import os

import click

from dalva.config import CONFIG_FILE, load_config


@click.group()
def config():
    """Configuration management commands."""
    pass


@config.command()
def show():
    """Show current configuration."""
    config = load_config()

    click.echo(click.style("Dalva Configuration", fg="blue", bold=True))
    click.echo(f"\nConfig file: {CONFIG_FILE}")

    if CONFIG_FILE.exists():
        click.echo(click.style("Status: Found", fg="green"))
    else:
        click.echo(click.style("Status: Not found (using defaults)", fg="yellow"))

    click.echo(click.style("\nCurrent Settings:", fg="blue"))
    click.echo(json.dumps(config.model_dump(), indent=2))

    # Show environment variable overrides
    env_vars = ["DALVA_DB_PATH"]

    active_env_vars = {var: os.getenv(var) for var in env_vars if os.getenv(var)}

    if active_env_vars:
        click.echo(click.style("\nActive Environment Variables:", fg="blue"))
        for var, value in active_env_vars.items():
            click.echo(f"  {var}: {value}")
