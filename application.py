import flask
import uuid
from flask import request
import random
import json
from server_isolation import Board
import constants
from discord_webhook import DiscordWebhook, DiscordEmbed
try:
    import server_secrets_hardcoded as server_secrets
except ImportError:
    import server_secrets
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from models.base import Base
from models.isolation_game import IsolationGame
import datetime
import copy

application = flask.Flask(__name__)
application.config['SQLALCHEMY_DATABASE_URI'] = server_secrets.DB_URL
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
engine = create_engine(application.config['SQLALCHEMY_DATABASE_URI'])
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)


false_values = ['false', 'f', '0', 'no', 'n', '']


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
    player_secret = str(uuid.uuid4())
    start_board = request.form['start_board']
    num_random_turns = int(request.form.get('num_random_turns', 0))
    num_rounds = int(request.form.get('num_rounds', 1))
    time_limit = request.form['time_limit']
    if 60 < int(time_limit) < 1:
        return flask.jsonify({'status': 'error', 'message': f'Invalid time limit {time_limit}, must be between 1 and 60'}), 400
    discord = False if request.form.get('discord', '').lower() in false_values else True
    secret = True if request.form.get('secret') == 'True' else False
    # Store this game ID in the db
    new_game = IsolationGame(
        player1=request.form['player_name'],
        player1_secret=player_secret,
        start_board=start_board,
        game_status=constants.GameStatus.NEED_SECOND_PLAYER,
        time_limit=time_limit,
        num_random_turns=num_random_turns,
        discord=discord,
        num_rounds=num_rounds
    )
    session = DBSession()
    session.add(new_game)
    session.commit()
    game_id = new_game.uuid
    session.close()
    if discord and not secret:
        webhook = DiscordWebhook(url=server_secrets.ANNOUNCEMENT_WEBHOOK_URL)
        start_board_str = start_board if len(start_board) < 20 else "CUSTOM"
        rules = f'start_board = {start_board_str}, time limit = {request.form["time_limit"]}, num rounds = {num_rounds}, num_random_turns = {num_random_turns}'
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
    if not cur_game.thread_id or not cur_game.discord:
        return
    formatted_board = emojify_board(board.print_board())
    webhook = DiscordWebhook(url=server_secrets.GAME_WEBHOOK_URL, thread_id=cur_game.thread_id)
    print(cur_game.player1, cur_game.player2, player_name)
    if cur_game.player1 == player_name:
        player_icon = "🟥"
        color = "c41e3a"
    else:
        player_icon = "🟦"
        color = "1e5ac4"
    embed = DiscordEmbed(title=f'{cur_game.player1} vs {cur_game.player2} - Round {cur_game.player1_wins + cur_game.player2_wins + 1} - Move #{board.move_count}', description=formatted_board, color=color)
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


def _apply_random_moves_to_board(start_board, num_random_turns, host, joiner, player1, player2):
    NUM_TRIES = 3
    for _ in range(NUM_TRIES):
        new_game = Board(host, joiner, start_board, player1 == host)
        game_over, winner = False, None
        for _ in range(num_random_turns):
            game_over, winner = new_game.__apply_move__(random.choice(new_game.get_player_moves(player1)))
            if game_over:
                break
            game_over, winner = new_game.__apply_move__(random.choice(new_game.get_player_moves(player2)))
            if game_over:
                break
        if not game_over:
            last_move = json.dumps('')
            new_game_json = new_game.to_json()
            return last_move, new_game_json
    raise ValueError(f'Could not apply random moves to board after {NUM_TRIES} tries, invalid settings')


@application.route('/game/<game_id>/join', methods=['POST'])
def join_game(game_id):
    """Join a game.
    POST variables:
    - player_name: the name of the player
    """
    player_name = request.form['player_name']
    player_secret = str(uuid.uuid4())

    session = DBSession()
    cur_game = session.query(IsolationGame).filter(IsolationGame.uuid == game_id).one()
    if cur_game is None:
        return flask.jsonify({'status': 'error', 'message': 'Game not found or not waiting for a player'}), 400
    # Get the cur_game's player
    host_player = cur_game.player1
    if host_player == player_name:
        return flask.jsonify({'status': 'error', 'message': 'You cannot join your own game'}), 400

    first_player = random.choice([player_name, host_player])
    second_player = host_player if first_player == player_name else player_name
    board = cur_game.start_board
    if board == "DEFAULT":
        board = copy.deepcopy(constants.DEFAULT_BOARD)
    elif board == "CASTLE":
        board = copy.deepcopy(constants.CASTLE_BOARD)
    else:
        board = json.loads(board)

    num_random_turns = cur_game.num_random_turns
    try:
        last_move, new_game_json = _apply_random_moves_to_board(board, num_random_turns, host_player, player_name, first_player, second_player)
    except ValueError as e:
        _end_game(game_id, '', reason=str(e))
        return flask.jsonify({'status': 'error', 'message': str(e)}), 400
    thread_id = ''
    # Need to add thread ID to DB, that's why we're calling it before.
    if cur_game.discord:
        thread_id = start_game_thread(host_player, player_name, game_id)
        announce_game_start_in_main_channel(host_player, player_name, thread_id)
    cur_game.player2 = request.form['player_name']
    cur_game.player2_secret = player_secret
    cur_game.game_status = constants.GameStatus.IN_PROGRESS
    cur_game.game_state = new_game_json
    cur_game.current_queen = first_player
    cur_game.last_move = last_move
    cur_game.thread_id = thread_id
    session.add(cur_game)
    session.commit()
    session.close()
    return flask.jsonify({'player_secret': player_secret, 'first_player': first_player})


def _get_game_status(game_id):
    session = DBSession()
    cur_game = session.query(IsolationGame).filter(IsolationGame.uuid == game_id).one()
    session.close()
    if cur_game is None:
        return None
    return {
            'game_status': cur_game.game_status,
            'current_queen': cur_game.current_queen,
            'player1': cur_game.player1,
            'player2': cur_game.player2,
            'time_limit': cur_game.time_limit,
            'winner': cur_game.winner,
            'last_move_time': cur_game.updated_at,
            'last_move': cur_game.last_move,
            'game_state': cur_game.game_state,
            'new_game_uuid': cur_game.new_game_uuid,
            'created_at': cur_game.created_at,
            'updated_at': cur_game.updated_at,
            'discord': cur_game.discord,
        }


@application.route('/game/<game_id>', methods=['GET'])
def get_game_status(game_id):
    """Get the state of a game.
    """
    request_time = datetime.datetime.utcnow().timestamp()
    game_status = _get_game_status(game_id)
    if game_status is None:
        return flask.jsonify({'status': 'error', 'message': 'Game not found'}), 404
    if game_status['game_status'] == constants.GameStatus.IN_PROGRESS and game_status['last_move_time'] and game_status['last_move_time'] + game_status['time_limit'] + 15 < request_time:
        # Update status to finished and set the winner to the other player
        _end_game(game_id, game_status['player1'] if game_status['current_queen'] == game_status['player2'] else game_status['player2'], reason=f'Timeout, status checked and significant time after last move')
    if game_status['game_status'] == constants.GameStatus.NEED_SECOND_PLAYER and (game_status['created_at'] + 60 * 10) < request_time:
        # Update status to finished and set the winner to the other player
        if game_status['discord']:
            announce_game_start_timeout(game_id)
        print(f'Game created at {game_status["created_at"]} and request time is {request_time} and 10 minutes have passed')
        _end_game(game_id, '', reason=f'No second player joined in time')
    return flask.jsonify(game_status)


def generate_new_game_with_prev_game_data(game_id, conn, player1_wins, player2_wins):
    session = DBSession()
    cur_game = session.query(IsolationGame).filter(IsolationGame.uuid == game_id).one()

    first_player = random.choice([cur_game.player1, cur_game.player2])
    second_player = cur_game.player1 if first_player == cur_game.player2 else cur_game.player2
    board = cur_game.start_board
    if board == "DEFAULT":
        board = copy.deepcopy(constants.DEFAULT_BOARD)
    elif board == "CASTLE":
        board = copy.deepcopy(constants.CASTLE_BOARD)
    else:
        board = json.loads(board)

    num_random_turns = cur_game.num_random_turns

    last_move, new_game_json = _apply_random_moves_to_board(
        board, num_random_turns, cur_game.player1, cur_game.player2, first_player, second_player)

    new_game_db = IsolationGame(
        player1=cur_game.player1,
        player1_secret=cur_game.player1_secret,
        player2=cur_game.player2,
        player2_secret=cur_game.player2_secret,
        start_board=cur_game.start_board,
        game_state=new_game_json,
        game_status=constants.GameStatus.IN_PROGRESS,
        time_limit=cur_game.time_limit,
        num_random_turns=cur_game.num_random_turns,
        discord=cur_game.discord,
        num_rounds=cur_game.num_rounds-1,
        current_queen=first_player,
        last_move=last_move,
        thread_id=cur_game.thread_id,
        player1_wins=player1_wins,
        player2_wins=player2_wins,
    )
    session.add(new_game_db)
    session.commit()
    new_game_uuid = new_game_db.uuid
    session.close()
    return new_game_uuid


def _end_game(game_id, winner, reason=''):
    session = DBSession()
    cur_game = session.query(IsolationGame).filter(IsolationGame.uuid == game_id).one()
    if winner.split(" - ")[0] == cur_game.player1:
        cur_game.player1_wins += 1
    elif winner.split(" - ")[0] == cur_game.player2:
        cur_game.player2_wins += 1
    else:
        raise ValueError(f'Unknown winner {winner}')
    new_game_uuid = ''
    new_game_num_rounds = cur_game.num_rounds - 1
    if new_game_num_rounds > 0 and abs(cur_game.player1_wins - cur_game.player2_wins) <= new_game_num_rounds:
        new_game_uuid = generate_new_game_with_prev_game_data(game_id, session, cur_game.player1_wins, cur_game.player2_wins)

    cur_game.game_status = constants.GameStatus.FINISHED
    cur_game.winner = winner
    cur_game.new_game_uuid = new_game_uuid
    session.commit()
    if cur_game.discord and cur_game.thread_id and cur_game.game_status != constants.GameStatus.NEED_SECOND_PLAYER:
        board = Board.from_json(cur_game.game_state)
        announce_game_over(cur_game.thread_id, winner, board, new_game_uuid == "", cur_game.player1_wins, cur_game.player2_wins, reason=reason)
    session.close()
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
    # client_time = float(request.form['client_time'])
    client_time = datetime.datetime.utcnow().timestamp()
    session = DBSession()
    cur_game = session.query(IsolationGame).filter(IsolationGame.uuid == game_id).one_or_none()

    if cur_game is None:
        return flask.jsonify({'status': 'error', 'message': 'Game not found'}), 400

    # Check that the game is in progress or waiting to start
    if cur_game.game_status != constants.GameStatus.IN_PROGRESS:
        return flask.jsonify({'status': 'error', 'message': 'Game not in progress'}), 400

    # Check that the player is in the game
    if cur_game.player1 != player_name and cur_game.player2 != player_name:
        return flask.jsonify({'status': 'error', 'message': 'Player not in game'}), 400

    # Check that it is the player's turn, and the secret is correct
    if (cur_game.current_queen == cur_game.player1):
        # Test that the current player is the host and the secret is correct
        other_player = cur_game.player2
        if cur_game.player1 == player_name and cur_game.player1_secret != player_secret:
            return flask.jsonify({'status': 'error', 'message': 'Invalid next player'}), 400
    else:
        # Test that the current player is the guest and the secret is correct
        other_player = cur_game.player1
        if cur_game.player2 == player_name and cur_game.player2_secret != player_secret:
            return flask.jsonify({'status': 'error', 'message': 'Invalid next player'}), 400

    # Check that the timestamp they sent is within 1 second of the server's time
    # This is causing issues, so I am ignoring it for now
    # if time.time() - client_time > 1:
    #     c.execute("UPDATE isolationgame SET game_status = ?, winner = ? WHERE uuid = ?", (constants.GameStatus.FINISHED, other_player, game_id))
    #     return flask.jsonify({'status': 'error', 'message': 'I don\'t believe your timestamp...'}), 400

    # Check their timestamp is within the time limit (within some bounds)
    if client_time - cur_game.updated_at > (1 + cur_game.time_limit):
        # Set the game as finished
        return _end_game(game_id, other_player, reason=f'You took too long, client_time: {client_time}, last move at: {cur_game.updated_at}, time_limit: {cur_game.time_limit}')

    # Create the board based on the game state and make the move
    board = Board.from_json(cur_game.game_state)
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

    cur_game.game_state = new_game_state
    cur_game.game_status = new_game_status
    cur_game.current_queen = other_player
    cur_game.last_move = json.dumps(move)
    cur_game.winner = winner
    session.add(cur_game)
    session.commit()
    session.close()
    # Update the game state
    if new_game_status == constants.GameStatus.FINISHED:
        return _end_game(game_id, winner, reason=f'{winner} won')
    return flask.jsonify(_get_game_status(game_id))


def _get_game_counts():
    session = DBSession()
    game_counts = session.query(IsolationGame.game_status, func.count()).group_by(IsolationGame.game_status).all()
    session.close()
    # convert to dict
    game_counts = {status: count for status, count in game_counts}
    return game_counts


@application.route('/')
def index():
    # Count number of games group by status
    game_counts = _get_game_counts()
    return flask.jsonify({'game_counts': game_counts, 'status': 'ok', 'hello': 'world'})


def emojify_board(board):
    return board.replace('  ', "⬜").replace("><","⬛").replace("Q1","🟥").replace("Q2","🟦").replace('\n\r','\n').replace("|","").replace("0","0️⃣").replace("1","1️⃣").replace("2","2️⃣").replace("3","3️⃣").replace("4","4️⃣").replace("5","5️⃣").replace("6","6️⃣").replace("7","7️⃣").replace("8","8️⃣").replace("9","9️⃣").replace(" ","")


if __name__ == '__main__':
    application.run()
