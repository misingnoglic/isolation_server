# Isolation Server

This is a quick project I spun up in order to play games of Isolation with classmates at Georgia Tech's AI course.
As part of this course, we built an AI to play Isolation. However, we are not allowed to share code with each other,
so there was no way to play against each other. This project is a simple flask server that will facilitate clients
creating games and sending moves to each other without exposing their inner logic.

# Client Setup - Needed to create and join games

- Install requirements with `pip install -r requirements_client.txt`
- Grab the `isolation_server.py` file from someone who has it (currently trying to get permission to host it)
- Modify variables in client_config.py
 - Get the server URL from whoever is hosting the server.
 - Import your bot from the assignment.
- Host a game with `python client.py --host --name <name> --time_limit <time_limit>`
  - This will give you an ID you can send to someone to join
  - Some other options:
    - `--num_random_moves <num_random_moves>`: The number of random moves to make at the start of the game
    - `--start_board <start_board>`: The board to start the game with. Can be "DEFAULT", "CASTLE", or a JSON string of an NxM array of spaces and X's
    - `--webhook <webhook>`: A discord webhook URL to send game updates to
- Join a game with `python client.py --join --name <name> --game_id <game_id>`
- Observe a game with `python client.py --observe --game_id <game_id>`


# Server Setup - Only needed if you are the one who wants to host the server

- Install requirements with `pip install -r requirements_server.txt`
- Get the `server_secrets.py` from someone.
- Grab the `isolation_server.py` file from someone who has it (currently trying to get permission to host it)
- Run the server with `python server.py` (this just runs a local flask app, you will have to host it yourself and provide a public domain)
