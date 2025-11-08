"""add user streak tracking fields

Revision ID: add_user_streak_fields
Revises: ec9c15efb2a8
Create Date: 2025-10-28 11:42:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_user_streak_fields'
down_revision = 'ec9c15efb2a8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('users')}
    dialect = bind.dialect.name

    if 'last_entry_at' not in columns:
        op.add_column('users', sa.Column('last_entry_at', sa.DateTime(), nullable=True))

    if 'streak_count' not in columns:
        op.add_column('users', sa.Column('streak_count', sa.Integer(), nullable=False, server_default='0'))
        op.execute(sa.text('UPDATE users SET streak_count = 0 WHERE streak_count IS NULL'))
        if not dialect.startswith('sqlite'):
            op.alter_column('users', 'streak_count', server_default=None)


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('users')}

    if 'streak_count' in columns:
        op.drop_column('users', 'streak_count')

    inspector = inspect(bind)
    columns = {col['name'] for col in inspector.get_columns('users')}
    if 'last_entry_at' in columns:
        op.drop_column('users', 'last_entry_at')
