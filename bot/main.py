import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands

from bot.config import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger: logging.Logger = logging.getLogger("bot")

# Bot configuration
intents: discord.Intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot: commands.Bot = commands.Bot(command_prefix=config.command_prefix, intents=intents)


@bot.event
async def on_ready() -> None:
    """Event triggered when the bot is ready."""
    if bot.user is None:
        logger.error("Bot user is None - this should not happen")
        return

    logger.info(
        f"{bot.user.name} has connected to Discord! (Mode: {config.mode_display}, Prefix: {config.command_prefix})"
    )

    # Load all cogs
    cogs_path = Path(__file__).parent / "cogs"
    for cog_file in cogs_path.glob("*.py"):
        if cog_file.name != "__init__.py":
            cog_name: str = f"bot.cogs.{cog_file.stem}"
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
    if not config.discord_token:
        logger.error(
            "No Discord token found. Please set the DISCORD_TOKEN environment variable."
        )
        return

    # Run database migrations before starting the bot
    try:
        import subprocess

        # Run Alembic migrations
        cmd = ["uv", "run", "alembic", "upgrade", "head"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Alembic migration failed: {result.stderr}")
            return
        else:
            logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return

    try:
        await bot.start(config.discord_token)
    except discord.errors.LoginFailure:
        logger.error(
            "Invalid Discord token. Please check your DISCORD_TOKEN environment variable."
        )
    except Exception as e:
        logger.error(f"An error occurred while starting the bot: {e}")


if __name__ == "__main__":
    asyncio.run(main())
