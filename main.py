import discord
import os
import importlib
import time
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import constants
import helpers.queries
import helpers.util
import views.collection_view
import views.confirm_view
from db import init_db, setup_db, get_pool
from helpers.logger import setup_logger

load_dotenv()
token = os.getenv(constants.TOKEN)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

cardBot = commands.Bot(command_prefix = constants.PREFIX, intents = intents)
cardBot.remove_command("help")
logger = setup_logger(cardBot, constants.LOGGING_CHANNEL)

### --------------------- BOT EVENTS START --------------------- ###
@cardBot.event
async def on_ready():
    activity = discord.Activity(type = discord.ActivityType.listening, name = constants.ACTIVITY)
    await cardBot.change_presence(status = discord.Status.online, activity = activity)

    for ext in helpers.util.load_cogs():
        try:
            await cardBot.load_extension(ext)
            logger.info(f"Loaded {ext}")
        except Exception as e:
            logger.exception(f"Failed to load {ext}")

    helpers.util.load_guilds()
    await init_db()
    await helpers.util.get_cards()
    await helpers.util.get_owners()
    helpers.util.get_collections()
    logger.info("Card bot online")

@cardBot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry = error.retry_after
        ts = int(time.time() + retry)
        await ctx.reply(f"Command on cooldown. Try again in <t:{ts}:R>")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.reply("`Not a command`", mention_author = False)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("Argument missing, please check the correct syntax in `bc help [command]`", mention_author = False)
    elif isinstance(error, commands.CheckFailure):
        await ctx.reply("This server is not authorized to use this bot!", mention_author = False)
    else:
        await ctx.reply("`Exception caught!`", mention_author = False)
        logger.error(f"{error}")
### ---------------------- BOT EVENTS END ---------------------- ###

### -------------------- BOT COMMANDS START -------------------- ###
@cardBot.command(hidden = True)
async def sync(ctx):
    if helpers.util.check_perms(ctx):
        await cardBot.tree.sync()
        await ctx.reply("`Commands synced`", mention_author = False)
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    logger.info("Command: sync")

@cardBot.command(hidden = True)
async def reload_extension(ctx, extension):
    if helpers.util.check_perms(ctx):
        try:
            if extension in cardBot.extensions:
                await cardBot.reload_extension(extension)
                await ctx.reply(f"`Extension reloaded: {extension}`", mention_author = False)
                logger.info(f"Extension reloaded: {extension}")
            else:
                await cardBot.load_extension(extension)
                helpers.util.save_cog(extension)
                await ctx.reply(f"`Extension loaded: {extension}`", mention_author = False)
                logger.info(f"Extension loaded: {extension}")
        except Exception as e:
            await ctx.reply("`Exception caught!`", mention_author = False)
            logger.exception("Exception: reload_extension command")
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    logger.info("Command: reload_extension")

@cardBot.command(hidden = True)
async def reload_helpers(ctx):
    if helpers.util.check_perms(ctx):
        try:
            importlib.reload(constants)
            importlib.reload(helpers.queries)
            importlib.reload(helpers.util)
            importlib.reload(views.collection_view)
            importlib.reload(views.confirm_view)

            helpers.util.load_guilds()
            await helpers.util.get_cards()
            await helpers.util.get_owners()
            helpers.util.get_collections()
            await ctx.reply("`Helpers reloaded`", mention_author = False)
            logger.info("Helpers reloaded")
        except Exception as e:
            await ctx.reply("`Exception caught!`", mention_author = False)
            logger.exception("Exception: reload_helpers command")
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    logger.info("Command: reload_helpers")

@cardBot.command(hidden = True)
async def sql_run(ctx, filepath):
    if helpers.util.check_perms(ctx):
        await helpers.util.run_sql(filepath)
        await ctx.reply("`Execution successful`")
        logger.info("SQL execution successful")
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    logger.info("Command: sql_run")

@cardBot.command(hidden = True)
@commands.is_owner()
async def create_tables(ctx):
    await setup_db()
    await helpers.util.get_cards()
    await helpers.util.get_owners()
    helpers.util.get_collections()
    await ctx.reply("`Initial tables created`")
    logger.info("Commands: create_tables")

@cardBot.command(hidden = True)
@commands.is_owner()
async def close_db(ctx):
    pool = await get_pool()
    if pool:
        pool.close()
        await pool.wait_closed()
        logger.info("Database connection closed")
    await ctx.reply("`DB connection closed`", mention_author = False)

@cardBot.command(hidden = True)
async def guild_check(ctx):
    return ctx.guild and ctx.guild.id in helpers.util.CACHE_GUILDS

@cardBot.command(hidden = True)
@commands.is_owner()
async def add_guild(ctx, guild: int):
    helpers.util.add_guild(guild)
    logger.info(f"Guild {guild} added")
    return await ctx.reply(f"Guild {guild} added")

@cardBot.command(hidden = True)
@commands.is_owner()
async def remove_guild(ctx, guild: int):
    helpers.util.remove_guild(guild)
    logger.info(f"Guild {guild} removed")
    await ctx.reply(f"Guild {guild} removed")
    server = cardBot.get_guild(guild)
    if server:
        await server.leave()
### --------------------- BOT COMMANDS END --------------------- ###

cardBot.add_check(guild_check)
cardBot.run(token)