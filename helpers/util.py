import json
import os
import secrets
import string
import aiomysql
import aiofiles
import constants

from db import get_pool
from helpers.queries import ID_CHECK, GET_USERS, GET_CARDS

COGS_FILE = "cogs.json"
CACHE_USERS_DICT = {}
CACHE_USERS_LIST = []
CACHE_CARDS_DICT = {}
CACHE_CARDS_LIST = []
CACHE_CARDS_NORMAL = []


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

def check_perms(ctx):
    perm_roles = [constants.BBH_ABSCBN, constants.BBH_DIREK, constants.BBH_MANAGER, constants.TEST_ADMIN]

    if not ctx.author.roles:
        return False
    
    if any(role.id in perm_roles for role in ctx.author.roles):
        return True
    else:
        return False

async def get_data(query, params = None):
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            if not params:
                await cursor.execute(query)
            else:
                await cursor.execute(query, params)
            rows = await cursor.fetchall()
            return rows
    
async def check_user(user):
    global CACHE_USERS_DICT, CACHE_USERS_LIST
    user_id = str(user)

    if user_id in CACHE_USERS_DICT:
        return True

    users = await get_data(GET_USERS)
    CACHE_USERS_DICT = {row["id"]: row for row in users}
    CACHE_USERS_LIST = list(CACHE_USERS_DICT.values())

    return user_id in CACHE_USERS_DICT

async def get_cards():
    global CACHE_CARDS_DICT, CACHE_CARDS_LIST, CACHE_CARDS_NORMAL
    cards = await get_data(GET_CARDS)
    CACHE_CARDS_DICT = {row["id"]: row for row in cards}
    CACHE_CARDS_LIST = list(CACHE_CARDS_DICT.values())
    CACHE_CARDS_NORMAL = [card for card in CACHE_CARDS_LIST if card["fd_type"] == "normal"]
    print("Cards cached")

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
                
async def run_sql(path):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            async with aiofiles.open(path, mode = "r") as f:
                sql_content = await f.read()

            statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]
            for stmt in statements:
                await cursor.execute(stmt)

        await conn.commit()

def one_percent_roll():
    return secrets.randbelow(100) == 0