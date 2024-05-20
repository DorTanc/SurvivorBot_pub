import discord
from discord.ext import commands
import csv
from discord.ui import Select, View

class TribeManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add_tribe')
    @commands.has_role('Host')
    async def add_tribe(self, ctx, tribe_name: str):
        guild = ctx.guild
        role = discord.utils.get(guild.roles, name=tribe_name)
        if role:
            await ctx.send(f"The tribe '{tribe_name}' already exists as a role.")
            return

        try:
            # Add the tribe to tribes.csv
            with open('tribes.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['tribe', tribe_name])

            # Create the tribe role in Discord
            await guild.create_role(name=tribe_name, mentionable=False)
            await ctx.send(f"The tribe '{tribe_name}' has been added and role created.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name='check_vote_time')
    async def check_vote_time(self, ctx):
        try:
            with open('tribes.csv', 'r') as csvfile:
                tribes = list(csv.reader(csvfile))
            if tribes and tribes[0][0] == 'voting':
                tribe_name = tribes[0][1]
                if tribe_name == 'none':
                    await ctx.send("It is not time to vote for any tribe.")
                else:
                    await ctx.send(f"It is time to vote for the tribe: {tribe_name}.")
            else:
                await ctx.send("Vote time information is not available.")
        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name='vote_time')
    @commands.has_role('Host')
    async def vote_time(self, ctx):
        try:
            with open('tribes.csv', 'r') as csvfile:
                tribes = [row[1] for row in csv.reader(csvfile) if row[1] != 'none']
            if not tribes:
                await ctx.send("No tribes found in tribes.csv.")
                return
            view = TribeSelectView(tribes)
            await ctx.send("Select a tribe to vote:", view=view)
        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

class TribeSelectMenu(Select):
    def __init__(self, tribes):
        options = [discord.SelectOption(label=tribe) for tribe in tribes]
        super().__init__(placeholder='Select a tribe to vote...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_tribe = self.values[0]
        with open('tribes.csv', 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['voting', selected_tribe])
        await interaction.response.send_message(f"The tribe {selected_tribe} can now vote.", ephemeral=True)

class TribeSelectView(View):
    def __init__(self, tribes):
        super().__init__()
        self.add_item(TribeSelectMenu(tribes))

async def setup(bot):
    await bot.add_cog(TribeManagement(bot))

