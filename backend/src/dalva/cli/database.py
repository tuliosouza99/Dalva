"""Database management commands."""

import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from sqlalchemy import create_engine, text

from dalva.config import load_config
from dalva.db.connection import get_db_url
from dalva.s3.sync import sync_from_s3, sync_to_s3


def _require_s3(config) -> None:
    """Exit with a clear error message if S3 is not configured."""
    if not config.database.s3_bucket:
        click.echo(
            click.style(
                "S3 not configured. Run 'dalva config s3 --bucket <name>' first.",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)


def _require_s3_credentials() -> None:
    """Exit with a clear error message if AWS credentials are missing."""
    from dalva.s3.sync import validate_s3_credentials

    if not validate_s3_credentials():
        click.echo(
            click.style("AWS credentials not found or invalid.", fg="red"),
            err=True,
        )
        click.echo(
            "Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_DEFAULT_REGION "
            "(or store them in ~/.dalva/.env).",
            err=True,
        )
        sys.exit(1)


@click.group(name="db")
def db():
    """Database management commands."""
    pass


@db.command()
def info():
    """Show database statistics."""
    config = load_config()
    db_path = Path(config.database.db_path).expanduser()

    click.echo(click.style("Database Information", fg="blue", bold=True))
    click.echo(f"\nDatabase Path: {db_path}")

    if config.database.s3_bucket:
        click.echo(f"S3 Bucket:     {config.database.s3_bucket}")
        click.echo(f"S3 Key:        {config.database.s3_key}")
        click.echo(f"S3 Region:     {config.database.s3_region}")

    if not db_path.exists():
        click.echo(click.style("\nDatabase does not exist yet.", fg="yellow"))
        return

    # Show file size
    file_size_mb = db_path.stat().st_size / (1024 * 1024)
    click.echo(f"File Size:     {file_size_mb:.2f} MB")

    # Connect and show table statistics
    engine = create_engine(get_db_url())

    click.echo(click.style("\nTable Statistics:", fg="green", bold=True))

    tables = [
        "projects",
        "runs",
        "configs",
        "metrics",
        "files",
        "custom_views",
        "dashboards",
    ]

    try:
        with engine.connect() as conn:
            for table in tables:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                click.echo(f"  {table:15s}: {count:>8,} rows")
    except Exception as e:
        click.echo(click.style(f"\nError reading database: {e}", fg="red"), err=True)


@db.command()
@click.option("--output", default=None, help="Output path for backup file")
def backup(output):
    """Create a backup of the database."""
    config = load_config()
    source_path = Path(config.database.db_path).expanduser()

    if not source_path.exists():
        click.echo(click.style("Database does not exist", fg="red"), err=True)
        sys.exit(1)

    # Generate backup path if not provided
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output = str(source_path.parent / f"dalva-backup-{timestamp}.duckdb")

    output_path = Path(output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    click.echo(f"Creating backup: {output_path}")
    shutil.copy2(source_path, output_path)

    click.echo(click.style("✓ Backup created successfully!", fg="green"))


@db.command()
@click.confirmation_option(prompt="Are you sure you want to delete all data?")
def reset():
    """Delete the database (requires confirmation)."""
    config = load_config()
    db_path = Path(config.database.db_path).expanduser()

    if db_path.exists():
        db_path.unlink()
        click.echo(click.style("✓ Database deleted", fg="green"))
    else:
        click.echo(click.style("Database does not exist", fg="yellow"))


@db.command()
def pull():
    """Download the database from S3 to ~/.dalva/dalva.duckdb."""
    config = load_config()
    _require_s3(config)
    _require_s3_credentials()

    local_path = Path(config.database.db_path).expanduser()

    try:
        click.echo(f"Downloading from S3 → {local_path} ...")
        sync_from_s3(destination=local_path)
        click.echo(click.style("✓ Successfully pulled from S3!", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Pull failed: {e}", fg="red"), err=True)
        sys.exit(1)


@db.command()
def push():
    """Upload ~/.dalva/dalva.duckdb to S3."""
    config = load_config()
    _require_s3(config)
    _require_s3_credentials()

    local_path = Path(config.database.db_path).expanduser()

    if not local_path.exists():
        click.echo(click.style("Database does not exist locally.", fg="red"), err=True)
        sys.exit(1)

    try:
        click.echo(f"Uploading {local_path} → S3 ...")
        sync_to_s3(source=local_path)
        click.echo(click.style("✓ Successfully pushed to S3!", fg="green"))
    except Exception as e:
        click.echo(click.style(f"✗ Push failed: {e}", fg="red"), err=True)
        sys.exit(1)
