#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger: logging.Logger = logging.getLogger("bot")

# Load environment variables
load_dotenv()
TOKEN: str | None = os.getenv("DISCORD_TOKEN")

# Create data directory if it doesn't exist
data_dir: Path = Path("data")
data_dir.mkdir(exist_ok=True)

# Add CLI args
cli_args: list[str] = sys.argv

# Bot configuration
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
intents.members = True

command_prefix: str = "?" if "--dev" in cli_args else "!"
bot: commands.Bot = commands.Bot(command_prefix=command_prefix, intents=intents)


@bot.event
async def on_ready() -> None:
    """Event triggered when the bot is ready."""
    if bot.user is None:
        logger.error("Bot user is None - this should not happen")
        return

    logger.info(f"{bot.user.name} has connected to Discord!")

    # Load all cogs
    for cog_file in Path("cogs").glob("*.py"):
        if cog_file.name != "__init__.py":
            cog_name: str = f"cogs.{cog_file.stem}"
            try:
                await bot.load_extension(cog_name)
                logger.info(f"Loaded extension {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load extension {cog_name}: {e}")


@bot.event
async def on_command_error(
    ctx: commands.Context[commands.Bot], error: commands.CommandError
) -> None:
    """Global error handler for bot commands."""
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Command not found. Try `!help` to see available commands.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"Bad argument: {error}")
    else:
        logger.error(f"Error in {ctx.command}: {error}")
        await ctx.send(f"An error occurred: {error}")


async def main() -> None:
    """Main entry point for the bot."""
    if not TOKEN:
        logger.error(
            "No Discord token found. Please set the DISCORD_TOKEN environment variable."
        )
        return

    try:
        await bot.start(TOKEN)
    except discord.errors.LoginFailure:
        logger.error(
            "Invalid Discord token. Please check your DISCORD_TOKEN environment variable."
        )
    except Exception as e:
        logger.error(f"An error occurred while starting the bot: {e}")


if __name__ == "__main__":
    asyncio.run(main())
