import requests
from test_players import RandomPlayer
# from submission import CustomPlayer
import constants
import client_config
from server_isolation import Board
import json
import time
import click

# Set to the public URL
URL = client_config.BASE_URL
if URL[-1] == '/':
    URL = URL[:-1]
NEW_GAME = URL + '/game/new'
GAME_STATUS = URL + '/game/%s'
MAKE_MOVE = URL + '/game/%s/move'
JOIN_GAME = URL + '/game/%s/join'

# Set your player class here
PLAYER_CLASS = client_config.PLAYER_CLASS

PING_INTERVAL = 0.5

def test_run():
    player_1_name = 'player1'
    player_2_name = 'player2'
    player_1_secret = ''
    player_2_secret = ''


    new_game = requests.post(NEW_GAME, data={'player_name': player_1_name, 'time_limit': 10, 'start_board': 'CASTLE'})
    if not new_game.ok:
        print('Error', new_game.json())
        return
    print(new_game.json())
    game_id = new_game.json()['game_id']
    player_1_secret = new_game.json()['player_secret']
    player_1_bot = RandomPlayer(player_1_name, player_1_secret)

    game_status_request = requests.get(GAME_STATUS % game_id)
    print(game_status_request.json())

    # Create a new player to join the game
    join_game = requests.post(JOIN_GAME  % game_id, data={'player_name': player_2_name})
    print(join_game.json())
    player_2_secret = join_game.json()['player_secret']
    player_2_bot = RandomPlayer(player_2_name, player_2_secret)

    game_status_request = requests.get(GAME_STATUS % game_id)
    print(game_status_request.json())

    while True:
        game_status_request = requests.get(GAME_STATUS % game_id)
        if game_status_request.json()['game_status'] != constants.GameStatus.IN_PROGRESS:
            print('game over')
            game = Board.from_json(game_status_request.json()['game_state'])
            print(game.print_board())
            print(game_status_request.json())
            break
        # Get current player
        current_player = game_status_request.json()['current_queen']
        print(current_player)
        if current_player == player_1_name:
            player = player_1_bot
            print('player 1')
        elif current_player == player_2_name:
            player = player_2_bot
            print('player 2')
        else:
            raise ValueError('Unknown player')
        # Make a move
        game = Board.from_json(game_status_request.json()['game_state'])
        print(game.print_board())
        move = player.move(game, 10)
        print(move)
        make_move_request = requests.post(
            MAKE_MOVE % game_id, data={
                'player_name': player.get_name(), 'player_secret': player.secret, 'move': json.dumps(move), 'client_time': time.time()})
        print(make_move_request.json())
        time.sleep(PING_INTERVAL)


def host_game(my_name, time_limit):
    new_game = requests.post(NEW_GAME, data={'player_name': my_name, 'time_limit': int(time_limit), 'start_board': 'CASTLE'})
    if not new_game.ok:
        print('Error', new_game.json())
        return
    print('Game started, please give this code to your friend and we will start')
    game_id = new_game.json()['game_id']
    print(new_game.json()['game_id'])
    my_secret = new_game.json()['player_secret']
    agent = PLAYER_CLASS()
    agent.name = my_name

    while True:
        game_status_request = requests.get(GAME_STATUS % game_id)
        if game_status_request.json()['game_status'] != constants.GameStatus.NEED_SECOND_PLAYER:
            break
        time.sleep(PING_INTERVAL)

    print('game started')
    play_until_game_is_over(game_id, my_name, my_secret, agent)


def play_until_game_is_over(game_id, my_name, my_secret, agent):
    while True:
        game_status_request = requests.get(GAME_STATUS % game_id)
        if game_status_request.json()['game_status'] != constants.GameStatus.IN_PROGRESS:
            print('Game finished - winner is', game_status_request.json()['winner'])
            print('Final board:')
            game = Board.from_json(game_status_request.json()['game_state'])
            print(game.print_board())
            break

        if game_status_request.json()['current_queen'] != my_name:
            # print('not my turn yet')
            time.sleep(PING_INTERVAL)  # Let's wait for our turn
            continue

        print('Your turn')
        game = Board.from_json(game_status_request.json()['game_state'])
        print(game.print_board())
        time_left = lambda: 1000 * (game_status_request.json()['time_limit'] - (time.time() - game_status_request.json()['last_move_time']))
        move = agent.move(game, time_left)
        print('Time left', time_left())
        if move is None:
            raise ValueError('Move is None')
        print(move)
        make_move_request = requests.post(
            MAKE_MOVE % game_id, data={
                'player_name': my_name, 'player_secret': my_secret, 'move': json.dumps(move), 'client_time': time.time()})
        if not make_move_request.ok:
            print('Error', make_move_request.json())
            return
        time.sleep(PING_INTERVAL)


def join_game(game_id, my_name):
    join_game = requests.post(JOIN_GAME % game_id, data={'player_name': my_name})
    print(join_game.json())
    if not join_game.ok:
        print('Error', join_game.json())
        return
    print(join_game.json())
    my_secret = join_game.json()['player_secret']
    agent = PLAYER_CLASS()
    agent.name = my_name
    print('successfully joined game')
    play_until_game_is_over(game_id, my_name, my_secret, agent)


@click.command()
# Can either host or join a game
@click.option('--host', is_flag=True, help='Host a new game')
@click.option('--join', is_flag=True, help='Join an existing game')
@click.option('--test', is_flag=True, help='Host a new game')
@click.option('--game_id', help='Game ID to join')
@click.option('--name', help='Your name')
@click.option('--time_limit', help='Time limit for each move')
def main(host, join, test, game_id, name, time_limit):
    if host:
        host_game(name, time_limit)
    elif join:
        join_game(game_id, name)
    elif test:
        test_run()
    else:
        # print help text
        print('Please specify --host or --join')


if __name__ == '__main__':
    # test_run()
    main()
