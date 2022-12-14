import platform
import aiofiles
import discord
import asyncio
import utils
import json
import sys
import os

from core.bot import Bot

from discord.ext import commands

class Detection(commands.Cog):
    def __init__(self, bot):
        super().__init__()
        self.bot: Bot = bot

    @commands.command()
    async def detect(self, ctx, attachment = None):
        attachment: discord.Attachment = await utils.FileConverter().convert(ctx, attachment)

        if sys.platform != "linux":
            return await ctx.send(f"Bot is hosted on unsupported device ({platform.system().title()})")

        types = {
            "video/quicktime": "mov",
            "video/mp4": "mp4",
            "audio/mpeg": "mp3",
            "audio/x-wav": "wav",
            "audio/ogg": "ogg"
        }

        req = await self.bot.session.get(attachment.url)
        headers = req.headers

        content_type = headers.get("Content-Type", None)

        try:
            _format = types[content_type]
        except KeyError:
            _list = [v for k,v in types.items()]
            msg = utils.format_list(list(_list))
            return await ctx.send(f"Unsupported file format, please use {msg}")

        msg = await ctx.send("Now processing request...")
        
        async with aiofiles.tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, f"song.{_format}")
            await attachment.save(path)

            cmd = "" if sys.platform == "linux" else "wsl\n"
            cmd += f"songrec audio-file-to-recognized-song {path}"
                
            try:
                proc = await asyncio.wait_for(
                    asyncio.create_subprocess_shell(
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                    ) , timeout=60
                )
            except asyncio.TimeoutError:
                return await ctx.send(f"Recognition took over 60 seconds and has therefore been cancelled")
                
            prv = await proc.communicate()
            r = prv[0].decode()
            r2= prv[1].decode()
            if len(r) == 0:
                if len(r2) == 0:
                    return await ctx.send("Empty result received")
                return await ctx.send(f"stdout is empty, but stderr returned **{r2}**")

        try:
            res = json.loads(r).get("track", {})
        except Exception:
            return await ctx.send(f"Corrupted result received\n**Result**: {await self.bot.myst.post(r)}")
        
        if res == {}:
            return await ctx.send("Could not recognise song")

        title = res.get("title")
        artist = res.get("subtitle")
        url = res.get("url")
        image = res.get("share", {}).get("image", None)
        genres = res.get("genres", {})
        genres_txt = "".join(f"⠀⠀{k.title()}: {v}" for k, v in genres.items())
        
        em = discord.Embed(title=title, description=f"**Title**: {title}\n**Artist**: {artist}\n**Genres** [{len(genres)}]:\n{'N/A' if len(genres) == 0 else genres_txt}", url=url)
        if image is not None:
            em.set_thumbnail(url=image)
        await msg.edit(embed=em, content=None)

async def setup(bot):
    await bot.add_cog(Detection(bot))
    