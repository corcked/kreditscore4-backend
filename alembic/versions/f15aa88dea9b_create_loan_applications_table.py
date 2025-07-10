"""create_loan_applications_table

Revision ID: f15aa88dea9b
Revises: a6dc00c8ea34
Create Date: 2025-07-10 23:00:47.966625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f15aa88dea9b'
down_revision: Union[str, None] = 'a6dc00c8ea34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type for application status
    application_status = postgresql.ENUM('pending', 'approved', 'rejected', 'cancelled', 'completed', name='applicationstatus')
    application_status.create(op.get_bind())
    
    # Create loan_applications table
    op.create_table('loan_applications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('loan_amount', sa.Float(), nullable=False),
        sa.Column('loan_term', sa.Integer(), nullable=False),
        sa.Column('loan_purpose', sa.String(length=100), nullable=False),
        sa.Column('monthly_income', sa.Float(), nullable=False),
        sa.Column('status', application_status, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_loan_applications_id'), 'loan_applications', ['id'], unique=False)
    op.create_index(op.f('ix_loan_applications_user_id'), 'loan_applications', ['user_id'], unique=False)
    op.create_index(op.f('ix_loan_applications_status'), 'loan_applications', ['status'], unique=False)
    
    # Migrate existing loan data from users table to loan_applications
    op.execute("""
        INSERT INTO loan_applications (user_id, loan_amount, loan_term, loan_purpose, monthly_income, status, created_at)
        SELECT id, loan_amount, loan_term, loan_purpose, monthly_income, 'pending', created_at
        FROM users
        WHERE loan_amount IS NOT NULL
    """)
    
    # Drop loan columns from users table
    op.drop_column('users', 'loan_amount')
    op.drop_column('users', 'loan_term')
    op.drop_column('users', 'loan_purpose')
    op.drop_column('users', 'monthly_income')


def downgrade() -> None:
    # Add loan columns back to users table
    op.add_column('users', sa.Column('monthly_income', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('loan_purpose', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('loan_term', sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column('users', sa.Column('loan_amount', sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True))
    
    # Migrate latest loan data back to users table
    op.execute("""
        UPDATE users u
        SET loan_amount = la.loan_amount,
            loan_term = la.loan_term,
            loan_purpose = la.loan_purpose,
            monthly_income = la.monthly_income
        FROM (
            SELECT DISTINCT ON (user_id) user_id, loan_amount, loan_term, loan_purpose, monthly_income
            FROM loan_applications
            ORDER BY user_id, created_at DESC
        ) la
        WHERE u.id = la.user_id
    """)
    
    # Drop loan_applications table
    op.drop_index(op.f('ix_loan_applications_status'), table_name='loan_applications')
    op.drop_index(op.f('ix_loan_applications_user_id'), table_name='loan_applications')
    op.drop_index(op.f('ix_loan_applications_id'), table_name='loan_applications')
    op.drop_table('loan_applications')
    
    # Drop enum type
    application_status = postgresql.ENUM('pending', 'approved', 'rejected', 'cancelled', 'completed', name='applicationstatus')
    application_status.drop(op.get_bind())
