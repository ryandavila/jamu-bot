"""Use timezone-aware timestamps

created_at and original_timestamp hold timezone-aware UTC datetimes (defaults
and Discord message timestamps). asyncpg cannot encode a tz-aware value into a
naive TIMESTAMP column, so these are widened to TIMESTAMPTZ. Existing naive
values are interpreted as UTC.

SQLite does not distinguish the types and does not support ALTER COLUMN, so the
migration is a no-op there.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-13 00:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.alter_column(
        "quotes",
        "created_at",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "quotes",
        "original_timestamp",
        existing_type=sa.DateTime(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=True,
        postgresql_using="original_timestamp AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.alter_column(
        "quotes",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=False,
        postgresql_using="created_at AT TIME ZONE 'UTC'",
    )
    op.alter_column(
        "quotes",
        "original_timestamp",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.DateTime(),
        existing_nullable=True,
        postgresql_using="original_timestamp AT TIME ZONE 'UTC'",
    )
