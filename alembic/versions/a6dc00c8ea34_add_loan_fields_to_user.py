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
    # Add loan fields to users table (safe for repeated execution)
    from sqlalchemy import text
    
    # Получаем соединение
    connection = op.get_bind()
    
    # Проверяем и добавляем loan_amount если не существует
    result = connection.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='users' AND column_name='loan_amount'
    """))
    if not result.fetchone():
        op.add_column('users', sa.Column('loan_amount', sa.Float(), nullable=True))
    
    # Проверяем и добавляем loan_term если не существует
    result = connection.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='users' AND column_name='loan_term'
    """))
    if not result.fetchone():
        op.add_column('users', sa.Column('loan_term', sa.Integer(), nullable=True))
    
    # Проверяем и добавляем loan_purpose если не существует
    result = connection.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='users' AND column_name='loan_purpose'
    """))
    if not result.fetchone():
        op.add_column('users', sa.Column('loan_purpose', sa.String(100), nullable=True))
    
    # Проверяем и добавляем monthly_income если не существует
    result = connection.execute(text("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name='users' AND column_name='monthly_income'
    """))
    if not result.fetchone():
        op.add_column('users', sa.Column('monthly_income', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove loan fields from users table
    op.drop_column('users', 'monthly_income')
    op.drop_column('users', 'loan_purpose')
    op.drop_column('users', 'loan_term')
    op.drop_column('users', 'loan_amount')
