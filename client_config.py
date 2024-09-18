## Modify these values to match your requirements - you will have to import your player class
from submission import CustomPlayer
from test_players import RandomPlayer

# Do not touch this
BASE_URL = 'http://isolation-dev.us-west-2.elasticbeanstalk.com'
# Change this to your player class
DEFAULT_PLAYER_CLASS = RandomPlayer

# If you want to test multiple player classes, you can add them here and set --player_to_use to the desired player
PLAYER_CLASSES = {
    'CustomPlayer': CustomPlayer,
    'RandomPlayer': RandomPlayer
}