"""drop status/proof from transactions (immutable ledger)

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-06-18 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b9c0d1e2f3a4'
down_revision: Union[str, Sequence[str], None] = 'a8b9c0d1e2f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # transactions becomes a pure immutable ledger; status + proof live on receipts now.
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.drop_column('status')
        batch_op.drop_column('proof_type')
        batch_op.drop_column('proof_content')


def downgrade() -> None:
    with op.batch_alter_table('transactions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('proof_content', sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column('proof_type', sa.String(length=10), nullable=True))
        batch_op.add_column(sa.Column(
            'status',
            sa.Enum('pending', 'approved', 'rejected', name='transactionstatus'),
            nullable=False,
            server_default='approved',
        ))
