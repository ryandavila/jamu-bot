"""Custom help command for better command discovery."""

import discord
from discord.ext import commands


class CustomHelp(commands.Cog):
    """Custom help command that shows all commands clearly."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Remove the default help command so we can replace it
        self.bot.remove_command("help")

    @commands.hybrid_command(name="help")  # type: ignore[arg-type]
    async def help_command(
        self, ctx: commands.Context[commands.Bot], *, command: str | None = None
    ) -> None:
        """Show all available commands or get help for a specific command."""
        try:
            if command:
                # Show help for a specific command
                await self._show_command_help(ctx, command)
            else:
                # Show all commands
                await self._show_all_commands(ctx)
        except Exception as e:
            print(f"Error in custom help command: {e}")
            await ctx.send(f"❌ Error showing help: {e}")

    async def _show_all_commands(self, ctx: commands.Context[commands.Bot]) -> None:
        """Show all available commands organized by category."""
        embed = discord.Embed(
            title="🤖 Jamu Bot Commands",
            description="Here are all available commands:",
            color=discord.Color.blue(),
        )

        # Check if user is admin
        is_admin = False
        if ctx.guild and hasattr(ctx.author, "guild_permissions"):
            is_admin = ctx.author.guild_permissions.administrator

        # Temporary: Force non-admin view for testing (remove this line when satisfied)
        # is_admin = False

        # Quote commands (available to everyone)
        quote_commands = [
            ("`!quote`", "Get a random quote"),
            ("`!quote add <quote> - <author>`", "Add a new quote"),
            ("`!quote list [author]`", "List all quotes or by author"),
            ("`!quote search <term>`", "Search quotes"),
            ("`!quote get <id>`", "Get a specific quote by ID"),
            ("`!quote delete <id>`", "Delete your own quotes"),
            ("`!quote random [author]`", "Get a random quote"),
        ]

        # Add admin-only commands if user is admin
        if is_admin:
            quote_commands.extend(
                [
                    ("`!quote export`", "Export all quotes (admin only)"),
                    ("`!quote import`", "Import quotes from CSV (admin only)"),
                ]
            )
            # Update delete description for admins
            for i, (cmd, _) in enumerate(quote_commands):
                if "delete" in cmd:
                    quote_commands[i] = (
                        cmd,
                        "Delete any quote (admin) or your own quotes",
                    )
                    break

        quote_text = "\n".join([f"**{cmd}** - {desc}" for cmd, desc in quote_commands])
        embed.add_field(name="📝 Quote Commands", value=quote_text, inline=False)

        # General commands
        embed.add_field(
            name="❓ General Commands",
            value="**`!help [command]`** - Show this help or help for a specific command",
            inline=False,
        )

        # Add footer with usage tips
        embed.set_footer(
            text="💡 Tip: You can also reply to any message with '!quote add' to quote it!"
        )

        await ctx.send(embed=embed)

    async def _show_command_help(
        self, ctx: commands.Context[commands.Bot], command_name: str
    ) -> None:
        """Show detailed help for a specific command."""
        # Handle quote subcommands
        if command_name.startswith("quote "):
            subcommand = command_name.split(" ", 1)[1]
            await self._show_quote_subcommand_help(ctx, subcommand)
            return

        # Handle main commands
        cmd = self.bot.get_command(command_name)
        if not cmd:
            await ctx.send(f"❌ Command '{command_name}' not found.")
            return

        embed = discord.Embed(
            title=f"Help: {cmd.name}",
            description=cmd.help or "No description available.",
            color=discord.Color.blue(),
        )

        if cmd.usage:
            embed.add_field(name="Usage", value=f"`!{cmd.usage}`", inline=False)

        if hasattr(cmd, "commands") and cmd.commands:
            # This is a group command, show subcommands
            subcommands = []
            for subcmd in cmd.commands:
                subcommands.append(
                    f"**`!{cmd.name} {subcmd.name}`** - {subcmd.help or 'No description'}"
                )

            embed.add_field(
                name="Subcommands", value="\n".join(subcommands), inline=False
            )

        await ctx.send(embed=embed)

    async def _show_quote_subcommand_help(
        self, ctx: commands.Context[commands.Bot], subcommand: str
    ) -> None:
        """Show help for quote subcommands."""
        # Check if user is admin
        is_admin = False
        if ctx.guild and hasattr(ctx.author, "guild_permissions"):
            is_admin = ctx.author.guild_permissions.administrator

        # Hide admin-only commands from non-admins
        admin_only_commands = ["export", "import"]
        if subcommand in admin_only_commands and not is_admin:
            await ctx.send(
                "❌ Command not found or you don't have permission to view its help."
            )
            return

        quote_help = {
            "add": {
                "description": "Add a new quote to the database",
                "usage": "!quote add <quote text> - <author name>",
                "examples": [
                    "!quote add Hello world! - John Doe",
                    "Reply to any message with `!quote add` to quote it automatically",
                ],
            },
            "list": {
                "description": "List quotes, optionally filtered by author",
                "usage": "!quote list [author name]",
                "examples": ["!quote list", "!quote list John"],
            },
            "search": {
                "description": "Search for quotes containing specific text",
                "usage": "!quote search <search term>",
                "examples": ["!quote search hello", "!quote search John"],
            },
            "get": {
                "description": "Get a specific quote by its ID number",
                "usage": "!quote get <quote id>",
                "examples": ["!quote get 42"],
            },
            "delete": {
                "description": "Delete a quote (only the person who added it or admins can delete)",
                "usage": "!quote delete <quote id>",
                "examples": ["!quote delete 42"],
            },
            "random": {
                "description": "Get a random quote, optionally from a specific author",
                "usage": "!quote random [author name]",
                "examples": ["!quote random", "!quote random John"],
            },
            "export": {
                "description": "Export all quotes to a CSV file (admin only)",
                "usage": "!quote export",
                "examples": ["!quote export"],
            },
            "import": {
                "description": "Import quotes from a CSV file (admin only)",
                "usage": "!quote import (attach CSV file)",
                "examples": ["!quote import (with CSV attachment)"],
            },
        }

        if subcommand not in quote_help:
            await ctx.send(f"❌ Quote subcommand '{subcommand}' not found.")
            return

        help_info = quote_help[subcommand]
        embed = discord.Embed(
            title=f"Help: quote {subcommand}",
            description=help_info["description"],
            color=discord.Color.blue(),
        )

        embed.add_field(name="Usage", value=f"`{help_info['usage']}`", inline=False)

        if help_info["examples"]:
            embed.add_field(
                name="Examples",
                value="\n".join([f"`{ex}`" for ex in help_info["examples"]]),
                inline=False,
            )

        await ctx.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    """Load the CustomHelp cog."""
    await bot.add_cog(CustomHelp(bot))
