"""add account closure fields (is_active, closed_at, closed_by)

Revision ID: d1e2f3a4b5c6
Revises: c0d1e2f3a4b5
Create Date: 2026-06-28 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = 'c0d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing accounts are all active -> backfill is_active = 1.
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')))
        batch_op.add_column(sa.Column('closed_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('closed_by', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_accounts_closed_by_users', 'users', ['closed_by'], ['id'])


def downgrade() -> None:
    with op.batch_alter_table('accounts', schema=None) as batch_op:
        batch_op.drop_constraint('fk_accounts_closed_by_users', type_='foreignkey')
        batch_op.drop_column('closed_by')
        batch_op.drop_column('closed_at')
        batch_op.drop_column('is_active')