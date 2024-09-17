## Modify these values to match your requirements - you will have to import your player class
from submission import CustomPlayer
from test_players import RandomPlayer

BASE_URL = 'http://isolation.eba-m5tmmetm.us-west-2.elasticbeanstalk.com'
PLAYER_CLASS = CustomPlayer

PLAYER_CLASSES = {
    'CustomPlayer': CustomPlayer,
    'RandomPlayer': RandomPlayer
}