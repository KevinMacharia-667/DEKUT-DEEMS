"""add tags to events

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-07-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("events", sa.Column("tags", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("events", "tags")
