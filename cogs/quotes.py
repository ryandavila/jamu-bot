import csv
import datetime
from io import StringIO
from pathlib import Path
from typing import Any

import aiosqlite
import discord
from discord.ext import commands


class Quotes(commands.Cog):
    """A cog for managing and retrieving quotes."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # Use separate database for dev mode
        import sys
        dev_mode = "--dev" in sys.argv
        db_name = "quotes_dev.db" if dev_mode else "quotes.db"
        self.db_path = Path(f"data/{db_name}")
        self.db_path.parent.mkdir(exist_ok=True)

    async def cog_load(self) -> None:
        """Initialize the database when the cog is loaded."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    added_by INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    original_timestamp TIMESTAMP
                )
                """
            )
            # Add the new column to existing databases (ignore if already exists)
            try:
                await db.execute(
                    "ALTER TABLE quotes ADD COLUMN original_timestamp TIMESTAMP"
                )
            except aiosqlite.OperationalError:
                pass  # Column already exists
            await db.execute(
                "CREATE INDEX IF NOT EXISTS idx_quotes_guild_id ON quotes(guild_id)"
            )
            await db.commit()

    def _create_quote_embed(self, quote: dict[str, Any]) -> discord.Embed:
        """Create a Discord embed for a quote."""
        # Use original timestamp if available, otherwise use created_at
        timestamp = quote.get("original_timestamp") or quote["created_at"]
        embed = discord.Embed(
            description=f'"{quote["content"]}"',
            color=discord.Color.blue(),
            timestamp=datetime.datetime.fromisoformat(timestamp),
        )
        embed.set_author(name=quote["author"])
        embed.set_footer(text=f"Quote #{quote['id']}")
        return embed

    @commands.hybrid_group(name="quote", invoke_without_command=True)  # type: ignore[arg-type]
    async def quote(self, ctx: commands.Context[commands.Bot]) -> None:
        """Get a random quote."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1",
                (ctx.guild.id,),
            )
            quote_row = await cursor.fetchone()
            if quote_row:
                quote_dict = dict(quote_row)
                embed = self._create_quote_embed(quote_dict)
                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    "No quotes found! Add some quotes with `!quote add <quote> - <author>`."
                )

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

                    await self._add_quote_to_db(ctx, quote_text, author, referenced_message.created_at)
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
        self, ctx: commands.Context[commands.Bot], quote_text: str, author: str, created_at: datetime.datetime | None = None
    ) -> None:
        """Helper method to add a quote to the database."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        async with aiosqlite.connect(self.db_path) as db:
            if created_at:
                await db.execute(
                    "INSERT INTO quotes (content, author, added_by, guild_id, original_timestamp) VALUES (?, ?, ?, ?, ?)",
                    (quote_text, author, ctx.author.id, ctx.guild.id, created_at.isoformat()),
                )
            else:
                await db.execute(
                    "INSERT INTO quotes (content, author, added_by, guild_id) VALUES (?, ?, ?, ?)",
                    (quote_text, author, ctx.author.id, ctx.guild.id),
                )
            await db.commit()

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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if author:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? AND author LIKE ? ORDER BY created_at DESC",
                    (ctx.guild.id, f"%{author}%"),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? ORDER BY created_at DESC",
                    (ctx.guild.id,),
                )

            quotes_rows = await cursor.fetchall()
            quotes = [dict(row) for row in quotes_rows]

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
                        name=f"#{quote['id']} - {quote['author']}",
                        value=f'"{quote["content"]}"',
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE id = ? AND guild_id = ?",
                (quote_id, ctx.guild.id),
            )
            quote_row = await cursor.fetchone()

            if quote_row:
                quote_dict = dict(quote_row)
                embed = self._create_quote_embed(quote_dict)
                await ctx.send(embed=embed)
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE id = ? AND guild_id = ?",
                (quote_id, ctx.guild.id),
            )
            quote_row = await cursor.fetchone()

            if not quote_row:
                await ctx.send(f"Quote with ID {quote_id} not found.")
                return

            quote_dict = dict(quote_row)

            # Check permissions
            if isinstance(ctx.author, discord.Member):
                is_admin = ctx.author.guild_permissions.administrator
            else:
                is_admin = False

            is_quote_adder = quote_dict["added_by"] == ctx.author.id

            if not (is_admin or is_quote_adder):
                await ctx.send(
                    "You can only delete quotes you added or you must be an admin."
                )
                return

            await db.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
            await db.commit()

            await ctx.send(f"Quote #{quote_id} has been deleted.")

    @quote.command(name="search")  # type: ignore[arg-type]
    async def search_quotes(
        self, ctx: commands.Context[commands.Bot], *, search_term: str
    ) -> None:
        """Search for quotes containing the given text."""
        if ctx.guild is None:
            await ctx.send("This command can only be used in a server.")
            return

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE guild_id = ? AND (content LIKE ? OR author LIKE ?) ORDER BY created_at DESC",
                (ctx.guild.id, f"%{search_term}%", f"%{search_term}%"),
            )
            quotes_rows = await cursor.fetchall()
            quotes = [dict(row) for row in quotes_rows]

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
                        name=f"#{quote['id']} - {quote['author']}",
                        value=f'"{quote["content"]}"',
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if author:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? AND author LIKE ? ORDER BY RANDOM() LIMIT 1",
                    (ctx.guild.id, f"%{author}%"),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1",
                    (ctx.guild.id,),
                )

            quote_row = await cursor.fetchone()
            if quote_row:
                quote_dict = dict(quote_row)
                embed = self._create_quote_embed(quote_dict)
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

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT id, content, author, added_by, created_at FROM quotes WHERE guild_id = ? ORDER BY id",
                (ctx.guild.id,),
            )
            quotes_rows = await cursor.fetchall()

            if not quotes_rows:
                await ctx.send("No quotes to export.")
                return

            # Create CSV content
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Content", "Author", "Added By", "Created At"])

            for quote_row in quotes_rows:
                quote = dict(quote_row)
                writer.writerow(
                    [
                        quote["id"],
                        quote["content"],
                        quote["author"],
                        quote["added_by"],
                        quote["created_at"],
                    ]
                )

            output.seek(0)
            csv_data = output.getvalue()
            file = discord.File(
                fp=csv_data.encode(), filename=f"quotes_{ctx.guild.id}.csv"
            )
            await ctx.send("Here are all the quotes exported as CSV:", file=file)

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

        async with aiosqlite.connect(self.db_path) as db:
            quotes_to_insert = []
            for row in csv_reader:
                try:
                    # Expecting columns: Content, Author
                    if "Content" in row and "Author" in row:
                        content_text = row["Content"].strip()
                        author = row["Author"].strip()

                        if content_text and author:
                            quotes_to_insert.append(
                                (content_text, author, ctx.author.id, ctx.guild.id)
                            )
                            imported_count += 1
                except Exception as e:
                    await ctx.send(f"Error importing row: {e}")
                    continue

            if quotes_to_insert:
                await db.executemany(
                    "INSERT INTO quotes (content, author, added_by, guild_id) VALUES (?, ?, ?, ?)",
                    quotes_to_insert,
                )
                await db.commit()

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
