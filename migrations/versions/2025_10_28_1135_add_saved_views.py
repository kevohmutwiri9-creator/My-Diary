"""create saved views table

Revision ID: add_saved_views
Revises: add_user_streak_fields
Create Date: 2025-10-28 11:35:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_saved_views'
down_revision = 'add_user_streak_fields'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'saved_views',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('filters', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_unique_constraint('uq_saved_views_user_name', 'saved_views', ['user_id', 'name'])

def downgrade():
    op.drop_constraint('uq_saved_views_user_name', 'saved_views', type_='unique')
    op.drop_table('saved_views')
