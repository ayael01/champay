"""Adding reschedule update and sending for trip

Revision ID: f6d9b69f77fa
Revises: 8df07cf2769b
Create Date: 2023-09-21 15:14:07.693848

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6d9b69f77fa'
down_revision = '8df07cf2769b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('group', sa.Column('ics_uid', sa.String(length=128), nullable=True))
    op.add_column('group', sa.Column('ics_sequence', sa.Integer(), nullable=True))
    op.add_column('group', sa.Column('is_scheduled', sa.Boolean(), nullable=True))
    op.create_unique_constraint(None, 'group', ['ics_uid'])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'group', type_='unique')
    op.drop_column('group', 'is_scheduled')
    op.drop_column('group', 'ics_sequence')
    op.drop_column('group', 'ics_uid')
    # ### end Alembic commands ###
