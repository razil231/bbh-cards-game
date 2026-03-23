from discord.ext import commands
from db import get_pool

class SetupDB(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def setupdb(self, ctx):
        pool = await get_pool()

        async with pool.acquire() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(
                    "CREATE TABLE IF NOT EXISTS cards ("
                        "id INT AUTO_INCREMENT PRIMARY KEY, "
                        "fd_type VARCHAR(255) NOT NULL, "
                        "fd_bundle VARCHAR(255) NOT NULL, "
                        "fd_name VARCHAR(255) NOT NULL, "
                        "fd_member VARCHAR(255) NOT NULL, "
                        "fd_image VARCHAR(255) NOT NULL, "
                        "fd_desc TEXT"
                    ")"
                )

        await ctx.reply("DB connected")

async def setup(bot):
    await bot.add_cog(SetupDB(bot))