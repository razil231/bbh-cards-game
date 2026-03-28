import discord
import json
import os
import hashlib
import secrets
import string
import aiohttp
import aiomysql
import aiofiles
import constants

from datetime import datetime
from discord.ext import commands
from PIL import Image
from io import BytesIO
from db import get_pool
from helpers.queries import ID_CHECK, GET_USERS, GET_CARDS, GET_OWNERS, ADD_USER, ADD_OWNER, UPDATE_COPIES, UPGRADE_CARD

COGS_FILE = "cogs.json"
CACHE_USERS_DICT = {}
CACHE_USERS_LIST = []
CACHE_CARDS_DICT = {}
CACHE_CARDS_LIST = []
CACHE_OWNERS_DICT = {}
CACHE_OWNERS_LIST = []
CACHE_CARDS_NORMAL = []
CACHE_CARDS_SIGNED = []
CACHE_CARDS_UPGRADE = {}
CACHE_CARDS_COLLECTION = {}
CACHE_IMAGES_MEMORY = {}

CACHE_DIR = "cache/images"
CACHE_MAX_MEMORY = 100

os.makedirs(CACHE_DIR, exist_ok = True)

BASE_COOLDOWNS = {
    constants.CooldownCommand.CARD: constants.CD_CARD,
    constants.CooldownCommand.DAILY: constants.CD_DAILY,
    constants.CooldownCommand.ASCEND: constants.CD_ASCEND,
    constants.CooldownCommand.UPGRADE: constants.CD_UPGRADE
}


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

def get_cache(path):
    filename = hashlib.md5(path.encode()).hexdigest() + ".png"
    return os.path.join(CACHE_DIR, filename)

def get_info(bot, command = None):
    is_command = True

    if not command:
        is_command = False

    embed = discord.Embed(
        title = f"Help for {command}" if is_command else "Available commands",
        color = 0xFF_FF_FF
    )

    if not is_command:
        embed.add_field(name = "`bc help [command]`", value = "- shows all commands", inline = False)
        embed.add_field(name = "`bc start`", value = "- initializes user profile", inline = False)
        embed.add_field(name = "`bc profile [@user]`", value = "- shows the profile of a user", inline = False)
        embed.add_field(name = "`bc card`", value = "- gets a card from the current pool", inline = False)
        embed.add_field(name = "`bc cards [@user]`", value = "- shows card collection of a user", inline = False)
        embed.add_field(name = "`bc upgrade <card id>`", value = "- upgrade a card to a higher rating", inline = False)
        embed.set_footer(text = "\"bc help [command]\" for more info")
    else:
        cmd = bot.get_command(command)
        if not cmd:
            return None
        
        embed.add_field(name = cmd.extras.get("syntax"), value = f"- {cmd.callback.__doc__}", inline = False)

        params = cmd.extras.get("args")
        if params is not None:
            embed.add_field(name = "Parameters:", value = params, inline = False)

        embed.set_footer(text = "Slash commands are also available")

    return embed

def display_date(timestamp, format = "%A, %B %d, %Y %I:%M %p"):
    return timestamp.strftime(format)

def check_perms(ctx):
    perm_roles = [constants.BBH_ABSCBN, constants.BBH_DIREK, constants.BBH_MANAGER, constants.TEST_ADMIN]

    if not ctx.author.roles:
        return False
    
    if any(role.id in perm_roles for role in ctx.author.roles):
        return True
    else:
        return False

def check_lock(user):
    details = CACHE_USERS_DICT.get(str(user))
    return details["fd_lock"] > 0

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

def get_card_rating(rating):
    str = ""

    for _ in range(rating):
        str += f"{constants.STAR_LIGHT}"
    for _ in range(5 - rating):
        str += f"{constants.STAR_DARK}"

    return str

def get_user_cards(user_id):
    global CACHE_CARDS_COLLECTION
    user = str(user_id)
    
    cards = CACHE_CARDS_COLLECTION.get(user)
    if cards is not None:
        return cards
    
    cards = [c for c in CACHE_OWNERS_LIST if c["fd_cowner"] == user]
    CACHE_CARDS_COLLECTION[user] = cards
    
    return cards

def get_cooldown(ctx, command_enum: constants.CooldownCommand):
    base = BASE_COOLDOWNS[command_enum]

    booster_role = discord.utils.get(ctx.author.roles, name = "Server Booster")
    if booster_role:
        base *= 0.8

    return commands.Cooldown(1, base)

def card_list_embed(user, cards, page, total):
    start = page * 10
    end = start + 10
    pages = cards[start:end]

    embed = discord.Embed(
        title = "Card Collection",
        description = f"{user.global_name}\'s cards:",
        color = 0xFF_FF_FF
    )
    for i, card in enumerate(pages, start = start):
        details = CACHE_CARDS_DICT.get(card["fd_card"])
        if details["fd_type"] == "signed":
            display = f"{constants.TYPE_SIGNED} **{details["fd_bundle"]}**: {details["fd_member"]}"
        else:
            display = f"{constants.TYPE_NORMAL} **{details["fd_bundle"]}**: {details["fd_member"]}"
        
        embed.add_field(name = f"`{card["fd_display"]}`", value = f"{display}", inline = True)
        if (i + 1) % 2 == 0:
            embed.add_field(name = "", value = "", inline = False)

    embed.set_footer(text = f"Page {page + 1}/{total}")
    return embed

def get_profile_embed(user, details):
    embed = discord.Embed(
        title = f"{user.display_name}\'s Profile",
        description = details["fd_desc"] if details["fd_desc"] is not None else "",
        color = 0xFF_FF_FF
    )
    curr = f"- {details["fd_curr1"]} {constants.BLOOM}\n"
    curr += f"- {details["fd_curr2"]} {constants.BLOOMCENSION}\n"
    curr += f"- {details["fd_curr3"]} {constants.BLOOMSPIN}"

    embed.set_thumbnail(url = user.display_avatar.url)
    embed.add_field(name = "Boosts:", value = f"- __**Signed**__: *{details['fd_multi']:.2f}%* chances", inline = False)
    embed.add_field(name = "Currency:", value = f"{curr}", inline = False)
    embed.set_footer(text = f"Created: {display_date(details["fd_created"])}")

    return embed

async def card_info_embed(card):
    details = CACHE_CARDS_DICT.get(card["fd_card"])
    desc = f"{details["fd_bundle"]}\n{details['fd_member']}\n{details['fd_type']}"

    file = await get_image_file(details["fd_image"])

    if details["fd_desc"]:
        desc += f"\n\n{details['fd_desc']}"

    if details["fd_type"] == "signed":
        embed = discord.Embed(
            title = f"Card ID: `{card["fd_display"]}`",
            description = f"{desc}",
            color = get_color(details["fd_member"])
        )
    else:
        embed = discord.Embed(
            title = f"Card ID: `{card["fd_display"]}`",
            description = f"{desc}"
        )
        
    embed.add_field(name = "", value = f"**Obtained by**: <@!{card["fd_oowner"]}>\n**Owned by**: <@!{card["fd_cowner"]}>")
    embed.add_field(name = "", value = f"Copies owned: {card["fd_dupes"]}\n{get_card_rating(card["fd_rating"])}", inline = False)
    embed.set_image(url = "attachment://card.png")
    embed.set_footer(text = f"Obtained: {display_date(card["fd_created"])}")
    return embed, file

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
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST, CACHE_CARDS_UPGRADE
    owners = await run_query(GET_OWNERS)
    CACHE_OWNERS_DICT = {(row["fd_card"], str(row["fd_cowner"])): row for row in owners}
    CACHE_OWNERS_LIST = list(CACHE_OWNERS_DICT.values())
    CACHE_CARDS_UPGRADE = {(row["fd_display"], str(row["fd_cowner"])): row for row in owners}
    print("Owners cached")

async def get_user(user_id):
    await check_user(user_id)
    return CACHE_USERS_DICT.get(str(user_id))

async def add_user(user):
    return await run_query(ADD_USER, (user.id, user.name, datetime.now()), False)

async def add_ownership(card, card_id, user, date):
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST, CACHE_CARDS_COLLECTION
    new = {
        "fd_card": card,
        "fd_display": card_id,
        "fd_rating": 0,
        "fd_dupes": 1,
        "fd_oowner": str(user["id"]),
        "fd_cowner": str(user["id"]),
        "fd_created": date
    }
    CACHE_OWNERS_DICT[(card, str(user["id"]))] = new
    CACHE_OWNERS_LIST.append(new)
    CACHE_CARDS_UPGRADE[(card_id, str(user["id"]))] = new

    collection = CACHE_CARDS_COLLECTION.get(str(user["id"]))
    if collection is not None:
        collection.append(new)
    else:
        CACHE_CARDS_COLLECTION[str(user["id"])] = [new]
    
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
                
async def get_image(url, max = (800, 800)):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                print(f"url: {url}")
                raise Exception("Failed to fetch image")
            
            data = await resp.read()

    img = Image.open(BytesIO(data))
    img = img.convert("RGB")
    img.thumbnail(max)

    output = BytesIO()
    img.save(output, format = "PNG")
    
    return output.getvalue()

async def get_image_file(path):
    global CACHE_IMAGES_MEMORY
    img_data = None

    if path in CACHE_IMAGES_MEMORY:
        img_data = CACHE_IMAGES_MEMORY[path]
    else:
        disk_cache = get_cache(path)
        if os.path.exists(disk_cache):
            with open(disk_cache, "rb") as f:
                img_data = f.read()

            CACHE_IMAGES_MEMORY[path] = img_data

    if img_data is None:
        img_data = await get_image(constants.IMAGE_HOST.format(path))
        CACHE_IMAGES_MEMORY[path] = img_data

        with open(disk_cache, "wb") as f:
            f.write(img_data)

    if len(CACHE_IMAGES_MEMORY) > CACHE_MAX_MEMORY:
        CACHE_IMAGES_MEMORY.pop(next(iter(CACHE_IMAGES_MEMORY)))

    return discord.File(fp = BytesIO(img_data), filename = "card.png")

async def generate_card_embed(card, user, signed = False):
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST
    now = datetime.now()
    copies = 1
    
    owned = CACHE_OWNERS_DICT.get((card["id"], str(user["id"])))
    if owned:
        caption = "**You acquired a duplicate card**"
        owned["fd_dupes"] += 1
        copies = owned["fd_dupes"]
        card_id = owned["fd_display"]
        now = owned["fd_created"]
        rating = get_card_rating(owned["fd_rating"])
        if await run_query(UPDATE_COPIES, (copies, card_id), False):
            print("Updated number of copies")
        else:
            print("Failed updating the number of copies")
    else:
        caption = "**You acquired a new card**"
        card_id = await generate_card_id()
        rating = get_card_rating(0)
        if await add_ownership(int(card["id"]), card_id, user, now):
            print("Added new ownership")
        else:
            print("Failed adding new ownership")

    desc = f"{card['fd_bundle']}\n{card['fd_member']}\n{card['fd_type']}"
    if card["fd_desc"]:
        desc += f"\n\n{card['fd_desc']}"

    file = await get_image_file(card["fd_image"])

    if signed:
        embed = discord.Embed(
            title = f"Card ID: `{card_id}`",
            description = desc,
            color = get_color(card["fd_member"])
        )
    else:
        embed = discord.Embed(
            title = f"Card ID: {card_id}",
            description = desc
        )

    embed.add_field(name = "", value = f"Copies owned: {copies}\n{rating}")
    embed.set_image(url = "attachment://card.png")
    embed.set_footer(text = f"Obtained: {display_date(now)}")

    return embed, file, caption

async def upgrade_card(card):
    rating = card["fd_rating"]
    copies = card["fd_dupes"]
    card_id = card["fd_display"]

    if rating == 5:
        return None, None, "Card is already max upgraded!"
    
    if copies < 2 ** (rating + 1):
        return None, None, f"You don\'t have enough copies to upgrade this card. ({copies}/{2 ** (rating + 1)})"
    else:
        rating += 1
        copies -= (2 ** rating)
        details = CACHE_CARDS_DICT.get(card["fd_card"])
        desc = f"{details["fd_bundle"]}\n{details['fd_member']}\n{details['fd_type']}"
        if details["fd_desc"]:
            desc += f"\n\n{details['fd_desc']}"

        file = await get_image_file(details["fd_image"])

        if await run_query(UPGRADE_CARD, (rating, copies + 1, card_id), False):
            updated = CACHE_OWNERS_DICT.get((card["fd_card"], card["fd_cowner"]))
            updated["fd_rating"] = rating
            updated["fd_dupes"] = copies + 1
            caption = "**You upgraded your card!**"
            if details["fd_type"] == "signed":
                embed = discord.Embed(
                    title = f"Card ID: `{card_id}`",
                    description = f"{desc}",
                    color = get_color(details["fd_member"])
                )
            else:
                embed = discord.Embed(
                    title = f"Card ID: `{card_id}`",
                    description = f"{desc}"
                )

            embed.add_field(name = "", value = f"Copies owned: {copies + 1}\n{get_card_rating(rating)}")
            embed.set_image(url = "attachment://card.png")
            embed.set_footer(text = f"Obtained: {display_date(card["fd_created"])}")

            return embed, file, caption
        else:
            return None, None, f"An error occured while trying to upgrade"
