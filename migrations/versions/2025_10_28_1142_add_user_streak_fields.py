"""add user streak tracking fields

Revision ID: add_user_streak_fields
Revises: ec9c15efb2a8
Create Date: 2025-10-28 11:42:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_user_streak_fields'
down_revision = 'ec9c15efb2a8'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.add_column(sa.Column('last_entry_at', sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column('streak_count', sa.Integer(), nullable=False, server_default='0'))

    # remove server default after backfill to avoid future implicit defaults
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('streak_count', server_default=None)


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('streak_count')
        batch_op.drop_column('last_entry_at')
