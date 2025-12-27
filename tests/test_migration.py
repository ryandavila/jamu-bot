"""Tests for SQLite to PostgreSQL migration script."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from bot.models import Base, Quote

# Import the migration class
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from migrate_sqlite_to_postgres import SQLiteToPostgresMigrator


@pytest.fixture
async def source_sqlite_db():
    """Create a source SQLite database with test data."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create engine and populate with test data
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Add test quotes
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        quotes = [
            Quote(
                content="Test quote 1",
                author="Author 1",
                added_by=111,
                guild_id=1,
                channel_id=10,
                created_at=datetime.now(UTC),
            ),
            Quote(
                content="Test quote 2",
                author="Author 2",
                added_by=222,
                guild_id=1,
                channel_id=20,
                created_at=datetime.now(UTC),
            ),
            Quote(
                content="Test quote 3",
                author="Author 1",
                added_by=333,
                guild_id=2,
                channel_id=30,
                created_at=datetime.now(UTC),
                original_timestamp=datetime.now(UTC),
            ),
        ]
        for quote in quotes:
            session.add(quote)
        await session.commit()

    await engine.dispose()

    yield db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


@pytest.fixture
async def target_sqlite_db():
    """Create an empty target SQLite database (for testing migration logic)."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    # Create empty database with schema
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

    target_url = f"sqlite+aiosqlite:///{db_path}"

    yield target_url, db_path

    # Cleanup
    if db_path.exists():
        db_path.unlink()


class TestMigration:
    """Test the SQLite to PostgreSQL migration script."""

    @pytest.mark.asyncio
    async def test_migration_basic(self, source_sqlite_db, target_sqlite_db):
        """Test basic migration from SQLite to SQLite (simulating PostgreSQL)."""
        target_url, target_path = target_sqlite_db

        migrator = SQLiteToPostgresMigrator(source_sqlite_db, target_url)

        try:
            await migrator.migrate(dry_run=False)

            # Verify data was migrated
            engine = create_async_engine(target_url, echo=False)
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session() as session:
                result = await session.execute(select(Quote))
                quotes = result.scalars().all()

                assert len(quotes) == 3
                assert quotes[0].content == "Test quote 1"
                assert quotes[1].author == "Author 2"
                assert quotes[2].original_timestamp is not None

            await engine.dispose()
        finally:
            await migrator.close()

    @pytest.mark.asyncio
    async def test_migration_dry_run(self, source_sqlite_db, target_sqlite_db):
        """Test dry run mode doesn't modify target database."""
        target_url, target_path = target_sqlite_db

        migrator = SQLiteToPostgresMigrator(source_sqlite_db, target_url)

        try:
            await migrator.migrate(dry_run=True)

            # Verify target database is still empty
            engine = create_async_engine(target_url, echo=False)
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session() as session:
                result = await session.execute(select(Quote))
                quotes = result.scalars().all()

                assert len(quotes) == 0

            await engine.dispose()
        finally:
            await migrator.close()

    @pytest.mark.asyncio
    async def test_migration_duplicate_detection(
        self, source_sqlite_db, target_sqlite_db
    ):
        """Test that duplicate quotes are skipped."""
        target_url, target_path = target_sqlite_db

        # Pre-populate target with one quote
        engine = create_async_engine(target_url, echo=False)
        async_session = sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            duplicate = Quote(
                content="Test quote 1",  # Same as source
                author="Author 1",
                added_by=111,
                guild_id=1,
                channel_id=10,
                created_at=datetime.now(UTC),
            )
            session.add(duplicate)
            await session.commit()

        await engine.dispose()

        # Run migration
        migrator = SQLiteToPostgresMigrator(source_sqlite_db, target_url)

        try:
            await migrator.migrate(dry_run=False)

            # Verify only 3 quotes total (1 duplicate skipped)
            engine = create_async_engine(target_url, echo=False)
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session() as session:
                result = await session.execute(select(Quote))
                quotes = result.scalars().all()

                # Should have 3 total: 1 pre-existing + 2 new (1 duplicate skipped)
                assert len(quotes) == 3

            await engine.dispose()
        finally:
            await migrator.close()

    @pytest.mark.asyncio
    async def test_migration_preserves_timestamps(
        self, source_sqlite_db, target_sqlite_db
    ):
        """Test that timestamps are preserved during migration."""
        target_url, target_path = target_sqlite_db

        migrator = SQLiteToPostgresMigrator(source_sqlite_db, target_url)

        try:
            await migrator.migrate(dry_run=False)

            # Get original timestamps from source
            source_engine = create_async_engine(
                f"sqlite+aiosqlite:///{source_sqlite_db}", echo=False
            )
            source_session = sessionmaker(
                source_engine, class_=AsyncSession, expire_on_commit=False
            )

            async with source_session() as session:
                result = await session.execute(select(Quote).order_by(Quote.id))
                source_quotes = result.scalars().all()
                source_timestamps = [
                    (q.created_at, q.original_timestamp) for q in source_quotes
                ]

            await source_engine.dispose()

            # Compare with target timestamps
            target_engine = create_async_engine(target_url, echo=False)
            target_session = sessionmaker(
                target_engine, class_=AsyncSession, expire_on_commit=False
            )

            async with target_session() as session:
                result = await session.execute(select(Quote).order_by(Quote.id))
                target_quotes = result.scalars().all()

                for i, quote in enumerate(target_quotes):
                    assert quote.created_at == source_timestamps[i][0]
                    assert quote.original_timestamp == source_timestamps[i][1]

            await target_engine.dispose()
        finally:
            await migrator.close()

    @pytest.mark.asyncio
    async def test_migration_batch_processing(self, target_sqlite_db):
        """Test migration with custom batch size."""
        # Create source with more quotes
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            source_path = Path(f.name)

        engine = create_async_engine(f"sqlite+aiosqlite:///{source_path}", echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as session:
            # Add 10 quotes
            for i in range(10):
                quote = Quote(
                    content=f"Quote {i}",
                    author=f"Author {i}",
                    added_by=i,
                    guild_id=1,
                    channel_id=1,
                    created_at=datetime.now(UTC),
                )
                session.add(quote)
            await session.commit()

        await engine.dispose()

        target_url, target_path = target_sqlite_db

        migrator = SQLiteToPostgresMigrator(source_path, target_url)

        try:
            # Use small batch size to test batching
            await migrator.migrate(dry_run=False, batch_size=3)

            # Verify all 10 quotes were migrated
            engine = create_async_engine(target_url, echo=False)
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session() as session:
                result = await session.execute(select(Quote))
                quotes = result.scalars().all()

                assert len(quotes) == 10

            await engine.dispose()
        finally:
            await migrator.close()
            if source_path.exists():
                source_path.unlink()

    @pytest.mark.asyncio
    async def test_migration_empty_source(self, target_sqlite_db):
        """Test migration with empty source database."""
        # Create empty source
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            source_path = Path(f.name)

        engine = create_async_engine(f"sqlite+aiosqlite:///{source_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

        target_url, target_path = target_sqlite_db

        migrator = SQLiteToPostgresMigrator(source_path, target_url)

        try:
            await migrator.migrate(dry_run=False)

            # Should complete without error and target should be empty
            engine = create_async_engine(target_url, echo=False)
            async_session = sessionmaker(
                engine, class_=AsyncSession, expire_on_commit=False
            )

            async with async_session() as session:
                result = await session.execute(select(Quote))
                quotes = result.scalars().all()

                assert len(quotes) == 0

            await engine.dispose()
        finally:
            await migrator.close()
            if source_path.exists():
                source_path.unlink()
