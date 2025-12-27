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
    uv run python bot.py
    ```

### Development

For development with type checking:
```bash
# Install development dependencies
uv sync --group dev

# Run type checking
uv run mypy .

# Run linting
uv run ruff check .
```

### Using the Makefile

A Makefile is provided for common development tasks:

```bash
# Show all available commands
make help

# Complete development setup
make dev-setup

# Install dependencies
make install-dev

# Run code quality checks
make check

# Run the bot in development mode
make run-dev

# Run the bot in production mode
make run

# Docker commands
make build
make up
make logs
make down
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

The bot uses the following environment variables for database configuration:
- `POSTGRES_HOST` - Database host (default: `postgres`)
- `POSTGRES_PORT` - Database port (default: `5432`)
- `POSTGRES_DB` - Database name (default: `jamu_quotes`)
- `POSTGRES_USER` - Database user (default: `jamu_bot`)
- `POSTGRES_PASSWORD` - Database password (required)

### Migrating from SQLite

If you have an existing SQLite database and want to migrate to PostgreSQL:

1. Make sure PostgreSQL is running and migrations are applied:
   ```bash
   docker compose up postgres -d
   docker compose run --rm jamu-bot uv run alembic upgrade head
   ```

2. Run the migration script (dry run first to preview):
   ```bash
   docker compose run --rm jamu-bot uv run python migrate_sqlite_to_postgres.py \
     --source /app/data/quotes.db --dry-run
   ```

3. If the preview looks good, run the actual migration:
   ```bash
   docker compose run --rm jamu-bot uv run python migrate_sqlite_to_postgres.py \
     --source /app/data/quotes.db
   ```

4. Verify the migration was successful:
   ```bash
   docker compose exec postgres psql -U jamu_bot -d jamu_quotes \
     -c "SELECT COUNT(*) FROM quotes;"
   ```
