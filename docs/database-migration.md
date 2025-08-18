# Database Migration Guide

This guide explains how to migrate data from an old SQLite database to the current Jamu Bot database schema.

## Overview

The `migrate_db.py` script allows you to import quotes from an old SQLite database into your current database. This is useful when:
- Deploying the bot on a new device
- Migrating from an older version of the bot
- Restoring from a backup database

## Prerequisites

- The old database must be a SQLite file containing a `quotes` table
- The quotes table should have at minimum: `content`, `author`, `added_by`, `guild_id` columns
- Optional columns: `channel_id`, `created_at`, `original_timestamp`

## Usage

### 1. Dry Run (Recommended First Step)

Always start with a dry run to see what data would be migrated:

```bash
uv run python migrate_db.py /path/to/old/database.db --dry-run
```

This will:
- Analyze the old database structure
- Show you how many quotes would be imported
- Display sample data that would be migrated
- **Make no changes** to your current database

### 2. Actual Migration

Once you're satisfied with the dry run results:

```bash
uv run python migrate_db.py /path/to/old/database.db
```

You'll be prompted to confirm before the migration proceeds.

### 3. Advanced Options

#### Migrate to a Specific Database

By default, the script uses your current environment's database (dev/prod based on `JAMU_ENV`). To migrate to a specific database:

```bash
uv run python migrate_db.py /path/to/old/database.db --target-db "sqlite+aiosqlite:///path/to/target.db"
```

#### Get Help

```bash
uv run python migrate_db.py --help
```

## Migration Process

1. **Schema Analysis**: The script examines the old database structure and identifies available columns
2. **Data Mapping**: Maps old schema fields to current schema requirements
3. **Duplicate Detection**: Checks for existing quotes to avoid duplicates (based on content + author + guild_id)
4. **Data Import**: Creates new Quote records in the target database

## Schema Compatibility

The migration script handles common schema differences:

| Old Schema | Current Schema | Handling |
|------------|----------------|----------|
| Missing `channel_id` | Required `channel_id` | Defaults to 0 |
| String timestamps | DateTime objects | Parses ISO format or timestamp |
| Missing `original_timestamp` | Optional field | Sets to NULL |
| Different column names | Current schema | Manual mapping required |

## Error Handling

- **Missing required fields**: Rows with missing `content`, `author`, `added_by`, or `guild_id` are skipped
- **Invalid timestamps**: Falls back to current timestamp with warning
- **Duplicate quotes**: Skipped automatically based on content + author + guild_id
- **Database errors**: Individual quote failures don't stop the entire migration

## Example Output

```
Migration utility starting...
Source: /home/user/old_quotes.db
Target: sqlite+aiosqlite:///data/quotes.db
Mode: LIVE MIGRATION

Starting migration from /home/user/old_quotes.db to current database...
Source table columns: ['id', 'content', 'author', 'added_by', 'guild_id', 'channel_id', 'created_at']
Found 150 quotes in source database
Are you sure you want to proceed with the migration? (y/N): y
Imported: Steve Jobs: The only way to do great work is to love what you do...
Imported: John Lennon: Life is what happens to you while you're busy making...
Quote already exists, skipping: Eleanor Roosevelt: The future belongs to those who believe...
Migration completed. Imported 149 quotes.
```

## Safety Features

- **Dry run mode**: Preview changes before applying
- **Confirmation prompt**: Prevents accidental migrations
- **Duplicate detection**: Avoids importing the same quote twice
- **Error isolation**: Individual quote failures don't affect others
- **Transaction safety**: All changes are committed together or rolled back

## Troubleshooting

### "No 'quotes' table found in source database"
- Verify the old database file path is correct
- Check that the database contains a table named `quotes`

### "Skipping row due to missing required field"
- The old database has incomplete data
- Check which quotes are missing required fields
- Consider manually fixing the old database if needed

### "Could not parse created_at"
- Timestamp format in old database is not recognized
- Migration will use current timestamp as fallback
- Data is still imported successfully

### Migration appears to hang
- Large databases may take time to process
- Check console output for progress messages
- Consider migrating in smaller batches if needed

## Post-Migration

After a successful migration:
1. Verify the quote count matches expectations
2. Test bot functionality with migrated data
3. Consider backing up the new database
4. Remove or archive the old database file

## Creating Test Data

For testing purposes, you can create a sample old database:

```python
# create_test_db.py
import sqlite3
from pathlib import Path

def create_test_database():
    test_db_path = Path("test_old_quotes.db")
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL,
            author VARCHAR(255) NOT NULL,
            added_by INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    
    cursor.execute("""
        INSERT INTO quotes (content, author, added_by, guild_id, channel_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        "Test quote content",
        "Test Author",
        123456789,
        987654321,
        111222333,
        "2024-01-15T10:30:00Z"
    ))
    
    conn.commit()
    conn.close()
    print(f"Created test database: {test_db_path}")

if __name__ == "__main__":
    create_test_database()
```

Run with: `python create_test_db.py`