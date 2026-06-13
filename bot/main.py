import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands

from bot import database
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


def _run_migrations() -> None:
    """Apply Alembic migrations up to head (synchronous)."""
    from alembic import command
    from alembic.config import Config as AlembicConfig

    root = Path(__file__).resolve().parent.parent
    alembic_cfg = AlembicConfig(str(root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(root / "migrations"))
    # Don't let Alembic reconfigure the root logger; keep the bot's logging.
    alembic_cfg.attributes["configure_logging"] = False
    command.upgrade(alembic_cfg, "head")


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
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("You don't have permission to use that command.")
    else:
        # Log the full traceback, but don't leak internal error details to users.
        logger.error("Error in command %s", ctx.command, exc_info=error)
        await ctx.send("An unexpected error occurred. Please try again later.")


async def main() -> None:
    """Main entry point for the bot."""
    if not config.discord_token:
        logger.error(
            "No Discord token found. Please set the DISCORD_TOKEN environment variable."
        )
        return

    # Run database migrations before starting the bot. Alembic's env.py drives
    # an async engine via asyncio.run(), so run it in a worker thread to avoid
    # nesting event loops inside this already-running loop.
    try:
        await asyncio.to_thread(_run_migrations)
        logger.info("Database migrations completed successfully")
    except Exception as e:
        logger.error(f"Database migration failed: {e}")
        return

    # Initialize the shared database engine/connection pool.
    database.init_engine()

    try:
        await bot.start(config.discord_token)
    except discord.errors.LoginFailure:
        logger.error(
            "Invalid Discord token. Please check your DISCORD_TOKEN environment variable."
        )
    except Exception as e:
        logger.error(f"An error occurred while starting the bot: {e}")
    finally:
        await database.dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
