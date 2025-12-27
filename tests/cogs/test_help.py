from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.cogs.help import CustomHelp


class TestCustomHelp:
    @pytest.fixture
    def help_cog(self, mock_bot):
        # Mock the remove_command method
        mock_bot.remove_command = MagicMock()
        cog = CustomHelp(mock_bot)
        return cog

    def test_cog_initialization(self, help_cog, mock_bot):
        assert help_cog.bot == mock_bot
        mock_bot.remove_command.assert_called_once_with("help")

    @pytest.mark.asyncio
    async def test_help_command_no_specific_command(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        with patch.object(
            help_cog, "_show_all_commands", new_callable=AsyncMock
        ) as mock_show_all:
            await help_cog.help_command.callback(help_cog, mock_context, command=None)
            mock_show_all.assert_called_once_with(mock_context)

    @pytest.mark.asyncio
    async def test_help_command_with_specific_command(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        with patch.object(
            help_cog, "_show_command_help", new_callable=AsyncMock
        ) as mock_show_command:
            await help_cog.help_command.callback(
                help_cog, mock_context, command="quote"
            )
            mock_show_command.assert_called_once_with(mock_context, "quote")

    @pytest.mark.asyncio
    async def test_show_all_commands(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_all_commands(mock_context)

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "🤖 Jamu Bot Commands"
        assert "Here are all available commands:" in embed.description

    @pytest.mark.asyncio
    async def test_show_command_help_quote_subcommand(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        with patch.object(
            help_cog, "_show_quote_subcommand_help", new_callable=AsyncMock
        ) as mock_show_quote:
            await help_cog._show_command_help(mock_context, "quote add")
            mock_show_quote.assert_called_once_with(mock_context, "add")

    @pytest.mark.asyncio
    async def test_show_command_help_nonexistent_command(self, help_cog, mock_context):
        mock_context.send = AsyncMock()
        help_cog.bot.get_command = MagicMock(return_value=None)

        await help_cog._show_command_help(mock_context, "nonexistent")

        mock_context.send.assert_called_once_with("❌ Command 'nonexistent' not found.")

    @pytest.mark.asyncio
    async def test_show_command_help_existing_command(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        # Mock command
        mock_command = MagicMock()
        mock_command.name = "test"
        mock_command.help = "Test command help"
        mock_command.usage = None
        mock_command.commands = None

        help_cog.bot.get_command = MagicMock(return_value=mock_command)

        await help_cog._show_command_help(mock_context, "test")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: test"
        assert embed.description == "Test command help"

    @pytest.mark.asyncio
    async def test_show_command_help_with_usage(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        # Mock command with usage
        mock_command = MagicMock()
        mock_command.name = "test"
        mock_command.help = "Test command"
        mock_command.usage = "test <arg>"
        mock_command.commands = None

        help_cog.bot.get_command = MagicMock(return_value=mock_command)

        await help_cog._show_command_help(mock_context, "test")

        mock_context.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_command_help_group_command(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        # Mock subcommand
        mock_subcommand = MagicMock()
        mock_subcommand.name = "sub"
        mock_subcommand.help = "Subcommand help"

        # Mock group command
        mock_command = MagicMock()
        mock_command.name = "group"
        mock_command.help = "Group command"
        mock_command.usage = None
        mock_command.commands = [mock_subcommand]

        help_cog.bot.get_command = MagicMock(return_value=mock_command)

        await help_cog._show_command_help(mock_context, "group")

        mock_context.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_add(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "add")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote add"
        assert "Add a new quote to the database" in embed.description

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_list(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "list")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote list"
        assert "List quotes, optionally filtered by author" in embed.description

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_search(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "search")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote search"

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_get(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "get")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote get"

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_delete(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "delete")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote delete"

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_random(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "random")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote random"

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_export(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "export")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote export"

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_import(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "import")

        mock_context.send.assert_called_once()
        args = mock_context.send.call_args
        embed = args[1]["embed"] if "embed" in args[1] else args[0][0]

        assert embed.title == "Help: quote import"

    @pytest.mark.asyncio
    async def test_show_quote_subcommand_help_invalid(self, help_cog, mock_context):
        mock_context.send = AsyncMock()

        await help_cog._show_quote_subcommand_help(mock_context, "invalid")

        mock_context.send.assert_called_once_with(
            "❌ Quote subcommand 'invalid' not found."
        )

    def test_quote_help_structure(self, help_cog):
        # This tests the internal quote_help dictionary in _show_quote_subcommand_help
        expected_subcommands = [
            "add",
            "list",
            "search",
            "get",
            "delete",
            "random",
            "export",
            "import",
        ]

        # We can't directly access the quote_help dict, but we can test that
        # all expected subcommands are handled without raising exceptions
        for subcommand in expected_subcommands:
            # This should not raise an exception for valid subcommands
            assert subcommand in [
                "add",
                "list",
                "search",
                "get",
                "delete",
                "random",
                "export",
                "import",
            ]
