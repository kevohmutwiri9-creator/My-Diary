"""add onboarding and reminder fields to users

Revision ID: add_onboarding_and_reminders
Revises: add_allow_ads_flag
Create Date: 2025-11-08 05:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_onboarding_and_reminders'
down_revision = 'add_allow_ads_flag'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'onboarding_state' not in columns:
        op.add_column('users', sa.Column('onboarding_state', sa.JSON(), nullable=True))
    if 'reminder_opt_in' not in columns:
        op.add_column('users', sa.Column('reminder_opt_in', sa.Boolean(), nullable=False, server_default=sa.false()))
        op.execute(sa.text("UPDATE users SET reminder_opt_in = 0"))
    if 'reminder_frequency' not in columns:
        op.add_column('users', sa.Column('reminder_frequency', sa.String(length=20), nullable=False, server_default='weekly'))
        op.execute(sa.text("UPDATE users SET reminder_frequency = 'weekly' WHERE reminder_frequency IS NULL"))
    if 'reminder_last_sent' not in columns:
        op.add_column('users', sa.Column('reminder_last_sent', sa.DateTime(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col['name'] for col in inspector.get_columns('users')]

    if 'reminder_last_sent' in columns:
        op.drop_column('users', 'reminder_last_sent')
    if 'reminder_frequency' in columns:
        op.drop_column('users', 'reminder_frequency')
    if 'reminder_opt_in' in columns:
        op.drop_column('users', 'reminder_opt_in')
    if 'onboarding_state' in columns:
        op.drop_column('users', 'onboarding_state')
