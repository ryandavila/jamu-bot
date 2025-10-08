#!/usr/bin/env python3
"""Export quotes from the Jamu bot database using SQLAlchemy."""

import argparse
import asyncio
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config import Config
from models import Quote


class QuoteExporter:
    """Export quotes from the database in various formats."""

    def __init__(self, config: Config):
        self.config = config
        self.engine = create_async_engine(config.database_url, echo=False)
        self.async_session = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    async def get_quotes(self, guild_id: int | None = None) -> list[Quote]:
        """Get quotes from the database, optionally filtered by guild."""
        async with self.async_session() as session:
            query = select(Quote)

            if guild_id:
                query = query.where(Quote.guild_id == guild_id)

            query = query.order_by(Quote.created_at.asc())
            result = await session.execute(query)
            return list(result.scalars().all())

    async def export_csv(self, quotes: list[Quote], output_file: Path) -> None:
        """Export quotes to CSV format."""
        with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                [
                    "id",
                    "content",
                    "author",
                    "added_by",
                    "guild_id",
                    "channel_id",
                    "created_at",
                    "original_timestamp",
                ]
            )

            for quote in quotes:
                writer.writerow(
                    [
                        quote.id,
                        quote.content,
                        quote.author,
                        quote.added_by,
                        quote.guild_id,
                        quote.channel_id,
                        quote.created_at.isoformat() if quote.created_at else "",
                        quote.original_timestamp.isoformat()
                        if quote.original_timestamp
                        else "",
                    ]
                )

    async def export_json(self, quotes: list[Quote], output_file: Path) -> None:
        """Export quotes to JSON format."""
        data = []
        for quote in quotes:
            data.append(
                {
                    "id": quote.id,
                    "content": quote.content,
                    "author": quote.author,
                    "added_by": quote.added_by,
                    "guild_id": quote.guild_id,
                    "channel_id": quote.channel_id,
                    "created_at": quote.created_at.isoformat()
                    if quote.created_at
                    else None,
                    "original_timestamp": quote.original_timestamp.isoformat()
                    if quote.original_timestamp
                    else None,
                }
            )

        with open(output_file, "w", encoding="utf-8") as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)

    async def export_txt(self, quotes: list[Quote], output_file: Path) -> None:
        """Export quotes to human-readable text format."""
        with open(output_file, "w", encoding="utf-8") as txtfile:
            for quote in quotes:
                timestamp = quote.original_timestamp or quote.created_at
                timestamp_str = (
                    timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Unknown"
                )

                txtfile.write(f'"{quote.content}" - {quote.author}\n')
                txtfile.write(f"  (ID: {quote.id}, Added: {timestamp_str})\n\n")

    async def export_markdown(self, quotes: list[Quote], output_file: Path) -> None:
        """Export quotes to Markdown format."""
        with open(output_file, "w", encoding="utf-8") as mdfile:
            mdfile.write("# Quotes Export\n\n")
            mdfile.write(
                f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )

            for quote in quotes:
                timestamp = quote.original_timestamp or quote.created_at
                timestamp_str = (
                    timestamp.strftime("%Y-%m-%d %H:%M:%S") if timestamp else "Unknown"
                )

                mdfile.write(f"## Quote #{quote.id}\n\n")
                mdfile.write(f'> "{quote.content}"\n')
                mdfile.write(f"> \n")
                mdfile.write(f"> — **{quote.author}**\n\n")
                mdfile.write(f"*Added: {timestamp_str}*\n\n")
                mdfile.write("---\n\n")

    async def close(self):
        """Close the database connection."""
        await self.engine.dispose()


async def main():
    """Main export function."""
    parser = argparse.ArgumentParser(description="Export quotes from Jamu bot database")
    parser.add_argument(
        "-o",
        "--output",
        default=f"quotes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        help="Output filename (without extension)",
    )
    parser.add_argument("-g", "--guild", type=int, help="Guild ID to filter by")
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "json", "txt", "md"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "--env",
        default="prod",
        choices=["dev", "prod"],
        help="Environment (default: prod)",
    )

    args = parser.parse_args()

    # Set environment variable if specified
    if args.env:
        os.environ["JAMU_ENV"] = args.env

    # Create config
    config = Config()

    # Check if database exists
    if not Path(config.database_path).exists():
        print(f"Error: Database not found at {config.database_path}")
        sys.exit(1)

    # Create exporter
    exporter = QuoteExporter(config)

    try:
        # Get quotes
        print(f"Fetching quotes from {config.database_path}...")
        if args.guild:
            print(f"Filtering by guild ID: {args.guild}")

        quotes = await exporter.get_quotes(args.guild)

        if not quotes:
            print("No quotes found!")
            return

        # Prepare output file
        output_file = Path(f"{args.output}.{args.format}")

        # Export based on format
        print(f"Exporting {len(quotes)} quotes to {output_file}...")

        if args.format == "csv":
            await exporter.export_csv(quotes, output_file)
        elif args.format == "json":
            await exporter.export_json(quotes, output_file)
        elif args.format == "txt":
            await exporter.export_txt(quotes, output_file)
        elif args.format == "md":
            await exporter.export_markdown(quotes, output_file)

        print(f"Export complete! {len(quotes)} quotes exported to {output_file}")

        # Show preview
        print("\nPreview (first 3 quotes):")
        for i, quote in enumerate(quotes[:3]):
            print(f'{i + 1}. "{quote.content}" - {quote.author}')

    finally:
        await exporter.close()


if __name__ == "__main__":
    asyncio.run(main())
