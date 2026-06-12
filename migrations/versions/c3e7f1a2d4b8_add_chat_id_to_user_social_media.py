"""add_chat_id_to_user_social_media

Revision ID: c3e7f1a2d4b8
Revises: 0a5491add3a1
Create Date: 2026-06-12 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3e7f1a2d4b8'
down_revision: Union[str, Sequence[str], None] = '0a5491add3a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('user_social_media_id', schema=None) as batch_op:
        batch_op.add_column(sa.Column('chat_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('user_social_media_id', schema=None) as batch_op:
        batch_op.drop_column('chat_id')