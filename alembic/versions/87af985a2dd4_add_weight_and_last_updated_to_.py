"""add weight and last_updated to GroupMember

Revision ID: 87af985a2dd4
Revises: 
Create Date: 2023-06-23 14:34:10.891508

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '87af985a2dd4'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('group_member', sa.Column('weight', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('group_member', sa.Column('last_updated', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('group_member', 'weight')
    op.drop_column('group_member', 'last_updated')
