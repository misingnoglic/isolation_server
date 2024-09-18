## Modify these values to match your requirements - you will have to import your player class
from submission import CustomPlayer
from test_players import RandomPlayer

BASE_URL = 'http://127.0.0.1:5000'
DEFAULT_PLAYER_CLASS = RandomPlayer

PLAYER_CLASSES = {
    'CustomPlayer': CustomPlayer,
    'RandomPlayer': RandomPlayer
}