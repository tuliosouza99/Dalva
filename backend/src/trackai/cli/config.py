"""Configuration management commands."""

import os
import json
import sys

import click

from trackai.config import CONFIG_FILE, load_config, update_s3_config
from trackai.s3.sync import validate_s3_credentials


@click.group()
def config():
    """Configuration management commands."""
    pass


@config.command()
@click.option("--bucket", required=True, help="S3 bucket name")
@click.option(
    "--key", default="trackai.duckdb", help="S3 object key (default: trackai.duckdb)"
)
@click.option("--region", default="us-east-1", help="AWS region (default: us-east-1)")
def s3(bucket, key, region):
    """Configure S3 storage settings."""
    click.echo(click.style("Configuring S3 storage...", fg="blue", bold=True))
    click.echo(f"\nBucket: {bucket}")
    click.echo(f"Key: {key}")
    click.echo(f"Region: {region}\n")

    # Validate AWS credentials
    click.echo("Validating AWS credentials...")
    if not validate_s3_credentials():
        click.echo(
            click.style(
                "✗ AWS credentials not found or invalid",
                fg="red",
            ),
            err=True,
        )
        click.echo("\nPlease set the following environment variables:")
        click.echo("  - AWS_ACCESS_KEY_ID")
        click.echo("  - AWS_SECRET_ACCESS_KEY")
        click.echo("  - AWS_DEFAULT_REGION (optional)")
        sys.exit(1)

    click.echo(click.style("✓ AWS credentials validated", fg="green"))

    # Update configuration
    update_s3_config(bucket, key, region)

    click.echo(
        click.style("\n✓ S3 storage configured successfully!", fg="green", bold=True)
    )
    click.echo("\nNext steps:")
    click.echo("  1. Run 'trackai db migrate' if you have existing SQLite data")
    click.echo("  2. Run 'trackai db push' to upload your local database to S3")
    click.echo("  3. Run 'trackai server start' to start the server")


@config.command()
def show():
    """Show current configuration."""
    config = load_config()

    click.echo(click.style("TrackAI Configuration", fg="blue", bold=True))
    click.echo(f"\nConfig file: {CONFIG_FILE}")

    if CONFIG_FILE.exists():
        click.echo(click.style("Status: Found", fg="green"))
    else:
        click.echo(click.style("Status: Not found (using defaults)", fg="yellow"))

    click.echo(click.style("\nCurrent Settings:", fg="blue"))
    click.echo(json.dumps(config.model_dump(), indent=2))

    # Show environment variable overrides
    env_vars = [
        "TRACKAI_DB_PATH",
        "TRACKAI_S3_BUCKET",
        "TRACKAI_S3_KEY",
        "TRACKAI_S3_REGION",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_DEFAULT_REGION",
    ]

    active_env_vars = {var: os.getenv(var) for var in env_vars if os.getenv(var)}

    if active_env_vars:
        click.echo(click.style("\nActive Environment Variables:", fg="blue"))
        for var, value in active_env_vars.items():
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
                click.echo(f"  {var}: {masked_value}")
            else:
                click.echo(f"  {var}: {value}")
