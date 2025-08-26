import csv
import datetime
from io import StringIO

import discord
from discord.ext import commands
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from config import config
from models import Quote


class Quotes(commands.Cog):
    """A cog for managing and retrieving quotes."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Use centralized database configuration
        self.engine = create_async_engine(config.database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def cog_load(self) -> None:
        """Initialize the cog when loaded."""
        # Database should already be migrated at app startup
        pass

    def _create_quote_embed(self, quote: Quote) -> discord.Embed:
        """Create a Discord embed for a quote."""
        # Use original timestamp if available, otherwise use created_at
        timestamp = quote.original_timestamp or quote.created_at
        embed = discord.Embed(
            description=f'"{quote.content}"',
            color=discord.Color.blue(),
            timestamp=timestamp,
        )
        embed.set_author(name=quote.author)
        return embed

    def _can_user_access_channel(self, user: discord.Member, channel_id: int) -> bool:
        """Check if a user can access a specific channel."""
        if channel_id == 0:  # Unknown/legacy channel, allow access
            return True

        channel = user.guild.get_channel(channel_id)
        if channel is None:
            # Channel doesn't exist anymore, don't show the quote
            return False

        # Check if user can view the channel
        if isinstance(
            channel,
            discord.TextChannel
            | discord.VoiceChannel
            | discord.StageChannel
            | discord.ForumChannel,
        ):
            return channel.permissions_for(user).view_channel

        # For other channel types, default to allowing access
        return True

    async def _get_accessible_channel_ids(self, user: discord.Member) -> list[int]:
        """Get list of channel IDs the user can access."""
        accessible_channel_ids = [0]  # Always include legacy quotes

        for channel in user.guild.channels:
            if isinstance(
                channel,
                discord.TextChannel
                | discord.VoiceChannel
                | discord.StageChannel
                | discord.ForumChannel,
            ):
                if channel.permissions_for(user).view_channel:
                    accessible_channel_ids.append(channel.id)

        return accessible_channel_ids

    @commands.hybrid_group(name="quote", invoke_without_command=True)  # type: ignore[arg-type]
    async def quote(self, ctx: commands.Context[commands.Bot]) -> None:
        """Quote command group. Use subcommands like 'add', 'random', 'list', etc."""
        await ctx.send_help(ctx.command)

    @quote.command(name="add")  # type: ignore[arg-type]
    async def add_quote(
        self, ctx: commands.Context[commands.Bot], *, content: str | None = None
    ) -> None:
        """Add a new quote to the database.

        Format: !quote add <quote> - <author>
        Or reply to a message with !quote add
        """
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        # Check if this is a reply to another message
        if ctx.message.reference and not content:
            # Get the message being replied to
            if ctx.message.reference.message_id is not None:
                try:
                    referenced_message = await ctx.channel.fetch_message(
                        ctx.message.reference.message_id
                    )
                    quote_text = referenced_message.content
                    author = referenced_message.author.display_name

                    if not quote_text:
                        await ctx.send(
                            "The referenced message has no content to quote."
                        )
                        return

                    await self._add_quote_to_db(
                        ctx,
                        quote_text,
                        author,
                        referenced_message.created_at,
                        referenced_message.channel.id,
                    )
                    return
                except discord.NotFound:
                    await ctx.send("Could not find the referenced message.")
                    return
                except discord.Forbidden:
                    await ctx.send("I don't have permission to access that message.")
                    return

        # Handle manual quote input
        if not content:
            await ctx.send(
                "Please provide a quote in the format: `!quote add <quote> - <author>` "
                "or reply to a message with `!quote add`"
            )
            return

        # Parse the quote and author
        if " - " not in content:
            await ctx.send("Please use the format: `!quote add <quote> - <author>`")
            return

        quote_text, author = content.rsplit(" - ", 1)
        quote_text = quote_text.strip()
        author = author.strip()

        if not quote_text or not author:
            await ctx.send(
                "Both quote and author must be provided. Format: `!quote add <quote> - <author>`"
            )
            return

        await self._add_quote_to_db(ctx, quote_text, author)

    async def _add_quote_to_db(
        self,
        ctx: commands.Context[commands.Bot],
        quote_text: str,
        author: str,
        created_at: datetime.datetime | None = None,
        channel_id: int | None = None,
    ) -> None:
        """Helper method to add a quote to the database."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        # Use the provided channel_id or default to the current channel
        quote_channel_id = channel_id if channel_id is not None else ctx.channel.id

        async with self.async_session() as session:
            new_quote = Quote(
                content=quote_text,
                author=author,
                added_by=ctx.author.id,
                guild_id=ctx.guild.id,
                channel_id=quote_channel_id,
                original_timestamp=created_at,
            )
            session.add(new_quote)
            await session.commit()

        # Reply in thread if possible, otherwise regular reply
        await ctx.reply(f"Quote by {author} has been added!", mention_author=False)

    @quote.command(name="list")  # type: ignore[arg-type]
    async def list_quotes(
        self, ctx: commands.Context[commands.Bot], *, author: str | None = None
    ) -> None:
        """List quotes, optionally filtered by author.

        Usage:
        !quote list - List all quotes
        !quote list <author> - List quotes by specific author
        """
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used by server members.")
            return

        async with self.async_session() as session:
            # Get accessible channel IDs
            accessible_channel_ids = await self._get_accessible_channel_ids(ctx.author)

            # Build query based on author filter
            query = (
                select(Quote)
                .where(
                    Quote.guild_id == ctx.guild.id,
                    Quote.channel_id.in_(accessible_channel_ids),
                )
                .order_by(Quote.created_at.desc())
            )

            if author:
                query = query.where(Quote.author.like(f"%{author}%"))

            result = await session.execute(query)
            quotes = result.scalars().all()

            if not quotes:
                if author:
                    await ctx.send(f"No quotes found for author '{author}'.")
                else:
                    await ctx.send("No quotes found.")
                return

            # Pagination
            quotes_per_page = 5
            total_pages = (len(quotes) + quotes_per_page - 1) // quotes_per_page
            current_page = 0

            def create_page_embed(page: int) -> discord.Embed:
                start_idx = page * quotes_per_page
                end_idx = min(start_idx + quotes_per_page, len(quotes))
                page_quotes = quotes[start_idx:end_idx]

                if author:
                    title = f"Quotes by {author} (Page {page + 1}/{total_pages})"
                else:
                    title = f"All Quotes (Page {page + 1}/{total_pages})"

                embed = discord.Embed(title=title, color=discord.Color.blue())

                for quote in page_quotes:
                    embed.add_field(
                        name=f"#{quote.id} - {quote.author}",
                        value=f'"{quote.content}"',
                        inline=False,
                    )

                return embed

            if total_pages == 1:
                await ctx.send(embed=create_page_embed(0))
            else:
                message = await ctx.send(embed=create_page_embed(current_page))
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")

                def check(
                    reaction: discord.Reaction, user: discord.Member | discord.User
                ) -> bool:
                    return (
                        user == ctx.author
                        and str(reaction.emoji) in ["⬅️", "➡️"]
                        and reaction.message.id == message.id
                    )

                while True:
                    try:
                        reaction, user = await self.bot.wait_for(
                            "reaction_add", timeout=60.0, check=check
                        )

                        if (
                            str(reaction.emoji) == "➡️"
                            and current_page < total_pages - 1
                        ):
                            current_page += 1
                            await message.edit(embed=create_page_embed(current_page))
                        elif str(reaction.emoji) == "⬅️" and current_page > 0:
                            current_page -= 1
                            await message.edit(embed=create_page_embed(current_page))

                        # Remove the user's reaction
                        if isinstance(user, discord.Member | discord.User):
                            await message.remove_reaction(reaction, user)

                    except Exception:
                        break

    @quote.command(name="get")  # type: ignore[arg-type]
    async def get_quote(
        self, ctx: commands.Context[commands.Bot], quote_id: int
    ) -> None:
        """Get a specific quote by its ID."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used by server members.")
            return

        async with self.async_session() as session:
            query = select(Quote).where(
                Quote.id == quote_id, Quote.guild_id == ctx.guild.id
            )
            result = await session.execute(query)
            quote = result.scalar_one_or_none()

            if quote:
                # Check if user can access the channel where this quote originated
                if self._can_user_access_channel(ctx.author, quote.channel_id):
                    embed = self._create_quote_embed(quote)
                    await ctx.send(embed=embed)
                else:
                    await ctx.send(f"Quote with ID {quote_id} not found.")
            else:
                await ctx.send(f"Quote with ID {quote_id} not found.")

    @quote.command(name="delete", aliases=["remove"])  # type: ignore[arg-type]
    async def delete_quote(
        self, ctx: commands.Context[commands.Bot], quote_id: int
    ) -> None:
        """Delete a quote by its ID. Only the quote adder or admins can delete quotes."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        async with self.async_session() as session:
            query = select(Quote).where(
                Quote.id == quote_id, Quote.guild_id == ctx.guild.id
            )
            result = await session.execute(query)
            quote = result.scalar_one_or_none()

            if not quote:
                await ctx.send(f"Quote with ID {quote_id} not found.")
                return

            # Check if user can access the channel where this quote originated
            if isinstance(ctx.author, discord.Member):
                if not self._can_user_access_channel(ctx.author, quote.channel_id):
                    await ctx.send(f"Quote with ID {quote_id} not found.")
                    return

                is_admin = ctx.author.guild_permissions.administrator
            else:
                is_admin = False

            is_quote_adder = quote.added_by == ctx.author.id

            if not (is_admin or is_quote_adder):
                await ctx.send(
                    "You can only delete quotes you added or you must be an admin."
                )
                return

            await session.delete(quote)
            await session.commit()

            await ctx.send(f"Quote #{quote_id} has been deleted.")

    @quote.command(name="search")  # type: ignore[arg-type]
    async def search_quotes(
        self, ctx: commands.Context[commands.Bot], *, search_term: str
    ) -> None:
        """Search for quotes containing the given text."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used by server members.")
            return

        async with self.async_session() as session:
            # Get accessible channel IDs
            accessible_channel_ids = await self._get_accessible_channel_ids(ctx.author)

            # Build search query
            query = (
                select(Quote)
                .where(
                    Quote.guild_id == ctx.guild.id,
                    Quote.channel_id.in_(accessible_channel_ids),
                    (
                        Quote.content.like(f"%{search_term}%")
                        | Quote.author.like(f"%{search_term}%")
                    ),
                )
                .order_by(Quote.created_at.desc())
            )

            result = await session.execute(query)
            quotes = result.scalars().all()

            if not quotes:
                await ctx.send(f"No quotes found containing '{search_term}'.")
                return

            # Pagination
            quotes_per_page = 5
            total_pages = (len(quotes) + quotes_per_page - 1) // quotes_per_page
            current_page = 0

            def create_page_embed(page: int) -> discord.Embed:
                start_idx = page * quotes_per_page
                end_idx = min(start_idx + quotes_per_page, len(quotes))
                page_quotes = quotes[start_idx:end_idx]

                title = f"Search Results for '{search_term}' (Page {page + 1}/{total_pages})"
                embed = discord.Embed(title=title, color=discord.Color.green())

                for quote in page_quotes:
                    embed.add_field(
                        name=f"#{quote.id} - {quote.author}",
                        value=f'"{quote.content}"',
                        inline=False,
                    )

                return embed

            if total_pages == 1:
                await ctx.send(embed=create_page_embed(0))
            else:
                message = await ctx.send(embed=create_page_embed(current_page))
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")

                def check(
                    reaction: discord.Reaction, user: discord.Member | discord.User
                ) -> bool:
                    return (
                        user == ctx.author
                        and str(reaction.emoji) in ["⬅️", "➡️"]
                        and reaction.message.id == message.id
                    )

                while True:
                    try:
                        reaction, user = await self.bot.wait_for(
                            "reaction_add", timeout=60.0, check=check
                        )

                        if (
                            str(reaction.emoji) == "➡️"
                            and current_page < total_pages - 1
                        ):
                            current_page += 1
                            await message.edit(embed=create_page_embed(current_page))
                        elif str(reaction.emoji) == "⬅️" and current_page > 0:
                            current_page -= 1
                            await message.edit(embed=create_page_embed(current_page))

                        # Remove the user's reaction
                        if isinstance(user, discord.Member | discord.User):
                            await message.remove_reaction(reaction, user)

                    except Exception:
                        break

    @quote.command(name="random")  # type: ignore[arg-type]
    async def random_quote(
        self, ctx: commands.Context[commands.Bot], *, author: str | None = None
    ) -> None:
        """Get a random quote, optionally filtered by author."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if not isinstance(ctx.author, discord.Member):
            await ctx.send("This command can only be used by server members.")
            return

        async with self.async_session() as session:
            # Get accessible channel IDs
            accessible_channel_ids = await self._get_accessible_channel_ids(ctx.author)

            # Get count first, then select random quote by offset
            count_query = select(func.count(Quote.id)).where(
                Quote.guild_id == ctx.guild.id,
                Quote.channel_id.in_(accessible_channel_ids),
            )

            if author:
                count_query = count_query.where(Quote.author.like(f"%{author}%"))

            count_result = await session.execute(count_query)
            total_quotes = count_result.scalar() or 0

            if total_quotes == 0:
                if author:
                    await ctx.send(f"No quotes found for author '{author}'.")
                else:
                    await ctx.send("No quotes found.")
                return

            # Use Python's random for better randomization
            import random

            random_offset = random.randint(0, total_quotes - 1)

            query = (
                select(Quote)
                .where(
                    Quote.guild_id == ctx.guild.id,
                    Quote.channel_id.in_(accessible_channel_ids),
                )
                .offset(random_offset)
                .limit(1)
            )

            if author:
                query = query.where(Quote.author.like(f"%{author}%"))

            result = await session.execute(query)
            quote = result.scalar_one_or_none()

            if quote:
                embed = self._create_quote_embed(quote)
                await ctx.send(embed=embed)
            else:
                if author:
                    await ctx.send(f"No quotes found for author '{author}'.")
                else:
                    await ctx.send("No quotes found.")

    @quote.command(name="export")  # type: ignore[arg-type]
    @commands.has_permissions(administrator=True)
    async def export_quotes(self, ctx: commands.Context[commands.Bot]) -> None:
        """Export all quotes to a CSV file. Admin only."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        async with self.async_session() as session:
            query = (
                select(Quote).where(Quote.guild_id == ctx.guild.id).order_by(Quote.id)
            )
            result = await session.execute(query)
            quotes = result.scalars().all()

            if not quotes:
                await ctx.send("No quotes to export.")
                return

            # Create CSV content
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(
                ["ID", "Content", "Author", "Added By", "Created At", "Channel ID"]
            )

            for quote in quotes:
                writer.writerow(
                    [
                        quote.id,
                        quote.content,
                        quote.author,
                        quote.added_by,
                        quote.created_at.isoformat() if quote.created_at else "",
                        quote.channel_id,
                    ]
                )

            output.seek(0)
            file = discord.File(fp=output, filename=f"quotes_{ctx.guild.id}.csv")

            try:
                await ctx.author.send(
                    "Here are all the quotes exported as CSV:", file=file
                )
                await ctx.send("CSV file has been sent to your DMs.")
            except discord.Forbidden:
                await ctx.send(
                    "I couldn't send you a DM. Please check your privacy settings and try again."
                )

    @quote.command(name="import")  # type: ignore[arg-type]
    @commands.has_permissions(administrator=True)
    async def import_quotes(self, ctx: commands.Context[commands.Bot]) -> None:
        """Import quotes from a CSV file. Admin only."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        if not ctx.message.attachments:
            await ctx.send("Please attach a CSV file with your quotes.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename or not attachment.filename.endswith(".csv"):
            await ctx.send("Please attach a CSV file.")
            return

        # Download the CSV file
        content = await attachment.read()
        csv_content = content.decode("utf-8")

        # Parse CSV
        csv_reader = csv.DictReader(StringIO(csv_content))
        imported_count = 0

        async with self.async_session() as session:
            for row in csv_reader:
                try:
                    # Expecting columns: Content, Author
                    if "Content" in row and "Author" in row:
                        content_text = row["Content"].strip()
                        author = row["Author"].strip()

                        if content_text and author:
                            new_quote = Quote(
                                content=content_text,
                                author=author,
                                added_by=ctx.author.id,
                                guild_id=ctx.guild.id,
                                channel_id=ctx.channel.id,
                            )
                            session.add(new_quote)
                            imported_count += 1
                except Exception as e:
                    await ctx.send(f"Error importing row: {e}")
                    continue

            if imported_count > 0:
                await session.commit()

        if imported_count > 0:
            await ctx.send(f"Successfully imported {imported_count} quotes!")
        else:
            await ctx.send(
                "No quotes were imported. Make sure your CSV has 'Content' and 'Author' columns."
            )

    # This method can be expanded later to handle reaction-based quoting
    @commands.Cog.listener()
    async def on_reaction_add(
        self, reaction: discord.Reaction, user: discord.Member
    ) -> None:
        """Event listener for reaction adds. Can be used for reaction-based quoting."""
        # This is a placeholder for future implementation of reaction-based quoting
        # The structure would be:
        # 1. Check if the reaction is a specific emoji (like 💬)
        # 2. Check if the user has permission to add quotes
        # 3. Add the message content as a quote with the message author as the quote author
        pass


async def setup(bot: commands.Bot) -> None:
    """Load the Quotes cog."""
    await bot.add_cog(Quotes(bot))
