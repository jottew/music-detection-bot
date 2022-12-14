import discord

from io import StringIO
from discord.ext import commands


class Context(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def send(self, content: str = None, *args, **kwargs):
        if content is not None:
            if len(content) > 2000:
                buf = StringIO()
                buf.write(content)
                buf.seek(0)
                return await super().send(content="Message was over 2000 characters, so it has been turned into a text file", file=discord.File(buf, filename="message.txt"))

        return await super().send(content, *args, **kwargs)
