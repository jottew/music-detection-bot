import os

from core.bot import bot
from dotenv import load_dotenv

load_dotenv()
bot.run(os.getenv("TOKEN"))
