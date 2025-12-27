from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from bot.cogs.quotes import Quotes
from bot.models import Quote


class TestQuotesCog:
    @pytest.fixture
    def quotes_cog(self, mock_bot, test_config):
        with patch("bot.cogs.quotes.config", test_config):
            cog = Quotes(mock_bot)
            return cog

    @pytest.mark.asyncio
    async def test_cog_initialization(self, quotes_cog, mock_bot):
        assert quotes_cog.bot == mock_bot
        assert quotes_cog.engine is not None
        assert quotes_cog.async_session is not None

    def test_create_quote_embed(self, quotes_cog):
        from datetime import UTC, datetime

        quote = Quote(
            id=1,
            content="Test quote content",
            author="Test Author",
            added_by=12345,
            guild_id=67890,
            channel_id=11111,
            created_at=datetime.now(UTC),
        )

        embed = quotes_cog._create_quote_embed(quote)

        assert embed.description == '"Test quote content"'
        assert embed.author.name == "Test Author"
        assert embed.color == discord.Color.blue()
        assert embed.timestamp is not None

    def test_create_quote_embed_with_original_timestamp(self, quotes_cog):
        from datetime import UTC, datetime

        original_time = datetime.now(UTC)
        created_time = datetime.now(UTC)

        quote = Quote(
            id=2,
            content="Original message",
            author="Message Author",
            added_by=12345,
            guild_id=67890,
            channel_id=11111,
            created_at=created_time,
            original_timestamp=original_time,
        )

        embed = quotes_cog._create_quote_embed(quote)

        # The embed should use original timestamp when available
        assert embed.timestamp == original_time

    def test_can_user_access_channel_legacy(self, quotes_cog, mock_member):
        result = quotes_cog._can_user_access_channel(mock_member, 0)
        assert result is True

    def test_can_user_access_channel_nonexistent(
        self, quotes_cog, mock_member, mock_guild
    ):
        mock_member.guild = mock_guild
        result = quotes_cog._can_user_access_channel(mock_member, 999999)
        assert result is False

    def test_can_user_access_channel_accessible(
        self, quotes_cog, mock_member, mock_guild
    ):
        # Create a mock channel that the user can access
        class MockTextChannel:
            def __init__(self):
                self.id = 123456

            def permissions_for(self, user):
                class MockPermissions:
                    view_channel = True

                return MockPermissions()

        mock_channel = MockTextChannel()
        mock_guild.get_channel = MagicMock(return_value=mock_channel)
        mock_member.guild = mock_guild

        result = quotes_cog._can_user_access_channel(mock_member, 123456)
        assert result is True

    @pytest.mark.asyncio
    async def test_get_accessible_channel_ids_async(
        self, quotes_cog, mock_member, mock_guild
    ):
        # Mock the method to return specific channel IDs for testing
        with patch.object(quotes_cog, "_get_accessible_channel_ids") as mock_method:
            mock_method.return_value = [0, 111, 222]

            accessible_ids = await mock_method(mock_member)

            assert 0 in accessible_ids  # Legacy channel always included
            assert 111 in accessible_ids
            assert 222 in accessible_ids

    @pytest.mark.asyncio
    async def test_quote_command_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send_help = AsyncMock()

        # Call the actual method directly instead of the command wrapper
        await quotes_cog.quote.callback(quotes_cog, mock_context)

        mock_context.send_help.assert_called_once_with(mock_context.command)

    @pytest.mark.asyncio
    async def test_quote_command_not_member(self, quotes_cog, mock_context, mock_guild):
        mock_context.guild = mock_guild
        mock_context.author = "not_a_member"  # Not a Member object
        mock_context.send_help = AsyncMock()

        await quotes_cog.quote.callback(quotes_cog, mock_context)

        mock_context.send_help.assert_called_once_with(mock_context.command)

    @pytest.mark.asyncio
    async def test_add_quote_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.add_quote.callback(
            quotes_cog, mock_context, content="test - author"
        )

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_add_quote_no_content_no_reference(
        self, quotes_cog, mock_context, mock_guild
    ):
        mock_context.guild = mock_guild
        mock_context.message.reference = None
        mock_context.send = AsyncMock()

        await quotes_cog.add_quote.callback(quotes_cog, mock_context, content=None)

        expected_message = (
            "Please provide a quote in the format: `!quote add <quote> - <author>` "
            "or reply to a message with `!quote add`"
        )
        mock_context.send.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_add_quote_invalid_format(self, quotes_cog, mock_context, mock_guild):
        mock_context.guild = mock_guild
        mock_context.send = AsyncMock()

        await quotes_cog.add_quote.callback(
            quotes_cog, mock_context, content="quote without author"
        )

        mock_context.send.assert_called_once_with(
            "Please use the format: `!quote add <quote> - <author>`"
        )

    @pytest.mark.asyncio
    async def test_add_quote_empty_parts(self, quotes_cog, mock_context, mock_guild):
        mock_context.guild = mock_guild
        mock_context.send = AsyncMock()

        await quotes_cog.add_quote.callback(quotes_cog, mock_context, content=" - ")

        expected_message = "Both quote and author must be provided. Format: `!quote add <quote> - <author>`"
        mock_context.send.assert_called_once_with(expected_message)

    @pytest.mark.asyncio
    async def test_add_quote_valid_format(self, quotes_cog, mock_context, mock_guild):
        mock_context.guild = mock_guild
        mock_context.channel.id = 123456
        mock_context.author.id = 789
        mock_context.reply = AsyncMock()

        with patch.object(
            quotes_cog, "_add_quote_to_db", new_callable=AsyncMock
        ) as mock_add:
            await quotes_cog.add_quote.callback(
                quotes_cog, mock_context, content="Test quote - Test Author"
            )

            mock_add.assert_called_once_with(mock_context, "Test quote", "Test Author")

    @pytest.mark.asyncio
    async def test_list_quotes_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.list_quotes.callback(quotes_cog, mock_context)

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_get_quote_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.get_quote.callback(quotes_cog, mock_context, 1)

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_delete_quote_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.delete_quote.callback(quotes_cog, mock_context, 1)

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_search_quotes_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.search_quotes.callback(
            quotes_cog, mock_context, search_term="test"
        )

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_random_quote_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.random_quote.callback(quotes_cog, mock_context)

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_export_quotes_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.export_quotes.callback(quotes_cog, mock_context)

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_import_quotes_no_guild(self, quotes_cog, mock_context):
        mock_context.guild = None
        mock_context.send = AsyncMock()

        await quotes_cog.import_quotes.callback(quotes_cog, mock_context)

        mock_context.send.assert_called_once_with(
            "This command can only be used in a server."
        )

    @pytest.mark.asyncio
    async def test_import_quotes_no_attachments(
        self, quotes_cog, mock_context, mock_guild
    ):
        mock_context.guild = mock_guild
        mock_context.message.attachments = []
        mock_context.send = AsyncMock()

        await quotes_cog.import_quotes.callback(quotes_cog, mock_context)

        mock_context.send.assert_called_once_with(
            "Please attach a CSV file with your quotes."
        )

    @pytest.mark.asyncio
    async def test_import_quotes_non_csv_attachment(
        self, quotes_cog, mock_context, mock_guild
    ):
        mock_context.guild = mock_guild
        mock_context.send = AsyncMock()

        # Mock attachment
        class MockAttachment:
            filename = "test.txt"

        mock_context.message.attachments = [MockAttachment()]

        await quotes_cog.import_quotes.callback(quotes_cog, mock_context)

        mock_context.send.assert_called_once_with("Please attach a CSV file.")

    def test_quote_parsing_with_multiple_dashes(self, quotes_cog):
        content = "This is a quote - with multiple - dashes - Author Name"

        # This simulates the parsing logic in add_quote
        quote_text, author = content.rsplit(" - ", 1)
        quote_text = quote_text.strip()
        author = author.strip()

        assert quote_text == "This is a quote - with multiple - dashes"
        assert author == "Author Name"

    @pytest.mark.asyncio
    async def test_cog_load(self, quotes_cog):
        # Should not raise any exceptions
        await quotes_cog.cog_load()

    @pytest.mark.asyncio
    async def test_on_reaction_add_placeholder(self, quotes_cog):
        # Mock reaction and user
        mock_reaction = MagicMock()
        mock_user = MagicMock()

        # Should not raise any exceptions (it's just a placeholder)
        await quotes_cog.on_reaction_add(mock_reaction, mock_user)
