INIT_TABLES = """
    CREATE TABLE IF NOT EXISTS tb_cards (
        id INT AUTO_INCREMENT PRIMARY KEY, 
        fd_type VARCHAR(255) NOT NULL, 
        fd_bundle VARCHAR(255) NOT NULL, 
        fd_name VARCHAR(255) NOT NULL, 
        fd_member VARCHAR(255) NOT NULL, 
        fd_image VARCHAR(255) NOT NULL, 
        fd_desc TEXT
    )
    CREATE TABLE IF NOT EXISTS tb_users (
        id VARCHAR(64) PRIMARY KEY, 
        fd_name VARCHAR(255) NOT NULL, 
        fd_desc VARCHAR(255), 
        fd_curr1 INT NOT NULL DEFAULT 0, 
        fd_curr2 INT NOT NULL DEFAULT 0, 
        fd_curr3 INT NOT NULL DEFAULT 0, 
        fd_multi FLOAT NOT NULL DEFAULT 1, 
        fd_fav INT NULL, 
        fd_lock INT NOT NULL DEFAULT 0, 
        fd_created TIMESTAMP NOT NULL
    )
    CREATE TABLE IF NOT EXISTS tb_owners (
        id INT AUTO_INCREMENT PRIMARY KEY, 
        fd_card VARCHAR(8) NOT NULL, 
        fd_rating INT NOT NULL DEFAULT 0, 
        fd_dupes INT NOT NULL DEFAULT 0, 
        fd_price INT NOT NULL DEFAULT 0, 
        fd_oowner VARCHAR(64) NULL, 
        fd_cowner VARCHAR(64) NULL, 
        fd_created TIMESTAMP NOT NULL, 
        fd_marketed TIMESTAMP NULL, 
        fd_deleted TIMESTAMP NULL,
    )
"""

ID_CHECK = "SELECT 1 FROM tb_owners WHERE fd_card = %s LIMIT 1"  