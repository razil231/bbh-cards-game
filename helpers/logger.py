import logging
import os
import discord

MAX_SIZE = 8 * 1024 * 1024

class DiscordFileLogger(logging.Handler):
    def __init__(self, bot, channel_id, log_file = "cardBot.log"):
        super().__init__()
        self.bot = bot
        self.channel_id = channel_id
        self.log_file = log_file
        self._sending = False

    async def send_log(self):
        if self._sending:
            return
        
        self._sending = True
        try:
            channel = self.bot.get_channel(self.channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(self.channel_id)

            if channel and os.path.exists(self.log_file):
                await channel.send(file = discord.File(self.log_file))
                os.remove(self.log_file)
        except Exception as e:
            print(f"Failed to send log: {e}")
        finally:
            self._sending = False

    def emit(self, record):
        try:
            log_entry = self.format(record)

            with open(self.log_file, "a", encoding = "utf-8") as f:
                f.write(log_entry + "\n")

            if (os.path.exists(self.log_file) and os.path.getsize(self.log_file) >= MAX_SIZE and not self._sending):
                self.bot.loop.create_task(self.send_log())
        except Exception as e:
            print(f"Logging error: {e}")


def setup_logger(bot, channel):
    logger = logging.getLogger("bbh_cards")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = DiscordFileLogger(bot, channel)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger