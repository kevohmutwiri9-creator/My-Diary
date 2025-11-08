"""Add security features and indexes

Revision ID: ec9c15efb2a8
Revises: bc65ec976c16
Create Date: 2025-10-26 09:08:01.289713

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'ec9c15efb2a8'
down_revision = 'bc65ec976c16'
branch_labels = None
depends_on = None


def _ensure_column(table, column_name, column):
    """Add column if it does not already exist."""
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {col['name'] for col in inspector.get_columns(table)}
    if column_name not in existing:
        op.add_column(table, column)


def _ensure_index(table, name, columns, unique=False):
    bind = op.get_bind()
    inspector = inspect(bind)
    existing = {idx['name'] for idx in inspector.get_indexes(table)}
    if name not in existing:
        op.create_index(name, table, columns, unique=unique)


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        inspector = inspect(bind)
        tables = set(inspector.get_table_names())

        if 'entries' not in tables and 'diary_entry' in tables:
            op.execute(sa.text('ALTER TABLE diary_entry RENAME TO entries'))
            inspector = inspect(bind)

        _ensure_column('entries', 'word_count', sa.Column('word_count', sa.Integer(), nullable=True))

        _ensure_index('entries', 'idx_entry_created', ['created_at'])
        _ensure_index('entries', 'idx_entry_user_created', ['user_id', 'created_at'])
        _ensure_index('entries', 'idx_entry_user_mood', ['user_id', 'mood'])
        _ensure_index('entries', 'idx_entry_user_private', ['user_id', 'is_private'])
        _ensure_index('entries', 'ix_entries_is_private', ['is_private'])
        _ensure_index('entries', 'ix_entries_mood', ['mood'])
        _ensure_index('entries', 'ix_entries_title', ['title'])
        _ensure_index('entries', 'ix_entries_updated_at', ['updated_at'])
        _ensure_index('entries', 'ix_entries_user_id', ['user_id'])

        _ensure_column('users', 'last_password_change', sa.Column('last_password_change', sa.DateTime(), nullable=True))
        _ensure_column('users', 'failed_login_attempts', sa.Column('failed_login_attempts', sa.Integer(), nullable=True))
        _ensure_column('users', 'account_locked_until', sa.Column('account_locked_until', sa.DateTime(), nullable=True))
        # SQLite cannot ALTER COLUMN to change type; keep existing password_hash length.
    else:
        # Original logic for databases that fully support ALTER TABLE
        with op.batch_alter_table('entries', schema=None) as batch_op:
            batch_op.add_column(sa.Column('word_count', sa.Integer(), nullable=True))
            batch_op.create_index('idx_entry_created', ['created_at'], unique=False)
            batch_op.create_index('idx_entry_user_created', ['user_id', 'created_at'], unique=False)
            batch_op.create_index('idx_entry_user_mood', ['user_id', 'mood'], unique=False)
            batch_op.create_index('idx_entry_user_private', ['user_id', 'is_private'], unique=False)
            batch_op.create_index(batch_op.f('ix_entries_is_private'), ['is_private'], unique=False)
            batch_op.create_index(batch_op.f('ix_entries_mood'), ['mood'], unique=False)
            batch_op.create_index(batch_op.f('ix_entries_title'), ['title'], unique=False)
            batch_op.create_index(batch_op.f('ix_entries_updated_at'), ['updated_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_entries_user_id'), ['user_id'], unique=False)

        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.add_column(sa.Column('last_password_change', sa.DateTime(), nullable=True))
            batch_op.add_column(sa.Column('failed_login_attempts', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('account_locked_until', sa.DateTime(), nullable=True))
            batch_op.alter_column('password_hash',
                   existing_type=sa.VARCHAR(length=128),
                   type_=sa.String(length=256),
                   existing_nullable=True)


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'sqlite':
        inspector = inspect(bind)
        entry_indexes = {idx['name'] for idx in inspector.get_indexes('entries')}
        user_columns = {col['name'] for col in inspector.get_columns('users')}

        for index_name in [
            'ix_entries_user_id',
            'ix_entries_updated_at',
            'ix_entries_title',
            'ix_entries_mood',
            'ix_entries_is_private',
            'idx_entry_user_private',
            'idx_entry_user_mood',
            'idx_entry_user_created',
            'idx_entry_created',
        ]:
            if index_name in entry_indexes:
                op.drop_index(index_name, table_name='entries')

        entry_columns = {col['name'] for col in inspector.get_columns('entries')}
        if 'word_count' in entry_columns:
            op.drop_column('entries', 'word_count')

        for column in ['account_locked_until', 'failed_login_attempts', 'last_password_change']:
            if column in user_columns:
                op.drop_column('users', column)
        # Skipping password_hash length reduction for SQLite.
    else:
        with op.batch_alter_table('users', schema=None) as batch_op:
            batch_op.alter_column('password_hash',
                   existing_type=sa.String(length=256),
                   type_=sa.VARCHAR(length=128),
                   existing_nullable=True)
            batch_op.drop_column('account_locked_until')
            batch_op.drop_column('failed_login_attempts')
            batch_op.drop_column('last_password_change')

        with op.batch_alter_table('entries', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_entries_user_id'))
            batch_op.drop_index(batch_op.f('ix_entries_updated_at'))
            batch_op.drop_index(batch_op.f('ix_entries_title'))
            batch_op.drop_index(batch_op.f('ix_entries_mood'))
            batch_op.drop_index(batch_op.f('ix_entries_is_private'))
            batch_op.drop_index('idx_entry_user_private')
            batch_op.drop_index('idx_entry_user_mood')
            batch_op.drop_index('idx_entry_user_created')
            batch_op.drop_index('idx_entry_created')
            batch_op.drop_column('word_count')
