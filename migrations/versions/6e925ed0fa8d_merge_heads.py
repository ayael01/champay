"""merge heads

Revision ID: 6e925ed0fa8d
Revises: 75ca6fa39bc3, 87af985a2dd4
Create Date: 2023-07-16 16:15:07.582962

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6e925ed0fa8d'
down_revision = ('75ca6fa39bc3', '87af985a2dd4')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
