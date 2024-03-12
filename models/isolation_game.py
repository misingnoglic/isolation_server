from sqlalchemy import Column, Integer, String, Text, Float, Boolean, TIMESTAMP
import uuid
import datetime

try:
    from base import Base
except ImportError:
    from .base import Base


class IsolationGame(Base):
    __tablename__ = 'isolation_game'

    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    player1 = Column(String(100), nullable=False)
    player1_secret = Column(String(100), nullable=False)
    player2 = Column(String(100), default='')
    player2_secret = Column(String(100), default='')
    start_board = Column(Text, nullable=False)
    game_status = Column(String(100), nullable=False)
    game_state = Column(Text, default='')
    current_queen = Column(String(100), default='')
    last_move = Column(String(100), default='')
    winner = Column(String(100), default='')
    time_limit = Column(Integer, nullable=False)
    epoch_time_limit_next_move = Column(Float, default=0)
    num_random_turns = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    thread_id = Column(String(100), default='')
    discord = Column(Boolean, default=True)
    num_rounds = Column(Integer, default=1)
    player1_wins = Column(Integer, default=0)
    player2_wins = Column(Integer, default=0)
    new_game_uuid = Column(String(100), default='')
