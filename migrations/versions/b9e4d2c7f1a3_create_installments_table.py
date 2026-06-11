"""create_installments_table

Revision ID: b9e4d2c7f1a3
Revises: a1f3c2e4b8d7
Create Date: 2026-06-11 18:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b9e4d2c7f1a3'
down_revision: Union[str, Sequence[str], None] = 'a1f3c2e4b8d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'installments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('loan_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'paid', name='installmentstatus'), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['loan_id'], ['loans.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('installments')
