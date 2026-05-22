"""add_xp_coins_notifications_playlists_progress_reports_reset_tokens

Revision ID: 3e3d6873d7ea
Revises: cf4cb00effbb
Create Date: 2026-05-21 16:09:37.471408

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3e3d6873d7ea'
down_revision = 'cf4cb00effbb'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('xp', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('coins_balance', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('coins_balance')
        batch_op.drop_column('xp')
