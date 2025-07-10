"""change telegram_id to bigint

Revision ID: b7c8d9e0f1a2
Revises: a6dc00c8ea34
Create Date: 2025-01-10 17:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, None] = 'a6dc00c8ea34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change telegram_id from INTEGER to BIGINT
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.Integer(),
                    type_=sa.BigInteger(),
                    existing_nullable=False)


def downgrade() -> None:
    # Change telegram_id back to INTEGER
    op.alter_column('users', 'telegram_id',
                    existing_type=sa.BigInteger(),
                    type_=sa.Integer(),
                    existing_nullable=False) 