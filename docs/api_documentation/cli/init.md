# Init Command

> **Removed.** `trackai init` no longer exists.

First-time S3 setup is done with [`trackai config s3`](config.md):

```bash
trackai config s3 --bucket my-bucket --key trackai.duckdb --region us-east-1
```

The database (`~/.trackai/trackai.duckdb`) is created automatically the first time the server starts or an experiment is logged.

See the [CLI Usage Guide](../../getting_started/cli_usage.md) for details.
