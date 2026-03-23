import aiomysql

db_pool = None

async def init_db():
    global db_pool
    db_pool = await aiomysql.create_pool(
        host = "127.0.0.1",
        port = 3306,
        user = "sa",
        password = "admintest",
        db = "cardtest",
        autocommit = False
    )

async def get_pool():
    return db_pool