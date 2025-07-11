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
check: lint type-check ## Run all code quality checks

lint: ## Run ruff linter
	uv run ruff check .

lint-fix: ## Run ruff linter with auto-fix
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
	docker compose build
	docker compose up $(or $(SERVICE),jamu-bot) -d

rebuild-full: ## Rebuild Docker image (clean build with cleanup) and start (use 'make rebuild-full SERVICE=jamu-bot-dev' for dev mode)
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
