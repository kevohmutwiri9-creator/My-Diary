"""create saved views table

Revision ID: add_saved_views
Revises: add_user_streak_fields
Create Date: 2025-10-28 11:35:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_saved_views'
down_revision = 'add_user_streak_fields'
branch_labels = None
depends_on = None


def _ensure_unique_index(table, name, columns):
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {idx['name'] for idx in inspector.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns, unique=True)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if 'saved_views' not in tables:
        op.create_table(
            'saved_views',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('filters', sa.JSON(), nullable=False, server_default='{}'),
            sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.UniqueConstraint('user_id', 'name', name='uq_saved_views_user_name'),
        )
    else:
        _ensure_unique_index('saved_views', 'uq_saved_views_user_name', ['user_id', 'name'])


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if 'saved_views' in tables:
        indexes = {idx['name'] for idx in inspector.get_indexes('saved_views')}
        if 'uq_saved_views_user_name' in indexes:
            op.drop_index('uq_saved_views_user_name', table_name='saved_views')
        op.drop_table('saved_views')
