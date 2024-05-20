import discord
from discord.ext import commands
import csv
import asyncio
from discord.ui import Select, View


class PlayerManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='players')
    async def players(self, ctx):
        await ctx.send("Processing !players command...")
        await self.show_players(ctx)

    @commands.command(name='voted')
    async def voted(self, ctx):
        await self.show_voted(ctx)

    @commands.command(name='not_voted')
    async def not_voted(self, ctx):
        await self.show_not_voted(ctx)

    @commands.command(name='add_player')
    @commands.has_role('Host')
    async def add_player(self, ctx, player_name: str):
        # Read the tribes from tribes.csv
        try:
            with open('tribes.csv', 'r') as csvfile:
                reader = csv.reader(csvfile)
                tribes = [row[1] for row in reader if row[0] == 'tribe']

            if not tribes:
                await ctx.send("No tribes available. Please add tribes first.")
                return
        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
            return
        except Exception as e:
            await ctx.send(f"An error occurred while reading tribes: {str(e)}")
            return

        # Create a selection menu for tribes
        view = TribeSelectView(self.bot, ctx, player_name, tribes)
        await ctx.send("Select a tribe for the player:", view=view)

    @commands.command(name='vote')
    async def vote(self, ctx, player_name: str = None):
        if player_name is None:
            await ctx.send("Usage: `!vote <player_name>`")
            return

        voter = ctx.author
        voter_role = None
        for role in voter.roles:
            if role.name != "@everyone":
                voter_role = role
                break

        if voter_role is None:
            await ctx.send("You do not have a tribe role.")
            return

        try:
            player_tribe = None
            with open('players.csv', 'r') as csvfile:
                players = csv.reader(csvfile)
                for row in players:
                    if row[1] == player_name:
                        player_tribe = row[2]
                        break

            if player_tribe:
                if voter_role.name != player_tribe:
                    await ctx.send(f"You can only vote for players in your tribe ({voter_role.name}).")
                    return

                with open('tribes.csv', 'r') as csvfile:
                    tribes = list(csv.reader(csvfile))
                if tribes and tribes[0][0] == 'voting' and tribes[0][1] == voter_role.name:
                    await ctx.send(f"Player {player_name} has received your vote for the tribe: {voter_role.name}.")
                    # Here you would add logic to record the vote
                else:
                    await ctx.send(f"It is not vote time for the tribe: {voter_role.name}.")
            else:
                await ctx.send("Player not found.")
        except FileNotFoundError:
            await ctx.send("The file 'players.csv' or 'tribes.csv' was not found. Please ensure they exist.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def show_players(self, ctx):
        # Implement your show_players logic here
        pass

    async def show_voted(self, ctx):
        # Implement your show_voted logic here
        pass

    async def show_not_voted(self, ctx):
        # Implement your show_not_voted logic here
        pass


class TribeSelectMenu(Select):
    def __init__(self, bot, ctx, player_name, tribes):
        self.bot = bot
        self.ctx = ctx
        self.player_name = player_name
        options = [discord.SelectOption(label=tribe) for tribe in tribes]
        super().__init__(placeholder='Select a tribe...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_tribe = self.values[0]
        await self.add_player_to_tribe(self.ctx, self.player_name, selected_tribe)
        await interaction.response.send_message(
            f"Player {self.player_name} has been added to the tribe {selected_tribe}.", ephemeral=True)

    async def add_player_to_tribe(self, ctx, player_name, tribe_name):
        guild = ctx.guild
        tribe_role = discord.utils.get(guild.roles, name=tribe_name)
        if not tribe_role:
            await ctx.send(f"The tribe '{tribe_name}' does not exist.")
            return

        try:
            # Find the member by name
            member = guild.get_member_named(player_name)
            if member is None:
                await ctx.send(f"Member '{player_name}' not found.")
                return

            player_id = str(member.id)

            # Add the player to players.csv
            with open('players.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([player_id, player_name, tribe_name])

            # Create the player role in Discord
            player_role = await guild.create_role(name=player_name, mentionable=False)

            await member.add_roles(tribe_role, player_role)

            await ctx.send(f"Player '{player_name}' has been added to the tribe '{tribe_name}' and role created.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class TribeSelectView(View):
    def __init__(self, bot, ctx, player_name, tribes):
        super().__init__()
        self.add_item(TribeSelectMenu(bot, ctx, player_name, tribes))


async def setup(bot):
    await bot.add_cog(PlayerManagement(bot))
