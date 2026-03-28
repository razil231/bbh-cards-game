import discord
import random
import helpers.util
import constants

from discord.ext import commands
from discord import app_commands
from views.collection_view import CardView
from views.confirm_view import ConfirmView


class CommandsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name = "ping", description = "pings the bot",
                             extras = {"syntax": "`bc ping`", "args": None})
    async def ping(self, ctx):
        '''pings the bot'''
        await ctx.reply("`pong`", mention_author = False)

    @commands.hybrid_command(name = "help", description = "shows all commands", 
                             extras = {"syntax": "`bc help [command]`", "args": "- command: **optional**, command name"})
    async def help(self, ctx, *, command = None):
        '''shows all commands'''
        if not command:
            embed = helpers.util.get_info(self.bot)
        else:
            embed = helpers.util.get_info(self.bot, command)

        if not embed:
            await ctx.reply(f"`{command} is not a command`")
        else:
            await ctx.reply(embed = embed, mention_author = False)
        print("Command: help")

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

    @commands.hybrid_command(name = "profile", description = "shows the profile of a user",
                             extras = {"syntax": "`bc profile [@user]`", "args": "- user: **optional**, user mention"})
    async def profile(self, ctx, user: discord.User = None):
        '''shows the profile of a user'''
        target = user or ctx.author
        if not await helpers.util.check_user(target.id):
            return await ctx.reply(f"<@!{target.id}> is not registered")
        
        if helpers.util.check_lock(ctx.author.id):
            return await ctx.reply("**You\'re account has been locked! Please contact any game admin.**")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(target.id))
        embed = helpers.util.get_profile_embed(target, details)

        await ctx.reply(embed = embed, mention_author = False)
        print("Command: profile")

    @commands.hybrid_command(name = "card", description = "gets a card from the current pool",
                             extras = {"syntax": "`bc card`", "args": None})
    @commands.dynamic_cooldown(lambda ctx: helpers.util.get_cooldown(ctx, constants.CooldownCommand.CARD), commands.BucketType.user)
    async def card(self, ctx):
        '''gets a card from the current pool'''
        if not await helpers.util.check_user(ctx.author.id):
            await ctx.reply("New user detected! Please use `start` command.")
        else:
            user = await helpers.util.get_user(ctx.author.id)
            if helpers.util.check_lock(user):
                return await ctx.reply("**You\'re account has been locked! Please contact any game admin.**")
            
            if helpers.util.roll_with_multi(user["fd_multi"]):
                card = random.choice(helpers.util.CACHE_CARDS_SIGNED) if helpers.util.CACHE_CARDS_SIGNED else None
                card_embed, card_image, caption = await helpers.util.generate_card_embed(card, user, True)
            else:
                card = random.choice(helpers.util.CACHE_CARDS_NORMAL) if helpers.util.CACHE_CARDS_NORMAL else None
                card_embed, card_image, caption = await helpers.util.generate_card_embed(card, user)
        
            await ctx.reply(content = f"{caption}", embed = card_embed, file = card_image, mention_author = False)
        print("Command: card")

    @commands.hybrid_command(name = "cards", description = "shows card collection of a user",
                             extras = {"syntax": "`bc cards [@user]`", "args": "- user: **optional**, user mention"})
    async def cards(self, ctx, user: discord.User = None):
        target = user or ctx.author

        if not await helpers.util.check_user(target.id):
            return await ctx.reply(f"<@!{target.id}> is not registered")
        
        if helpers.util.check_lock(target.id):
            return await ctx.reply("**You\'re account has been locked! Please contact any game admin.**")
            
        user_cards = helpers.util.get_user_cards(target.id)
        if not user_cards:
            return await ctx.reply(f"<@!{target.id}> has no cards")
        
        view = CardView(ctx.author, target, user_cards)
        embed = helpers.util.card_list_embed(target, user_cards, 0, view.total)

        await ctx.reply(embed = embed, view = view, mention_author = False)
        print("Command: cards")

    @commands.hybrid_command(name = "upgrade", description = "upgrade a card to a higher rating",
                             extras = {"syntax": "`bc upgrade <card_id>`", "args": "- card_id: **required**, ID of the card"})
    @commands.dynamic_cooldown(lambda ctx: helpers.util.get_cooldown(ctx, constants.CooldownCommand.UPGRADE), commands.BucketType.user)
    async def upgrade(self, ctx, card_id):
        '''upgrade a card to a higher rating'''
        if not await helpers.util.check_user(ctx.author.id):
            await ctx.reply("New user detected! Please use `start` command.")
        else:
            if helpers.util.check_lock(ctx.author.id):
                return await ctx.reply("**You\'re account has been locked! Please contact any game admin.**")
            
            view = ConfirmView(ctx.author)
            message = await ctx.reply(constants.CONFIRM_UPGRADE.format(card_id), view = view)
            await view.wait()

            if view.value is None:
                for child in view.children:
                    child.disabled = True
                    await message.edit(content = "Timed out!", view = None)
            elif view.value:
                card = helpers.util.CACHE_CARDS_UPGRADE.get((card_id, str(ctx.author.id)))
                if not card:
                    await message.edit(content = "Card not found. Please check the card ID again", view = None)
                else:
                    card_embed, card_image, caption = await helpers.util.upgrade_card(card)
                    if card_embed:
                        await message.reply(content = f"{caption}", embed = card_embed, file = card_image, mention_author = False)
                    else:
                        await message.edit(content = f"{caption}", view = None)
            else:
                await message.edit(content = "Upgrade cancelled", view = None)
        print("Command: upgrade")

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))