# Jamu Quote Bot

A Discord bot for storing and retrieving quotes, built with Python and discord.py.

## Features

- Add quotes with author attribution
- Reply-based quoting (just reply to a message with `!quote add`)
- Retrieve random quotes
- Search quotes by content or author
- List all quotes with pagination
- Export quotes to CSV
- Import quotes from CSV
- Per-server quote database

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a Discord bot on the [Discord Developer Portal](https://discord.com/developers/applications)
4. Enable the "Message Content Intent" in the Bot section
5. Copy your bot token
6. Create a `.env` file in the project root with:
   ```
   DISCORD_TOKEN=your_discord_token_here
   ```
7. Invite your bot to your server with the proper permissions (Send Messages, Read Message History, Add Reactions)
8. Run the bot:
   ```
   python bot.py
   ```

## Commands

- `!quote` - Get a random quote
- `!quote add <quote> - <author>` - Add a new quote manually
- Reply to any message with `!quote add` - Quote that message
- `!quote list [author]` - List all quotes, optionally filtered by author
- `!quote get <id>` - Get a specific quote by ID
- `!quote delete <id>` - Delete a quote by ID
- `!quote search <term>` - Search for quotes containing a term
- `!quote random [author]` - Get a random quote, optionally by author
- `!quote export` - Export all quotes to CSV (admin only)
- `!quote import` - Import quotes from CSV (admin only)

## Data Storage

Quotes are stored in an SQLite database (`data/quotes.db`), which is automatically created when the bot first runs.

## Requirements

- Python 3.7+
- discord.py 2.0+
- aiosqlite
- python-dotenv
