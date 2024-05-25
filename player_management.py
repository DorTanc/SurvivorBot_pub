import discord
from discord.ext import commands
from discord import app_commands
import csv
import os
from typing import Optional
from collections import defaultdict

log_channel_id = 1243911112978858075

class PlayerManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="players", description="מציג רשימה של כל השחקנים והשבטים שלהם.")
    async def players(self, interaction: discord.Interaction):
        tribes_dict = defaultdict(list)

        # Read players and their tribes from the CSV file
        with open('players.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                user_id, player_name, tribe_name = row
                tribes_dict[tribe_name].append(player_name)

        # Format the output
        response = ""
        for tribe, players in tribes_dict.items():
            response += f"**{tribe}:**\n"
            for index, player in enumerate(players, start=1):
                response += f"{index}. {player}\n"
            response += "\n"

        if response:
            await interaction.response.send_message(response)
        else:
            await interaction.response.send_message("אין שחקנים רשומים כרגע.")
    @app_commands.command(name="add_player",
                          description="מוסיף שחקן חדש ומקצה לו תפקיד ושבט. (זמין רק למשתמשים בעלי תפקיד Host)")
    @app_commands.describe(player_name="שם השחקן להוספה")
    @commands.has_role('Host')
    async def add_player(self, interaction: discord.Interaction, player_name: str):
        class TribeSelect(discord.ui.Select):
            def __init__(self, tribes, player_name, interaction):
                self.player_name = player_name
                self.interaction = interaction
                options = [discord.SelectOption(label=tribe, value=tribe) for tribe in tribes if tribe]
                super().__init__(placeholder="בחר שבט", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                tribe_name = self.values[0]
                player_name = self.player_name
                user_id = None

                # Fetch the member object for the specified player name
                for member in select_interaction.guild.members:
                    if member.display_name == player_name:
                        user_id = member.id
                        break

                if user_id is None:
                    await select_interaction.response.send_message(f"שחקן בשם {player_name} לא נמצא בשרת.",
                                                                   ephemeral=True)
                    return

                member = select_interaction.guild.get_member(user_id)

                try:
                    # Defer the interaction response to acknowledge the interaction
                    await select_interaction.response.defer()

                    # Add player to the tribe and create role
                    role = await select_interaction.guild.create_role(name=player_name, mentionable=True)
                    tribe_role = discord.utils.get(select_interaction.guild.roles, name=tribe_name)
                    await member.add_roles(role, tribe_role)

                    with open('players.csv', 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([user_id, player_name, tribe_name])

                    # Create channels for the player
                    category = await select_interaction.guild.create_category(player_name)
                    for channel_name in [f"{player_name} - וידויים", f"{player_name} - משחק",
                                         f"{player_name} - חיפוש פסלון"]:
                        channel = await category.create_text_channel(channel_name)
                        await channel.set_permissions(member, read_messages=True, send_messages=True)
                        await channel.set_permissions(select_interaction.guild.default_role, read_messages=False)

                    await select_interaction.followup.send(f"השחקן {player_name} נוסף בהצלחה לשבט {tribe_name}.")

                    # Log the addition of the player
                    log_channel = select_interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(f"השחקן {player_name} נוסף בהצלחה לשבט: {tribe_name}")

                    # Delete the initial "בחר שבט לשחקן:" message
                    await self.interaction.delete_original_response()

                except Exception as e:
                    await select_interaction.followup.send(f"שגיאה התרחשה: {str(e)}")

        # Load tribes from CSV and remove duplicates
        tribes = []
        with open('tribes.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # Skip the header row
            tribes = list(set(row[1] for row in reader if row[1] != 'none'))

        if tribes:
            view = discord.ui.View()
            view.add_item(TribeSelect(tribes, player_name, interaction))
            await interaction.response.send_message("בחר שבט לשחקן:", view=view)
        else:
            await interaction.response.send_message("אין שבטים זמינים.")


    # @commands.command(name='vote')
    # async def vote(self, ctx):
    #     voter = ctx.author
    #     voter_role = None
    #     player_tribes = []
    #
    #     try:
    #         # Load player data
    #         with open('players.csv', 'r') as csvfile:
    #             players = csv.reader(csvfile)
    #             player_tribes = list(players)
    #
    #         # Identify the voter's tribe role
    #         for role in voter.roles:
    #             if role.name in [row[2] for row in player_tribes if len(row) >= 3 and row[0] != '<player_id>']:
    #                 voter_role = role
    #                 break
    #
    #         if voter_role is None:
    #             await ctx.send("You do not have a tribe role.")
    #             return
    #
    #         # Check if the voter's tribe is allowed to vote
    #         with open('tribes.csv', 'r') as csvfile:
    #             tribes = list(csv.reader(csvfile))
    #             voting_tribes_row = [row for row in tribes if len(row) >= 2 and row[0] == 'voting']
    #             if voting_tribes_row:
    #                 voting_tribes = voting_tribes_row[0][1].split(', ')
    #             else:
    #                 voting_tribes = []
    #
    #         if voter_role.name not in voting_tribes:
    #             await ctx.send(f"It is not vote time for your tribe ({voter_role.name}).")
    #             return
    #
    #         # Create a selection menu for players in the voter's tribe
    #         tribe_players = [row[1] for row in player_tribes if
    #                          len(row) >= 3 and row[2] == voter_role.name and row[1] != voter.display_name]
    #         if not tribe_players:
    #             await ctx.send(f"There are no other players in your tribe ({voter_role.name}) to vote for.")
    #             return
    #
    #         view = VoteSelectView(self.bot, ctx, tribe_players, voter_role.name)
    #         await ctx.send("Select a player to vote for:", view=view)
    #
    #     except FileNotFoundError:
    #         await ctx.send("The file 'players.csv' or 'tribes.csv' was not found. Please ensure they exist.")
    #     except Exception as e:
    #         await ctx.send(f"An error occurred: {str(e)}")

    @app_commands.command(name="change_tribe",
                          description="פונקציה להעברת שחקן לשבט חדש. (זמין רק למשתמשים בעלי תפקיד Host)")
    @commands.has_role('Host')
    async def change_tribe(self, interaction: discord.Interaction):
        class PlayerSelect(discord.ui.Select):
            def __init__(self, players):
                options = [discord.SelectOption(label=player) for player in players if player]
                super().__init__(placeholder="בחר שחקן", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                selected_player = self.values[0]
                player_select_message = select_interaction.message

                class TribeSelect(discord.ui.Select):
                    def __init__(self, tribes):
                        options = [discord.SelectOption(label=tribe) for tribe in tribes if tribe]
                        super().__init__(placeholder="בחר שבט", min_values=1, max_values=1, options=options)

                    async def callback(self, tribe_interaction: discord.Interaction):
                        selected_tribe = self.values[0]
                        guild = tribe_interaction.guild
                        member = discord.utils.get(guild.members, display_name=selected_player)
                        tribe_role = discord.utils.get(guild.roles, name=selected_tribe)

                        if member and tribe_role:
                            # Remove current tribe roles
                            current_roles = member.roles
                            for current_role in current_roles:
                                if current_role.name in tribes:
                                    former_tribe = current_role.name
                                    await member.remove_roles(current_role)
                            # Add new tribe role
                            await member.add_roles(tribe_role)

                            # Update CSV
                            with open('players.csv', 'r', newline='') as csvfile:
                                reader = list(csv.reader(csvfile))
                            with open('players.csv', 'w', newline='') as csvfile:
                                writer = csv.writer(csvfile)
                                for row in reader:
                                    if row[1] == selected_player:
                                        row[2] = selected_tribe
                                    writer.writerow(row)

                            await tribe_interaction.response.send_message(
                                f"השחקן {selected_player} הועבר לשבט {selected_tribe}.")
                            await player_select_message.delete()
                            await tribe_interaction.message.delete()
                            # Log the tribe change
                            log_channel = tribe_interaction.guild.get_channel(log_channel_id)
                            if log_channel:
                                await log_channel.send(
                                    f"השחקן {selected_player} עבר משבט {former_tribe} לשבט {selected_tribe}.")
                        else:
                            await tribe_interaction.response.send_message("שחקן או שבט לא נמצאו.")

                tribes = []
                with open('tribes.csv', 'r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader)  # Skip the first row
                    tribes = [row[1] for row in reader]

                if tribes:
                    await select_interaction.response.send_message("בחר שבט:",
                                                                   view=discord.ui.View().add_item(TribeSelect(tribes)))
                else:
                    await select_interaction.response.send_message("אין שבטים זמינים.")

        players = []
        with open('players.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            players = [row[1] for row in reader]

        if players:
            await interaction.response.send_message("בחר שחקן:", view=discord.ui.View().add_item(PlayerSelect(players)))
        else:
            await interaction.response.send_message("אין שחקנים זמינים.")

    # @app_commands.command(name="vote_time",
    #                       description="פתיחת חלון לבחירת שבטים שיכולים להצביע. (זמין רק למשתמשים בעלי תפקיד Host)")
    # @commands.has_role('Host')
    # async def vote_time(self, interaction: discord.Interaction):
    #     try:
    #         # Load tribes
    #         with open('tribes.csv', 'r') as csvfile:
    #             tribes = list(csv.reader(csvfile))
    #
    #         tribe_names = [row[0] for row in tribes if row[0] != 'none']
    #         if not tribe_names:
    #             await interaction.response.send_message("No tribes found.")
    #             return
    #
    #         view = VotingTribesSelectView(self.bot, interaction, tribe_names)
    #         await interaction.response.send_message("Select tribes that can vote:", view=view)
    #
    #     except FileNotFoundError:
    #         await interaction.response.send_message("The file 'tribes.csv' was not found. Please ensure it exists.")
    #     except Exception as e:
    #         await interaction.response.send_message(f"An error occurred: {str(e)}")
    #
    # @app_commands.command(name="end_vote",
    #                       description="סיום ההצבעה עבור שבטים נבחרים. (זמין רק למשתמשים בעלי תפקיד Host)")
    # @commands.has_role('Host')
    # async def end_vote(self, interaction: discord.Interaction):
    #     try:
    #         # Load tribes data
    #         with open('tribes.csv', 'r') as csvfile:
    #             tribes_data = list(csv.reader(csvfile))
    #
    #         voting_tribes_row = [row for row in tribes_data if len(row) >= 2 and row[0] == 'voting']
    #         if voting_tribes_row:
    #             voting_tribes = voting_tribes_row[0][1].split(', ')
    #         else:
    #             voting_tribes = []
    #
    #         if not voting_tribes:
    #             await interaction.response.send_message("No tribes are currently allowed to vote.")
    #             return
    #
    #         view = EndVotingTribesSelectView(self.bot, interaction, voting_tribes)
    #         await interaction.response.send_message("Select tribes that should stop voting:", view=view)
    #
    #     except FileNotFoundError:
    #         await interaction.response.send_message("The file 'tribes.csv' was not found. Please ensure it exists.")
    #     except Exception as e:
    #         await interaction.response.send_message(f"An error occurred: {str(e)}")

    @app_commands.command(name="alliance",
                          description="יצירת ברית חדשה עם תפקידים נבחרים, ויצירת ערוץ טקסט וערוץ קול עבור הברית.")
    @app_commands.describe(alliance_name="שם הברית (אופציונלי)")
    async def create_alliance(self, interaction: discord.Interaction, alliance_name: Optional[str] = None):
        class PlayerSelect(discord.ui.Select):
            def __init__(self, players):
                options = [discord.SelectOption(label=player) for player in players if player]
                super().__init__(placeholder="בחר שחקנים", min_values=1, max_values=len(players), options=options)

            async def callback(self, select_interaction: discord.Interaction):
                selected_players = self.values
                guild = select_interaction.guild
                member = select_interaction.user
                selected_players.append(member.display_name)  # Changed to display_name to match players.csv

                if not alliance_name:
                    alliance_name_generated = "-".join(selected_players)
                else:
                    alliance_name_generated = alliance_name

                # קבלת רשימת השחקנים והתגובות שלהם מהקובץ players.csv
                players_roles = {}
                players_tribes = {}
                with open('players.csv', 'r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    for row in reader:
                        player_name = row[1]
                        player_role = row[1]  # assuming that the role name is the same as player name
                        player_tribe = row[2]  # assuming that the tribe name is stored in the third column
                        players_roles[player_name] = player_role
                        players_tribes[player_name] = player_tribe

                selected_players_roles = [players_roles.get(player) for player in selected_players if
                                          player in players_roles]
                selected_players_tribes = [players_tribes.get(player) for player in selected_players if
                                           player in players_tribes]

                if not selected_players_roles or len(selected_players_roles) != len(selected_players):
                    await select_interaction.response.send_message("אחד או יותר מהשחקנים שנבחרו אינם תקפים.",
                                                                   ephemeral=True)
                    return

                if all(tribe == selected_players_tribes[0] for tribe in selected_players_tribes):
                    category_name = f"{selected_players_tribes[0]} - בריתות"
                else:
                    category_name = "בריתות בין שבטיות"

                # יצירת קטגוריה אם היא לא קיימת
                category = discord.utils.get(guild.categories, name=category_name)
                if not category:
                    category = await guild.create_category(category_name, overwrites={
                        guild.default_role: discord.PermissionOverwrite(read_messages=False)
                    })

                # יצירת ערוצים לברית אם הם לא קיימים
                alliance_text_channel = discord.utils.get(guild.text_channels, name=alliance_name_generated)
                if not alliance_text_channel:
                    alliance_text_channel = await guild.create_text_channel(alliance_name_generated, category=category,
                                                                            overwrites={
                                                                                guild.default_role: discord.PermissionOverwrite(
                                                                                    read_messages=False)
                                                                            })

                alliance_voice_channel = discord.utils.get(guild.voice_channels, name=alliance_name_generated)
                if not alliance_voice_channel:
                    alliance_voice_channel = await guild.create_voice_channel(alliance_name_generated,
                                                                              category=category, overwrites={
                            guild.default_role: discord.PermissionOverwrite(connect=False)
                        })

                for player in selected_players:
                    role_name = players_roles.get(player)
                    if role_name:
                        role = discord.utils.get(guild.roles, name=role_name)
                        if role:
                            await alliance_text_channel.set_permissions(role, read_messages=True, send_messages=True)
                            await alliance_voice_channel.set_permissions(role, connect=True, speak=True)

                await select_interaction.message.delete()

                # Acknowledge the interaction and send the follow-up message
                try:
                    await select_interaction.response.send_message(f"הברית {alliance_name_generated} נוצרה בהצלחה.",
                                                                   ephemeral=True)
                except Exception as e:
                    print(f"Failed to send initial response: {e}")

                # Log the creation of the alliance
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    players_list = ", ".join(selected_players)
                    await log_channel.send(f"הברית {alliance_name_generated} המכילה את {players_list} נוצרה בהצלחה.")

        class PlayerSelectView(discord.ui.View):
            def __init__(self, players):
                super().__init__()
                self.add_item(PlayerSelect(players))

        # קבלת רשימת השחקנים מקובץ players.csv
        players = []
        with open('players.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            players = [row[1] for row in reader if row[1] != interaction.user.display_name]

        if players:
            view = PlayerSelectView(players)
            await interaction.response.send_message("בחר שחקנים לברית:", view=view)
        else:
            await interaction.response.send_message("אין שחקנים זמינים לברית.")

    @app_commands.command(name="expel",
                          description="פותח חלון לבחירת שחקן להדחה ואז חלון נוסף לבחירת תפקיד חדש (מודח או מושבע).")
    @commands.has_role('Host')
    async def expel(self, interaction: discord.Interaction):
        class PlayerSelect(discord.ui.Select):
            def __init__(self, players):
                options = [discord.SelectOption(label=player) for player in players if player]
                super().__init__(placeholder="איזה שחקן תרצה להדיח?", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                selected_player = self.values[0]
                player_select_message = select_interaction.message

                guild = select_interaction.guild
                member = discord.utils.get(guild.members, display_name=selected_player)
                if member:
                    # Remove player role and tribe role
                    roles_to_remove = []
                    tribe_roles = []
                    player_role = discord.utils.get(guild.roles, name=selected_player)

                    with open('tribes.csv', 'r', newline='') as csvfile:
                        reader = csv.reader(csvfile)
                        for row in reader:
                            tribe_roles.append(row[1])  # Assuming tribe names are in the second column

                    for role in member.roles:
                        if role.name.startswith("Tribe") or role.name in tribe_roles or role == player_role:
                            roles_to_remove.append(role)

                    await member.remove_roles(*roles_to_remove)

                    # Remove the player from the CSV
                    with open('players.csv', 'r', newline='') as csvfile:
                        reader = list(csv.reader(csvfile))

                    with open('players.csv', 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        for row in reader:
                            if row[1] != selected_player:
                                writer.writerow(row)

                    # Remove player's advantages from advantages.csv
                    with open('advantages.csv', 'r', newline='') as csvfile:
                        reader = list(csv.reader(csvfile))

                    with open('advantages.csv', 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        for row in reader:
                            if row[0] != selected_player:
                                writer.writerow(row)

                    await player_select_message.delete()

                    class ExpelTypeSelect(discord.ui.Select):
                        def __init__(self):
                            options = [
                                discord.SelectOption(label="מושבע"),
                                discord.SelectOption(label="מודח")
                            ]
                            super().__init__(placeholder="איזה סוג מודח?", min_values=1, max_values=1, options=options)

                        async def callback(self, expel_interaction: discord.Interaction):
                            expel_type = self.values[0]
                            role = discord.utils.get(guild.roles, name=expel_type)
                            if not role:
                                role = await guild.create_role(name=expel_type)

                            await member.add_roles(role)
                            await expel_interaction.response.send_message(
                                f"השחקן {selected_player} סומן כ-{expel_type}.")
                            await expel_interaction.message.delete()

                            # Log the expulsion
                            log_channel = interaction.guild.get_channel(log_channel_id)
                            if log_channel:
                                await log_channel.send(f"השחקן {selected_player} הודח, וסומן כ-{expel_type}.")

                    await select_interaction.response.send_message("בחר סוג מודח:",
                                                                   view=discord.ui.View().add_item(ExpelTypeSelect()))
                else:
                    await select_interaction.response.send_message("שחקן לא נמצא.")

        # Load players from CSV
        players = []
        with open('players.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            players = [row[1] for row in reader]

        if players:
            await interaction.response.send_message("בחר שחקן:", view=discord.ui.View().add_item(PlayerSelect(players)))
        else:
            await interaction.response.send_message("אין שחקנים זמינים.")

    @app_commands.command(name="add_advantage", description="מוסיף יתרון לשחקן נבחר")
    @commands.has_role('Host')
    async def add_advantage(self, interaction: discord.Interaction):
        class PlayerSelect(discord.ui.Select):
            def __init__(self, players):
                options = [discord.SelectOption(label=player, value=player) for player in players if player]
                super().__init__(placeholder="בחר שחקן", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                selected_player = self.values[0]

                class AdvantageSelect(discord.ui.Select):
                    def __init__(self, player):
                        self.player = player
                        options = [
                            discord.SelectOption(label="פסלון", value="פסלון"),
                            discord.SelectOption(label="צ'יפים", value="צ'יפים")
                        ]
                        super().__init__(placeholder="בחר סוג יתרון", min_values=1, max_values=1, options=options)

                    async def callback(self, advantage_interaction: discord.Interaction):
                        advantage_type = self.values[0]
                        player = self.player

                        if advantage_type == "צ'יפים":
                            class ChipsModal(discord.ui.Modal, title="כמה צ'יפים להוסיף?"):
                                chips = discord.ui.TextInput(label="מספר צ'יפים", placeholder="כמה צ'יפים להוסיף",
                                                             min_length=1, max_length=5, required=True)

                                async def on_submit(self, modal_interaction: discord.Interaction):
                                    try:
                                        chips_amount = int(self.chips.value)
                                        if chips_amount <= 0:
                                            raise ValueError("מספר הצ'יפים חייב להיות חיובי.")
                                    except ValueError:
                                        await modal_interaction.response.send_message(
                                            "מספר צ'יפים לא תקין. אנא נסה שוב.", ephemeral=True)
                                        return

                                    advantages = []
                                    with open('advantages.csv', 'r', newline='') as csvfile:
                                        reader = csv.reader(csvfile)
                                        advantages = list(reader)

                                    found = False
                                    for advantage in advantages:
                                        if advantage[0] == player and advantage[1] == "צ'יפים":
                                            advantage[2] = str(int(advantage[2]) + chips_amount)
                                            found = True
                                            break

                                    if not found:
                                        advantages.append([player, "צ'יפים", str(chips_amount)])

                                    with open('advantages.csv', 'w', newline='') as csvfile:
                                        writer = csv.writer(csvfile)
                                        writer.writerows(advantages)

                                    await modal_interaction.response.send_message(
                                        f"נוספו {chips_amount} צ'יפים לשחקן {player}.", ephemeral=False)

                                    # Log the addition
                                    log_channel = interaction.guild.get_channel(log_channel_id)
                                    if log_channel:
                                        await log_channel.send(f"נוספו {chips_amount} צ'יפים לשחקן {player}.")

                            await advantage_interaction.response.send_modal(ChipsModal())
                        else:
                            advantages = []
                            with open('advantages.csv', 'r', newline='') as csvfile:
                                reader = csv.reader(csvfile)
                                advantages = list(reader)

                            found = False
                            for advantage in advantages:
                                if advantage[0] == player and advantage[1] == "פסלון":
                                    advantage[2] = str(int(advantage[2]) + 1)
                                    found = True
                                    break

                            if not found:
                                advantages.append([player, "פסלון", '1'])

                            with open('advantages.csv', 'w', newline='') as csvfile:
                                writer = csv.writer(csvfile)
                                writer.writerows(advantages)

                            await advantage_interaction.response.send_message(f"נוסף פסלון לשחקן {player}.",
                                                                              ephemeral=False)

                            # Log the addition
                            log_channel = interaction.guild.get_channel(log_channel_id)
                            if log_channel:
                                await log_channel.send(f"נוסף פסלון לשחקן {player}")

                view = discord.ui.View()
                view.add_item(AdvantageSelect(selected_player))
                await select_interaction.response.send_message("בחר סוג יתרון:", view=view, ephemeral=True)

        players = []
        with open('players.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            players = [row[1] for row in reader]

        if players:
            view = discord.ui.View()
            view.add_item(PlayerSelect(players))
            await interaction.response.send_message("בחר שחקן:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("אין שחקנים זמינים.", ephemeral=True)

    @app_commands.command(name="advantages",
                          description="מציג את היתרונות של השחקן (זמין רק בערוצים פרטיים של השחקן)")
    async def advantages(self, interaction: discord.Interaction):
        # Get the player's display name and normalize it
        player_display_name = interaction.user.display_name.lower()

        # Define private channel names and normalize them
        private_channel_names = [f"{player_display_name}-וידויים",
                                 f"{player_display_name}-משחק",
                                 f"{player_display_name}-חיפוש-פסלון"]

        # Normalize the current channel name
        current_channel_name = interaction.channel.name.lower()

        # Check if the command is used in one of the private channels
        if current_channel_name not in private_channel_names:
            await interaction.response.send_message("הפקודה עובדת רק בערוצים הפרטיים", ephemeral=False)
            return

        # Retrieve the player's advantages from advantages.csv
        advantages = []
        with open('advantages.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row[0].lower() == player_display_name:
                    advantages.append(f"{row[1]}: {row[2]}")

        if advantages:
            advantages_message = "היתרונות שלך:\n" + "\n".join(advantages)
        else:
            advantages_message = "אין לך יתרונות."

        await interaction.response.send_message(advantages_message, ephemeral=False)

    @app_commands.command(name="transfer_advantage",
                          description="מעביר יתרון משחקן אחד לאחר.")
    async def transfer_advantage(self, interaction: discord.Interaction):
        user_name = interaction.user.display_name
        user_private_channels = [f"{user_name}-וידויים", f"{user_name}-משחק", f"{user_name}-חיפוש-פסלון"]

        # Convert to lowercase for comparison
        current_channel_name = interaction.channel.name.lower()
        expected_private_channels = [channel.lower() for channel in user_private_channels]

        # Check if the command is used in one of the private channels
        if current_channel_name not in expected_private_channels:
            await interaction.response.send_message("הפקודה עובדת רק בערוצים הפרטיים", ephemeral=False)
            return

        # Read the user's advantages from advantages.csv
        advantages = {}
        with open('advantages.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row[0] == user_name:
                    advantage_type = row[1]
                    advantage_amount = int(row[2])
                    if advantage_type in advantages:
                        advantages[advantage_type] += advantage_amount
                    else:
                        advantages[advantage_type] = advantage_amount

        if not advantages:
            await interaction.response.send_message("אין לך יתרונות להעביר.", ephemeral=True)
            return

        class AdvantageSelect(discord.ui.Select):
            def __init__(self, advantages):
                options = [discord.SelectOption(label=f"{adv} - {amt}", value=adv) for adv, amt in advantages.items()]
                super().__init__(placeholder="בחר יתרון להעברה", min_values=1, max_values=1, options=options)

            async def callback(self, advantage_interaction: discord.Interaction):
                selected_advantage = self.values[0]

                class AmountModal(discord.ui.Modal):
                    def __init__(self):
                        super().__init__(title="בחר כמות להעברה")
                        self.amount = discord.ui.TextInput(label="כמות", placeholder="כמה להעביר?", min_length=1, max_length=5)
                        self.add_item(self.amount)  # Adding the input component to the modal

                    async def on_submit(self, amount_interaction: discord.Interaction):
                        amount = int(self.amount.value)
                        if amount > advantages[selected_advantage]:
                            await amount_interaction.response.send_message(f"אין מספיק יתרונות להעברה.", ephemeral=True)
                            return

                        class TargetPlayerSelect(discord.ui.Select):
                            def __init__(self, players):
                                options = [discord.SelectOption(label=player) for player in players if player != user_name]
                                super().__init__(placeholder="בחר שחקן להעברה", min_values=1, max_values=1, options=options)

                            async def callback(self, target_interaction: discord.Interaction):
                                target_player = self.values[0]

                                # Read and update advantages.csv
                                updated = False
                                rows = []
                                with open('advantages.csv', 'r', newline='') as csvfile:
                                    reader = csv.reader(csvfile)
                                    for row in reader:
                                        if row[0] == user_name and row[1] == selected_advantage:
                                            current_amount = int(row[2])
                                            if current_amount > amount:
                                                row[2] = str(current_amount - amount)
                                                rows.append(row)
                                            elif current_amount == amount:
                                                continue
                                        elif row[0] == target_player and row[1] == selected_advantage:
                                            row[2] = str(int(row[2]) + amount)
                                            updated = True
                                            rows.append(row)
                                        else:
                                            rows.append(row)
                                if not updated:
                                    rows.append([target_player, selected_advantage, str(amount)])

                                with open('advantages.csv', 'w', newline='') as csvfile:
                                    writer = csv.writer(csvfile)
                                    writer.writerows(rows)

                                await target_interaction.response.send_message(
                                    f"העברת {amount} {selected_advantage} לשחקן {target_player}.", ephemeral=False)

                                # Send a message to the target player's private channel
                                target_channel_name = f"{target_player}-משחק".lower()
                                target_channel = discord.utils.get(target_interaction.guild.text_channels, name=target_channel_name)
                                if target_channel:
                                    await target_channel.send(f"אתה קיבלת {amount} {selected_advantage} מ-{user_name}.")

                                # Log the transfer
                                log_channel = target_interaction.guild.get_channel(log_channel_id)
                                if log_channel:
                                    await log_channel.send(
                                        f"{user_name} העביר {amount} {selected_advantage} ל-{target_player}.")

                        players = []
                        with open('players.csv', 'r', newline='') as csvfile:
                            reader = csv.reader(csvfile)
                            players = [row[1] for row in reader]

                        if players:
                            view = discord.ui.View()
                            view.add_item(TargetPlayerSelect(players))
                            await amount_interaction.response.send_message("בחר שחקן להעברה:", view=view, ephemeral=True)
                        else:
                            await amount_interaction.response.send_message("אין שחקנים זמינים להעברה.", ephemeral=False)

                await advantage_interaction.response.send_modal(AmountModal())

        view = discord.ui.View()
        view.add_item(AdvantageSelect(advantages))
        await interaction.response.send_message("בחר יתרון להעברה:", view=view, ephemeral=True)

    @app_commands.command(name="find_idol", description="מחפש את הפסלון בשבט שלך.")
    async def find_idol(self, interaction: discord.Interaction):
        user_name = interaction.user.display_name
        user_private_channel = [f"{user_name}-חיפוש-פסלון"]

        # Convert to lowercase for comparison
        current_channel_name = interaction.channel.name.lower()
        expected_private_channels = [channel.lower() for channel in user_private_channel]

        # Check if the command is used in one of the private channels
        if current_channel_name not in expected_private_channels:
            await interaction.response.send_message("הפקודה עובדת רק בערוץ חיפוש הפסלון", ephemeral=False)
            return

        # Read player's tribe from players.csv
        user_tribe = None
        with open('players.csv', 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row[1] == user_name:
                    user_tribe = row[2]
                    break

        if not user_tribe:
            await interaction.response.send_message("שגיאה: לא נמצא שבט לשחקן.", ephemeral=True)
            return

        class IdolModal(discord.ui.Modal):
            def __init__(self):
                super().__init__(title="מצא פסלון")
                self.idol_name = discord.ui.TextInput(label="שם הפסלון", placeholder="הכנס את שם הפסלון", min_length=1,
                                                      max_length=50)
                self.add_item(self.idol_name)

            async def on_submit(self, modal_interaction: discord.Interaction):
                idol_name = self.idol_name.value.strip()

                # Check if the idol exists in idols.csv
                idol_found = False
                idol_row_index = None
                idols_data = []
                with open('idols.csv', 'r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    idols_data = list(reader)
                    for index, row in enumerate(idols_data):
                        if row[0] == idol_name and row[1] == user_tribe and row[2] == '0':
                            idol_found = True
                            idol_row_index = index
                            break

                if idol_found:
                    # Update the idol's status to found
                    idols_data[idol_row_index][2] = '1'
                    with open('idols.csv', 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(idols_data)

                    # Add the idol to the user's advantages
                    advantage_added = False
                    advantages_data = []
                    with open('advantages.csv', 'r', newline='') as csvfile:
                        reader = csv.reader(csvfile)
                        advantages_data = list(reader)
                        for row in advantages_data:
                            if row[0] == user_name and row[1] == 'פסלון':
                                row[2] = str(int(row[2]) + 1)
                                advantage_added = True
                        if not advantage_added:
                            advantages_data.append([user_name, 'פסלון', '1'])

                    with open('advantages.csv', 'w', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerows(advantages_data)

                    await modal_interaction.response.send_message(f"מצאת את הפסלון {idol_name}! הפסלון נוסף ליתרונות שלך", ephemeral=False)

                    # Log the finding of the idol
                    log_channel = interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(f"{user_name} מצא את הפסלון {idol_name} בשבט {user_tribe}.")
                else:
                    await modal_interaction.response.send_message("לא נמצא פסלון כזה או שהפסלון כבר נמצא בעבר.",
                                                                  ephemeral=False)

        await interaction.response.send_modal(IdolModal())


    @app_commands.command(name="commands", description="מציג רשימת פקודות")
    async def show_commands(self, interaction: discord.Interaction):
        commands_description = """
פקודות בוט:

1. /players - מציג רשימה של כל השחקנים והשבטים שלהם.
2. /add_player [שם_שחקן] - מוסיף שחקן חדש ומקצה לו תפקיד ושבט. יוצר ערוצים פרטיים עבור השחקן. (זמין רק למשתמשים בעלי תפקיד Host)
3. /add_tribe [שם_שבט] - מוסיף שבט חדש ומקצה לו תפקיד. יוצר ערוץ צ'אט תחת הקטגוריה 'שבטים' עם הרשאות מתאימות.
4. /change_tribe - פותח חלון לבחירת שחקן ואז חלון נוסף לבחירת שבט חדש עבור השחקן. (זמין רק למשתמשים בעלי תפקיד Host)
5. /alliance [שם_ברית] - יצירת ברית חדשה עם תפקידים נבחרים, ויצירת ערוץ טקסט וערוץ קול עבור הברית.
6. /expel - פותח חלון לבחירת שחקן להדחה ואז חלון נוסף לבחירת תפקיד חדש (מודח או מושבע). (זמין רק למשתמשים בעלי תפקיד Host)
7. /add_advantage - פותח חלון לבחירת שחקן ואז חלון נוסף לבחירת סוג יתרון (פסלון או צ'יפים). אם נבחר צ'יפים, ישנה שאלה לגבי כמות הצ'יפים להוסיף. (זמין רק למשתמשים בעלי תפקיד Host)
8. /advantages - מציג את היתרונות של השחקן (זמין רק בערוצים פרטיים של השחקן).
9. /transfer_advantage - מעביר יתרון לשחקן אחר.
10. /find_idol - פותח חלון לחיפוש האישיות של הפסלון.
"""
        await interaction.response.send_message(f"```\n{commands_description}\n```")


async def setup(bot):
    await bot.add_cog(PlayerManagement(bot))
