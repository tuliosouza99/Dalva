# Database Commands

CLI commands for database management.

## Commands

### trackai db info

Show database statistics.

### trackai db backup

Backup database to a file.

### trackai db reset

Delete all data (warning: irreversible).

### trackai db migrate

Migrate from SQLite to DuckDB.

### trackai db pull

Download the database from S3 to `~/.trackai/trackai.duckdb`.
Requires S3 to be configured (`trackai config s3`) and valid AWS credentials.

### trackai db push

Upload `~/.trackai/trackai.duckdb` to S3.
Requires S3 to be configured (`trackai config s3`) and valid AWS credentials.

See the [CLI Usage Guide](../../getting_started/cli_usage.md) for complete documentation.
