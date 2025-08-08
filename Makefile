.PHONY: help install sync check lint type-check format run clean build up down restart logs status env-example dev-setup pre-commit

# Default target
help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation and setup
install: ## Install production dependencies
	uv sync --no-extra dev

sync: ## Sync dependencies (alias for install-dev)
	uv sync --extra dev

# Code quality and checking
check: lint type-check test ## Run all code quality checks including tests

test: ## Run tests with pytest
	uv run pytest tests/ -v

test-cov: ## Run tests with coverage report
	uv run pytest tests/ --cov=. --cov-report=term-missing

test-cov-html: ## Run tests with HTML coverage report
	uv run pytest tests/ --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

test-fast: ## Run tests without verbose output
	uv run pytest tests/

test-watch: ## Run tests in watch mode (re-run on file changes)
	uv run pytest-watch tests/

lint: ## Run ruff linter with auto-fix
	uv run ruff check --fix .

type-check: ## Run mypy type checking
	uv run mypy .

format: ## Format code with ruff
	uv run ruff format .

# Running the bot
run: ## Run the bot in production mode
	uv run python bot.py

run-dev: ## Run the bot in development mode
	uv run python bot.py --dev

# Docker commands
rebuild: ## Rebuild and start Docker container (use 'make rebuild SERVICE=jamu-bot-dev' for dev mode)
	@echo "This will rebuild the Docker container for $(or $(SERVICE),jamu-bot)"
	@read -p "Continue? [y/N]: " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || exit 1
	docker compose build
	docker compose up $(or $(SERVICE),jamu-bot) -d

rebuild-full: ## Rebuild Docker image (clean build with cleanup) and start (use 'make rebuild-full SERVICE=jamu-bot-dev' for dev mode)
	@echo "WARNING: This will do a FULL rebuild with cleanup for $(or $(SERVICE),jamu-bot)"
	@echo "This includes: stopping containers, removing volumes, pruning system, and rebuilding from scratch"
	@read -p "Continue? [y/N]: " confirm && [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ] || exit 1
	docker compose down -v
	docker system prune -f
	docker compose build --no-cache
	docker compose up $(or $(SERVICE),jamu-bot) -d

up: ## Start the bot with docker compose (use 'make up SERVICE=jamu-bot-dev' for dev mode)
	docker compose up $(or $(SERVICE),jamu-bot) -d

down: ## Stop and remove containers (use 'make down SERVICE=jamu-bot-dev' for dev only)
	docker compose stop $(or $(SERVICE),jamu-bot)
	docker compose rm -f $(or $(SERVICE),jamu-bot)

restart: ## Restart the bot (use 'make restart SERVICE=jamu-bot-dev' for dev mode)
	docker compose restart $(or $(SERVICE),jamu-bot)

logs: ## Show Docker container logs (use 'make logs SERVICE=jamu-bot-dev' for dev mode)
	docker compose logs -f $(or $(SERVICE),jamu-bot)

status: ## Show container status
	docker compose ps

# Utility commands
clean: ## Clean up cache files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true

env-example: ## Copy .env.example to .env
	cp .env.example .env
	@echo "Created .env file. Please edit it with your Discord token."

# Development workflow
dev-setup: install-dev env-example ## Complete development setup
	@echo "Development setup complete!"
	@echo "1. Edit .env with your Discord token"
	@echo "2. Run 'make run-dev' to start the bot"

pre-commit: check ## Run pre-commit checks (lint + type-check)
	@echo "All checks passed! ✅"

# Database migration targets
migrate: ## Run Alembic database migrations
	uv run alembic upgrade head

migrate-dev: ## Run Alembic database migrations for dev environment
	uv run alembic --dev upgrade head

migration: ## Create a new migration (usage: make migration MESSAGE="description")
	uv run alembic revision --autogenerate -m "$(MESSAGE)"

migration-dev: ## Create a new migration in dev mode
	uv run alembic --dev revision --autogenerate -m "$(MESSAGE)"

migration-history: ## Show migration history
	uv run alembic history

migration-current: ## Show current migration
	uv run alembic current
