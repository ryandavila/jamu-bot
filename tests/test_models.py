"""Tests for SQLAlchemy models."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from bot.models import Quote


class TestQuote:
    @pytest.mark.asyncio
    async def test_quote_creation(self, test_db_session):
        quote = Quote(
            content="Test quote content",
            author="Test Author",
            added_by=12345,
            guild_id=67890,
            channel_id=11111,
        )

        test_db_session.add(quote)
        await test_db_session.commit()

        assert quote.id is not None
        assert quote.content == "Test quote content"
        assert quote.author == "Test Author"
        assert quote.added_by == 12345
        assert quote.guild_id == 67890
        assert quote.channel_id == 11111
        assert isinstance(quote.created_at, datetime)
        assert quote.original_timestamp is None

    @pytest.mark.asyncio
    async def test_quote_with_original_timestamp(self, test_db_session):
        original_time = datetime.now(UTC)

        quote = Quote(
            content="Quoted message",
            author="Message Author",
            added_by=12345,
            guild_id=67890,
            channel_id=11111,
            original_timestamp=original_time,
        )

        test_db_session.add(quote)
        await test_db_session.commit()

        assert quote.original_timestamp == original_time
        assert quote.created_at != original_time  # Should be set automatically

    @pytest.mark.asyncio
    async def test_quote_default_channel_id(self, test_db_session):
        quote = Quote(
            content="Test content",
            author="Test Author",
            added_by=12345,
            guild_id=67890,
            # channel_id not provided
        )

        test_db_session.add(quote)
        await test_db_session.commit()

        assert quote.channel_id == 0

    @pytest.mark.asyncio
    async def test_quote_repr(self, test_db_session):
        quote = Quote(
            content="This is a long quote content that should be truncated in the repr method",
            author="Test Author",
            added_by=12345,
            guild_id=67890,
            channel_id=11111,
        )

        test_db_session.add(quote)
        await test_db_session.commit()

        repr_str = repr(quote)
        assert f"Quote(id={quote.id}" in repr_str
        assert "author='Test Author'" in repr_str
        # The content should be truncated to 50 characters plus "..."
        # Check that the content is truncated (contains ...)
        assert "..." in repr_str
        assert "This is a long quote content that should be trunca" in repr_str

    @pytest.mark.asyncio
    async def test_quote_query_by_guild(self, test_db_session):
        # Create quotes for different guilds
        quote1 = Quote(
            content="Guild 1 quote",
            author="Author 1",
            added_by=12345,
            guild_id=111,
            channel_id=222,
        )

        quote2 = Quote(
            content="Guild 2 quote",
            author="Author 2",
            added_by=12345,
            guild_id=333,
            channel_id=444,
        )

        test_db_session.add_all([quote1, quote2])
        await test_db_session.commit()

        # Query quotes for guild 111
        result = await test_db_session.execute(
            select(Quote).where(Quote.guild_id == 111)
        )
        guild_quotes = result.scalars().all()

        assert len(guild_quotes) == 1
        assert guild_quotes[0].content == "Guild 1 quote"
        assert guild_quotes[0].guild_id == 111

    @pytest.mark.asyncio
    async def test_quote_query_by_author(self, test_db_session):
        quotes = [
            Quote(
                content="First quote",
                author="John Doe",
                added_by=12345,
                guild_id=111,
                channel_id=222,
            ),
            Quote(
                content="Second quote",
                author="John Doe",
                added_by=12345,
                guild_id=111,
                channel_id=222,
            ),
            Quote(
                content="Third quote",
                author="Jane Smith",
                added_by=12345,
                guild_id=111,
                channel_id=222,
            ),
        ]

        test_db_session.add_all(quotes)
        await test_db_session.commit()

        # Query quotes by John Doe
        result = await test_db_session.execute(
            select(Quote).where(Quote.author.like("%John Doe%"))
        )
        john_quotes = result.scalars().all()

        assert len(john_quotes) == 2
        assert all(quote.author == "John Doe" for quote in john_quotes)

    @pytest.mark.asyncio
    async def test_quote_query_by_content(self, test_db_session):
        quotes = [
            Quote(
                content="Hello world from Python",
                author="Developer",
                added_by=12345,
                guild_id=111,
                channel_id=222,
            ),
            Quote(
                content="Goodbye world",
                author="Developer",
                added_by=12345,
                guild_id=111,
                channel_id=222,
            ),
            Quote(
                content="Testing quotes",
                author="Tester",
                added_by=12345,
                guild_id=111,
                channel_id=222,
            ),
        ]

        test_db_session.add_all(quotes)
        await test_db_session.commit()

        # Search for quotes containing "world"
        result = await test_db_session.execute(
            select(Quote).where(Quote.content.like("%world%"))
        )
        world_quotes = result.scalars().all()

        assert len(world_quotes) == 2
        assert all("world" in quote.content for quote in world_quotes)

    @pytest.mark.asyncio
    async def test_quote_required_fields(self, test_db_session):
        with pytest.raises(IntegrityError):
            incomplete_quote = Quote(
                # Missing required fields
                content="Test content"
                # author, added_by, guild_id missing
            )
            test_db_session.add(incomplete_quote)
            await test_db_session.commit()
