#!/usr/bin/env python3
"""Database migration utility for importing from old SQLite databases."""

import argparse
import asyncio
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import config
from models import Base, Quote


class DatabaseMigrator:
    """Handles migration from old SQLite database to current schema."""

    def __init__(self, source_db_path: Path, target_db_url: str):
        self.source_db_path = source_db_path
        self.target_db_url = target_db_url
        self.engine = create_async_engine(target_db_url)
        self.async_session = async_sessionmaker(self.engine, class_=AsyncSession)

    async def migrate(self, dry_run: bool = False) -> None:
        """Execute the migration process."""
        print(f"Starting migration from {self.source_db_path} to current database...")

        if dry_run:
            print("DRY RUN MODE - No changes will be made")

        # Analyze source database
        source_data = self._analyze_source_db()
        if not source_data:
            print("No data found in source database or incompatible schema")
            return

        print(f"Found {len(source_data)} quotes in source database")

        # Create tables if needed (in case of fresh database)
        if not dry_run:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

        # Import data
        async with self.async_session() as session:
            imported_count = await self._import_quotes(session, source_data, dry_run)
            if not dry_run:
                await session.commit()

        print(f"Migration completed. Imported {imported_count} quotes.")

    def _analyze_source_db(self) -> list[dict[str, Any]]:
        """Analyze the source database and extract quote data."""
        if not self.source_db_path.exists():
            print(f"Source database not found: {self.source_db_path}")
            return []

        try:
            conn = sqlite3.connect(self.source_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Check if quotes table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='quotes'"
            )
            if not cursor.fetchone():
                print("No 'quotes' table found in source database")
                return []

            # Get table schema
            cursor.execute("PRAGMA table_info(quotes)")
            columns = {row["name"]: row for row in cursor.fetchall()}
            print(f"Source table columns: {list(columns.keys())}")

            # Extract all quotes
            cursor.execute("SELECT * FROM quotes")
            rows = cursor.fetchall()

            quotes = []
            for row in rows:
                quote_data = dict(row)

                # Map old schema to new schema if needed
                quote_data = self._map_quote_data(quote_data, columns)
                if quote_data:  # Only add if mapping succeeded
                    quotes.append(quote_data)

            conn.close()
            return quotes

        except Exception as e:
            print(f"Error analyzing source database: {e}")
            return []

    def _map_quote_data(
        self, row_data: dict[str, Any], columns: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Map old schema data to current schema."""
        try:
            # Required fields in current schema
            required_fields = ["content", "author", "added_by", "guild_id"]

            # Check if all required fields exist
            for field in required_fields:
                if field not in row_data or row_data[field] is None:
                    print(
                        f"Skipping row due to missing required field '{field}': {row_data}"
                    )
                    return None

            # Build mapped data
            mapped = {
                "content": str(row_data["content"]),
                "author": str(row_data["author"]),
                "added_by": int(row_data["added_by"]),
                "guild_id": int(row_data["guild_id"]),
                "channel_id": int(
                    row_data.get("channel_id", 0)
                ),  # Default to 0 if missing
            }

            # Handle timestamps
            if "created_at" in row_data and row_data["created_at"]:
                try:
                    # Try to parse existing timestamp
                    if isinstance(row_data["created_at"], str):
                        # Parse ISO format or other common formats
                        created_at = datetime.fromisoformat(
                            row_data["created_at"].replace("Z", "+00:00")
                        )
                    else:
                        # Assume it's already a datetime or timestamp
                        created_at = datetime.fromtimestamp(
                            float(row_data["created_at"]), tz=UTC
                        )
                    mapped["created_at"] = created_at
                except (ValueError, TypeError) as e:
                    print(
                        f"Warning: Could not parse created_at '{row_data['created_at']}': {e}"
                    )
                    mapped["created_at"] = datetime.now(UTC)
            else:
                mapped["created_at"] = datetime.now(UTC)

            # Handle original_timestamp if present
            if "original_timestamp" in row_data and row_data["original_timestamp"]:
                try:
                    if isinstance(row_data["original_timestamp"], str):
                        original_timestamp = datetime.fromisoformat(
                            row_data["original_timestamp"].replace("Z", "+00:00")
                        )
                    else:
                        original_timestamp = datetime.fromtimestamp(
                            float(row_data["original_timestamp"]), tz=UTC
                        )
                    mapped["original_timestamp"] = original_timestamp
                except (ValueError, TypeError):
                    mapped["original_timestamp"] = None
            else:
                mapped["original_timestamp"] = None

            return mapped

        except Exception as e:
            print(f"Error mapping row data: {e}")
            print(f"Row data: {row_data}")
            return None

    async def _import_quotes(
        self, session: AsyncSession, quotes_data: list[dict[str, Any]], dry_run: bool
    ) -> int:
        """Import quotes into the target database."""
        imported_count = 0

        for quote_data in quotes_data:
            try:
                if dry_run:
                    print(
                        f"Would import: {quote_data['author']}: {quote_data['content'][:50]}..."
                    )
                    imported_count += 1
                    continue

                # Check if quote already exists (to avoid duplicates)
                existing = await session.execute(
                    text("""
                        SELECT id FROM quotes
                        WHERE content = :content
                        AND author = :author
                        AND guild_id = :guild_id
                    """),
                    {
                        "content": quote_data["content"],
                        "author": quote_data["author"],
                        "guild_id": quote_data["guild_id"],
                    },
                )

                if existing.fetchone():
                    print(
                        f"Quote already exists, skipping: {quote_data['author']}: {quote_data['content'][:50]}..."
                    )
                    continue

                # Create new quote
                quote = Quote(
                    content=quote_data["content"],
                    author=quote_data["author"],
                    added_by=quote_data["added_by"],
                    guild_id=quote_data["guild_id"],
                    channel_id=quote_data["channel_id"],
                    created_at=quote_data["created_at"],
                    original_timestamp=quote_data["original_timestamp"],
                )

                session.add(quote)
                imported_count += 1
                print(
                    f"Imported: {quote_data['author']}: {quote_data['content'][:50]}..."
                )

            except Exception as e:
                print(f"Error importing quote: {e}")
                print(f"Quote data: {quote_data}")
                continue

        return imported_count

    async def close(self) -> None:
        """Clean up resources."""
        await self.engine.dispose()


async def main() -> None:
    """Main entry point for the migration utility."""
    parser = argparse.ArgumentParser(
        description="Migrate quotes from old SQLite database"
    )
    parser.add_argument(
        "source_db", type=Path, help="Path to the source SQLite database file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--target-db", type=str, help="Target database URL (defaults to current config)"
    )

    args = parser.parse_args()

    # Use provided target DB or default to current config
    target_db_url = args.target_db or config.database_url

    print("Migration utility starting...")
    print(f"Source: {args.source_db}")
    print(f"Target: {target_db_url}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE MIGRATION'}")
    print()

    if not args.dry_run:
        confirm = input("Are you sure you want to proceed with the migration? (y/N): ")
        if confirm.lower() != "y":
            print("Migration cancelled.")
            return

    migrator = DatabaseMigrator(args.source_db, target_db_url)
    try:
        await migrator.migrate(dry_run=args.dry_run)
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())
