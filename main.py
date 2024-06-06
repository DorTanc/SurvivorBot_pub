import os
import discord
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv
import logging
import asyncio

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = int(os.getenv('DISCORD_GUILD_ID'))  # Add your guild ID to the .env file
DATABASE_PLAYERS_CHANNEL_ID = int(os.getenv('DISCORD_DATABASE_PLAYERS_CHANNEL_ID'))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True  # Ensure message_content intent is enabled
intents.messages = True
intents.guilds = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='/', intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        # Sync commands only for the specific guild during testing
        self.tree.copy_global_to(guild=guild)
        # await self.tree.sync(guild=guild)
        # Comment out the global sync if you don't want to register commands globally
        # await self.tree.sync()

bot = MyBot()

@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    await bot.change_presence(activity=discord.Game(name="הישרדות עונה 6"))

@bot.command()
@commands.has_role('Host')
async def add_command(ctx, name: str, description: str):
    async def new_command(interaction: discord.Interaction):
        await interaction.response.send_message(f'You used the new command {name}!')

    new_cmd = app_commands.Command(name=name, description=description, callback=new_command)
    bot.tree.add_command(new_cmd)
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))

    await ctx.send(f'Command /{name} added and synced!')

@bot.command()
@commands.has_role('Host')
async def sync_commands(ctx):
    guild = discord.Object(id=GUILD_ID)
    await bot.tree.sync(guild=guild)
    await bot.tree.sync()  # Sync globally
    await ctx.send("Commands have been resynced!")

@bot.command()
@commands.has_role('Host')
async def clear_commands(ctx):
    guild = discord.Object(id=GUILD_ID)
    bot.tree.clear_commands(guild=guild)
    await bot.tree.sync(guild=guild)
    await bot.tree.sync()  # Sync globally
    await ctx.send("Commands have been cleared and resynced!")

async def main():
    async with bot:
        await bot.load_extension('commands')
        await bot.start(TOKEN)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
