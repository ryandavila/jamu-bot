import discord
from discord.ext import commands
import aiosqlite
import random
import datetime
from pathlib import Path
from typing import Optional, Union


class Quotes(commands.Cog):
    """A cog for managing and retrieving quotes."""

    def __init__(self, bot):
        self.bot = bot
        self.db_path = Path("data/quotes.db")
        self.bot.loop.create_task(self.setup_db())

    async def setup_db(self):
        """Set up the SQLite database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS quotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    author TEXT NOT NULL,
                    added_by INTEGER NOT NULL,
                    guild_id INTEGER NOT NULL,
                    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    @commands.group(name="quote", invoke_without_command=True)
    async def quote(self, ctx):
        """Get a random quote from the database."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1",
                (ctx.guild.id,),
            )
            quote = await cursor.fetchone()

            if quote:
                embed = self._create_quote_embed(quote)
                await ctx.send(embed=embed)
            else:
                await ctx.send(
                    "No quotes found! Add some with `!quote add <quote> - <author>`"
                )

    @quote.command(name="add")
    async def add_quote(self, ctx, *, content: str = None):
        """Add a new quote to the database.

        Format: !quote add <quote> - <author>
        Example: !quote add The way to get started is to quit talking and begin doing. - Walt Disney

        You can also reply to a message to quote it:
        Example: (reply to a message) !quote add
        """
        # Check if this is a reply to another message
        if ctx.message.reference and not content:
            # Get the message being replied to
            try:
                referenced_message = await ctx.fetch_message(
                    ctx.message.reference.message_id
                )
                quote_text = referenced_message.content
                author = referenced_message.author.display_name

                # Handle empty messages (e.g., only attachments)
                if not quote_text:
                    await ctx.send(
                        "The message you're replying to doesn't have any text content."
                    )
                    return

                # Add the quote
                await self._add_quote_to_db(ctx, quote_text, author)

            except discord.NotFound:
                await ctx.send("I couldn't find the message you replied to.")
            except Exception as e:
                await ctx.send(f"An error occurred: {str(e)}")
            return

        # Handle manual quote addition
        if not content:
            await ctx.send("Please provide a quote or reply to a message to quote it.")
            return

        if " - " not in content:
            await ctx.send(
                "Invalid format. Use `!quote add <quote> - <author>` or reply to a message."
            )
            return

        quote_text, author = content.rsplit(" - ", 1)
        quote_text = quote_text.strip()
        author = author.strip()

        if not quote_text or not author:
            await ctx.send("Both quote and author must be provided.")
            return

        await self._add_quote_to_db(ctx, quote_text, author)

    async def _add_quote_to_db(self, ctx, quote_text: str, author: str):
        """Helper method to add a quote to the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO quotes (content, author, added_by, guild_id) VALUES (?, ?, ?, ?)",
                (quote_text, author, ctx.author.id, ctx.guild.id),
            )
            await db.commit()

        await ctx.send(f"Quote by {author} has been added!")

    @quote.command(name="list")
    async def list_quotes(self, ctx, *, author: str = None):
        """List quotes, optionally filtered by author.

        Usage:
        !quote list - List all quotes
        !quote list <author> - List quotes by a specific author
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if author:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? AND LOWER(author) LIKE ? ORDER BY id",
                    (ctx.guild.id, f"%{author.lower()}%"),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? ORDER BY id",
                    (ctx.guild.id,),
                )

            quotes = await cursor.fetchall()

            if not quotes:
                if author:
                    await ctx.send(f"No quotes found by author matching '{author}'.")
                else:
                    await ctx.send("No quotes found in the database.")
                return

            # Create a paginated list of quotes
            quote_pages = []
            page_size = 5

            for i in range(0, len(quotes), page_size):
                page_quotes = quotes[i : i + page_size]
                embed = discord.Embed(
                    title=f"Quotes {i + 1}-{min(i + page_size, len(quotes))} of {len(quotes)}",
                    color=discord.Color.blue(),
                )

                for quote in page_quotes:
                    embed.add_field(
                        name=f"#{quote['id']} - {quote['author']}",
                        value=f'"{quote["content"]}"',
                        inline=False,
                    )

                quote_pages.append(embed)

            # Send the first page
            current_page = 0
            message = await ctx.send(embed=quote_pages[current_page])

            # Add reactions for pagination if there are multiple pages
            if len(quote_pages) > 1:
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")

                def check(reaction, user):
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
                            and current_page < len(quote_pages) - 1
                        ):
                            current_page += 1
                            await message.edit(embed=quote_pages[current_page])
                            await message.remove_reaction(reaction, user)

                        elif str(reaction.emoji) == "⬅️" and current_page > 0:
                            current_page -= 1
                            await message.edit(embed=quote_pages[current_page])
                            await message.remove_reaction(reaction, user)

                        else:
                            await message.remove_reaction(reaction, user)

                    except:
                        break

    @quote.command(name="get")
    async def get_quote(self, ctx, quote_id: int):
        """Get a specific quote by its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE id = ? AND guild_id = ?",
                (quote_id, ctx.guild.id),
            )
            quote = await cursor.fetchone()

            if quote:
                embed = self._create_quote_embed(quote)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Quote with ID {quote_id} not found.")

    @quote.command(name="delete", aliases=["remove"])
    async def delete_quote(self, ctx, quote_id: int):
        """Delete a quote by its ID. Only the quote adder or admins can delete quotes."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE id = ? AND guild_id = ?",
                (quote_id, ctx.guild.id),
            )
            quote = await cursor.fetchone()

            if not quote:
                await ctx.send(f"Quote with ID {quote_id} not found.")
                return

            # Check if user is the one who added the quote or has admin permissions
            if (
                quote["added_by"] != ctx.author.id
                and not ctx.author.guild_permissions.administrator
            ):
                await ctx.send("You don't have permission to delete this quote.")
                return

            await db.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
            await db.commit()

            await ctx.send(f"Quote #{quote_id} has been deleted.")

    @quote.command(name="search")
    async def search_quotes(self, ctx, *, search_term: str):
        """Search for quotes containing the given text."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE guild_id = ? AND (LOWER(content) LIKE ? OR LOWER(author) LIKE ?)",
                (ctx.guild.id, f"%{search_term.lower()}%", f"%{search_term.lower()}%"),
            )
            quotes = await cursor.fetchall()

            if not quotes:
                await ctx.send(f"No quotes found matching '{search_term}'.")
                return

            await ctx.send(f"Found {len(quotes)} quotes matching '{search_term}':")

            # Create a paginated list of quotes
            quote_pages = []
            page_size = 5

            for i in range(0, len(quotes), page_size):
                page_quotes = quotes[i : i + page_size]
                embed = discord.Embed(
                    title=f"Search Results {i + 1}-{min(i + page_size, len(quotes))} of {len(quotes)}",
                    color=discord.Color.green(),
                )

                for quote in page_quotes:
                    embed.add_field(
                        name=f"#{quote['id']} - {quote['author']}",
                        value=f'"{quote["content"]}"',
                        inline=False,
                    )

                quote_pages.append(embed)

            # Send the first page
            current_page = 0
            message = await ctx.send(embed=quote_pages[current_page])

            # Add reactions for pagination if there are multiple pages
            if len(quote_pages) > 1:
                await message.add_reaction("⬅️")
                await message.add_reaction("➡️")

                def check(reaction, user):
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
                            and current_page < len(quote_pages) - 1
                        ):
                            current_page += 1
                            await message.edit(embed=quote_pages[current_page])
                            await message.remove_reaction(reaction, user)

                        elif str(reaction.emoji) == "⬅️" and current_page > 0:
                            current_page -= 1
                            await message.edit(embed=quote_pages[current_page])
                            await message.remove_reaction(reaction, user)

                        else:
                            await message.remove_reaction(reaction, user)

                    except:
                        break

    @quote.command(name="random")
    async def random_quote(self, ctx, *, author: str = None):
        """Get a random quote, optionally filtered by author."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if author:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? AND LOWER(author) LIKE ? ORDER BY RANDOM() LIMIT 1",
                    (ctx.guild.id, f"%{author.lower()}%"),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1",
                    (ctx.guild.id,),
                )

            quote = await cursor.fetchone()

            if quote:
                embed = self._create_quote_embed(quote)
                await ctx.send(embed=embed)
            else:
                if author:
                    await ctx.send(f"No quotes found by author matching '{author}'.")
                else:
                    await ctx.send("No quotes found in the database.")

    @quote.command(name="export")
    @commands.has_permissions(administrator=True)
    async def export_quotes(self, ctx):
        """Export all quotes to a CSV file (admin only)."""
        import csv
        from io import StringIO

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM quotes WHERE guild_id = ? ORDER BY id", (ctx.guild.id,)
            )
            quotes = await cursor.fetchall()

            if not quotes:
                await ctx.send("No quotes to export.")
                return

            # Create CSV in memory
            output = StringIO()
            writer = csv.writer(output)
            writer.writerow(["ID", "Quote", "Author", "Added By", "Date Added"])

            for quote in quotes:
                writer.writerow(
                    [
                        quote["id"],
                        quote["content"],
                        quote["author"],
                        quote["added_by"],
                        quote["date_added"],
                    ]
                )

            # Create a Discord file from the CSV
            output.seek(0)
            file = discord.File(
                fp=StringIO(output.getvalue()),
                filename=f"quotes_{ctx.guild.name}_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
            )

            await ctx.send("Here are all the quotes:", file=file)

    @quote.command(name="import")
    @commands.has_permissions(administrator=True)
    async def import_quotes(self, ctx):
        """Import quotes from a CSV file (admin only).

        The CSV should be attached to the message and have the format:
        Quote,Author
        """
        if not ctx.message.attachments:
            await ctx.send("Please attach a CSV file with your quotes.")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".csv"):
            await ctx.send("Please attach a CSV file.")
            return

        import csv
        from io import StringIO

        # Download the CSV file
        content = await attachment.read()
        csv_content = content.decode("utf-8")

        # Parse the CSV
        reader = csv.reader(StringIO(csv_content))

        try:
            # Skip header row
            next(reader)

            # Process quotes
            quotes_added = 0
            async with aiosqlite.connect(self.db_path) as db:
                for row in reader:
                    if len(row) >= 2:  # Ensure we have at least quote and author
                        quote_text = row[0].strip()
                        author = row[1].strip()

                        if quote_text and author:
                            await db.execute(
                                "INSERT INTO quotes (content, author, added_by, guild_id) VALUES (?, ?, ?, ?)",
                                (quote_text, author, ctx.author.id, ctx.guild.id),
                            )
                            quotes_added += 1

                await db.commit()

            await ctx.send(f"Successfully imported {quotes_added} quotes!")

        except Exception as e:
            await ctx.send(f"Error importing quotes: {str(e)}")

    def _create_quote_embed(self, quote):
        """Create a Discord embed for a quote."""
        # Use a warm purple color for a more elegant look
        embed = discord.Embed(color=discord.Color.from_rgb(147, 112, 219))

        # Add the quote with stylized formatting
        embed.description = f"❝ {quote['content']} ❞"

        # Add author with a decorative separator
        embed.add_field(name="", value=f"― *{quote['author']}*", inline=False)

        # Format the date in a cleaner way
        date_added = datetime.datetime.strptime(
            quote["date_added"], "%Y-%m-%d %H:%M:%S"
        )
        formatted_date = date_added.strftime("%B %d, %Y")

        # Add a subtle footer with quote ID and date
        embed.set_footer(text=f"Quote #{quote['id']} • {formatted_date}")

        return embed

    # This method can be expanded later to handle reaction-based quoting
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Event listener for reaction adds. Can be used for reaction-based quoting."""
        # This is a placeholder for future implementation of reaction-based quoting
        # The structure would be:
        # 1. Check if the reaction is the quote emoji
        # 2. Check if the user has permission to add quotes
        # 3. Add the quote to the database
        pass


async def setup(bot):
    await bot.add_cog(Quotes(bot))
