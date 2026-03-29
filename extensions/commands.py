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
    async def help(self, ctx, *, command: str = None):
        '''shows all commands'''
        if not command:
            embed = helpers.util.get_info(self.bot)
        else:
            embed = helpers.util.get_info(self.bot, command)

        if not embed:
            await ctx.reply(f"`{command} is not a command`")
        else:
            await ctx.reply(embed = embed, mention_author = False)

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

    @commands.hybrid_command(name = "profile", description = "shows the profile of a user",
                             extras = {"syntax": "`bc profile [@user]`", "args": "- user: **optional**, user mention"})
    async def profile(self, ctx, user: discord.User = None):
        '''shows the profile of a user'''
        target = user or ctx.author
        if not await helpers.util.check_user(target.id):
            return await ctx.reply(f"<@!{target.id}> is not registered")
        if not await helpers.util.check_user(ctx.author.id):
            pass
        else:
            if helpers.util.check_lock(ctx.author.id):
                return await ctx.reply("**You\'re account has been locked! Please contact any game admin.**")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(target.id))
        embed, file = await helpers.util.get_profile_embed(target, details)

        if file is not None:
            return await ctx.reply(embed = embed, file = file, mention_author = False)
        else:
            return await ctx.reply(embed = embed, mention_author = False)

    @commands.hybrid_command(name = "card", description = "gets a card from the current pool",
                             extras = {"syntax": "`bc card`", "args": None})
    @commands.dynamic_cooldown(lambda ctx: helpers.util.get_cooldown(ctx, constants.CooldownCommand.CARD), commands.BucketType.user)
    async def card(self, ctx):
        '''gets a card from the current pool'''
        if not await helpers.util.check_user(ctx.author.id):
            return await ctx.reply("New user detected! Please use `start` command.")
        else:
            user = await helpers.util.get_user(ctx.author.id)
            if helpers.util.check_lock(user["id"]):
                return await ctx.reply("**You\'re account has been locked! Please contact any game admin.**")
            
            if helpers.util.roll_with_multi(user["fd_multi"]):
                card = random.choice(helpers.util.CACHE_CARDS_SIGNED) if helpers.util.CACHE_CARDS_SIGNED else None
                card_embed, card_image, caption = await helpers.util.generate_card_embed(card, user, True)
            else:
                card = random.choice(helpers.util.CACHE_CARDS_NORMAL) if helpers.util.CACHE_CARDS_NORMAL else None
                card_embed, card_image, caption = await helpers.util.generate_card_embed(card, user)
        
            return await ctx.reply(content = f"{caption}", embed = card_embed, file = card_image, mention_author = False)

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

    @commands.hybrid_command(name = "upgrade", description = "upgrade a card to a higher rating",
                             extras = {"syntax": "`bc upgrade <card_id>`", "args": "- card_id: **required**, ID of the card"})
    @commands.dynamic_cooldown(lambda ctx: helpers.util.get_cooldown(ctx, constants.CooldownCommand.UPGRADE), commands.BucketType.user)
    async def upgrade(self, ctx, card_id: str):
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

    @commands.hybrid_group(name = "set", description = "sets values to multiple things", with_app_command = True,
                           extras = {"syntax": "`bc set <field> <value>`", "args": "- field: **required**, field to set value\n- value: **required**, value to set"})
    async def set(self, ctx):
        '''set value to a field'''
        if ctx.invoked_subcommand is None:
            perms = helpers.util.get_command_perms(ctx)
            await ctx.reply(f"Available fields: `bio`, `favorite`{perms}")

    @set.command(name = "bio", description = "sets bio of a user",
                 extras = {"syntax": "`bc set bio <value>`", "args": "- value: **required**, bio content"})
    async def bio(self, ctx, *, value: str):
        '''sets bio of a user'''
        if not await helpers.util.check_user(ctx.author.id):
            return await ctx.reply("New user detected! Please use `start` command.")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(ctx.author.id))
        if not await helpers.util.update_user(details, "fd_desc", value):
            return await ctx.reply("An error occured while trying to update user")
        
        embed, file = await helpers.util.get_profile_embed(ctx.author, details)
        if file is not None:
            return await ctx.reply(content = "Bio set successfully", embed = embed, file = file)
        else:
            return await ctx.reply(content = "Bio set successfully", embed = embed)

    @set.command(name = "favorite", description = "sets a card image for your profile",
                 extras = {"syntax": "`bc set favorite <card ID>`", "args": "- card ID: **required**, card ID on your collection"})
    async def favorite(self, ctx, card: str):
        '''sets a card image for your profile'''
        if not await helpers.util.check_user(ctx.author.id):
            return await ctx.reply("New user detected! Please use `start` command.")
        
        if (card, str(ctx.author.id)) not in helpers.util.CACHE_CARDS_UPGRADE:
            return await ctx.reply("You don\'t own this card")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(ctx.author.id))
        if not await helpers.util.update_user(details, "fd_fav", card):
            return await ctx.reply("An error occured while trying to update user")
        
        embed, file = await helpers.util.get_profile_embed(ctx.author, details)
        return await ctx.reply(content = "Favorite card set successfully", embed = embed, file = file)

    @set.command(name = "bloom", description = "adds bloom to a user", hidden = True,
                 extras = {"syntax": "`bc set bloom <user ID> <amount>`", "args": "- user ID: **required**, discord user ID\n- amount: **required**, amount of blooms to be added"})
    async def bloom(self, ctx, user, amount: int):
        '''adds blooms to a user'''
        if not helpers.util.check_perms(ctx):
            return await ctx.reply("`Not a command`")
        
        if not await helpers.util.check_user(user):
            return await ctx.reply(f"User is not registered")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(user))
        total = details["fd_curr1"] + amount
        if not await helpers.util.update_user(details, "fd_curr1", total):
            return await ctx.reply("An error occured while trying to update user")
        else:
            return await ctx.reply(f"Added {amount} {constants.BLOOM} to user {user}", mention_author = False)

    @set.command(name = "bloomcension", description = "adds bloomcension to a user", hidden = True,
                 extras = {"syntax": "`bc set bloomcension <user ID> <amount>`", "args": "- user ID: **required**, discord user ID\n- amount: **required**, amount of bloomscensions to be added"})
    async def bloomcension(self, ctx, user, amount: int):
        '''adds bloomscensions to a user'''
        if not helpers.util.check_perms(ctx):
            return await ctx.reply("`Not a command`")
        
        if not await helpers.util.check_user(user):
            return await ctx.reply(f"User is not registered")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(user))
        total = details["fd_curr2"] + amount
        if not await helpers.util.update_user(details, "fd_curr2", total):
            return await ctx.reply("An error occured while trying to update user")
        else:
            return await ctx.reply(f"Added {amount} {constants.BLOOMCENSION} to user {user}", mention_author = False)

    @set.command(name = "bloomspin", description = "adds bloomspin to a user", hidden = True,
                 extras = {"syntax": "`bc set bloomspin <user ID> <amount>`", "args": "- user ID: **required**, discord user ID\n- amount: **required**, amount of bloomsspins to be added"})
    async def bloomspin(self, ctx, user, amount: int):
        '''adds bloomspins to a user'''
        if not helpers.util.check_perms(ctx):
            return await ctx.reply("`Not a command`")
        
        if not await helpers.util.check_user(user):
            return await ctx.reply(f"User is not registered")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(user))
        total = details["fd_curr3"] + amount
        if not await helpers.util.update_user(details, "fd_curr3", total):
            return await ctx.reply("An error occured while trying to update user")
        else:
            return await ctx.reply(f"Added {amount} {constants.BLOOMSPIN} to user {user}", mention_author = False)

    @set.command(name = "lock", description = "locks a user account from the bot", hidden = True,
                 extras = {"syntax": "`bc set lock <user ID> <boolean>`", "args": "- user ID: **required**, discord user ID\n- boolean: **required**, True or False"})
    async def lock(self, ctx, user, value: bool):
        '''locks a user account from the bot'''
        if not helpers.util.check_perms(ctx):
            return await ctx.reply("`Not a command`")
        
        if not await helpers.util.check_user(user):
            return await ctx.reply(f"User is not registered")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(user))
        if not await helpers.util.update_user(details, "fd_lock", value):
            return await ctx.reply("An error occured while trying to update user")
        else:
            return await ctx.reply(f"User {user} has been locked out of the bot!", mention_author = False)
        
    @set.command(name = "multi", description = "sets chance multiplier for a user", hidden = True,
                 extras = {"syntax": "`bc set multi <user ID> <multiplier>`", "args": "- user ID: **required**, discord user ID\n- multiplier: **required**, float, chances in rate form (`%` not included)"})
    async def multi(self, ctx, user, value: float):
        '''sets chance multiplier for a user'''
        if not helpers.util.check_perms(ctx):
            return await ctx.reply("`Not a command`")
        
        if not await helpers.util.check_user(user):
            return await ctx.reply(f"User is not registered")
        
        details = helpers.util.CACHE_USERS_DICT.get(str(user))
        multiplier = helpers.util.parse_multi(value)
        if multiplier is not None:
            if not await helpers.util.update_user(details, "fd_multi", multiplier):
                return await ctx.reply("An error occured while trying to update user")
            else:
                return await ctx.reply(f"User {user} multiplier has been set", mention_author = False)
        else:
            return await ctx.reply("Make sure the value is within 0 to 100")

async def setup(bot):
    await bot.add_cog(CommandsCog(bot))