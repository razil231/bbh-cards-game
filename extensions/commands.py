import discord
import constants
import random
import helpers.util

from discord.ext import commands
from discord import app_commands
from datetime import datetime


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name = "ping", description = "pings the bot",
                             extras = {"syntax": "`bc ping`", "args": None})
    async def ping(self, ctx):
        '''pings the bot'''
        await ctx.reply("`pong`", mention_author = False)

    @commands.hybrid_command(name = "card", description = "gets a card from the current pool",
                             extras = {"syntax": "`bc card`", "args": None})
    async def card(self, ctx):
        '''gets a card from the current pool'''
        # if not await helpers.util.check_user(ctx.author.id):
        #     await ctx.reply("New user detected! Please use `start` command.")
        # else:
        if helpers.util.one_percent_roll():
            await ctx.reply("Signature drop!")
        else:
            card = random.choice(helpers.util.CACHE_CARDS_NORMAL) if helpers.util.CACHE_CARDS_NORMAL else None

            if not card:
                await ctx.reply("No card")
                return

            embed = discord.Embed(
                title = "",
                description = ""
            )
            file = discord.File(card["fd_image"], filename = "card.png")
            embed.set_image(url = "attachment://card.png")

            await ctx.reply(content = "Normal drop!", embed = embed, file = file, mention_author = False)


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))