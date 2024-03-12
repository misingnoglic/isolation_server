"""Change created/updated to be Float

Revision ID: 0bc4d05bebb1
Revises: 01accd19c74d
Create Date: 2024-03-11 23:34:59.491091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bc4d05bebb1'
down_revision: Union[str, None] = '01accd19c74d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change created_at and updated_at to Float
    op.add_column('isolation_game', sa.Column('created_at_temp', sa.Float(), server_default='0'))
    op.add_column('isolation_game', sa.Column('update_at_temp', sa.Float(), server_default='0'))

    # drop the old columns
    op.drop_column('isolation_game', 'created_at')
    op.drop_column('isolation_game', 'updated_at')

    # rename the new columns
    op.alter_column('isolation_game', 'created_at_temp', new_column_name='created_at')
    op.alter_column('isolation_game', 'update_at_temp', new_column_name='updated_at')


def downgrade() -> None:
    # Change Float to TIMESTAMP
    op.add_column('isolation_game', sa.Column('created_at_temp', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()))
    op.add_column('isolation_game', sa.Column('update_at_temp', sa.TIMESTAMP(), server_default=sa.func.now()))

    # drop the old columns
    op.drop_column('isolation_game', 'created_at')
    op.drop_column('isolation_game', 'updated_at')

    # rename the new columns
    op.alter_column('isolation_game', 'created_at_temp', new_column_name='created_at')
    op.alter_column('isolation_game', 'update_at_temp', new_column_name='updated_at')
