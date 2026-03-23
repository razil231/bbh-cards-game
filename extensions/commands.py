import discord
import constants

from discord.ext import commands
from discord import app_commands
from datetime import datetime
from helpers.util import run_transaction
from db import get_pool


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name = "ping", description = "pings the bot",
                             extras = {"syntax": "`bcping`", "args": None})
    async def ping(self, ctx):
        '''pings the bot'''
        await ctx.reply("`pong`", mention_author = False)

    @commands.hybrid_command(name = "closedb", description = "closes the db connection")
    @commands.is_owner()
    async def closedb(self, ctx):
        '''closes the db connection'''
        pool = await get_pool()
        if pool:
            pool.close()
            await pool.wait_closed()
            print("DB connection closed")
        await ctx.reply("`DB connection closed`", mention_author = False)

    @commands.hybrid_command(name = "testinsert")
    async def testinsert(self, ctx):
        now = datetime.now()
        await run_transaction([
            ("INSERT INTO cards (fd_type, fd_bundle, fd_name, fd_member, fd_image)"
            "VALUES ('TYPE', 'BUNDLE', 'NAME', 'MEMBER', 'images/Chamen.png')",
             (now)
            )
        ])

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))