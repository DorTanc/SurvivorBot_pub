import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Ensure message_content intent is enabled
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    logger.info(f'{bot.user} has connected to Discord!')

async def main():
    async with bot:
        await bot.load_extension('player_management')
        await bot.load_extension('tribe_management')
        await bot.start(TOKEN)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
