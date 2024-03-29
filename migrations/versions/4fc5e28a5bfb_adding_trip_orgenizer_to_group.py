"""Adding trip orgenizer to group

Revision ID: 4fc5e28a5bfb
Revises: 88dff399a609
Create Date: 2023-09-26 16:49:58.559843

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4fc5e28a5bfb'
down_revision = '88dff399a609'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('group', sa.Column('organizer_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'group', 'user', ['organizer_id'], ['id'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'group', type_='foreignkey')
    op.drop_column('group', 'organizer_id')
    # ### end Alembic commands ###
