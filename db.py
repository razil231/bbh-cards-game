import aiomysql
from helpers.queries import INIT_TABLES

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

    print("DB initialization done")

async def get_pool():
    return db_pool

async def setup_db():
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(INIT_TABLES)

    print("DB setup done")