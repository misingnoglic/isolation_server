"""Change updated_at to have timezone

Revision ID: a3640492bf45
Revises: 01accd19c74d
Create Date: 2024-03-11 23:01:53.065901

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3640492bf45'
down_revision: Union[str, None] = '01accd19c74d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change TIMESTAMP to TIMESTAMP(timezone=True)
    op.alter_column('isolation_game', 'updated_at', type_=sa.TIMESTAMP(timezone=True))


def downgrade() -> None:
    # Change TIMESTAMP(timezone=True) to TIMESTAMP
    op.alter_column('isolation_game', 'updated_at', type_=sa.TIMESTAMP())

