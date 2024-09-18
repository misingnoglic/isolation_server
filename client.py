import requests
from test_players import RandomPlayer
# from submission import CustomPlayer
import constants
import client_config
from server_isolation import Board
import json
import time
import datetime
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
PLAYER_CLASS = client_config.DEFAULT_PLAYER_CLASS

PING_INTERVAL = 0.5

def test_run():
    player_1_name = 'player1'
    player_2_name = 'player2'
    player_1_secret = ''
    player_2_secret = ''

    new_game = requests.post(NEW_GAME, data={'player_name': player_1_name, 'time_limit': 10, 'start_board': 'CASTLE', 'num_random_turns': 1, 'webhook': ''})
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
                'player_name': player.get_name(), 'player_secret': player.secret, 'move': json.dumps(move), 'client_time': datetime.datetime.utcnow().timestamp()})
        print(make_move_request.json())
        time.sleep(PING_INTERVAL)


def host_game(my_name, time_limit, start_board, num_random_turns, discord, secret, num_rounds, player_to_use):
    payload = {'player_name': my_name, 'time_limit': int(time_limit), 'start_board': start_board, 'num_random_turns': num_random_turns, 'discord': discord, 'secret': secret, 'num_rounds': num_rounds}
    new_game = requests.post(NEW_GAME, data=payload)
    if not new_game.ok:
        print('Error', new_game.json())
        return
    print('Game started, please give this code to your friend and we will start')
    game_id = new_game.json()['game_id']
    print(new_game.json()['game_id'])
    my_secret = new_game.json()['player_secret']
    if player_to_use:
        agent = client_config.PLAYER_CLASSES[player_to_use]()
    else:
        agent = PLAYER_CLASS()
    agent.name = my_name

    while True:
        game_status_request = requests.get(GAME_STATUS % game_id)
        if not game_status_request.ok:
            print('Error', game_status_request.text)
            return
        if game_status_request.json()['game_status'] != constants.GameStatus.NEED_SECOND_PLAYER:
            break
        time.sleep(PING_INTERVAL)

    print('game started')
    play_until_game_is_over(game_id, my_name, my_secret, agent)


def play_until_game_is_over(game_id, my_name, my_secret, agent):
    while True:
        game_status_request = requests.get(GAME_STATUS % game_id)
        if not game_status_request.ok:
            print('Error', game_status_request)
            return
        if game_status_request.json()['game_status'] != constants.GameStatus.IN_PROGRESS:
            print('Game finished - winner is', game_status_request.json()['winner'])
            print('Final board:')
            game_state = game_status_request.json()['game_state']
            if game_state:
                game = Board.from_json(game_state)
                print(game.print_board())
                print(game_status_request.json())
            if game_status_request.json()['new_game_uuid']:
                game_id = game_status_request.json()['new_game_uuid']
                print('New game started', game_id)
                continue
            else:
                break

        if game_status_request.json()['current_queen'] != my_name:
            # print('not my turn yet')
            time.sleep(PING_INTERVAL)  # Let's wait for our turn
            continue
        print('Your turn')
        game = Board.from_json(game_status_request.json()['game_state'])
        print(game.print_board())
        print(f'Last move time: {game_status_request.json()["last_move_time"]}')
        start_time = time.time()
        time_left = lambda: 1000 * (game_status_request.json()['time_left'] - (time.time() - start_time))
        print('Time left start', time_left())
        move = agent.move(game, time_left)
        print('Time left end', time_left())
        if move is None:
            raise ValueError('Move is None')
        print(move)
        make_move_request = requests.post(
            MAKE_MOVE % game_id, data={
                'player_name': my_name, 'player_secret': my_secret, 'move': json.dumps(move), 'client_time': datetime.datetime.utcnow().timestamp()})
        if not make_move_request.ok:
            print('Error', make_move_request.text)
            return
        time.sleep(PING_INTERVAL)


def join_game(game_id, my_name, player_to_use):
    join_game = requests.post(JOIN_GAME % game_id, data={'player_name': my_name})
    print(join_game.json())
    if not join_game.ok:
        print('Error', join_game.json())
        return
    print(join_game.json())
    my_secret = join_game.json()['player_secret']
    if player_to_use:
        agent = client_config.PLAYER_CLASSES[player_to_use]()
    else:
        agent = PLAYER_CLASS()
    agent.name = my_name
    print('successfully joined game')
    play_until_game_is_over(game_id, my_name, my_secret, agent)


def observe_game(game_id):
    prev_game_status = None
    prev_current_queen = None
    while True:
        game_status_request = requests.get(GAME_STATUS % game_id)
        game_status = game_status_request.json()
        if game_status != prev_game_status or game_status['current_queen'] != prev_current_queen:
            current_status = game_status['game_status']
            print(f'Game status: {current_status}')
            print(f'Current knight: {game_status["current_queen"]}')
            print(f'Last move: {game_status["last_move"]}')
            board_state = game_status['game_state']
            game = Board.from_json(board_state)
            print(game.print_board())
            prev_game_status = game_status
            prev_current_queen = game_status['current_queen']

            if current_status == constants.GameStatus.FINISHED:
                break


@click.command()
# Can either host or join a game
@click.option('--host', is_flag=True, help='Host a new game')
@click.option('--join', is_flag=True, help='Join an existing game')
@click.option('--observe', is_flag=True, help='Observe an existing game')
@click.option('--test', is_flag=True, help='Host a new game')
@click.option('--game_id', help='Game ID to join')
@click.option('--start_board', help='Start board (DEFAULT or CASTLE or RANDOM or JSON dumped custom board of spaces and Xs)', default='DEFAULT')
@click.option('--num_random_turns', help='Number of random turns to make at the start', default=0, type=int)
@click.option('--name', help='Your name')
@click.option('--time_limit', default=None, help='Time limit for each move')
@click.option('--discord/--no_discord', help='Whether to replay on class Discord server', default=True, is_flag=True)
@click.option('--secret', help='Whether to announce the game to class Discord server', is_flag=True)
@click.option('--num_rounds', help='Number of rounds to play', default=1, type=int)
@click.option('--player_to_use', help='Which config player to use', default='')
def main(host, join, observe, test, game_id, start_board, num_random_turns, name, time_limit, discord, secret, num_rounds, player_to_use):
    if host:
        host_game(name, time_limit, start_board, num_random_turns, discord, secret, num_rounds, player_to_use)
    elif join:
        join_game(game_id, name, player_to_use)
    elif test:
        test_run()
    elif observe:
        observe_game(game_id)
    else:
        print('Invalid arguments. Use --help for help')


if __name__ == '__main__':
    # test_run()
    main()
