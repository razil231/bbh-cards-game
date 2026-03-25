import discord
import json
import os
import secrets
import string
import aiomysql
import aiofiles
import constants

from datetime import datetime
from db import get_pool
from helpers.queries import ID_CHECK, GET_USERS, GET_CARDS, GET_OWNERS, ADD_USER, ADD_OWNER, UPDATE_COPIES

COGS_FILE = "cogs.json"
CACHE_USERS_DICT = {}
CACHE_USERS_LIST = []
CACHE_CARDS_DICT = {}
CACHE_CARDS_LIST = []
CACHE_OWNERS_DICT = {}
CACHE_OWNERS_LIST = []
CACHE_CARDS_NORMAL = []
CACHE_CARDS_SIGNED = []


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

def roll_with_multi(multi):
    base_rate = 0.01
    chance = min(base_rate * multi, 1.0)
    return secrets.randbelow(10_000) < int(chance * 10_000)

def get_color(member):
    color = constants.COLOR_OT8
    if member == "Aiah":
        color = constants.COLOR_AIAHPRODITES
    elif member == "Colet":
        color = constants.COLOR_COCACOLETS
    elif member == "Maloi":
        color = constants.COLOR_LUCKIES
    elif member == "Gwen":
        color = constants.COLOR_AGWENGERS
    elif member == "Stacey":
        color = constants.COLOR_STARS
    elif member == "Mikha":
        color = constants.COLOR_MIKHALITES
    elif member == "Jhoanna":
        color = constants.COLOR_AMITIES
    elif member == "Sheena":
        color = constants.COLOR_SHINIES
    return color
                
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

async def run_query(query, params = None, fetch = True):
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            await cursor.execute(query, params)

            if fetch:
                return await cursor.fetchall()
            else:
                await conn.commit()
                return cursor.rowcount
    
async def check_user(user):
    global CACHE_USERS_DICT, CACHE_USERS_LIST
    user_id = str(user)

    if user_id in CACHE_USERS_DICT:
        return True

    users = await run_query(GET_USERS)
    CACHE_USERS_DICT = {str(row["id"]): row for row in users}
    CACHE_USERS_LIST = list(CACHE_USERS_DICT.values())
    print("Users cached")

    return user_id in CACHE_USERS_DICT

async def get_cards():
    global CACHE_CARDS_DICT, CACHE_CARDS_LIST, CACHE_CARDS_NORMAL, CACHE_CARDS_SIGNED
    cards = await run_query(GET_CARDS)
    CACHE_CARDS_DICT = {row["id"]: row for row in cards}
    CACHE_CARDS_LIST = list(CACHE_CARDS_DICT.values())
    CACHE_CARDS_NORMAL = [card for card in CACHE_CARDS_LIST if card["fd_type"] == "normal"]
    CACHE_CARDS_SIGNED = [card for card in CACHE_CARDS_LIST if card["fd_type"] == "signed"]
    print("Cards cached")

async def get_owners():
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST
    owners = await run_query(GET_OWNERS)
    CACHE_OWNERS_DICT = {(row["fd_card"], str(row["fd_cowner"])): row for row in owners}
    CACHE_OWNERS_LIST = list(CACHE_OWNERS_DICT.values())
    print("Owners cached")

async def get_user(user_id):
    await check_user(user_id)
    return CACHE_USERS_DICT.get(str(user_id))

async def add_user(user):
    return await run_query(ADD_USER, (user.id, user.global_name, datetime.now()), False)

async def add_ownership(card_id, card, user, date):
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST
    new = {
        "fd_card": card,
        "fd_display": card_id,
        "fd_dupes": 1,
        "fd_oowner": str(user["id"]),
        "fd_cowner": str(user["id"]),
        "fd_created": date
    }
    CACHE_OWNERS_DICT[(card, str(user["id"]))] = new
    CACHE_OWNERS_LIST.append(new)
    
    return await run_query(ADD_OWNER, (card, card_id, str(user["id"]), str(user["id"]), date), False)

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
                
async def generate_card_embed(card, user):
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST
    now = datetime.now()
    caption = ""
    card_id = ""
    copies = 1
    
    owned = CACHE_OWNERS_DICT.get((card["id"], str(user["id"])))
    if owned:
        caption = "**You acquired a duplicate card**"
        owned["fd_dupes"] += 1
        copies = owned["fd_dupes"]
        card_id = owned["fd_display"]
        now = owned["fd_created"]
        if await run_query(UPDATE_COPIES, (copies, card_id), False):
            print("Updated number of copies")
        else:
            print("Failed updating the number of copies")
    else:
        caption = "**You acquired a new card**"
        card_id = await generate_card_id()
        if await add_ownership(card_id, int(card["id"]), user, now):
            print("Added new ownership")
        else:
            print("Failed adding new ownership")

    desc = f"{card['fd_bundle']}\n{card['fd_type']}\n{card['fd_member']}"
    if card["fd_desc"]:
        desc += f"\n\n{card['fd_desc']}"

    file = discord.File(card["fd_image"], filename = "card.png")
    display_date = now.strftime("%A, %B %d, %Y %I:%M %p")
    embed_color = get_color(card["fd_member"])

    embed = discord.Embed(
        title = f"Card ID: {card_id}",
        description = desc,
        color = embed_color
    )

    embed.add_field(name = "", value = f"Copies owned: {copies}")
    embed.set_image(url = "attachment://card.png")
    embed.set_footer(text = f"Obtained: {display_date}")

    return embed, file, caption