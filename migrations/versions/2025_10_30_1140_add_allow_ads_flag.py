"""add allow ads flag on users

Revision ID: add_allow_ads_flag
Revises: add_tags
Create Date: 2025-10-30 11:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_allow_ads_flag'
down_revision = 'add_tags'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'allow_ads' not in columns:
        op.add_column(
            'users',
            sa.Column('allow_ads', sa.Boolean(), nullable=False, server_default=sa.false())
        )
        # Ensure existing users default to disabled; keep server default for simplicity
        op.execute(sa.text("UPDATE users SET allow_ads = 0"))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'allow_ads' in columns:
        op.drop_column('users', 'allow_ads')
