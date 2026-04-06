import discord
import json
import os
import hashlib
import secrets
import string
import math
import aiohttp
import aiomysql
import aiofiles
import logging
import constants

from datetime import datetime
from discord.ext import commands
from collections import defaultdict
from PIL import Image
from io import BytesIO
from db import get_pool
from helpers.queries import ID_CHECK, ASCEND_CHECK, GET_USERS, GET_CARDS, GET_OWNERS, ADD_USER, ADD_OWNER, UPDATE_OWNERSHIP, UPDATE_USER

COGS_FILE = "cogs.json"
GUILDS_FILE = "guilds.json"
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
CACHE_GUILDS = set()

logger = logging.getLogger("bbh_cards")

os.makedirs(CACHE_DIR, exist_ok = True)

BASE_COOLDOWNS = {
    constants.CooldownCommand.CARD: constants.CD_CARD,
    constants.CooldownCommand.DAILY: constants.CD_DAILY,
    constants.CooldownCommand.ASCEND: constants.CD_ASCEND,
    constants.CooldownCommand.UPGRADE: constants.CD_UPGRADE
}

def load_guilds():
    global CACHE_GUILDS
    try:
        with open(GUILDS_FILE, "r") as f:
            data = json.load(f)
            CACHE_GUILDS = set(data.get("guilds", []))
    except FileNotFoundError:
        CACHE_GUILDS = set()

def save_guilds():
    with open(GUILDS_FILE, "w") as f:
        json.dump({"guilds": list(CACHE_GUILDS)}, f, indent = 4)

def add_guild(guild):
    global CACHE_GUILDS
    CACHE_GUILDS.add(guild)
    save_guilds()

def remove_guild(guild):
    global CACHE_GUILDS
    CACHE_GUILDS.discard(guild)
    save_guilds()

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

def get_start_embed(start = False):
    embed = discord.Embed(
        title = "Welcome to BBH Cards",
        description = "A fun card collecting discord bot exclusive to this server",
        color = 0xFF_FF_FF
    )
    embed.add_field(name = "What is it about?", value = "A discord bot that will let users collect, upgrade, ascend and trade BINI cards", inline = False)
    embed.add_field(name = "How to play?", value = "To start you just have to create a user profile via `/start`", inline = False)
    embed.add_field(name = "What does upgrade mean?", value = "Upgrading a card via `/upgrade` will use copies of that specific card to upgrade it to the next star", inline = False)
    embed.add_field(name = "What does ascend mean?", value = "Ascending a card will tier up any 5 star card to *rare*, *legendary* or *ultimate* tier", inline = False)
    embed.add_field(name = "So ascending is random?", value = "Yes, the base chances are as follows: *rare*: ***60%***, *legendary*: ***30%*** and *ultimate*: ***10%***", inline = False)
    embed.add_field(name = "This embed?", value = "You can still see this embed via `/info` command", inline = False)
    embed.add_field(name = "", value = "", inline = False)
    if start:
        embed.add_field(name = "Create a user profile?", value = "If the buttons below are disabled, use the `/start` command again.")
    embed.set_footer(text = "Please report bugs to any game admins")

    return embed

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
        embed.add_field(name = "`bc set bio <content>`", value = "- sets bio of a user", inline = False)
        embed.add_field(name = "`bc set favorite <card ID>`", value = "- sets a card image for your profile", inline = False)
        embed.add_field(name = "`bc profile [@user]`", value = "- shows the profile of a user", inline = False)
        embed.add_field(name = "`bc card`", value = "- gets a card from the current pool", inline = False)
        embed.add_field(name = "`bc cards [@user]`", value = "- shows card collection of a user", inline = False)
        embed.add_field(name = "`bc upgrade <card ID>`", value = "- upgrade a card to a higher rating", inline = False)
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

def parse_multi(value):
    try:
        multi = float(value)
    except (ValueError, TypeError):
        return None
    
    if not math.isfinite(multi):
        return None
    
    if 0 > multi:
        return None
    if 100 < multi:
        return None
    
    return round(multi, 2)

def roll_with_multi(multi):
    base_rate = 0.01
    chance = min(base_rate * multi, 1.0)
    return secrets.randbelow(10_000) < int(chance * 10_000)

def roll_ascend(multi):
    multi = max(0, min(multi, 100))
    additional = 1 + (multi / 100) if multi != 1 else 1

    ultimate = 10 * additional
    legendary = 30
    rare = 60

    scale = 100
    ultimate = int(ultimate * scale)
    legendary = int(legendary * scale)
    rare = int(rare * scale)
    total = ultimate + legendary + rare

    roll = secrets.randbelow(total)
    if roll < ultimate:
        return constants.RARITY[2], 8
    elif roll < ultimate + legendary:
        return constants.RARITY[1], 7
    else:
        return constants.RARITY[0], 6

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
    stars = ""
    rarity = "basic"

    if rating > 5:
        if rating == 6:
            rarity = "rare"
            stars = f"{constants.STAR_RARE}{constants.STAR_RARE}{constants.STAR_RARE}{constants.STAR_RARE}{constants.STAR_RARE}"
        elif rating == 7:
            rarity = "legendary"
            stars = f"{constants.STAR_LEGENDARY}{constants.STAR_LEGENDARY}{constants.STAR_LEGENDARY}{constants.STAR_LEGENDARY}{constants.STAR_LEGENDARY}"
        elif rating == 8:
            rarity = "ultimate"
            stars = f"{constants.STAR_ULTIMATE}{constants.STAR_ULTIMATE}{constants.STAR_ULTIMATE}{constants.STAR_ULTIMATE}{constants.STAR_ULTIMATE}"
    else:
        for _ in range(rating):
            stars += f"{constants.STAR_LIGHT}"
        for _ in range(5 - rating):
            stars += f"{constants.STAR_DARK}"

    return stars, rarity

def get_user_cards(user_id):
    return CACHE_CARDS_COLLECTION.get(str(user_id), [])

def get_cooldown(ctx, command_enum: constants.CooldownCommand):
    base = BASE_COOLDOWNS[command_enum]

    booster_role = discord.utils.get(ctx.author.roles, id = constants.BBH_BOOSTER)
    tester_role = discord.utils.get(ctx.author.roles, id = constants.BBH_TESTER)

    if booster_role:
        base *= 0.8

    if tester_role:
        base = base ** 0

    return commands.Cooldown(1, base)

def card_list_embed(user, cards, page, total):
    start = page * 9
    end = start + 9
    pages = cards[start:end]

    embed = discord.Embed(
        title = "Card Collection",
        description = f"{user.global_name}\'s cards:",
        color = 0xFF_FF_FF
    )
    for _, card in enumerate(pages, start = start):
        copies = card["o"]["fd_dupes"]
        if card["c"]["fd_type"] == "signed":
            if card["o"]["fd_rarity"] == constants.RARITY[0]:
                display = f"{constants.TYPE_SIGNED_RARE} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
            elif card["o"]["fd_rarity"] == constants.RARITY[1]:
                display = f"{constants.TYPE_SIGNED_LEGENDARY} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
            elif card["o"]["fd_rarity"] == constants.RARITY[2]:
                display = f"{constants.TYPE_SIGNED_ULTIMATE} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
            else:
                display = f"{constants.TYPE_SIGNED} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
        else:
            if card["o"]["fd_rarity"] == constants.RARITY[0]:
                display = f"{constants.TYPE_NORMAL_RARE} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
            elif card["o"]["fd_rarity"] == constants.RARITY[1]:
                display = f"{constants.TYPE_NORMAL_LEGENDARY} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
            elif card["o"]["fd_rarity"] == constants.RARITY[2]:
                display = f"{constants.TYPE_NORMAL_ULTIMATE} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
            else:
                display = f"{constants.TYPE_NORMAL} **{card["c"]["fd_bundle"]}**: {card["c"]["fd_member"]} - {copies} {"copies" if copies > 1 else "copy"}"
        
        stars, _ = get_card_rating(card["o"]["fd_rating"])
        embed.add_field(name = f"`{card["o"]['fd_display']}` - {stars}", value = f"{display}", inline = False)

    embed.set_footer(text = f"Page {page + 1}/{total}")
    return embed

def get_command_perms(ctx):
    if not check_perms(ctx):
        return ""
    
    return ", `bloom`, `bloomcension`, `bloomspin`, `multi`, `lock`"

def get_collections():
    global CACHE_CARDS_COLLECTION
    CACHE_CARDS_COLLECTION = defaultdict(list)

    for ownership in CACHE_OWNERS_LIST:
        card = CACHE_CARDS_DICT.get(ownership["fd_card"])
        if not card:
            continue

        data = {"o": ownership, "c": card}
        user = str(ownership["fd_cowner"])
        CACHE_CARDS_COLLECTION[user].append(data)

def add_ownership(card, card_id, user, date, rarity, rating):
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST, CACHE_CARDS_COLLECTION
    new = {
        "fd_card": card,
        "fd_display": card_id,
        "fd_rating": rating,
        "fd_rarity": rarity,
        "fd_dupes": 1,
        "fd_oowner": str(user["id"]),
        "fd_cowner": str(user["id"]),
        "fd_created": date,
        "fd_deleted": None
    }
    CACHE_OWNERS_DICT[(card, str(user["id"]), rarity)] = new
    CACHE_OWNERS_LIST.append(new)
    CACHE_CARDS_UPGRADE[(card_id, str(user["id"]))] = new

    details = CACHE_CARDS_DICT.get(card)
    data = {"o": new, "c": details}
    CACHE_CARDS_COLLECTION.setdefault(str(user["id"]), []).append(data)
    
    query = [(ADD_OWNER, (card, card_id, rating, rarity, str(user["id"]), str(user["id"]), date))]
    return query

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

async def run_query(queries, fetch = True):
    pool = await get_pool()

    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            if isinstance(queries, tuple):
                queries = [queries]

            results = []
            try:
                for query, params in queries:
                    await cursor.execute(query, params)
                    if fetch:
                        results.append(await cursor.fetchall())

                if not fetch:
                    await conn.commit()
                    return cursor.rowcount
                else:
                    return results if len(results) > 1 else results[0]
            except Exception:
                logger.exception("Exception: run_query")
                print("run_query exception")
                await conn.rollback()
                raise
    
async def check_ascend_dupe(type, rating, rarity, owner):
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(ASCEND_CHECK, (type, rating, rarity, owner))
            if not await cursor.fetchone():
                return False
            else:
                return True

async def check_user(user):
    global CACHE_USERS_DICT, CACHE_USERS_LIST
    user_id = str(user)

    if user_id in CACHE_USERS_DICT:
        return True

    query = [(GET_USERS, None)]
    users = await run_query(query)
    CACHE_USERS_DICT = {str(row["id"]): row for row in users}
    CACHE_USERS_LIST = list(CACHE_USERS_DICT.values())

    return user_id in CACHE_USERS_DICT

async def get_cards():
    global CACHE_CARDS_DICT, CACHE_CARDS_LIST, CACHE_CARDS_NORMAL, CACHE_CARDS_SIGNED
    query = [(GET_CARDS, None)]
    cards = await run_query(query)
    CACHE_CARDS_DICT = {row["id"]: row for row in cards}
    CACHE_CARDS_LIST = list(CACHE_CARDS_DICT.values())
    CACHE_CARDS_NORMAL = [card for card in CACHE_CARDS_LIST if card["fd_type"] == "normal"]
    CACHE_CARDS_SIGNED = [card for card in CACHE_CARDS_LIST if card["fd_type"] == "signed"]

async def get_owners():
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST, CACHE_CARDS_UPGRADE
    query = [(GET_OWNERS, None)]
    owners = await run_query(query)
    CACHE_OWNERS_DICT = {(row["fd_card"], str(row["fd_cowner"]), row["fd_rarity"]): row for row in owners}
    CACHE_OWNERS_LIST = list(CACHE_OWNERS_DICT.values())
    CACHE_CARDS_UPGRADE = {(row["fd_display"], str(row["fd_cowner"])): row for row in owners}

async def get_user(user_id):
    await check_user(user_id)
    return CACHE_USERS_DICT.get(str(user_id))

async def add_user(user):
    query = [(ADD_USER, (user.id, user.name, datetime.now()))]
    return await run_query(query, False) is not None

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
                
async def get_image(url, rarity, max = (800, 800)):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception("Failed to fetch image")
            
            data = await resp.read()

    if rarity == constants.RARITY[0]:
        overlay = Image.open("images/overlay_rare.png").convert("RGBA")
    elif rarity == constants.RARITY[1]:
        overlay = Image.open("images/overlay_legendary.png").convert("RGBA")
    elif rarity == constants.RARITY[2]:
        overlay = Image.open("images/overlay_ultimate.png").convert("RGBA")
    else:
        overlay = None

    img = Image.open(BytesIO(data))
    img = img.convert("RGBA")
    img.thumbnail(max)

    if overlay is not None:
        overlay = overlay.resize(img.size)
        img.paste(overlay, (0, 0), overlay)

    output = BytesIO()
    img.save(output, format = "PNG")
    
    return output.getvalue()

async def get_image_file(path, rarity):
    global CACHE_IMAGES_MEMORY
    cache_key = f"{path}-{rarity}"
    img_data = None

    if cache_key in CACHE_IMAGES_MEMORY:
        img_data = CACHE_IMAGES_MEMORY[cache_key]
    else:
        disk_cache = get_cache(cache_key)
        if os.path.exists(disk_cache):
            with open(disk_cache, "rb") as f:
                img_data = f.read()

            CACHE_IMAGES_MEMORY[cache_key] = img_data

    if img_data is None:
        img_data = await get_image(constants.IMAGE_HOST.format(path), rarity)
        CACHE_IMAGES_MEMORY[cache_key] = img_data

        with open(disk_cache, "wb") as f:
            f.write(img_data)

    if len(CACHE_IMAGES_MEMORY) > CACHE_MAX_MEMORY:
        CACHE_IMAGES_MEMORY.pop(next(iter(CACHE_IMAGES_MEMORY)))

    return discord.File(fp = BytesIO(img_data), filename = "card.png")

async def get_fav_file(card, user):
    o_details = CACHE_CARDS_UPGRADE.get((card, str(user)))
    c_details = CACHE_CARDS_DICT.get(o_details["fd_card"])
    stars, rarity = get_card_rating(o_details["fd_rating"])
    file = await get_image_file(c_details["fd_image"], rarity)
    return file, stars

async def generate_card_embed(card, user, signed = False, rarity = "basic"):
    global CACHE_OWNERS_DICT, CACHE_OWNERS_LIST
    now = datetime.now()
    copies = 1
    
    owned = CACHE_OWNERS_DICT.get((card["id"], str(user["id"]), rarity))
    if owned:
        caption = "**You acquired a duplicate card**"
        owned["fd_dupes"] += 1
        copies = owned["fd_dupes"]
        card_id = owned["fd_display"]
        now = owned["fd_created"]
        stars, rarity = get_card_rating(owned["fd_rating"])
        query = [(UPDATE_OWNERSHIP, (owned["fd_rating"], rarity, copies, user["id"], card_id))]
        await run_query(query, False)
    else:
        caption = "**You acquired a new card**"
        card_id = await generate_card_id()
        stars, rarity = get_card_rating(0)
        query = add_ownership(int(card["id"]), card_id, user, now, rarity, 0)
        await run_query(query, False)

    desc = f"{card['fd_bundle']}\n{card['fd_member']}\n{card['fd_type']}"
    if card["fd_desc"]:
        desc += f"\n\n{card['fd_desc']}"

    file = await get_image_file(card["fd_image"], rarity)

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

    embed.add_field(name = "", value = f"Copies owned: {copies}\n{stars}")
    embed.set_image(url = "attachment://card.png")
    embed.set_footer(text = f"Obtained: {display_date(now)}")
    logger.info(f"{now}: User {user["id"]} got a copy of {card_id} {rarity}{" signed" if signed else " normal"} {card["fd_bundle"]} {card["fd_member"]} - {copies} total")
    print(f"{now}: User {user["id"]} got a copy of {card_id} {rarity}{" signed" if signed else " normal"} {card["fd_bundle"]} {card["fd_member"]} - {copies} total")
    return embed, file, caption

async def get_profile_embed(user, details):
    embed = discord.Embed(
        title = f"{user.display_name}\'s Profile {'(🔒Locked)' if int(details["fd_lock"]) == 1 else ''}",
        description = details["fd_desc"] if details["fd_desc"] is not None else "",
        color = 0xFF_FF_FF
    )
    curr = f"- {details["fd_curr1"]} {constants.BLOOM}\n"
    curr += f"- {details["fd_curr2"]} {constants.BLOOMCENSION}\n"
    curr += f"- {details["fd_curr3"]} {constants.BLOOMSPIN}"

    ascend = 10 * (1 + (details["fd_multi"]/100)) if details["fd_multi"] != 1 else 10
    boosts = f"- __**Signed**__: *{details['fd_multi']:.2f}%* chances\n"
    boosts += f"- __**Ultimate**__: *{ascend:.2f}%* chances"

    embed.add_field(name = "Boosts:", value = f"{boosts}", inline = False)
    embed.add_field(name = "Currency:", value = f"{curr}", inline = False)

    if details["fd_fav"] is not None:
        image, rating = await get_fav_file(details["fd_fav"], user.id)
        embed.set_image(url = "attachment://card.png")
        embed.add_field(name = "", value = f"{rating}")
    else:
        image = None

    embed.set_thumbnail(url = user.display_avatar.url)
    embed.set_footer(text = f"Created: {display_date(details["fd_created"])}")
    
    return embed, image

async def card_info_embed(card):
    desc = f"{card["c"]["fd_bundle"]}\n{card["c"]['fd_member']}\n{card["c"]['fd_type']}"

    stars, rarity = get_card_rating(card["o"]["fd_rating"])
    file = await get_image_file(card["c"]["fd_image"], rarity)

    if card["c"]["fd_desc"]:
        desc += f"\n\n{card["c"]['fd_desc']}"

    if card["c"]["fd_type"] == "signed":
        embed = discord.Embed(
            title = f"Card ID: `{card["o"]["fd_display"]}`",
            description = f"{desc}",
            color = get_color(card["c"]["fd_member"])
        )
    else:
        embed = discord.Embed(
            title = f"Card ID: `{card["o"]["fd_display"]}`",
            description = f"{desc}"
        )
        
    embed.add_field(name = "", value = f"**Obtained by**: <@!{card["o"]["fd_oowner"]}>\n**Owned by**: <@!{card["o"]["fd_cowner"]}>")
    embed.add_field(name = "", value = f"Copies owned: {card["o"]["fd_dupes"]}\n{stars}", inline = False)
    embed.set_image(url = "attachment://card.png")
    embed.set_footer(text = f"Obtained: {display_date(card["o"]["fd_created"])}")
    return embed, file

async def upgrade_card(card, stars):
    from_rating = card["fd_rating"]
    rating = card["fd_rating"]
    copies = card["fd_dupes"]
    card_id = card["fd_display"]

    card_value = (2 ** rating)
    total_value = card_value + (copies - 1)
    stars = stars if stars > 0 else rating + 1

    if rating >= 5:
        return None, None, "Card is already max upgraded!"
    
    if total_value < 2 ** stars:
        return None, None, f"You don\'t have enough copies to upgrade this card. ({total_value}/{2 ** (stars)})"
    else:
        rating = stars
        copies = copies - ((2 ** rating) - card_value)
        details = CACHE_CARDS_DICT.get(card["fd_card"])
        desc = f"{details["fd_bundle"]}\n{details['fd_member']}\n{details['fd_type']}"
        if details["fd_desc"]:
            desc += f"\n\n{details['fd_desc']}"

        stars, rarity = get_card_rating(rating)
        file = await get_image_file(details["fd_image"], rarity)

        query = [(UPDATE_OWNERSHIP, (rating, card["fd_rarity"], copies + 1, card["fd_cowner"], card_id))]
        if await run_query(query, False) is not None:
            updated = CACHE_OWNERS_DICT.get((card["fd_card"], card["fd_cowner"], card["fd_rarity"]))
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

            embed.add_field(name = "", value = f"Copies owned: {copies + 1}\n{stars}")
            embed.set_image(url = "attachment://card.png")
            embed.set_footer(text = f"Obtained: {display_date(card["fd_created"])}")
            logger.info(f"User {card["fd_cowner"]} upgraded {card["fd_display"]} {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]} to {stars} stars")
            print(f"{datetime.now()}: User {card["fd_cowner"]} upgraded {card["fd_display"]} {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]} to {stars} stars")
            return embed, file, caption
        else:
            logger.error(f"There was an issue after user {card["fd_cowner"]} tried to upgrade {from_rating} {card["fd_display"]} {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]} to {stars} stars")
            print(f"{datetime.now()}: ERROR: There was an issue after user {card["fd_cowner"]} tried to upgrade {from_rating} {card["fd_display"]} {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]} to {stars} stars")
            return None, None, f"An error occured while trying to upgrade"
        
async def ascend_card(card, user):
    bloomcension = user["fd_curr2"]

    details = CACHE_CARDS_DICT.get(card["fd_card"])
    filtered = [owned for owned in CACHE_OWNERS_LIST if owned["fd_card"] == card["fd_card"] 
                and owned["fd_cowner"] == user["id"] and owned["fd_deleted"] is None]
    if len(filtered) == 4:
        return None, None, "You have already owned all the rarity tiers for this card"

    if card["fd_rating"] < 5:
        return None, None, "This is not a 5 star card!"
    elif card["fd_rating"] > 5:
        return None, None, "This card is ascended already!"
    
    if bloomcension < 1:
        return None, None, f"You don\'t have enough {constants.BLOOMCENSION} available."
    else:
        queries = []
        rarity, rating = roll_ascend(user["fd_multi"])
        if not await check_ascend_dupe(details["id"], rating, rarity, user["id"]):
            copies = card["fd_dupes"] - 1
            user["fd_curr2"] = bloomcension - 1
            queries.append((UPDATE_OWNERSHIP, (5, "basic", copies, str(user["id"]), card["fd_display"])))
            new_card = await generate_card_id()
            now = datetime.now()
            queries.append((UPDATE_USER, (
                user["fd_desc"], user["fd_curr1"], user["fd_curr2"], user["fd_curr3"], 
                user["fd_multi"], user["fd_fav"], user["fd_lock"], str(user["id"])
                )))
            queries.extend(add_ownership(int(details["id"]), new_card, user, now, rarity, rating))
            if await run_query(queries, False) is not None:
                caption = f"**You ascended your card to __*{rarity}*__ tier!**"
                desc = f"{details["fd_bundle"]}\n{details['fd_member']}\n{details['fd_type']}"

                if details["fd_desc"]:
                    desc += f"\n\n{details['fd_desc']}"

                stars, _ = get_card_rating(rating)
                file = await get_image_file(details["fd_image"], rarity)

                if details["fd_type"] == "signed":
                    embed = discord.Embed(
                        title = f"Card ID: `{new_card}`",
                        description = f"{desc}",
                        color = get_color(details["fd_member"])
                    )
                else:
                    embed = discord.Embed(
                        title = f"Card ID: `{new_card}`",
                        description = f"{desc}"
                    )

                embed.add_field(name = "", value = f"Copies owned: 1\n{stars}")
                embed.set_image(url = "attachment://card.png")
                embed.set_footer(text = f"Obtained: {display_date(card["fd_created"])}")
                logger.info(f"User {user["id"]} ascended {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]} to {rarity} tier")
                print(f"{now}: User {user["id"]} ascended {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]} to {rarity} tier")
                return embed, file, caption
            else:
                logger.error(f"There was an issue while user {user["id"]} tried to ascend {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]}")
                print(f"{now}: ERROR: There was an issue while user {user["id"]} tried to ascend {details["fd_type"]} {details["fd_bundle"]} {details["fd_member"]}")
                return None, None, f"An error occured while trying to ascend"
        else:
            message = f"You already have {'an' if rarity == constants.RARITY[2] else 'a'} {rarity} tier of this card!\n"
            message += f"-# Your bloomscension {constants.BLOOMCENSION} has been reimbursed but your cooldown is spent"
            return None, None, f"{message}"

async def update_user(details, field, value):
    details[field] = value
    query = [(UPDATE_USER, (details["fd_desc"], details["fd_curr1"], 
        details["fd_curr2"], details["fd_curr3"], 
        details["fd_multi"], details["fd_fav"], 
        details["fd_lock"], details["id"]))]
    if await run_query(query, False) is None:
        return False
    return True