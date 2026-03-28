import discord
import os
import importlib
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import constants
import helpers.queries
import helpers.util
import views.collection_view
import views.confirm_view
from db import init_db, setup_db, get_pool

load_dotenv()
token = os.getenv(constants.TOKEN)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

cardBot = commands.Bot(command_prefix = constants.PREFIX, intents = intents)
cardBot.remove_command("help")

### --------------------- BOT EVENTS START --------------------- ###
@cardBot.event
async def on_ready():
    activity = discord.Activity(type = discord.ActivityType.listening, name = constants.ACTIVITY)
    await cardBot.change_presence(status = discord.Status.online, activity = activity)

    for ext in helpers.util.load_cogs():
        try:
            await cardBot.load_extension(ext)
            print(f"Loaded {ext}")
        except Exception as e:
            print(f"Failed to load {ext}: {e}")

    await init_db()
    await helpers.util.get_cards()
    await helpers.util.get_owners()

    print("Card bot online")

@cardBot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        retry = error.retry_after

        hours = int(retry // 3_600)
        mins = int((retry % 3_600) // 60)
        secs = int(retry % 60)

        parts = []
        if hours: parts.append(f"{hours:02}:")
        if mins: parts.append(f"{mins:02}:")
        parts.append(f"{secs:02}s")

        await ctx.reply(f"Command on cooldown. Try again in {"".join(parts)}")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.reply("`Not a command`", mention_author = False)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("Argument missing, please check the correct syntax in `bc help [command]`", mention_author = False)
    else:
        await ctx.reply("`Exception caught!`", mention_author = False)
        print(f"Exception: {error}")
### ---------------------- BOT EVENTS END ---------------------- ###

### -------------------- BOT COMMANDS START -------------------- ###
@cardBot.command(hidden = True)
async def sync(ctx):
    if helpers.util.check_perms(ctx):
        await cardBot.tree.sync()
        await ctx.reply("`Commands synced`", mention_author = False)
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    print("Command: sync")

@cardBot.command(hidden = True)
async def reload_extension(ctx, extension):
    if helpers.util.check_perms(ctx):
        try:
            if extension in cardBot.extensions:
                await cardBot.reload_extension(extension)
                await ctx.reply(f"`Extension reloaded: {extension}`", mention_author = False)
            else:
                await cardBot.load_extension(extension)
                helpers.util.save_cog(extension)
                await ctx.reply(f"`Extension loaded: {extension}`", mention_author = False)
        except Exception as e:
            await ctx.reply("`Exception caught!`", mention_author = False)
            print(f"Exception: {e}")
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    print("Command: reload_extension")

@cardBot.command(hidden = True)
async def reload_helpers(ctx):
    if helpers.util.check_perms(ctx):
        try:
            importlib.reload(constants)
            importlib.reload(helpers.queries)
            importlib.reload(helpers.util)
            importlib.reload(views.collection_view)
            importlib.reload(views.confirm_view)

            await helpers.util.get_cards()
            await helpers.util.get_owners()
            await ctx.reply("`Helpers reloaded`", mention_author = False)
        except Exception as e:
            await ctx.reply("`Exception caught!`", mention_author = False)
            print(f"Exception: {e}")
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    print("Command: reload_helpers")

@cardBot.command(hidden = True)
async def sql_run(ctx, filepath):
    if helpers.util.check_perms(ctx):
        await helpers.util.run_sql(filepath)
        await ctx.reply("`Execution successful`")
    else:
        await ctx.reply("`Missing permissions`", mention_author = False)
    print("Command: sql_run")

@cardBot.command(hidden = True)
@commands.is_owner()
async def create_tables(ctx):
    await setup_db()
    await ctx.reply("`Initial tables created`")
    print("Commands: create_tables")

@cardBot.command(hidden = True)
@commands.is_owner()
async def close_db(ctx):
    pool = await get_pool()
    if pool:
        pool.close()
        await pool.wait_closed()
        print("DB connection closed")
    await ctx.reply("`DB connection closed`", mention_author = False)

### --------------------- BOT COMMANDS END --------------------- ###

cardBot.run(token)