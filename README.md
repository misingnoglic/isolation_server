# Isolation Server

This is a quick project I spun up in order to play games of Isolation with classmates at Georgia Tech's AI course.
As part of this course, we built an AI to play Isolation. However, we are not allowed to share code with each other,
so there was no way to play against each other. This project is a simple flask server that will facilitate clients
creating games and sending moves to each other without exposing their inner logic.

# Client Setup - Needed to create and join games

- Install requirements with `pip install -r requirements_client.txt`
- Bring in your `submission.py` from the assignment.
- Optionally, modify variables in client_config.py
  - Change the name/import of your bot **if** it's something other than `CustomBot`
  - Change the `DEFAULT_PLAYER_NAME` if you'd like your display name to be something other than your os username
  
- Host a game with `python client.py --host`
  - This will give you an ID you can send to someone to join, or that someone can read on Discord.
  <details>
  <summary>Some other <b>optional</b> flags</summary>
  <ul>
    <li>
      <code>--name &ltname&gt</code>: Display name to use, defaults to logged in os username
    </li>
    <li>
      <code>--start_board &ltstart_board&gt</code>: The board to start the game with. Can be "DEFAULT", "CASTLE", or a JSON string of an NxM array of spaces and X's
    </li>
    <li>
      <code>--secret</code>: If toggled, your game ID won't be posted on Discord. Good if you want someone specific to join.
    </li>
    <li>
      <code>--no_discord</code>: If toggled, your game won't be broadcast on Discord.
    </li>
    <li>
      <code>--num_random_turns &ltnum_random_turns&gt</code>: If set, the game will start with agents making N random moves in the beginning
    <li>
      <code>--num_rounds &ltnum_rounds&gt</code>: If set, the game will play num_rounds rounds of the game with the same settings
    </li>
    <li>
      <code>--player_to_use &ltplayer_name&gt</code>: If set, the game will use the player set in client_config.py with that name, instead of the DEFAULT_PLAYER_CLASS
    </li>
  </ul>
  </details>
  
- Join a game with `python client.py --join --game_id <game_id>`
  - optionally add `--name <name>` to use a custom display name
- Observe a game with `python client.py --observe --game_id <game_id>` (or just watch on Discord).


# Server Setup - Only needed if you are the one who wants to host the server

- Install requirements with `pip install -r requirements.txt`
- Get the `server_secrets.py` variables from someone and set them in your OS variables
- Run the server locally with `python application.py`, or host it wherever. I had success with AWS Elastic Beanstalk.