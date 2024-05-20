import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import contextlib

# Load the bot token from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Create initial files if they don't exist
files = ["players.csv", "tribes.csv", "vote_time", "idols.csv", "token", "playernum"]
initial_data = {
    "tribes.csv": "voting,none\n",
    "vote_time": "0",
    "playernum": "0"
}

for file in files:
    if not os.path.exists(file):
        with open(file, 'w') as f:
            if file in initial_data:
                f.write(initial_data[file])

# Create the bot and ensure the 'host' role exists
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def on_ready():
    guild = bot.guilds[0]  # Assumes bot is only in one guild
    if not discord.utils.get(guild.roles, name='Host'):
        await guild.create_role(name='Host')
    await bot.close()


async def main():
    async with bot:
        await bot.start(TOKEN)


async def cleanup(loop):
    tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
    for task in tasks:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    await loop.shutdown_asyncgens()
    session = bot.http._HTTPClient__session
    if session:
        await session.close()


# Run the bot
if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        loop.run_until_complete(cleanup(loop))
        loop.close()
