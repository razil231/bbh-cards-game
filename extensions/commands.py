import random
import helpers.util

from discord.ext import commands
from discord import app_commands


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name = "ping", description = "pings the bot",
                             extras = {"syntax": "`bc ping`", "args": None})
    async def ping(self, ctx):
        '''pings the bot'''
        await ctx.reply("`pong`", mention_author = False)

    @commands.hybrid_command(name = "start", description = "initializes user profile",
                             extras = {"syntax": "`bc start`", "args": None})
    async def start(self, ctx):
        '''initializes user profile'''
        if await helpers.util.check_user(ctx.author.id):
            await ctx.reply("You're already registered")
        else:
            if await helpers.util.add_user(ctx.author):
                await ctx.reply("Successfully registered! You can check with `profile` command")
            else:
                await ctx.reply("A problem was encountered during registration! Please try again later")
        print("Command: start")

    @commands.hybrid_command(name = "card", description = "gets a card from the current pool",
                             extras = {"syntax": "`bc card`", "args": None})
    async def card(self, ctx):
        '''gets a card from the current pool'''
        if not await helpers.util.check_user(ctx.author.id):
            await ctx.reply("New user detected! Please use `start` command.")
        else:
            user = await helpers.util.get_user(ctx.author.id)
            if helpers.util.roll_with_multi(user["fd_multi"]):
                await ctx.reply("Signature drop!")
            else:
                card = random.choice(helpers.util.CACHE_CARDS_NORMAL) if helpers.util.CACHE_CARDS_NORMAL else None
                card_embed, card_image, caption = await helpers.util.generate_card_embed(card, user)
                await ctx.reply(content = f"{caption}", embed = card_embed, file = card_image, mention_author = False)
        print("Command: card")


async def setup(bot):
    await bot.add_cog(CommandsCog(bot))