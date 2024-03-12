"""Change timestamp to have timezone

Revision ID: 01accd19c74d
Revises: 91c5a4d86377
Create Date: 2024-03-11 22:50:55.793896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01accd19c74d'
down_revision: Union[str, None] = '91c5a4d86377'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Change TIMESTAMP to TIMESTAMP(timezone=True)
    op.alter_column('isolation_game', 'created_at', type_=sa.TIMESTAMP(timezone=True))


def downgrade() -> None:
    # Change TIMESTAMP(timezone=True) to TIMESTAMP
    op.alter_column('isolation_game', 'created_at', type_=sa.TIMESTAMP())

