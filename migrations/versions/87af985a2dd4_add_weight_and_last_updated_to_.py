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
    # create the group_member table
    op.create_table(
        'group_member',
        sa.Column('id', sa.Integer, primary_key=True),
        # include all other necessary columns here,
        # make sure the column definitions match those in your model
    )
    
    # then add new columns
    op.add_column('group_member', sa.Column('weight', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('group_member', sa.Column('last_updated', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_table('group_member')

