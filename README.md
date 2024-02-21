# Isolation Server

This is a quick project I spun up in order to play games of Isolation with classmates at Georgia Tech's AI course.
As part of this course, we built an AI to play Isolation. However, we are not allowed to share code with each other,
so there was no way to play against each other. This project is a simple flask server that will facilitate clients
creating games and sending moves to each other without exposing their inner logic.

# Server Setup

- Install requirements with `pip install -r requirements_server.txt`
- Run the server with `python server.py` (this just runs a local flask app, you will have to host it yourself and provide a public domain)

# Client Setup

- Install requirements with `pip install -r requirements_client.txt`
- Modify variables in client_config.py
- Host a game with `python client.py --host --name <name> --time_limit <time_limit>`
  - This will give you an ID you can send to someone to join
- Join a game with `python client.py --join --name <name> --game_id <game_id>`
- Observe a game with `python client.py --observe --game_id <game_id>`