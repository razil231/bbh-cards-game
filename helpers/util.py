import json
import os
import secrets
import string

from db import get_pool
from helpers.queries import ID_CHECK

COGS_FILE = "cogs.json"


def load_cogs() -> list[str]:
    if not os.path.exists(COGS_FILE):
        return []
    
    with open(COGS_FILE, "r", encoding = "utf-8") as f:
        data = json.load(f)

    return data.get("extensions", [])

def save_cog(extension: str):
    data = {"extensions: []"}

    if os.path.exists(COGS_FILE):
        with open(COGS_FILE, "r", encoding = "utf-8") as f:
            data = json.load(f)

    if extension not in data["extension"]:
        data["extensions"].append(extension)

        with open(COGS_FILE, "w", encoding = "utf-8") as f:
            json.dump(data, f, indent = 4)

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

async def generate_card_id(length = 8):
    chars = string.ascii_uppercase + string.digits
    pool = await get_pool()

    while True:
        code = ''.join(secrets.choice(chars) for _ in range(length))

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(ID_CHECK, (code,))
                if not await cursor.fetchone():
                    return code