import platform
import tempfile
import discord
import asyncio
import utils
import json
import sys
import os
import re

from core.bot import Bot
from io import StringIO

from discord.ext import commands


class Detection(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: Bot = bot

        self.TIKTOK_REGEX = re.compile(
            r"https?:\/\/www\.tiktok\.com\/(?:@.+)\/video\/(?P<id>\d+)/?"
        )
        self.TIKTOK_MOBILE_REGEX = re.compile(
            r"https?:\/\/vm\.tiktok\.com\/(?P<id>.+)/?"
        )
        self.YOUTUBE_REGEX = re.compile(
            r"^(https?\:\/\/)?((www\.)?youtube\.com|youtu\.?be)\/.+$"
        )

    @commands.command()
    async def detect(self, ctx, attachment=None):
        msg = None
        _format = None

        if (
            attachment is not None
            and self.TIKTOK_REGEX.match(attachment or "")
            or self.TIKTOK_MOBILE_REGEX.match(attachment or "")
            or self.YOUTUBE_REGEX.match(attachment or "")
        ):
            d = tempfile.TemporaryDirectory()
            path = os.path.join(d.name, "video.mp3")
            cmd = f'yt-dlp --audio-format mp3 --extract-audio --output "{path}" {attachment}'

            if self.YOUTUBE_REGEX.match(attachment):
                msg = await ctx.reply("Now downloading YouTube video...")
            else:
                msg = await ctx.reply("Now downloading TikTok video...")

            try:
                proc = await asyncio.wait_for(
                    asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    ),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                return await ctx.send(
                    f"Download took over 60 seconds and has therefore been cancelled"
                )

            prv = await proc.communicate()
            r = prv[0].decode()
            r2 = prv[1].decode()
            if len(r) == 0:
                if len(r2) == 0:
                    return await ctx.send("Empty result received")
                return await ctx.send(f"stdout is empty, but stderr returned **{r2}**")

            if not os.path.isfile(path):
                buf = StringIO()
                buf.write(f"stdout:\n\n{r}\n\nstderr:\n\n{r2}")
                buf.seek(0)
                return await ctx.send(file=discord.File(buf, filename="error.txt"))

            attachment: discord.Attachment = utils.FileObject(path)
        else:
            attachment: discord.Attachment = await utils.FileConverter().convert(
                ctx, attachment
            )

            types = {
                "video/quicktime": "mov",
                "video/mp4": "mp4",
                "audio/mpeg": "mp3",
                "audio/x-wav": "wav",
                "audio/ogg": "ogg",
            }

            req = await self.bot.session.get(attachment.url)
            headers = req.headers

            content_type = headers.get("Content-Type", None)

            try:
                _format = types[content_type]
            except KeyError:
                _list = [v for k, v in types.items()]
                msg = utils.format_list(list(_list))
                return await ctx.send(f"Unsupported file format, please use {msg}")

            if sys.platform != "linux":
                return await ctx.send(
                    f"Bot is hosted on unsupported device ({platform.system().title()})"
                )

        if msg is None:
            msg = await ctx.send(content="Now processing request...")
        else:
            await msg.edit(content="Now processing request...")

        with tempfile.TemporaryDirectory() as nd:
            name = nd if "d" not in locals() else d.name
            path = os.path.join(name, f"song.{_format or 'mp3'}")
            await attachment.save(path)

            cmd = "" if sys.platform == "linux" else "wsl\n"
            cmd += f"songrec audio-file-to-recognized-song {path}"

            try:
                proc = await asyncio.wait_for(
                    asyncio.create_subprocess_shell(
                        cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    ),
                    timeout=60,
                )
            except asyncio.TimeoutError:
                return await ctx.send(
                    f"Recognition took over 60 seconds and has therefore been cancelled"
                )

            prv = await proc.communicate()
            r = prv[0].decode()
            r2 = prv[1].decode()
            if len(r) == 0:
                if len(r2) == 0:
                    return await ctx.send("Empty result received")
                return await ctx.send(f"stdout is empty, but stderr returned **{r2}**")

            if "d" in locals():
                d.cleanup()

        try:
            res = json.loads(r).get("track", {})
        except Exception:
            return await ctx.send(
                f"Corrupted result received\n**Result**: {await self.bot.myst.post(r)}"
            )

        if res == {}:
            return await ctx.send("Could not recognise song")

        title = res.get("title")
        artist = res.get("subtitle")
        url = res.get("url")
        image = res.get("share", {}).get("image", None)
        genres = res.get("genres", {})
        genres_txt = "".join(f"⠀⠀{k.title()}: {v}" for k, v in genres.items())

        em = discord.Embed(
            title=title,
            description=f"**Title**: {title}\n**Artist**: {artist}\n**Genres** [{len(genres)}]:\n{'N/A' if len(genres) == 0 else genres_txt}",
            url=url,
        )
        if image is not None:
            em.set_thumbnail(url=image)
        await msg.edit(embed=em, content=None)


async def setup(bot):
    await bot.add_cog(Detection(bot))
