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

app = flask.Flask(__name__)

# enum for game states


@app.route('/game/new', methods=['POST'])
def host_game():
    """Host a new game.
    POST variables:
    - player_name: the name of the player
    - time_limit: the time limit for the game
    - start_board: JSON string of default board for the game (if None, will be the standard board. If "CASTLE" will be the castle board)
    - webhook: Discord webhook url to send move updates to
    """
    game_id = str(uuid.uuid4())
    player_secret = str(uuid.uuid4())
    start_board = request.form['start_board']
    # Store this game ID in the db
    conn = sqlite3.connect('sql/isolation.db')
    c = conn.cursor()
    c.execute(
        "INSERT INTO isolationgame (uuid, player1, player1_secret, start_board, game_status, time_limit, webhook) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (game_id, request.form['player_name'], player_secret, start_board, constants.GameStatus.NEED_SECOND_PLAYER, request.form['time_limit'], request.form['webhook']))
    conn.commit()
    conn.close()
    return flask.jsonify({'game_id': game_id, 'player_secret': player_secret})

@app.route('/game/<game_id>/join', methods=['POST'])
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
    board = cur_game['start_board']
    if board == "DEFAULT":
        board = constants.DEFAULT_BOARD
    elif board == "CASTLE":
        board = constants.CASTLE_BOARD
    else:
        board = json.loads(board)


    new_game = Board(host_player, player_name, board, first_player == host_player)
    new_game_json = new_game.to_json()

    c.execute(
        "UPDATE isolationgame SET player2 = ?, player2_secret = ?, game_status = ?, game_state = ?,  current_queen = ?, updated_at = ? WHERE uuid = ? AND game_status = ?",
        (request.form['player_name'], player_secret, constants.GameStatus.IN_PROGRESS, new_game_json, first_player, time.time(), game_id, constants.GameStatus.NEED_SECOND_PLAYER)
    )
    if cur_game['webhook']:
        webhook = DiscordWebhook(url=cur_game['webhook'])
        embed = DiscordEmbed(title="NEW GAME!!!", description=cur_game['player1'] + " vs " + cur_game['player2'])
        webhook.add_embed(embed)
        response = webhook.execute()
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
        return flask.jsonify({'status': 'error', 'message': 'Game not found'}), 400
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
        }

@app.route('/game/<game_id>', methods=['GET'])
def get_game_status(game_id):
    """Get the state of a game.
    """
    game_status = _get_game_status(game_id)
    if game_status['game_status'] == constants.GameStatus.IN_PROGRESS and game_status['last_move_time'] and game_status['last_move_time'] + game_status['time_limit'] + 5 < time.time():
        # Update status to finished and set the winner to the other player
        conn = sqlite3.connect('sql/isolation.db')
        c = conn.cursor()
        c.execute("UPDATE isolationgame SET game_status = ?, winner = ? WHERE uuid = ?", (constants.GameStatus.FINISHED, game_status['player1'] if game_status['current_queen'] == game_status['player2'] else game_status['player2'], game_id))
        conn.commit()
        conn.close()
        return flask.jsonify(_get_game_status(game_id))
    return flask.jsonify(game_status)


@app.route('/game/<game_id>/move', methods=['POST'])
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
    if abs(client_time - time.time()) > 1:
        c.execute("UPDATE isolationgame SET game_status = ?, winner = ? WHERE uuid = ?", (constants.GameStatus.FINISHED, other_player, game_id))
        return flask.jsonify({'status': 'error', 'message': 'I don\'t believe your timestamp...'}), 400

    # Check their timestamp is within the time limit
    if client_time - cur_game['updated_at'] > cur_game['time_limit']:
        # Set the game as finished
        c.execute("UPDATE isolationgame SET game_status = ?, winner = ? WHERE uuid = ?", (constants.GameStatus.FINISHED, other_player, game_id))
        return flask.jsonify({'status': 'error', 'message': 'You took too long!'}), 400

    # Create the board based on the game state and make the move
    board = Board.from_json(cur_game['game_state'])
    # Check that the move is legal
    if move not in board.get_player_moves(player_name):
        c.execute("UPDATE isolationgame SET game_status = ?, winner = ? WHERE uuid = ?", (constants.GameStatus.FINISHED, other_player, game_id))
        return flask.jsonify({'status': 'error', 'message': 'Illegal move'}), 400

    game_over, winner = board.__apply_move__(move)
    new_game_state = board.to_json()
    new_game_status = constants.GameStatus.FINISHED if game_over else constants.GameStatus.IN_PROGRESS
    # Update the game state

    # Send to webhook
    if cur_game['webhook']:
        formatted_board = board.print_board().replace('  ', "⬜").replace("><","⬛").replace("Q1","🟥").replace("Q2","🟦").replace('\n\r','\n').replace("|","").replace("0","0️⃣").replace("1","1️⃣").replace("2","2️⃣").replace("3","3️⃣").replace("4","4️⃣").replace("5","5️⃣").replace("6","6️⃣").replace("7","7️⃣").replace("8","8️⃣").replace("9","9️⃣").replace(" ","")
        webhook = DiscordWebhook(url=cur_game['webhook'])
        embed = DiscordEmbed(title=cur_game['player1'] + " vs " + cur_game['player2'], description=formatted_board)
        webhook.add_embed(embed)
        response = webhook.execute()

    if new_game_status == constants.GameStatus.FINISHED:
        if cur_game['webhook']:
            webhook = DiscordWebhook(url=cur_game['webhook'])
            embed = DiscordEmbed(title="GAME OVER!!!", description=winner + "wins!!")
            webhook.add_embed(embed)
            response = webhook.execute()
    c.execute("UPDATE isolationgame SET game_state = ?, game_status = ?, current_queen = ?, updated_at = ?, last_move = ?, winner = ?, updated_at = ? WHERE uuid = ?", (new_game_state, new_game_status, other_player, time.time(), json.dumps(move), winner, time.time(), game_id))
    conn.commit()
    conn.close()
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


if __name__ == '__main__':
    setup_db_first_time()
    app.run()
