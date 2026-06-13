# Jamu Quote Bot

A Discord bot for storing and retrieving quotes, built with Python and discord.py.

## Features

- Add quotes with author attribution
- Reply-based quoting (just reply to a message with `!quote add`)
- Retrieve random quotes
- Search quotes by content or author
- List all quotes with pagination
- Export quotes to CSV
- Import quotes from CSV
- Per-server quote database

## Setup

### Prerequisites
- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Docker and Docker Compose (for PostgreSQL database)

### Installation

1. Clone this repository
2. Install uv if you haven't already:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
3. Install dependencies:
   ```bash
   uv sync
   ```
4. Create a Discord bot on the [Discord Developer Portal](https://discord.com/developers/applications)
5. Enable the "Message Content Intent" in the Bot section
6. Copy your bot token
7. Create a `.env` file in the project root based on `.env.example`:
   ```bash
   cp .env.example .env
   ```
   Then edit `.env` and add your credentials:
   ```
   DISCORD_TOKEN=your_discord_token_here
   POSTGRES_PASSWORD=your_secure_password_here
   ```
8. Start the PostgreSQL database:
   ```bash
   docker compose up postgres -d
   ```
9. Run database migrations:
   ```bash
   docker compose run --rm jamu-bot uv run alembic upgrade head
   ```
10. Invite your bot to your server with the proper permissions (Send Messages, Read Message History, Add Reactions)
11. Run the bot:
    ```bash
    docker compose up jamu-bot -d
    ```
    Or for local development:
    ```bash
    uv run python -m bot.main
    ```

### Development

Common tasks are available via [just](https://github.com/casey/just):

```bash
# Show all available recipes
just

# Complete development setup (install deps, create .env)
just dev-setup

# Run all code quality checks (lint, type-check, tests)
just check

# Individually
just lint        # ruff lint with autofix
just type-check  # ty on the bot package
just test        # run the test suite

# Run the bot locally
just run         # production mode
just run-dev     # development mode

# Docker
just up          # start with docker compose
just logs        # tail logs
just down        # stop and remove containers
```

## Commands

- `!quote` - Get a random quote
- `!quote add <quote> - <author>` - Add a new quote manually
- Reply to any message with `!quote add` - Quote that message
- `!quote list [author]` - List all quotes, optionally filtered by author
- `!quote get <id>` - Get a specific quote by ID
- `!quote delete <id>` - Delete a quote by ID
- `!quote search <term>` - Search for quotes containing a term
- `!quote random [author]` - Get a random quote, optionally by author
- `!quote export` - Export all quotes to CSV (admin only)
- `!quote import` - Import quotes from CSV (admin only)

## Data Storage

Quotes are stored in a PostgreSQL database, which provides better reliability and data persistence for production deployments. The database is run in a Docker container with a persistent volume to prevent data loss.

### Database Configuration

There are two ways to point the bot at a database:

**Full connection string (managed providers like Neon).** Set `DATABASE_URL` to
the connection string from your provider. It takes precedence over the
`POSTGRES_*` variables, and plain `postgres://` / `postgresql://` URLs are
rewritten to use the async driver automatically:

```
DATABASE_URL=postgresql://user:password@ep-xxx-pooler.region.aws.neon.tech/jamu_quotes?sslmode=require
```

`sslmode` (and other libpq-only query params) are translated into the driver's
SSL settings, so Neon's required TLS works out of the box. The prepared-statement
cache is disabled by default (`DB_STATEMENT_CACHE_SIZE=0`), which is required
behind Neon's transaction-mode pooled endpoint.

**Individual settings (local Docker Postgres).** Used when `DATABASE_URL` is not
set:
- `POSTGRES_HOST` - Database host (default: `postgres`)
- `POSTGRES_PORT` - Database port (default: `5432`)
- `POSTGRES_DB` - Database name (default: `jamu_quotes`)
- `POSTGRES_USER` - Database user (default: `jamu_bot`)
- `POSTGRES_PASSWORD` - Database password (required)

Optional tuning: `DB_SSL` (`require`/`disable` to override TLS inference),
`DB_STATEMENT_CACHE_SIZE`, and `DB_POOL_RECYCLE`. See `.env.example`.

To run against Neon, set `DATABASE_URL`, apply migrations with
`uv run alembic upgrade head`, then start the bot — no other changes needed.

### Migrating from SQLite

If you have an existing SQLite database and want to migrate to PostgreSQL:

1. Make sure PostgreSQL is running and migrations are applied:
   ```bash
   docker compose up postgres -d
   docker compose run --rm jamu-bot uv run alembic upgrade head
   ```

2. Run the migration script (dry run first to preview):
   ```bash
   docker compose run --rm jamu-bot uv run python scripts/migrate_sqlite_to_postgres.py \
     --source /app/data/quotes.db --dry-run
   ```

3. If the preview looks good, run the actual migration:
   ```bash
   docker compose run --rm jamu-bot uv run python scripts/migrate_sqlite_to_postgres.py \
     --source /app/data/quotes.db
   ```

4. Verify the migration was successful:
   ```bash
   docker compose exec postgres psql -U jamu_bot -d jamu_quotes \
     -c "SELECT COUNT(*) FROM quotes;"
   ```
