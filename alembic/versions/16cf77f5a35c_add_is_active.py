"""Add is_active

Revision ID: 16cf77f5a35c
Revises: 
Create Date: 2026-01-27 21:49:35.039826

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16cf77f5a35c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add column as nullable first
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True))

    # 2. Update existing rows to True
    op.execute("UPDATE users SET is_active = true")

    # 3. Alter column to be NOT NULL
    op.alter_column('users', 'is_active', nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_active')
