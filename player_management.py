import discord
from discord.ext import commands
import csv
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
    async def vote(self, ctx):
        voter = ctx.author
        voter_role = None
        player_tribes = []

        try:
            # Load player data
            with open('players.csv', 'r') as csvfile:
                players = csv.reader(csvfile)
                player_tribes = list(players)

            # Identify the voter's tribe role
            for role in voter.roles:
                if role.name in [row[2] for row in player_tribes if len(row) >= 3 and row[0] != '<player_id>']:
                    voter_role = role
                    break

            if voter_role is None:
                await ctx.send("You do not have a tribe role.")
                return

            # Check if the voter's tribe is allowed to vote
            with open('tribes.csv', 'r') as csvfile:
                tribes = list(csv.reader(csvfile))
                voting_tribes_row = [row for row in tribes if len(row) >= 2 and row[0] == 'voting']
                if voting_tribes_row:
                    voting_tribes = voting_tribes_row[0][1].split(', ')
                else:
                    voting_tribes = []

            if voter_role.name not in voting_tribes:
                await ctx.send(f"It is not vote time for your tribe ({voter_role.name}).")
                return

            # Create a selection menu for players in the voter's tribe
            tribe_players = [row[1] for row in player_tribes if
                             len(row) >= 3 and row[2] == voter_role.name and row[1] != voter.display_name]
            if not tribe_players:
                await ctx.send(f"There are no other players in your tribe ({voter_role.name}) to vote for.")
                return

            view = VoteSelectView(self.bot, ctx, tribe_players, voter_role.name)
            await ctx.send("Select a player to vote for:", view=view)

        except FileNotFoundError:
            await ctx.send("The file 'players.csv' or 'tribes.csv' was not found. Please ensure they exist.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name='change_tribe')
    @commands.has_role('Host')
    async def change_tribe(self, ctx):
        try:
            # Load player data
            with open('players.csv', 'r') as csvfile:
                players = list(csv.reader(csvfile))

            player_names = [row[1] for row in players if len(row) >= 3 and row[0] != '<player_id>']
            if not player_names:
                await ctx.send("No players found.")
                return

            view = PlayerSelectView(self.bot, ctx, player_names)
            await ctx.send("Select a player to change their tribe:", view=view)

        except FileNotFoundError:
            await ctx.send("The file 'players.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name='vote_time')
    @commands.has_role('Host')
    async def vote_time(self, ctx):
        try:
            # Load tribes
            with open('tribes.csv', 'r') as csvfile:
                tribes = list(csv.reader(csvfile))

            tribe_names = [row[1] for row in tribes if len(row) >= 2 and row[0] == 'tribe']
            if not tribe_names:
                await ctx.send("No tribes found.")
                return

            view = VotingTribesSelectView(self.bot, ctx, tribe_names)
            await ctx.send("Select tribes that can vote:", view=view)

        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name='end_vote')
    @commands.has_role('Host')
    async def end_vote(self, ctx):
        try:
            # Load tribes data
            with open('tribes.csv', 'r') as csvfile:
                tribes_data = list(csv.reader(csvfile))

            voting_tribes_row = [row for row in tribes_data if len(row) >= 2 and row[0] == 'voting']
            if voting_tribes_row:
                voting_tribes = voting_tribes_row[0][1].split(', ')
            else:
                voting_tribes = []

            if not voting_tribes:
                await ctx.send("No tribes are currently allowed to vote.")
                return

            view = EndVotingTribesSelectView(self.bot, ctx, voting_tribes)
            await ctx.send("Select tribes that should stop voting:", view=view)

        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command(name='create_voice_channel_menu')
    async def create_voice_channel_menu(self, ctx, *, channel_name=None):
        # Load mentionable roles from the server
        guild = ctx.guild
        roles = [role for role in guild.roles if role != guild.default_role and role.mentionable]

        if not roles:
            await ctx.send("No mentionable roles found.")
            return

        view = VoiceChannelRoleSelectView(self.bot, ctx, roles, channel_name)
        await ctx.send("Select roles for the voice channel:", view=view)

    @commands.command(name='alliance')
    async def create_alliance(self, ctx, *, alliance_name=None):
        guild = ctx.guild
        player_role = None

        # Read player names from players.csv
        player_names = []
        player_tribes = {}
        try:
            with open('players.csv', 'r') as csvfile:
                reader = csv.reader(csvfile)
                player_data = [row for row in reader if row[0] != '<player_id>']
                player_names = [row[1] for row in player_data]
                player_tribes = {row[1]: row[2] for row in player_data}
        except FileNotFoundError:
            await ctx.send("The file 'players.csv' was not found. Please ensure it exists.")
            return
        except Exception as e:
            await ctx.send(f"An error occurred while reading players: {str(e)}")
            return

        for role in ctx.author.roles:
            if role.name in player_names:
                player_role = role
                break

        roles = [role for role in guild.roles if role != guild.default_role and role.mentionable and role != player_role and role.name in player_names]

        if not roles:
            await ctx.send("No mentionable player roles found.")
            return

        view = AllianceRoleSelectView(self.bot, ctx, roles, alliance_name, player_role, player_tribes)
        await ctx.send("Select roles for the alliance:", view=view)

    @commands.command(name='expel')
    @commands.has_role('Host')
    async def expel(self, ctx):
        try:
            # Load player data
            with open('players.csv', 'r') as csvfile:
                players = list(csv.reader(csvfile))

            player_names = [row[1] for row in players if len(row) >= 3 and row[0] != '<player_id>']
            if not player_names:
                await ctx.send("No players found.")
                return

            view = ExpelPlayerSelectView(self.bot, ctx, player_names)
            await ctx.send("Select a player to expel:", view=view)

        except FileNotFoundError:
            await ctx.send("The file 'players.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def show_players(self, ctx):
        try:
            with open('players.csv', 'r') as csvfile:
                players = list(csv.reader(csvfile))
            if not players:
                await ctx.send("No players found.")
                return

            response = "Players and their tribes:\n"
            for idx, player in enumerate(players, 1):
                response += f"Player {idx}: {player[1]} (ID: {player[0]}) - Tribe: {player[2]}\n"
            await ctx.send(response)
        except FileNotFoundError:
            await ctx.send("The file 'players.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    async def show_voted(self, ctx):
        # Implement your show_voted logic here
        pass

    async def show_not_voted(self, ctx):
        # Implement your show_not_voted logic here
        pass

    @commands.command(name='commands')
    async def show_commands(self, ctx):
        commands_description = """
פקודות בוט:

1. !players - מציג רשימה של כל השחקנים והשבטים שלהם.
2. !voted - מציג רשימה של השחקנים שכבר הצביעו.
3. !not_voted - מציג רשימה של השחקנים שעדיין לא הצביעו.
4. !add_player [שם_שחקן] - מוסיף שחקן חדש ומקצה לו תפקיד ושבט. יוצר ערוצים פרטיים עבור השחקן. (זמין רק למשתמשים בעלי תפקיד Host)
5. !vote - פותח חלון לבחירת שחקן להצבעה מהשבט של המשתמש.
6. !add_tribe [שם_שבט] - מוסיף שבט חדש ומקצה לו תפקיד. יוצר ערוץ צ'אט תחת הקטגוריה 'שבטים' עם הרשאות מתאימות.
7. !change_tribe - פותח חלון לבחירת שחקן ואז חלון נוסף לבחירת שבט חדש עבור השחקן. (זמין רק למשתמשים בעלי תפקיד Host)
8. !vote_time - פתיחת חלון לבחירת שבטים שיכולים להצביע. (זמין רק למשתמשים בעלי תפקיד Host)
9. !end_vote - סיום ההצבעה עבור שבטים נבחרים. (זמין רק למשתמשים בעלי תפקיד Host)
10. !create_voice_channel_menu - יצירת חלון לבחירת תפקידים עבור ערוץ הקול.
11. !alliance [שם_ברית] - יצירת ברית חדשה עם תפקידים נבחרים, ויצירת ערוץ טקסט וערוץ קול עבור הברית.
12. !expel - פותח חלון לבחירת שחקן להדחה ואז חלון נוסף לבחירת תפקיד חדש (מודח או מושבע). (זמין רק למשתמשים בעלי תפקיד Host)
"""
        await ctx.send(f"```\n{commands_description}\n```")

class VoteSelectMenu(Select):
    def __init__(self, bot, ctx, players, tribe_name):
        self.bot = bot
        self.ctx = ctx
        self.tribe_name = tribe_name
        options = [discord.SelectOption(label=player) for player in players]
        super().__init__(placeholder='Select a player to vote for...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_player = self.values[0]
        await self.record_vote(self.ctx, interaction.user, selected_player)

        # Delete the interaction message and send a new message
        await interaction.message.delete()
        await interaction.channel.send(
            f"Player {selected_player} has received your vote for the tribe: {self.tribe_name}.")

    async def record_vote(self, ctx, voter, player_name):
        try:
            votes = []
            voter_has_voted = False

            try:
                with open('votes.csv', 'r') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        if len(row) >= 2 and row[0] == str(voter.id):
                            row[1] = player_name  # Update the vote
                            voter_has_voted = True
                        votes.append(row)
            except FileNotFoundError:
                pass  # If the file doesn't exist, we'll create it later

            if not voter_has_voted:
                votes.append([str(voter.id), player_name])

            with open('votes.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(votes)

        except Exception as e:
            await ctx.send(f"An error occurred while recording the vote: {str(e)}")


class VoteSelectView(View):
    def __init__(self, bot, ctx, players, tribe_name):
        super().__init__()
        self.add_item(VoteSelectMenu(bot, ctx, players, tribe_name))


class PlayerSelectMenu(Select):
    def __init__(self, bot, ctx, players):
        self.bot = bot
        self.ctx = ctx
        options = [discord.SelectOption(label=player) for player in players]
        super().__init__(placeholder='Select a player...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_player = self.values[0]
        await self.select_new_tribe(self.ctx, selected_player)

        # Delete the interaction message and send a new message
        await interaction.message.delete()

    async def select_new_tribe(self, ctx, player_name):
        try:
            # Load tribes
            with open('tribes.csv', 'r') as csvfile:
                tribes = list(csv.reader(csvfile))

            tribe_names = [row[1] for row in tribes if len(row) >= 2 and row[0] == 'tribe']
            if not tribe_names:
                await ctx.send("No tribes found.")
                return

            view = TribeChangeView(self.bot, ctx, player_name, tribe_names)
            await ctx.send(f"Select a new tribe for {player_name}:", view=view)

        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class PlayerSelectView(View):
    def __init__(self, bot, ctx, players):
        super().__init__()
        self.add_item(PlayerSelectMenu(bot, ctx, players))


class TribeChangeMenu(Select):
    def __init__(self, bot, ctx, player_name, tribes):
        self.bot = bot
        self.ctx = ctx
        self.player_name = player_name
        options = [discord.SelectOption(label=tribe) for tribe in tribes]
        super().__init__(placeholder='Select a new tribe...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_tribe = self.values[0]
        await self.change_player_tribe(self.ctx, self.player_name, selected_tribe)

        # Delete the interaction message and send a new message
        await interaction.message.delete()
        await interaction.channel.send(f"Player {self.player_name} has been moved to the tribe {selected_tribe}.")

    async def change_player_tribe(self, ctx, player_name, new_tribe_name):
        guild = ctx.guild
        try:
            # Load player data
            with open('players.csv', 'r') as csvfile:
                players = list(csv.reader(csvfile))

            player_id = None
            old_tribe_name = None
            for row in players:
                if len(row) >= 3 and row[1] == player_name:
                    player_id = row[0]
                    old_tribe_name = row[2]
                    row[2] = new_tribe_name
                    break

            if player_id is None:
                await ctx.send(f"Player {player_name} not found.")
                return

            # Save updated player data
            with open('players.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(players)

            # Change roles in Discord
            member = guild.get_member(int(player_id))
            if member is None:
                await ctx.send(f"Member with ID {player_id} not found.")
                return

            old_tribe_role = discord.utils.get(guild.roles, name=old_tribe_name)
            new_tribe_role = discord.utils.get(guild.roles, name=new_tribe_name)
            if old_tribe_role:
                await member.remove_roles(old_tribe_role)
            if new_tribe_role:
                await member.add_roles(new_tribe_role)

        except FileNotFoundError:
            await ctx.send("The file 'players.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class TribeChangeView(View):
    def __init__(self, bot, ctx, player_name, tribes):
        super().__init__()
        self.add_item(TribeChangeMenu(bot, ctx, player_name, tribes))


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

        # Delete the interaction message and send a new message
        await interaction.message.delete()
        await interaction.channel.send(f"Player {self.player_name} has been added to the tribe {selected_tribe}.")

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
            player_role = await guild.create_role(name=player_name, mentionable=True)

            await member.add_roles(tribe_role, player_role)

            # Create a new category for the player with specific permissions
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                member: discord.PermissionOverwrite(view_channel=True)
            }
            category = await guild.create_category(player_name, overwrites=overwrites)

            # Create the three channels under the new category
            await guild.create_text_channel(f"{player_name} - וידויים", category=category)
            await guild.create_text_channel(f"{player_name} - משחק", category=category)
            await guild.create_text_channel(f"{player_name} - חיפוש פסלון", category=category)

            await ctx.send(
                f"Player '{player_name}' has been added to the tribe '{tribe_name}', role created, and private channels set up.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class TribeSelectView(View):
    def __init__(self, bot, ctx, player_name, tribes):
        super().__init__()
        self.add_item(TribeSelectMenu(bot, ctx, player_name, tribes))


class VotingTribesSelectMenu(Select):
    def __init__(self, bot, ctx, tribes):
        self.bot = bot
        self.ctx = ctx
        options = [discord.SelectOption(label=tribe) for tribe in tribes]
        super().__init__(placeholder='Select tribes...', min_values=1, max_values=len(tribes), options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_tribes = self.values
        await self.set_voting_tribes(self.ctx, selected_tribes)

        # Delete the interaction message and send a new message
        await interaction.message.delete()
        await interaction.channel.send(f"The tribes {', '.join(selected_tribes)} can now vote.")

    async def set_voting_tribes(self, ctx, tribes):
        try:
            # Load tribes data
            with open('tribes.csv', 'r') as csvfile:
                tribes_data = list(csv.reader(csvfile))

            # Update voting tribes
            voting_tribes_row = None
            for row in tribes_data:
                if len(row) >= 2 and row[0] == 'voting':
                    voting_tribes_row = row
                    break

            if voting_tribes_row is None:
                voting_tribes_row = ['voting', '']
                tribes_data.append(voting_tribes_row)

            voting_tribes_row[1] = ', '.join(tribes)

            with open('tribes.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(tribes_data)

        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class VotingTribesSelectView(View):
    def __init__(self, bot, ctx, tribes):
        super().__init__()
        self.add_item(VotingTribesSelectMenu(bot, ctx, tribes))


class EndVotingTribesSelectMenu(Select):
    def __init__(self, bot, ctx, voting_tribes):
        self.bot = bot
        self.ctx = ctx
        options = [discord.SelectOption(label=tribe) for tribe in voting_tribes]
        super().__init__(placeholder='Select tribes...', min_values=1, max_values=len(voting_tribes), options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_tribes = self.values
        await self.end_voting_tribes(self.ctx, selected_tribes)

        # Delete the interaction message and send a new message
        await interaction.message.delete()
        await interaction.channel.send(f"The tribes {', '.join(selected_tribes)} can no longer vote.")

    async def end_voting_tribes(self, ctx, tribes):
        try:
            # Load tribes data
            with open('tribes.csv', 'r') as csvfile:
                tribes_data = list(csv.reader(csvfile))

            # Update voting tribes
            voting_tribes_row = None
            for row in tribes_data:
                if len(row) >= 2 and row[0] == 'voting':
                    voting_tribes_row = row
                    break

            if voting_tribes_row is None:
                await ctx.send("No tribes are currently allowed to vote.")
                return

            current_voting_tribes = voting_tribes_row[1].split(', ')
            new_voting_tribes = [tribe for tribe in current_voting_tribes if tribe not in tribes]

            voting_tribes_row[1] = ', '.join(new_voting_tribes)

            with open('tribes.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(tribes_data)

        except FileNotFoundError:
            await ctx.send("The file 'tribes.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class EndVotingTribesSelectView(View):
    def __init__(self, bot, ctx, voting_tribes):
        super().__init__()
        self.add_item(EndVotingTribesSelectMenu(bot, ctx, voting_tribes))


class VoiceChannelRoleSelectMenu(Select):
    def __init__(self, bot, ctx, roles, channel_name):
        self.bot = bot
        self.ctx = ctx
        self.channel_name = channel_name
        options = [discord.SelectOption(label=role.name, value=str(role.id)) for role in roles]
        super().__init__(placeholder='Select roles for the voice channel...', min_values=1, max_values=len(roles),
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_role_ids = self.values
        selected_roles = [discord.utils.get(self.ctx.guild.roles, id=int(role_id)) for role_id in selected_role_ids]
        await self.create_voice_channel(self.ctx, self.channel_name, selected_roles)

        # Delete the interaction message and send a new message
        await interaction.message.delete()

    async def create_voice_channel(self, ctx, channel_name, roles):
        guild = ctx.guild
        try:
            # If no channel name is provided, create a default name
            if not channel_name:
                channel_name = '-'.join([role.name for role in roles])

            # Create a new voice channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True),
            }
            for role in roles:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)

            voice_channel = await guild.create_voice_channel(name=channel_name, overwrites=overwrites)
            await ctx.send(f"Voice channel '{channel_name}' created successfully.")
        except Exception as e:
            await ctx.send(f"An error occurred while creating the voice channel: {str(e)}")


class VoiceChannelRoleSelectView(View):
    def __init__(self, bot, ctx, roles, channel_name):
        super().__init__()
        self.add_item(VoiceChannelRoleSelectMenu(bot, ctx, roles, channel_name))


class AllianceRoleSelectMenu(Select):
    def __init__(self, bot, ctx, roles, alliance_name, player_role, player_tribes):
        self.bot = bot
        self.ctx = ctx
        self.alliance_name = alliance_name
        self.player_role = player_role
        self.player_tribes = player_tribes
        options = [discord.SelectOption(label=role.name, value=str(role.id)) for role in roles]
        super().__init__(placeholder='Select roles for the alliance...', min_values=1, max_values=len(roles), options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_role_ids = self.values
        selected_roles = [discord.utils.get(self.ctx.guild.roles, id=int(role_id)) for role_id in selected_role_ids]
        selected_roles.append(self.player_role)  # Include the player's role
        await self.create_alliance(self.ctx, self.alliance_name, selected_roles)

        # Delete the interaction message and send a new message
        await interaction.message.delete()

    async def create_alliance(self, ctx, alliance_name, roles):
        guild = ctx.guild
        try:
            # Determine the tribes of the players
            tribes = {self.player_tribes[role.name] for role in roles if role.name in self.player_tribes}
            if len(tribes) == 1:
                # All players are from the same tribe
                tribe_name = tribes.pop()
                category_name = f"{tribe_name} - בריתות"
            else:
                # Players are from different tribes
                category_name = "בריתות בין שבטיות"

            # Find or create the category
            category = discord.utils.get(guild.categories, name=category_name)
            if not category:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(view_channel=False),
                }
                category = await guild.create_category(category_name, overwrites=overwrites)

            # Create a new text and voice channel
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(view_channel=True),
            }
            for role in roles:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True)

            if not alliance_name:
                alliance_name = '-'.join([role.name for role in roles])

            text_channel = await guild.create_text_channel(name=alliance_name, category=category, overwrites=overwrites)
            voice_channel = await guild.create_voice_channel(name=alliance_name, category=category, overwrites=overwrites)

            await ctx.send(f"Alliance channels '{alliance_name}' created successfully.")
        except Exception as e:
            await ctx.send(f"An error occurred while creating the alliance channels: {str(e)}")



class AllianceRoleSelectView(View):
    def __init__(self, bot, ctx, roles, alliance_name, player_role, player_tribes):
        super().__init__()
        self.add_item(AllianceRoleSelectMenu(bot, ctx, roles, alliance_name, player_role, player_tribes))


class ExpelRoleSelectMenu(Select):
    def __init__(self, bot, ctx, player_name):
        self.bot = bot
        self.ctx = ctx
        self.player_name = player_name
        options = [
            discord.SelectOption(label="מודח"),
            discord.SelectOption(label="מושבע")
        ]
        super().__init__(placeholder='Select a new role for the player...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_role = self.values[0]
        await self.assign_new_role(self.ctx, self.player_name, selected_role)

        # Delete the interaction message and send a new message
        await interaction.message.delete()
        await interaction.channel.send(f"Player {self.player_name} has been assigned the role {selected_role}.")

    async def assign_new_role(self, ctx, player_name, new_role_name):
        guild = ctx.guild
        try:
            # Find the member by name
            member = guild.get_member_named(player_name)
            if member is None:
                await ctx.send(f"Member '{player_name}' not found.")
                return

            new_role = discord.utils.get(guild.roles, name=new_role_name)
            if not new_role:
                new_role = await guild.create_role(name=new_role_name, mentionable=True)

            await member.add_roles(new_role)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class ExpelRoleSelectView(View):
    def __init__(self, bot, ctx, player_name):
        super().__init__()
        self.add_item(ExpelRoleSelectMenu(bot, ctx, player_name))


class ExpelPlayerSelectMenu(Select):
    def __init__(self, bot, ctx, players):
        self.bot = bot
        self.ctx = ctx
        options = [discord.SelectOption(label=player) for player in players]
        super().__init__(placeholder='Select a player to expel...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_player = self.values[0]
        await self.expel_player(self.ctx, selected_player)

        # Delete the interaction message and send a new message
        await interaction.message.delete()

    async def expel_player(self, ctx, player_name):
        guild = ctx.guild
        try:
            # Load player data
            with open('players.csv', 'r') as csvfile:
                players = list(csv.reader(csvfile))

            player_id = None
            tribe_name = None
            for row in players:
                if len(row) >= 3 and row[1] == player_name:
                    player_id = row[0]
                    tribe_name = row[2]
                    players.remove(row)
                    break

            if player_id is None:
                await ctx.send(f"Player {player_name} not found.")
                return

            # Save updated player data
            with open('players.csv', 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(players)

            # Remove roles in Discord
            member = guild.get_member(int(player_id))
            if member is None:
                await ctx.send(f"Member with ID {player_id} not found.")
                return

            tribe_role = discord.utils.get(guild.roles, name=tribe_name)
            player_role = discord.utils.get(guild.roles, name=player_name)
            if tribe_role:
                await member.remove_roles(tribe_role)
            if player_role:
                await member.remove_roles(player_role)

            # Open a selection window for the new role
            view = ExpelRoleSelectView(self.bot, ctx, player_name)
            await ctx.send(f"Select a new role for {player_name}:", view=view)

        except FileNotFoundError:
            await ctx.send("The file 'players.csv' was not found. Please ensure it exists.")
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")


class ExpelPlayerSelectView(View):
    def __init__(self, bot, ctx, players):
        super().__init__()
        self.add_item(ExpelPlayerSelectMenu(bot, ctx, players))


async def setup(bot):
    await bot.add_cog(PlayerManagement(bot))
