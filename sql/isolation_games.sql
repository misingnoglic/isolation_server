PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS isolationgame (
    id INT AUTO_INCREMENT,
    uuid VARCHAR(100) NOT NULL PRIMARY KEY,
    player1 VARCHAR(100) NOT NULL,
    player1_secret VARCHAR(100) NOT NULL,
    player2 VARCHAR(100) DEFAULT '',  /* Allow null for before game starts */
    player2_secret VARCHAR(100) DEFAULT '',  /* Allow null for before game starts */
    start_board TEXT NOT NULL,
    game_status VARCHAR(100) NOT NULL,
    game_state TEXT DEFAULT '',
    current_queen VARCHAR(100) DEFAULT '',
    last_move VARCHAR(100) DEFAULT '',
    winner VARCHAR(100) DEFAULT '',
    time_limit INT NOT NULL,
    epoch_time_limit_next_move FLOAT DEFAULT 0,
    num_random_turns INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at FLOAT,
    webhook VARCHAR(200) DEFAULT ''
);