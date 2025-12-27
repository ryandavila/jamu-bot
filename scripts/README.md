# Scripts Directory

This directory contains utility scripts for managing and maintaining the Jamu Quote Bot.

## Migration Scripts

### `migrate_sqlite_to_postgres.py`

Migrates quote data from SQLite database to PostgreSQL.

**Usage:**
```bash
# Dry run (preview what will be migrated)
uv run python scripts/migrate_sqlite_to_postgres.py --source data/quotes.db --dry-run

# Actual migration
uv run python scripts/migrate_sqlite_to_postgres.py --source data/quotes.db

# With custom target database
uv run python scripts/migrate_sqlite_to_postgres.py --source data/quotes.db --target postgresql+asyncpg://user:pass@host:port/db

# Custom batch size
uv run python scripts/migrate_sqlite_to_postgres.py --source data/quotes.db --batch-size 500
```

**Features:**
- Dry-run mode for safe preview
- Batch processing (default: 1000 records)
- Duplicate detection and skipping
- Transactional with automatic rollback on errors
- Progress reporting and validation

### `production_migration.sh`

Complete end-to-end migration workflow for production servers. Automates the entire process of migrating from SQLite to PostgreSQL.

**Usage:**
```bash
./scripts/production_migration.sh
```

**What it does:**
1. Backs up existing SQLite database
2. Starts PostgreSQL container
3. Waits for PostgreSQL to be healthy
4. Runs Alembic migrations (creates schema)
5. Runs data migration with confirmation
6. Verifies migration success
7. Starts the Discord bot

## Data Export Scripts

### `export_quotes.py`

Export quotes from the database to various formats.

**Usage:**
```bash
# Export to CSV
uv run python scripts/export_quotes.py --format csv --output quotes.csv

# Export to JSON
uv run python scripts/export_quotes.py --format json --output quotes.json

# Filter by guild
uv run python scripts/export_quotes.py --guild-id 123456789 --output guild_quotes.csv
```

## Development Scripts

### `dev.sh`

Starts the bot in development mode.

**Usage:**
```bash
./scripts/dev.sh
```

### `prod.sh`

Starts the bot in production mode.

**Usage:**
```bash
./scripts/prod.sh
```

## Notes

- All Python scripts should be run with `uv run python scripts/<script_name>.py`
- Shell scripts should be made executable: `chmod +x scripts/<script_name>.sh`
- For Docker-based deployment, use `docker compose run --rm jamu-bot uv run python scripts/<script>.py`
