"""add_loan_fields_to_user

Revision ID: a6dc00c8ea34
Revises: 
Create Date: 2025-07-08 10:51:24.806271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6dc00c8ea34'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add loan fields to users table
    op.add_column('users', sa.Column('loan_amount', sa.Float(), nullable=True))
    op.add_column('users', sa.Column('loan_term', sa.Integer(), nullable=True))
    op.add_column('users', sa.Column('loan_purpose', sa.String(100), nullable=True))
    op.add_column('users', sa.Column('monthly_income', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove loan fields from users table
    op.drop_column('users', 'monthly_income')
    op.drop_column('users', 'loan_purpose')
    op.drop_column('users', 'loan_term')
    op.drop_column('users', 'loan_amount')
