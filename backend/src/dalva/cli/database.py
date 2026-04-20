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
from dalva.services.export import export_db
from dalva.services.import_db import import_db


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


@db.command("export")
@click.option("--output", default="-", help="Output file path (default: stdout)")
@click.option(
    "--project", "project_name", default=None, help="Export only a specific project"
)
def export_command(output, project_name):
    """Export database to NDJSON format."""
    from dalva.db.connection import init_db

    config = load_config()
    db_path = Path(config.database.db_path).expanduser()

    if not db_path.exists():
        click.echo(click.style("Database does not exist", fg="red"), err=True)
        sys.exit(1)

    init_db()

    if output == "-":
        counts = export_db(sys.stdout, project_name=project_name)
    else:
        with open(output, "w") as f:
            counts = export_db(f, project_name=project_name)

    total = sum(counts.values())
    if total == 0:
        click.echo(click.style("No data to export.", fg="yellow"), err=True)
        return

    parts = []
    if counts["projects"]:
        parts.append(f"{counts['projects']} project(s)")
    if counts["runs"]:
        parts.append(f"{counts['runs']} run(s)")
    if counts["configs"]:
        parts.append(f"{counts['configs']} config(s)")
    if counts["metrics"]:
        parts.append(f"{counts['metrics']} metric(s)")
    if counts["tables"]:
        parts.append(f"{counts['tables']} table(s)")
    if counts["table_rows"]:
        parts.append(f"{counts['table_rows']} table row(s)")

    click.echo(
        click.style("✓ Exported ", fg="green") + ", ".join(parts),
        err=True,
    )


@db.command("import")
@click.argument("file", default="-")
@click.option(
    "--fail-on-conflict", is_flag=True, help="Fail on conflicts instead of skipping"
)
def import_command(file, fail_on_conflict):
    """Import NDJSON data into database.

    FILE is the path to an NDJSON export file. Use - to read from stdin.
    """
    from dalva.db.connection import init_db

    init_db()

    try:
        if file == "-":
            counts = import_db(sys.stdin, fail_on_conflict=fail_on_conflict)
        else:
            path = Path(file).expanduser()
            if not path.exists():
                click.echo(click.style(f"File not found: {file}", fg="red"), err=True)
                sys.exit(1)
            with open(path) as f:
                counts = import_db(f, fail_on_conflict=fail_on_conflict)
    except ValueError as e:
        click.echo(click.style(f"Import error: {e}", fg="red"), err=True)
        sys.exit(1)

    parts = []
    if counts["projects_created"]:
        parts.append(f"{counts['projects_created']} project(s) created")
    if counts["projects_skipped"]:
        parts.append(f"{counts['projects_skipped']} project(s) skipped")
    if counts["runs_created"]:
        parts.append(f"{counts['runs_created']} run(s) created")
    if counts["runs_skipped"]:
        parts.append(f"{counts['runs_skipped']} run(s) skipped")
    if counts["configs_imported"]:
        parts.append(f"{counts['configs_imported']} config(s)")
    if counts["configs_skipped"]:
        parts.append(f"{counts['configs_skipped']} config(s) skipped")
    if counts["metrics_imported"]:
        parts.append(f"{counts['metrics_imported']} metric(s)")
    if counts["tables_created"]:
        parts.append(f"{counts['tables_created']} table(s) created")
    if counts["tables_skipped"]:
        parts.append(f"{counts['tables_skipped']} table(s) skipped")
    if counts["table_rows_imported"]:
        parts.append(f"{counts['table_rows_imported']} table row(s)")

    if not parts:
        click.echo(click.style("Nothing to import.", fg="yellow"), err=True)
        return

    click.echo(
        click.style("✓ Imported: ", fg="green") + ", ".join(parts),
        err=True,
    )
