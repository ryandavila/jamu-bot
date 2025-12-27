#!/bin/bash
# Production SQLite to PostgreSQL Migration Script
# Run this on your production server after deploying the new PostgreSQL setup

set -e  # Exit on any error

echo "=========================================="
echo "Jamu Bot: SQLite to PostgreSQL Migration"
echo "=========================================="
echo ""

# Step 1: Backup SQLite database
echo "Step 1: Backing up SQLite database..."
if [ -f data/quotes.db ]; then
    BACKUP_FILE="data/quotes.db.backup-$(date +%Y%m%d-%H%M%S)"
    cp data/quotes.db "$BACKUP_FILE"
    echo "✓ Backup created: $BACKUP_FILE"
else
    echo "⚠ Warning: No SQLite database found at data/quotes.db"
    echo "  If you don't have existing data, you can skip this migration."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Migration cancelled."
        exit 0
    fi
fi
echo ""

# Step 2: Start PostgreSQL
echo "Step 2: Starting PostgreSQL container..."
docker compose up postgres -d
echo "✓ PostgreSQL container started"
echo ""

# Step 3: Wait for PostgreSQL to be ready
echo "Step 3: Waiting for PostgreSQL to be healthy..."
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U jamu_bot -q; then
        echo "✓ PostgreSQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ PostgreSQL failed to start after 30 seconds"
        exit 1
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done
echo ""

# Step 4: Run Alembic migrations
echo "Step 4: Creating database schema..."
docker compose run --rm jamu-bot uv run alembic upgrade head
echo "✓ Database schema created"
echo ""

# Step 5: Migrate data (if SQLite database exists)
if [ -f data/quotes.db ]; then
    echo "Step 5: Migrating data from SQLite to PostgreSQL..."
    echo ""
    echo "Running dry-run first..."
    docker compose run --rm jamu-bot uv run python migrate_sqlite_to_postgres.py \
        --source /app/data/quotes.db --dry-run
    echo ""

    read -p "Does the dry-run look correct? Proceed with migration? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Running actual migration..."
        docker compose run --rm jamu-bot uv run python migrate_sqlite_to_postgres.py \
            --source /app/data/quotes.db
        echo "✓ Data migration completed"
    else
        echo "Migration skipped. You can run it manually later with:"
        echo "  docker compose run --rm jamu-bot uv run python migrate_sqlite_to_postgres.py --source /app/data/quotes.db"
    fi
else
    echo "Step 5: Skipping data migration (no SQLite database found)"
fi
echo ""

# Step 6: Verify migration
echo "Step 6: Verifying migration..."
QUOTE_COUNT=$(docker compose exec -T postgres psql -U jamu_bot -d jamu_quotes -t -c "SELECT COUNT(*) FROM quotes;")
echo "Total quotes in PostgreSQL: $QUOTE_COUNT"
echo ""

# Step 7: Start the bot
echo "Step 7: Starting the Discord bot..."
docker compose up jamu-bot -d
echo "✓ Bot started"
echo ""

echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Check bot logs: docker compose logs -f jamu-bot"
echo "  2. Test bot commands in Discord"
echo "  3. Keep SQLite backup for safety: $BACKUP_FILE"
echo ""
echo "Once you've verified everything works, you can:"
echo "  - Remove SQLite backups"
echo "  - Remove ./data volume mount from compose.yml (optional)"
echo "  - Remove aiosqlite from pyproject.toml dependencies"
echo "  - Remove migrate_sqlite_to_postgres.py script"
