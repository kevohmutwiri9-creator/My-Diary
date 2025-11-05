"""add tags and entry tag association

Revision ID: add_tags
Revises: add_user_streak_fields
Create Date: 2025-10-28 11:50:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_tags'
down_revision = 'add_saved_views'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'tags' not in inspector.get_table_names():
        op.create_table(
            'tags',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('name', sa.String(length=50), nullable=False),
            sa.Column('slug', sa.String(length=64), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('name'),
            sa.UniqueConstraint('slug')
        )
        op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=False)
        op.create_index(op.f('ix_tags_slug'), 'tags', ['slug'], unique=False)

    if 'entry_tags' not in inspector.get_table_names():
        op.create_table(
            'entry_tags',
            sa.Column('entry_id', sa.Integer(), nullable=False),
            sa.Column('tag_id', sa.Integer(), nullable=False),
            sa.ForeignKeyConstraint(['entry_id'], ['entries.id'], ),
            sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
            sa.PrimaryKeyConstraint('entry_id', 'tag_id')
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    if 'entry_tags' in inspector.get_table_names():
        op.drop_table('entry_tags')

    if 'tags' in inspector.get_table_names():
        op.drop_index(op.f('ix_tags_slug'), table_name='tags')
        op.drop_index(op.f('ix_tags_name'), table_name='tags')
        op.drop_table('tags')
