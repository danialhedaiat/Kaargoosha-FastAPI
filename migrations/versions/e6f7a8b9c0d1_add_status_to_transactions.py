"""add status to transactions

Revision ID: e6f7a8b9c0d1
Revises: d4e5f6a7b8c9
Create Date: 2026-06-18 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6f7a8b9c0d1'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing transactions are all completed money movements -> backfill as 'approved'.
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'status',
            sa.Enum('pending', 'approved', 'rejected', name='transactionstatus'),
            nullable=False,
            server_default='approved',
        ))


def downgrade() -> None:
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_column('status')
