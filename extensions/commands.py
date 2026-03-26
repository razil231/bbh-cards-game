import discord
import random
import helpers.util
import constants

from discord.ext import commands
from discord import app_commands
from views.collection_view import CardView


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
    @commands.dynamic_cooldown(lambda ctx: helpers.util.get_cooldown(ctx, constants.CooldownCommand.CARD), commands.BucketType.user)
    async def card(self, ctx):
        '''gets a card from the current pool'''
        if not await helpers.util.check_user(ctx.author.id):
            await ctx.reply("New user detected! Please use `start` command.")
        else:
            user = await helpers.util.get_user(ctx.author.id)
            if helpers.util.roll_with_multi(user["fd_multi"]):
                card = random.choice(helpers.util.CACHE_CARDS_SIGNED) if helpers.util.CACHE_CARDS_SIGNED else None
                card_embed, card_image, caption = await helpers.util.generate_card_embed(card, user, True)
            else:
                card = random.choice(helpers.util.CACHE_CARDS_NORMAL) if helpers.util.CACHE_CARDS_NORMAL else None
                card_embed, card_image, caption = await helpers.util.generate_card_embed(card, user)
        
            await ctx.reply(content = f"{caption}", embed = card_embed, file = card_image, mention_author = False)
        print("Command: card")

    @commands.hybrid_command(name = "cards", description = "shows card collection of a user",
                             extras = {"syntax": "`bc cards [user]`", "args": "user: **optional**, user mention"})
    async def cards(self, ctx, user: discord.User = None):
        target = user or ctx.author
        user_cards = helpers.util.get_user_cards(target.id)

        if not await helpers.util.check_user(target.id):
            return await ctx.reply(f"<@!{target.id}> is not registered")

        if not user_cards:
            return await ctx.reply(f"<@!{target.id}> has no cards")
        
        view = CardView(ctx.author, target, user_cards)
        embed = helpers.util.card_list_embed(target, user_cards, 0, view.total)

        await ctx.reply(embed = embed, view = view, mention_author = False)
        print("Command: cards")

    @commands.hybrid_command(name = "upgrade", description = "upgrade a card to a higher rating",
                             extras = {"syntax": "`bc upgrade <card_id>`", "args": "card_id: **required**, ID of the card"})
    @commands.dynamic_cooldown(lambda ctx: helpers.util.get_cooldown(ctx, constants.CooldownCommand.UPGRADE), commands.BucketType.user)
    async def upgrade(self, ctx, card_id):
        '''upgrade a card to a higher rating'''
        if not await helpers.util.check_user(ctx.author.id):
            await ctx.reply("New user detected! Please use `start` command.")
        else:
            card = helpers.util.CACHE_CARDS_UPGRADE.get((card_id, str(ctx.author.id)))
            if not card:
                await ctx.reply("Card not found. Please check the card ID again")
            else:
                card_embed, card_image, caption = await helpers.util.upgrade_card(card)
                if card_embed:
                    await ctx.reply(content = f"{caption}", embed = card_embed, file = card_image, mention_author = False)
                else:
                    await ctx.reply(f"{caption}", mention_author = False)
        print("Command: upgrade")

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))