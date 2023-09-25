"""Adding datetime created for group

Revision ID: 88dff399a609
Revises: f6d9b69f77fa
Create Date: 2023-09-21 20:03:57.474311

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '88dff399a609'
down_revision = 'f6d9b69f77fa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('group', sa.Column('created_at', sa.DateTime(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('group', 'created_at')
    # ### end Alembic commands ###