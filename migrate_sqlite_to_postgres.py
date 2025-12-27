#!/usr/bin/env python3
"""Migration utility for transferring data from SQLite to PostgreSQL."""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import config
from models import Base, Quote


class SQLiteToPostgresMigrator:
    """Handles migration from SQLite to PostgreSQL database."""

    def __init__(self, source_db_path: Path, target_db_url: str):
        self.source_db_path = source_db_path
        self.target_db_url = target_db_url

        # Create engines for both databases
        source_url = f"sqlite+aiosqlite:///{source_db_path}"
        self.source_engine = create_async_engine(source_url, echo=False)
        self.target_engine = create_async_engine(target_db_url, echo=False)

        self.source_session = async_sessionmaker(
            self.source_engine, class_=AsyncSession, expire_on_commit=False
        )
        self.target_session = async_sessionmaker(
            self.target_engine, class_=AsyncSession, expire_on_commit=False
        )

    async def migrate(self, dry_run: bool = False, batch_size: int = 1000) -> None:
        """Execute the migration process."""
        print(f"Starting migration from SQLite to PostgreSQL...")
        print(f"Source: {self.source_db_path}")
        print(f"Target: {self.target_db_url}")
        print()

        if dry_run:
            print("=" * 60)
            print("DRY RUN MODE - No changes will be made to target database")
            print("=" * 60)
            print()

        # Verify source database exists
        if not self.source_db_path.exists():
            print(f"ERROR: Source database not found: {self.source_db_path}")
            return

        # Verify target database schema exists
        if not dry_run:
            await self._verify_target_schema()

        # Get quote count from source
        async with self.source_session() as source:
            result = await source.execute(select(Quote))
            source_quotes = result.scalars().all()
            source_count = len(source_quotes)

        if source_count == 0:
            print("No quotes found in source database. Nothing to migrate.")
            return

        print(f"Found {source_count} quotes in source database")
        print()

        # Get existing quote count in target
        async with self.target_session() as target:
            result = await target.execute(select(Quote))
            target_quotes = result.scalars().all()
            target_count = len(target_quotes)

        print(f"Target database currently has {target_count} quotes")
        print()

        # Migrate data in batches
        imported_count = 0
        skipped_count = 0

        for i in range(0, source_count, batch_size):
            batch = source_quotes[i : i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (source_count + batch_size - 1) // batch_size

            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} quotes)...")

            batch_imported, batch_skipped = await self._migrate_batch(
                batch, dry_run=dry_run
            )
            imported_count += batch_imported
            skipped_count += batch_skipped

        print()
        print("=" * 60)
        print("Migration Summary")
        print("=" * 60)
        print(f"Total quotes in source:     {source_count}")
        print(f"Quotes imported:            {imported_count}")
        print(f"Quotes skipped (duplicates): {skipped_count}")
        print(f"Expected final count:       {target_count + imported_count}")
        print()

        if not dry_run:
            # Verify final count
            async with self.target_session() as target:
                result = await target.execute(select(Quote))
                final_count = len(result.scalars().all())

            print(f"Actual final count:         {final_count}")

            if final_count == target_count + imported_count:
                print()
                print("✓ Migration completed successfully!")
            else:
                print()
                print("⚠ Warning: Final count doesn't match expected count")
        else:
            print("DRY RUN - No actual changes were made")

    async def _verify_target_schema(self) -> None:
        """Verify that the target database has the correct schema."""
        print("Verifying target database schema...")

        async with self.target_engine.begin() as conn:
            # Check if quotes table exists
            result = await conn.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'quotes'
                    )
                """)
            )
            table_exists = result.scalar()

            if not table_exists:
                print("Target database schema not found. Creating tables...")
                await conn.run_sync(Base.metadata.create_all)
                print("✓ Schema created successfully")
            else:
                print("✓ Target database schema verified")
        print()

    async def _migrate_batch(
        self, quotes: list[Quote], dry_run: bool = False
    ) -> tuple[int, int]:
        """Migrate a batch of quotes to PostgreSQL."""
        imported_count = 0
        skipped_count = 0

        if dry_run:
            for quote in quotes:
                print(f"  Would import: [{quote.author}] {quote.content[:50]}...")
                imported_count += 1
            return imported_count, skipped_count

        async with self.target_session() as target:
            try:
                for quote in quotes:
                    # Check if quote already exists (by content, author, and guild_id)
                    result = await target.execute(
                        select(Quote).where(
                            Quote.content == quote.content,
                            Quote.author == quote.author,
                            Quote.guild_id == quote.guild_id,
                        )
                    )
                    existing = result.scalar_one_or_none()

                    if existing:
                        skipped_count += 1
                        continue

                    # Create new quote in target database
                    new_quote = Quote(
                        content=quote.content,
                        author=quote.author,
                        added_by=quote.added_by,
                        guild_id=quote.guild_id,
                        channel_id=quote.channel_id,
                        created_at=quote.created_at,
                        original_timestamp=quote.original_timestamp,
                    )
                    target.add(new_quote)
                    imported_count += 1

                # Commit the batch
                await target.commit()
                print(f"  ✓ Imported {imported_count} quotes, skipped {skipped_count} duplicates")

            except Exception as e:
                await target.rollback()
                print(f"  ✗ Error migrating batch: {e}")
                raise

        return imported_count, skipped_count

    async def close(self) -> None:
        """Clean up resources."""
        await self.source_engine.dispose()
        await self.target_engine.dispose()


async def main() -> None:
    """Main entry point for the migration utility."""
    parser = argparse.ArgumentParser(
        description="Migrate quotes from SQLite to PostgreSQL"
    )
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Path to the source SQLite database file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--target",
        type=str,
        help="Target PostgreSQL database URL (defaults to config.database_url)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Number of quotes to process per batch (default: 1000)",
    )

    args = parser.parse_args()

    # Use provided target DB or default to current config
    target_db_url = args.target or config.database_url

    print()
    print("=" * 60)
    print("SQLite to PostgreSQL Migration Utility")
    print("=" * 60)
    print()

    if not args.dry_run:
        print("⚠ WARNING: This will modify the target PostgreSQL database")
        print()
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() not in ("yes", "y"):
            print("Migration cancelled.")
            return
        print()

    migrator = SQLiteToPostgresMigrator(args.source, target_db_url)
    try:
        await migrator.migrate(dry_run=args.dry_run, batch_size=args.batch_size)
    except Exception as e:
        print()
        print(f"✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await migrator.close()


if __name__ == "__main__":
    asyncio.run(main())
