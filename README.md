# Isolation Server

This is a quick project I spun up in order to play games of Isolation with classmates at Georgia Tech's AI course.
As part of this course, we built an AI to play Isolation. However, we are not allowed to share code with each other,
so there was no way to play against each other. This project is a simple flask server that will facilitate clients
creating games and sending moves to each other without exposing their inner logic.

# Client Setup - Needed to create and join games

- Install requirements with `pip install -r requirements_client.txt`
- Modify variables in client_config.py
 - Import your bot from the assignment and set it to DEFAULT_PLAYER_CLASS.
- Host a game with `python client.py --host --name <your name> --time_limit <time_limit (s)>`
  - This will give you an ID you can send to someone to join, or that someone can read on Discord.
  - Some other options:
    - `--start_board <start_board>`: The board to start the game with. Can be "DEFAULT", "CASTLE", or a JSON string of an NxM array of spaces and X's
    - `--secret`: If toggled, your code won't be posted on Discord. Good if you want someone specific to join.
    - `--no_discord`: If toggled, your game won't be broadcast on Discord.
    - `--num_random_turns <num_random_turns>`: If set, the game will start with agents making N random moves in the beginning
    - `--num_rounds <num_rounds>`: If set, the game will play N rounds of the game with the same settings
    - `--player_to_use <player_namee>`: If set, the game will use the player set in client_config.py with that name, instead of the DEFAULT_PLAYER_CLASS
- Join a game with `python client.py --join --name <name> --game_id <game_id>`
- Observe a game with `python client.py --observe --game_id <game_id>` (or just watch on Discord).


# Server Setup - Only needed if you are the one who wants to host the server

- Install requirements with `pip install -r requirements.txt`
- Get the `server_secrets.py` variables from someone and set them in your OS variables
- Run the server locally with `python application.py`, or host it wherever. I had success with AWS Elastic Beanstalk.