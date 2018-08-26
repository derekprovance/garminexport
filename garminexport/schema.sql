CREATE TABLE IF NOT EXISTS daily_statistics (
    id INT AUTO_INCREMENT,
    entry_date DATE NOT NULL UNIQUE,
    max_hr INT,
    min_hr INT,
    resting_hr INT,
    total_sleep INT,
    total_steps INT,
    highly_active_seconds INT,
    active_seconds INT,
    sedentary_seconds INT,
    sleeping_seconds INT,
    max_stress_level INT,
    low_stress_duration INT,
    medium_stress_duration INT,
    high_stress_duration INT,
    PRIMARY KEY(id)
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS sleep (
    id INT AUTO_INCREMENT,
    daily_statistics_id INT NOT NULL UNIQUE,
    sleep_start DATETIME,
    sleep_end DATETIME,
    deep_sleep INT,
    light_sleep INT,
    rem_sleep INT,
    awake_sleep INT,
    FOREIGN KEY(daily_statistics_id)
        REFERENCES daily_statistics(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(id)
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS sleep_movement (
    id INT AUTO_INCREMENT,
    sleep_id INT NOT NULL,
    start DATETIME,
    end DATETIME,
    activity_level DECIMAL(14,13),
    FOREIGN KEY(sleep_id)
        REFERENCES sleep(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(id)
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS hr_data (
    id INT AUTO_INCREMENT,
    daily_statistics_id INT,
    event_time DATETIME,
    hr_value INT,
    FOREIGN KEY(daily_statistics_id)
        REFERENCES daily_statistics(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(id)
) ENGINE=INNODB;

CREATE TABLE IF NOT EXISTS movement_data (
    id INT AUTO_INCREMENT,
    daily_statistics_id INT,
    event_time DATETIME,
    movement DECIMAL(5,4),
    FOREIGN KEY(daily_statistics_id)
        REFERENCES daily_statistics(id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    PRIMARY KEY(id)
) ENGINE=INNODB;