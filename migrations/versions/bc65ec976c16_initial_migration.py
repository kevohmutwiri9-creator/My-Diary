"""Initial migration

Revision ID: bc65ec976c16
Revises: 
Create Date: 2025-10-25 09:21:55.673813

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'bc65ec976c16'
down_revision = None
branch_labels = None
depends_on = None


def _ensure_index(table, name, columns, unique=False):
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {idx['name'] for idx in inspector.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns, unique=unique)


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if 'diary_entry' in tables and 'entries' not in tables:
        op.execute(sa.text('ALTER TABLE diary_entry RENAME TO entries'))
        inspector = inspect(bind)
        tables = set(inspector.get_table_names())
    elif 'diary_entry' in tables:
        op.execute(sa.text('DROP TABLE IF EXISTS diary_entry'))
        inspector = inspect(bind)
        tables = set(inspector.get_table_names())

    if 'users' not in tables:
        op.create_table(
            'users',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('username', sa.String(length=64), nullable=False, unique=True),
            sa.Column('email', sa.String(length=120), nullable=False, unique=True),
            sa.Column('password_hash', sa.String(length=128), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('last_seen', sa.DateTime(), nullable=True),
            sa.Column('is_admin', sa.Boolean(), nullable=True, server_default=sa.sql.expression.false()),
        )
        inspector = inspect(bind)

    _ensure_index('users', 'ix_users_email', ['email'], unique=True)
    _ensure_index('users', 'ix_users_username', ['username'], unique=True)

    tables = set(inspector.get_table_names())
    if 'entries' not in tables:
        op.create_table(
            'entries',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('title', sa.String(length=200), nullable=True),
            sa.Column('content', sa.Text(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('is_private', sa.Boolean(), nullable=True, server_default=sa.sql.expression.true()),
            sa.Column('mood', sa.String(length=50), nullable=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        )
        inspector = inspect(bind)

    _ensure_index('entries', 'ix_entries_user_id', ['user_id'])
    _ensure_index('entries', 'ix_entries_created_at', ['created_at'])

    tables = set(inspector.get_table_names())
    if 'entry_templates' not in tables:
        op.create_table(
            'entry_templates',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('description', sa.String(length=200), nullable=True),
            sa.Column('category', sa.String(length=50), nullable=False),
            sa.Column('template_content', sa.Text(), nullable=False),
            sa.Column('icon', sa.String(length=50), nullable=True, server_default='bi-journal-text'),
            sa.Column('is_default', sa.Boolean(), nullable=True, server_default=sa.sql.expression.false()),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=True),
        )
        inspector = inspect(bind)

    _ensure_index('entry_templates', 'ix_entry_templates_category', ['category'])
    _ensure_index('entry_templates', 'ix_entry_templates_user_id', ['user_id'])


def downgrade():
    op.drop_index('ix_entry_templates_user_id', table_name='entry_templates')
    op.drop_index('ix_entry_templates_category', table_name='entry_templates')
    op.drop_table('entry_templates')

    op.drop_index('ix_entries_created_at', table_name='entries')
    op.drop_index('ix_entries_user_id', table_name='entries')
    op.drop_table('entries')

    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
