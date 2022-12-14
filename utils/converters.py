import inspect
import discord
import aiohttp
import typing
import time
import os
import re

from io import BufferedIOBase, BytesIO
from discord.ext import commands

URL_REGEX = re.compile(
    r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
)


class URLObject:
    def __init__(self, url: str):
        if not URL_REGEX.match(url):
            raise TypeError(f"Invalid url provided")
        self.url = url
        self.name = url.split("/")[-1]

    async def read(self, *, session=None) -> bytes:
        """Reads this asset."""
        _session = session or aiohttp.ClientSession()
        try:
            async with _session.get(self.url) as resp:
                if resp.status == 200:
                    return await resp.read()
                elif resp.status == 404:
                    raise discord.NotFound(resp, "asset not found")
                elif resp.status == 403:
                    raise discord.Forbidden(resp, "cannot retrieve asset")
                else:
                    raise discord.HTTPException(resp, "failed to get asset")
        finally:
            if not session:
                await _session.close()

    async def save(
        self, fp: BufferedIOBase | os.PathLike[typing.Any], *, seek_begin: bool = True
    ) -> int:
        """Saves to an object or buffer."""
        data = await self.read()
        if isinstance(fp, BufferedIOBase):
            written = fp.write(data)
            if seek_begin:
                fp.seek(0)
            return written
        else:
            with open(fp, "wb") as f:
                return f.write(data)

    @property
    def spoiler(self):
        """Wether the file is a spoiler"""
        return self.name.startswith("SPOILER_")

    @spoiler.setter
    def spoiler(self, value: bool):
        if value != self.spoiler:
            if value is True:
                self.name = f"SPOILER_{self.name}"
            else:
                self.name = self.name.split("_", maxsplit=1)[1]

    async def to_file(self, *, session: aiohttp.ClientSession = None):
        return discord.File(
            BytesIO(await self.read(session=session)), self.name, spoiler=False
        )


class FileObject:
    def __init__(self, path: os.PathLike):
        if not os.path.isfile(path):
            raise TypeError(f"Invalid path provided")
        self.path = path
        self.name = path.split("/")[-1]

    async def read(self) -> bytes:
        """Reads this asset."""
        with open(self.path, "rb") as f:
            return f.read()

    async def save(
        self, fp: BufferedIOBase | os.PathLike[typing.Any], *, seek_begin: bool = True
    ) -> int:
        """Saves to an object or buffer."""
        data = await self.read()
        if isinstance(fp, BufferedIOBase):
            written = fp.write(data)
            if seek_begin:
                fp.seek(0)
            return written
        else:
            with open(fp, "wb") as f:
                return f.write(data)

    @property
    def spoiler(self):
        """Wether the file is a spoiler"""
        return self.name.startswith("SPOILER_")

    @spoiler.setter
    def spoiler(self, value: bool):
        if value != self.spoiler:
            if value is True:
                self.name = f"SPOILER_{self.name}"
            else:
                self.name = self.name.split("_", maxsplit=1)[1]

    async def to_file(self):
        return discord.File(BytesIO(await self.read()), self.name, spoiler=False)


class FileConverter(commands.Converter):
    async def convert(
        self, ctx: commands.Context, file: str = None
    ) -> discord.Attachment:
        if file is None:
            if ctx.message.attachments:
                attachment = ctx.message.attachments[0]
            elif ctx.message.reference:
                if ctx.message.reference.resolved.attachments:
                    attachment = ctx.message.reference.resolved.attachments[0]
                else:
                    raise commands.MissingRequiredArgument(
                        inspect.Parameter("file", inspect.Parameter.KEYWORD_ONLY)
                    )
            else:
                raise commands.MissingRequiredArgument(
                    inspect.Parameter("file", inspect.Parameter.KEYWORD_ONLY)
                )
        else:
            attachment = URLObject(file)

        return attachment
