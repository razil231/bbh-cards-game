import discord
import json
import os
import constants
import aiomysql

from db import get_pool

COGS_FILE = "cogs.json"


def load_cogs() -> list[str]:
    if not os.path.exists(COGS_FILE):
        return []
    
    with open(COGS_FILE, "r", encoding = "utf-8") as f:
        data = json.load(f)

    return data.get("extensions", [])

async def run_transaction(queries):
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            try:
                await conn.begin()

                for query, params in queries:
                    await cursor.execute(query, params)

                await conn.commit()
            except:
                await conn.rollback()
                raise