DEFAULT_WIDTH = 9
DEFAULT_HEIGHT = 9
DEFAULT_BOARD = [[" " for i in range(DEFAULT_WIDTH)] for j in range(DEFAULT_HEIGHT)]
CASTLE_BOARD = [[" "," "," "," "," "," "," "," "," "],
                [" "," "," "," "," "," "," "," "," "],
                [" "," ","X","X"," ","X","X"," "," "],
                [" "," ","X"," "," "," ","X"," "," "],
                [" "," "," "," "," "," "," "," "," "],
                [" "," ","X"," "," "," ","X"," "," "],
                [" "," ","X","X"," ","X","X"," "," "],
                [" "," "," "," "," "," "," "," "," "],
                [" "," "," "," "," "," "," "," "," "]]


class GameStatus:
    NEED_SECOND_PLAYER = 'need_second_player'
    IN_PROGRESS = 'in_progress'
    FINISHED = 'finished'
