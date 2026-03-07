# Default: show available commands
default:
    @just --list

# Install production dependencies
install:
    uv sync --no-extra dev

# Sync dependencies (including dev)
sync:
    uv sync --extra dev

# Run all code quality checks including tests
check: lint type-check test

# Run tests with pytest
test:
    uv run pytest tests/ -v

# Run tests with coverage report
test-cov:
    uv run pytest tests/ --cov=. --cov-report=term-missing

# Run tests with HTML coverage report
test-cov-html:
    uv run pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
    @echo "Coverage report generated in htmlcov/index.html"

# Run tests without verbose output
test-fast:
    uv run pytest tests/

# Run tests in watch mode (re-run on file changes)
test-watch:
    uv run pytest-watch tests/

# Run ruff linter with auto-fix
lint:
    uv run ruff check --fix .

# Run mypy type checking
type-check:
    uv run mypy .

# Format code with ruff
format:
    uv run ruff format .

# Run the bot in production mode
run:
    uv run python bot.py

# Run the bot in development mode
run-dev:
    uv run python bot.py --dev

# Rebuild and start Docker container (pass service=jamu-bot-dev for dev mode)
rebuild service="jamu-bot":
    @echo "This will rebuild the Docker container for {{service}}"
    @read -p "Continue? [y/N]: " confirm && [ "$confirm" = "y" ] || [ "$confirm" = "Y" ] || exit 1
    docker compose build
    docker compose up {{service}} -d

# Rebuild Docker image (clean build with cleanup) and start
rebuild-full service="jamu-bot":
    @echo "WARNING: This will do a FULL rebuild with cleanup for {{service}}"
    @echo "This includes: stopping containers, removing volumes, pruning system, and rebuilding from scratch"
    @read -p "Continue? [y/N]: " confirm && [ "$confirm" = "y" ] || [ "$confirm" = "Y" ] || exit 1
    docker compose down -v
    docker system prune -f
    docker compose build --no-cache
    docker compose up {{service}} -d

# Start the bot with docker compose (pass service=jamu-bot-dev for dev mode)
up service="jamu-bot":
    docker compose up {{service}} -d

# Stop and remove containers (pass service=jamu-bot-dev for dev only)
down service="jamu-bot":
    docker compose stop {{service}}
    docker compose rm -f {{service}}

# Restart the bot (pass service=jamu-bot-dev for dev mode)
restart service="jamu-bot":
    docker compose restart {{service}}

# Show Docker container logs (pass service=jamu-bot-dev for dev mode)
logs service="jamu-bot":
    docker compose logs -f {{service}}

# Show container status
status:
    docker compose ps

# Clean up cache files
clean:
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true

# Copy .env.example to .env
env-example:
    cp .env.example .env
    @echo "Created .env file. Please edit it with your Discord token."

# Complete development setup
dev-setup: sync env-example
    @echo "Development setup complete!"
    @echo "1. Edit .env with your Discord token"
    @echo "2. Run 'just run-dev' to start the bot"

# Run pre-commit checks (lint + type-check)
pre-commit: check
    @echo "All checks passed!"

# Run Alembic database migrations
migrate:
    uv run alembic upgrade head

# Run Alembic database migrations for dev environment
migrate-dev:
    uv run alembic --dev upgrade head

# Create a new migration (usage: just migration "description")
migration message:
    uv run alembic revision --autogenerate -m "{{message}}"

# Create a new migration in dev mode
migration-dev message:
    uv run alembic --dev revision --autogenerate -m "{{message}}"

# Show migration history
migration-history:
    uv run alembic history

# Show current migration
migration-current:
    uv run alembic current
