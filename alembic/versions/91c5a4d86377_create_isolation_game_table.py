"""Create isolation_game table

Revision ID: 91c5a4d86377
Revises: 
Create Date: 2024-03-09 14:16:16.713855

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '91c5a4d86377'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('isolation_game',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('uuid', sa.String(length=100), nullable=False),
    sa.Column('player1', sa.String(length=100), nullable=False),
    sa.Column('player1_secret', sa.String(length=100), nullable=False),
    sa.Column('player2', sa.String(length=100), nullable=True),
    sa.Column('player2_secret', sa.String(length=100), nullable=True),
    sa.Column('start_board', sa.Text(), nullable=False),
    sa.Column('game_status', sa.String(length=100), nullable=False),
    sa.Column('game_state', sa.Text(), nullable=True),
    sa.Column('current_queen', sa.String(length=100), nullable=True),
    sa.Column('last_move', sa.String(length=100), nullable=True),
    sa.Column('winner', sa.String(length=100), nullable=True),
    sa.Column('time_limit', sa.Integer(), nullable=False),
    sa.Column('epoch_time_limit_next_move', sa.Float(), nullable=True),
    sa.Column('num_random_turns', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
    sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
    sa.Column('thread_id', sa.String(length=100), nullable=True),
    sa.Column('discord', sa.Boolean(), nullable=True),
    sa.Column('num_rounds', sa.Integer(), nullable=True),
    sa.Column('player1_wins', sa.Integer(), nullable=True),
    sa.Column('player2_wins', sa.Integer(), nullable=True),
    sa.Column('new_game_uuid', sa.String(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('uuid')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('isolation_game')
    # ### end Alembic commands ###
