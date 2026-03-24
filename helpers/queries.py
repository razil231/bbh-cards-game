INIT_TABLES = """
    CREATE TABLE IF NOT EXISTS tb_cards (
        id INT AUTO_INCREMENT PRIMARY KEY, 
        fd_type VARCHAR(255) NOT NULL, 
        fd_bundle VARCHAR(255) NOT NULL, 
        fd_name VARCHAR(255) NOT NULL, 
        fd_member VARCHAR(255) NOT NULL, 
        fd_image VARCHAR(255) NOT NULL, 
        fd_desc TEXT
    );
    CREATE TABLE IF NOT EXISTS tb_users (
        id VARCHAR(64) PRIMARY KEY, 
        fd_name VARCHAR(255) NOT NULL, 
        fd_desc VARCHAR(255), 
        fd_curr1 INT NOT NULL DEFAULT 0, 
        fd_curr2 INT NOT NULL DEFAULT 0, 
        fd_curr3 INT NOT NULL DEFAULT 0, 
        fd_multi FLOAT NOT NULL DEFAULT 1, 
        fd_fav VARCHAR(8) NULL, 
        fd_lock INT NOT NULL DEFAULT 0, 
        fd_created TIMESTAMP NOT NULL
    );
    CREATE TABLE IF NOT EXISTS tb_owners (
        id INT AUTO_INCREMENT PRIMARY KEY, 
        fd_card INT NULL, 
        fd_display VARCHAR(8) NOT NULL, 
        fd_rating INT NOT NULL DEFAULT 0, 
        fd_dupes INT NOT NULL DEFAULT 0, 
        fd_price INT NOT NULL DEFAULT 0, 
        fd_oowner VARCHAR(64) NULL, 
        fd_cowner VARCHAR(64) NULL, 
        fd_created TIMESTAMP NOT NULL, 
        fd_marketed TIMESTAMP NULL, 
        fd_deleted TIMESTAMP NULL
    );
    ALTER TABLE tb_owners
    ADD CONSTRAINT u_disp UNIQUE (fd_display),
    ADD CONSTRAINT fk_card_id FOREIGN KEY (fd_card) REFERENCES tb_cards(id),
    ADD CONSTRAINT fk_oowner_id FOREIGN KEY (fd_oowner) REFERENCES tb_users(id),
    ADD CONSTRAINT fk_cowner_id FOREIGN KEY (fd_cowner) REFERENCES tb_users(id);
    ALTER TABLE tb_users
    ADD CONSTRAINT fk_fav_id FOREIGN KEY (fd_fav) REFERENCES tb_owners(fd_display);
"""

ID_CHECK = "SELECT 1 FROM tb_owners WHERE fd_card = %s LIMIT 1"  