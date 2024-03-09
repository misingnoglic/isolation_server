import flask
import uuid
import sqlite3
from flask import request
import random
import json
from server_isolation import Board
import time
import constants
from discord_webhook import DiscordWebhook, DiscordEmbed
try:
    import server_secrets_hardcoded as server_secrets
except ImportError:
    import server_secrets

application = flask.Flask(__name__)
import logging
log = logging.getLogger('werkzeug')


@application.route('/game/new', methods=['POST'])
def host_game():
    """Host a new game.
    POST variables:
    - player_name: the name of the player
    - time_limit: the time limit for the game
    - start_board: JSON string of default board for the game (if None, will be the standard board. If "CASTLE" will be the castle board)
    - num_random_turns: number of random turns to make at the start
    - discord: Whether to send updates to Discord
    - secret: Whether to announce game beforehand on Discord
    """
    game_id = str(uuid.uuid4())
    player_secret = str(uuid.uuid4())
    start_board = request.form['start_board']
    num_random_turns = 0  # TODO: This results in really buggy games, so I'm setting it to 0 for now
    num_rounds = int(request.form.get('num_rounds', 1))
    time_limit = request.form['time_limit']
    if 60 < int(time_limit) < 1:
        return flask.jsonify({'status': 'error', 'message': f'Invalid time limit {time_limit}, must be between 1 and 60'}), 400
    discord = False if request.form.get('discord') == 'False' else True
    secret = True if request.form.get('secret') == 'True' else False
    # Store this game ID in the db
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO isolationgame (uuid, player1, player1_secret, start_board, game_status, time_limit, num_random_turns, discord, num_rounds, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (game_id, request.form['player_name'], player_secret, start_board, constants.GameStatus.NEED_SECOND_PLAYER, time_limit, num_random_turns, discord, num_rounds, time.time()))
    conn.commit()
    conn.close()
    if discord and not secret:
        webhook = DiscordWebhook(url=server_secrets.ANNOUNCEMENT_WEBHOOK_URL)
        start_board_str = start_board if len(start_board) < 20 else "CUSTOM"
        rules = f'start_board = {start_board_str}, time limit = {request.form["time_limit"]}, num rounds = {num_rounds}'
        embed = DiscordEmbed(title="New Game!", description=f'{request.form["player_name"]} is waiting for a player, join them with this game ID: {game_id}. Rules are: {rules}')
        webhook.add_embed(embed)
        webhook.execute()
    return flask.jsonify({'game_id': game_id, 'player_secret': player_secret})


def announce_game_start_in_main_channel(player1, player2, thread_id):
    webhook = DiscordWebhook(url=server_secrets.ANNOUNCEMENT_WEBHOOK_URL)
    embed = DiscordEmbed(title="Game Started!", description=f'{player1} vs {player2} has started! Click [here](https://discord.com/channels/{server_secrets.DISCORD_CHANNEL_ID}/{thread_id}) to watch along!')
    webhook.add_embed(embed)
    webhook.execute()


def announce_game_start_timeout(game_id):
    webhook = DiscordWebhook(url=server_secrets.ANNOUNCEMENT_WEBHOOK_URL)
    embed = DiscordEmbed(title="Timeout", description=f'Nobody joined {game_id} in time! Please start a new game')
    webhook.add_embed(embed)
    webhook.execute()


def start_game_thread(player1, player2, game_id):
    webhook = DiscordWebhook(url=server_secrets.GAME_WEBHOOK_URL, thread_name=f'{player1} vs {player2} - {game_id}', content='Good luck everyone!')
    response = webhook.execute()
    return response.json()['id']


def announce_game_move(board, cur_game, player_name, move):
    if not cur_game['thread_id'] or not cur_game['discord']:
        return
    formatted_board = emojify_board(board.print_board())
    webhook = DiscordWebhook(url=server_secrets.GAME_WEBHOOK_URL, thread_id=cur_game['thread_id'])
    if cur_game['player1'] == player_name:
        player_icon = "🟥"
        color = "c41e3a"
    else:
        player_icon = "🟦"
        color = "1e5ac4"
    embed = DiscordEmbed(title=f'{cur_game["player1"]} vs {cur_game["player2"]} - Round {cur_game["player1_wins"] + cur_game["player2_wins"] + 1} - Move #{board.move_count}', description=formatted_board, color=color)
    embed.set_footer(text=f'{player_icon} {board.get_inactive_player()} moved to {str(move[0])}, {str(move[1])}')
    webhook.add_embed(embed)
    webhook.execute()


def announce_game_over(thread_id, winner, board, last_round, player1_wins, player2_wins, reason=""):
    if not thread_id:
        return
    webhook = DiscordWebhook(thread_id=thread_id, url=server_secrets.GAME_WEBHOOK_URL)
    title = "GAME OVER!"
    if reason:
        title = f'{title} - {reason}'
    if last_round:
        title = f'{title} - Last Round!'
    embed = DiscordEmbed(title=title, description=f'{winner} wins! Score: {player1_wins} - {player2_wins}')
    webhook.add_embed(embed)
    webhook.execute()
    embed = DiscordEmbed(title='Final Board', description=emojify_board(board.print_board()))
    webhook.add_embed(embed)
    webhook.execute()


@application.route('/game/<game_id>/join', methods=['POST'])
def join_game(game_id):
    """Join a game.
    POST variables:
    - player_name: the name of the player
    """
    player_name = request.form['player_name']
    player_secret = str(uuid.uuid4())
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    c.row_factory = sqlite3.Row
    # Make sure the game exists and is waiting for a player
    c.execute("SELECT * FROM isolationgame WHERE uuid = ? AND game_status = ?", (game_id, constants.GameStatus.NEED_SECOND_PLAYER))
    cur_game = c.fetchone()
    if cur_game is None:
        return flask.jsonify({'status': 'error', 'message': 'Game not found or not waiting for a player'}), 400
    # Get the cur_game's player
    host_player = cur_game['player1']
    if host_player == player_name:
        return flask.jsonify({'status': 'error', 'message': 'You cannot join your own game'}), 400

    first_player = random.choice([player_name, host_player])
    second_player = host_player if first_player == player_name else player_name
    board = cur_game['start_board']
    if board == "DEFAULT":
        board = constants.DEFAULT_BOARD
    elif board == "CASTLE":
        board = constants.CASTLE_BOARD
    else:
        board = json.loads(board)


    new_game = Board(host_player, player_name, board, first_player == host_player)

    num_random_turns = cur_game['num_random_turns']
    last_move = ''
    for _ in range(num_random_turns):
        last_move = new_game.__apply_move__(random.choice(new_game.get_player_moves(first_player)))
        last_move = new_game.__apply_move__(random.choice(new_game.get_player_moves(second_player)))
    last_move = json.dumps(last_move)
    new_game_json = new_game.to_json()
    thread_id = ''
    # Need to add thread ID to DB, that's why we're calling it before.
    if cur_game['discord']:
        thread_id = start_game_thread(host_player, player_name, game_id)
        announce_game_start_in_main_channel(host_player, player_name, thread_id)
    c.execute(
        "UPDATE isolationgame SET player2 = ?, player2_secret = ?, game_status = ?, game_state = ?, current_queen = ?, last_move = ?, thread_id = ?, updated_at = ? WHERE uuid = ? AND game_status = ?",
        (request.form['player_name'], player_secret, constants.GameStatus.IN_PROGRESS, new_game_json, first_player, last_move, thread_id, time.time(), game_id, constants.GameStatus.NEED_SECOND_PLAYER)
    )

    conn.commit()
    conn.close()
    return flask.jsonify({'player_secret': player_secret, 'first_player': first_player})


def _get_game_status(game_id):
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    c.row_factory = sqlite3.Row
    c.execute("SELECT * FROM isolationgame WHERE uuid = ?", (game_id,))
    cur_game = c.fetchone()
    if cur_game is None:
        return None
    return {
            'game_status': cur_game['game_status'],
            'current_queen': cur_game['current_queen'],
            'player1': cur_game['player1'],
            'player2': cur_game['player2'],
            'time_limit': cur_game['time_limit'],
            'winner': cur_game['winner'],
            'last_move_time': cur_game['updated_at'],
            'last_move': cur_game['last_move'],
            'game_state': cur_game['game_state'],
            'new_game_uuid': cur_game['new_game_uuid'],
            'created_at': cur_game['created_at'],
            'updated_at': cur_game['updated_at'],
        }


@application.route('/game/<game_id>', methods=['GET'])
def get_game_status(game_id):
    """Get the state of a game.
    """
    game_status = _get_game_status(game_id)
    if game_status is None:
        return flask.jsonify({'status': 'error', 'message': 'Game not found'}), 404
    if game_status['game_status'] == constants.GameStatus.IN_PROGRESS and game_status['last_move_time'] and game_status['last_move_time'] + game_status['time_limit'] + 15 < time.time():
        # Update status to finished and set the winner to the other player
        _end_game(game_id, game_status['player1'] if game_status['current_queen'] == game_status['player2'] else game_status['player2'], reason=f'Timeout, status checked and significant time after last move')
    if game_status['game_status'] == constants.GameStatus.NEED_SECOND_PLAYER and game_status['created_at'] + 60 * 5 < time.time():
        # Update status to finished and set the winner to the other player
        announce_game_start_timeout(game_id)
        _end_game(game_id, '', reason=f'No second player joined in time')
    return flask.jsonify(game_status)


def generate_new_game_with_prev_game_data(game_id, conn, player1_wins, player2_wins):
    c = conn.cursor()
    c.row_factory = sqlite3.Row
    c.execute("SELECT * FROM isolationgame WHERE uuid = ?", (game_id,))
    cur_game = c.fetchone()
    first_player = random.choice([cur_game['player1'], cur_game['player2']])
    new_uuid = str(uuid.uuid4())
    board = cur_game['start_board']
    if board == "DEFAULT":
        board = constants.DEFAULT_BOARD
    elif board == "CASTLE":
        board = constants.CASTLE_BOARD
    else:
        board = json.loads(board)

    new_game = Board(cur_game['player1'], cur_game['player2'], board, first_player == cur_game['player1'])
    new_game_json = new_game.to_json()

    c.execute('INSERT INTO isolationgame (uuid, player1, player1_secret, player2, player2_secret, start_board, game_state, game_status, time_limit, num_random_turns, discord, num_rounds, current_queen, last_move, thread_id, player1_wins, player2_wins, updated_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
              (new_uuid, cur_game['player1'], cur_game['player1_secret'], cur_game['player2'], cur_game['player2_secret'], cur_game['start_board'], new_game_json, constants.GameStatus.IN_PROGRESS, cur_game['time_limit'], cur_game['num_random_turns'], cur_game['discord'], cur_game['num_rounds']-1, first_player, '', cur_game['thread_id'], player1_wins, player2_wins, time.time(), time.time()))
    conn.commit()
    return new_uuid


def _end_game(game_id, winner, reason=''):
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    # c.row_factory = sqlite3.Row
    # Get game from DB
    c.execute("SELECT game_status, discord, thread_id, game_state, num_rounds, player1, player2, player1_wins, player2_wins FROM isolationgame WHERE uuid = ?", (game_id,))
    game_status, discord, thread_id, game_state, num_rounds, player1, player2, player1_wins, player2_wins = c.fetchone()
    if winner.split(" - ")[0] == player1:
        player1_wins += 1
    elif winner.split(" - ")[0] == player2:
        player2_wins += 1
    else:
        raise ValueError(f'Unknown winner {winner}')
    new_game_uuid = ''
    num_rounds -= 1
    if num_rounds > 0 and abs(player1_wins - player2_wins) <= num_rounds:
        new_game_uuid = generate_new_game_with_prev_game_data(game_id, conn, player1_wins, player2_wins)

    c.execute("UPDATE isolationgame SET game_status = ?, winner = ?, new_game_uuid = ?, player1_wins = ?, player2_wins=? WHERE uuid = ?", (constants.GameStatus.FINISHED, winner, new_game_uuid, player1_wins, player2_wins, game_id))
    conn.commit()
    conn.close()
    board = Board.from_json(game_state)
    if discord and thread_id and game_status != constants.GameStatus.NEED_SECOND_PLAYER:
        announce_game_over(thread_id, winner, board, new_game_uuid == "", player1_wins, player2_wins, reason=reason)
    return flask.jsonify(
        _get_game_status(game_id)
    )


@application.route('/game/<game_id>/move', methods=['POST'])
def make_move(game_id):
    """
    Make a move in a game.
    :param game_id:
    POST variables:
    - player_name: the name of the player
    - player_secret: the secret of the player making the move
    - move: the move to make (JSON string of two coordinates)
    - client_time: time.time() - the time the client thinks it is when it sends (to account for ping, honor system)
    :return:
    - New board state
    - New game state
    - Winner (if game is over)
    """

    # Get the game
    player_name = request.form['player_name']
    player_secret = request.form['player_secret']
    move = request.form['move']
    if move:
        move = tuple(json.loads(move))
    client_time = float(request.form['client_time'])
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    c.row_factory = sqlite3.Row
    c.execute("SELECT * FROM isolationgame WHERE uuid = ?", (game_id,))
    cur_game = c.fetchone()
    if cur_game is None:
        return flask.jsonify({'status': 'error', 'message': 'Game not found'}), 400

    # Check that the game is in progress or waiting to start
    if cur_game['game_status'] != constants.GameStatus.IN_PROGRESS:
        return flask.jsonify({'status': 'error', 'message': 'Game not in progress'}), 400

    # Check that the player is in the game
    if cur_game['player1'] != player_name and cur_game['player2'] != player_name:
        return flask.jsonify({'status': 'error', 'message': 'Player not in game'}), 400

    # Check that it is the player's turn, and the secret is correct
    if (cur_game['current_queen'] == cur_game['player1']):
        # Test that the current player is the host and the secret is correct
        other_player = cur_game['player2']
        if cur_game['player1'] == player_name and cur_game['player1_secret'] != player_secret:
            return flask.jsonify({'status': 'error', 'message': 'Invalid next player'}), 400
    else:
        # Test that the current player is the guest and the secret is correct
        other_player = cur_game['player1']
        if cur_game['player2'] == player_name and cur_game['player2_secret'] != player_secret:
            return flask.jsonify({'status': 'error', 'message': 'Invalid next player'}), 400

    # Check that the timestamp they sent is within 1 second of the server's time
    # This is causing issues, so I am ignoring it for now
    # if time.time() - client_time > 1:
    #     c.execute("UPDATE isolationgame SET game_status = ?, winner = ? WHERE uuid = ?", (constants.GameStatus.FINISHED, other_player, game_id))
    #     return flask.jsonify({'status': 'error', 'message': 'I don\'t believe your timestamp...'}), 400

    # Check their timestamp is within the time limit (within some bounds)
    if client_time - cur_game['updated_at'] > (1 + cur_game['time_limit']):
        # Set the game as finished
        return _end_game(game_id, other_player, reason=f'You took too long, client_time: {client_time}, last move at: {cur_game["updated_at"]}, time_limit: {cur_game["time_limit"]}')

    # Create the board based on the game state and make the move
    board = Board.from_json(cur_game['game_state'])
    # Check that the move is legal
    if move not in board.get_player_moves(player_name):
        return _end_game(
            game_id, other_player,
            reason=f'Illegal Move for {player_name} - {move}. Legal moves: {board.get_player_moves(player_name)}'
        )

    game_over, winner = board.__apply_move__(move)
    new_game_state = board.to_json()
    new_game_status = constants.GameStatus.FINISHED if game_over else constants.GameStatus.IN_PROGRESS

    announce_game_move(board, cur_game, player_name, move)

    # Update the game state
    c.execute("UPDATE isolationgame SET game_state = ?, game_status = ?, current_queen = ?, updated_at = ?, last_move = ?, winner = ?, updated_at = ? WHERE uuid = ?", (new_game_state, new_game_status, other_player, time.time(), json.dumps(move), winner, time.time(), game_id))
    conn.commit()
    conn.close()
    if new_game_status == constants.GameStatus.FINISHED:
        return _end_game(game_id, winner, reason=f'{winner} won')
    return flask.jsonify(_get_game_status(game_id))


def setup_db_first_time():
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    # Run the SQL command in sql/isolation_games.sql
    with open('sql/isolation_games.sql', 'r') as f:
        sql = f.read()
        c.executescript(sql)
    conn.commit()
    conn.close()


def _get_game_counts():
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    c.row_factory = sqlite3.Row
    c.execute("SELECT game_status, COUNT(*) FROM isolationgame GROUP BY game_status")
    game_counts = c.fetchall()
    conn.close()
    # convert to dict
    game_counts = {row['game_status']: row['COUNT(*)'] for row in game_counts}
    return game_counts


@application.route('/')
def index():
    # Count number of games group by status
    try:
        game_counts = _get_game_counts()
    except sqlite3.OperationalError as e:
        if 'no such table' in str(e):
            setup_db_first_time()
            game_counts = _get_game_counts()
        else:
            raise e
    return flask.jsonify({'game_counts': game_counts, 'status': 'ok', 'hello': 'world'})


def emojify_board(board):
    return board.replace('  ', "⬜").replace("><","⬛").replace("Q1","🟥").replace("Q2","🟦").replace('\n\r','\n').replace("|","").replace("0","0️⃣").replace("1","1️⃣").replace("2","2️⃣").replace("3","3️⃣").replace("4","4️⃣").replace("5","5️⃣").replace("6","6️⃣").replace("7","7️⃣").replace("8","8️⃣").replace("9","9️⃣").replace(" ","")


if __name__ == '__main__':
    setup_db_first_time()
    application.run()
