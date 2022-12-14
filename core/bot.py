import traceback
import discord
import logging
import aiohttp
import os


from datetime import datetime
from discord.ext import commands


logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)


class Bot(commands.AutoShardedBot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.uptime = datetime.utcnow()

        self.owner_id = 797044260196319282
        self.owner_ids = (797044260196319282,)

        self.data = None
        self.acknowledgments = None
        self.session = None

    async def is_owner(self, user: discord.User):
        return user.id == self.owner_id or user.id in self.owner_ids

    async def on_connect(self):
        print("Connected to discord gateway")

    async def setup_hook(self) -> None:
        session = aiohttp.ClientSession()
        self.session = session

        await self.load_extension("jishaku")

        for i in os.listdir("cogs"):
            if not i.endswith(".py"):
                continue

            cog = f"cogs.{i[:-3]}"
            try:
                await self.load_extension(cog)
            except Exception as exc:
                print(exc)

    async def on_message(self, message):
        if message.author.bot:
            return

        await self.process_commands(message)

    async def on_ready(self):
        print(
            f"Logged in as {self.user} ({len(self.guilds)} guilds) ({round(self.latency*1000)}ms)"
        )
        print(
            "------------------------------------------------------------------------------------"
        )

    async def close(self):
        try: await self.session.close()
        except Exception as exc: traceback.print_exception(
            type(exc),
            exc,
            exc.__traceback__
        )

        await super().close()

    async def on_command_error(self, ctx: commands.Context, exc: Exception):
        error = traceback.format_exception(
            type(exc),
            exc,
            exc.__traceback__
        )

        final_error = "\n".join(error)
        wrap = "```"

        await ctx.reply(wrap+final_error+wrap)

async def get_prefix(bot_: Bot, message):
    prefixes = ["m!"]

    result = commands.when_mentioned_or(*prefixes)(bot_, message)
    return result


bot = Bot(
    command_prefix=get_prefix,
    allowed_mentions=discord.AllowedMentions.none(),
    intents=discord.Intents.all(),
    strip_after_prefix=True
)
