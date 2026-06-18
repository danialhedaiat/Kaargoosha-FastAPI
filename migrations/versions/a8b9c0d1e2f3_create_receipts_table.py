"""create receipts table

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-18 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8b9c0d1e2f3'
down_revision: Union[str, Sequence[str], None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'receipts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('type', sa.Enum('deposit', 'installment_payment', name='receipttype'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('proof_type', sa.String(length=10), nullable=False),
        sa.Column('proof_path', sa.String(length=500), nullable=True),
        sa.Column('proof_text', sa.String(length=500), nullable=True),
        sa.Column('status', sa.Enum('pending', 'approved', 'rejected', name='receiptstatus'), nullable=False),
        sa.Column('reviewed_by', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(), nullable=True),
        sa.Column('rejection_reason', sa.String(length=500), nullable=True),
        sa.Column('reference_type', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['reviewed_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_receipts_type_status_created', 'receipts', ['type', 'status', 'created_at'])

    # Backfill from the legacy request tables (dev data). Old PHOTO proofs were Bale
    # file_ids (no bytes on disk), so the old proof_content is preserved into proof_text
    # as a legacy reference; proof_path stays NULL for those.
    op.execute("""
        INSERT INTO receipts (user_id, type, amount, proof_type, proof_text, status,
                              reviewed_by, reviewed_at, rejection_reason, reference_type, reference_id, created_at)
        SELECT user_id, 'deposit', amount, proof_type, proof_content, status,
               approved_by, approved_at, rejection_reason, 'deposit_request', id, created_at
        FROM deposit_requests
    """)
    op.execute("""
        INSERT INTO receipts (user_id, type, amount, proof_type, proof_text, status,
                              reviewed_by, reviewed_at, rejection_reason, reference_type, reference_id, created_at)
        SELECT ipr.user_id, 'installment_payment',
               COALESCE((SELECT i.amount FROM installments i WHERE i.id = ipr.installment_id), 0),
               ipr.proof_type, ipr.proof_content, ipr.status,
               ipr.approved_by, ipr.approved_at, ipr.rejection_reason,
               'installment', ipr.installment_id, ipr.created_at
        FROM installment_payment_requests ipr
    """)


def downgrade() -> None:
    op.drop_index('ix_receipts_type_status_created', table_name='receipts')
    op.drop_table('receipts')
