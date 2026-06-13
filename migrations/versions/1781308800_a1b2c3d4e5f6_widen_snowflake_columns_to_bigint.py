"""Widen snowflake columns to BigInteger

Discord IDs (added_by, guild_id, channel_id) are 64-bit snowflakes that
overflow a 32-bit PostgreSQL INTEGER. This migration widens them to BIGINT.

SQLite stores all integers as 64-bit and does not support ALTER COLUMN type
changes, so the migration is a no-op there.

Revision ID: a1b2c3d4e5f6
Revises: b34761c88524
Create Date: 2026-06-13 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "b34761c88524"
branch_labels = None
depends_on = None

_COLUMNS = ("added_by", "guild_id", "channel_id")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    for column in _COLUMNS:
        op.alter_column(
            "quotes",
            column,
            existing_type=sa.Integer(),
            type_=sa.BigInteger(),
            existing_nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    for column in _COLUMNS:
        op.alter_column(
            "quotes",
            column,
            existing_type=sa.BigInteger(),
            type_=sa.Integer(),
            existing_nullable=False,
        )
