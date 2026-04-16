"""Database management commands."""

import shutil
import sys
from datetime import datetime
from pathlib import Path

import click
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from dalva.config import load_config
from dalva.db.connection import get_db_url


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

    if not db_path.exists():
        click.echo(click.style("\nDatabase does not exist yet.", fg="yellow"))
        return

    # Show file size
    file_size_mb = db_path.stat().st_size / (1024 * 1024)
    click.echo(f"File Size:     {file_size_mb:.2f} MB")

    # Connect and show table statistics
    engine = create_engine(get_db_url(), poolclass=NullPool)

    click.echo(click.style("\nTable Statistics:", fg="green", bold=True))

    try:
        with engine.connect() as conn:
            table_names = [
                row[0]
                for row in conn.execute(
                    text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'main' ORDER BY table_name"
                    )
                ).fetchall()
                if not row[0].endswith("_id_seq")
            ]
            for table in table_names:
                count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                click.echo(f"  {table:20s}: {count:>8,} rows")
    except Exception as e:
        click.echo(click.style(f"\nError reading database: {e}", fg="red"), err=True)
        sys.exit(1)


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
