import discord
import os
import importlib
import aiohttp
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import constants
from db import init_db
from helpers.util import load_cogs

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

    await init_db()

    for ext in load_cogs():
        try:
            await cardBot.load_extension(ext)
            print(f"Loaded {ext}")
        except Exception as e:
            print(f"Failed to load {ext}: {e}")

    print("Card bot online")

@cardBot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.reply("`Not a command`", mention_author = False)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply("Argument missing, please check the correct syntax in `char help [command]`", mention_author = False)
    else:
        await ctx.reply("`Exception caught!`", mention_author = False)
        print(f"Exception: {error}")
### ---------------------- BOT EVENTS END ---------------------- ###

cardBot.run(token)