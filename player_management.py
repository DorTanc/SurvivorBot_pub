import discord
from discord.ext import commands
from discord import app_commands
import csv
import os
from typing import Optional
from collections import defaultdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

log_channel_id = 1243911112978858075
database_players_channel_id = 1244238505882947626
database_tribes_channel_id = 1244328239086829712
database_advantages_channel_id = 1244334271615991841
database_idol_channel_id = 1244710921482535042

class PlayerManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Helper Commands

    async def fetch_players(self, guild):
        database_players_channel = guild.get_channel(database_players_channel_id)
        players = []
        async for message in database_players_channel.history(limit=None):
            players.append(message.content.split(','))
        return players

    async def fetch_players_with_details(self, guild):
        database_players_channel = guild.get_channel(database_players_channel_id)
        players = []
        async for message in database_players_channel.history(limit=None):
            user_id, player_name, tribe_name = message.content.split(',')
            players.append((user_id.strip(), player_name.strip(), tribe_name.strip()))
        return players

    async def fetch_tribes(self, guild):
        database_tribes_channel = guild.get_channel(database_tribes_channel_id)
        tribes = {}
        async for message in database_tribes_channel.history(limit=None):
            tribe_name, color_hex = message.content.split(',')
            tribes[tribe_name.strip()] = color_hex.strip()
        return tribes

    async def fetch_advantages(self, guild):
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        advantages = []
        async for message in database_advantages_channel.history(limit=None):
            advantages.append(message.content.split(','))
        return advantages

    async def fetch_idols(self, guild):
        database_idol_channel = guild.get_channel(database_idol_channel_id)
        idols = []
        async for message in database_idol_channel.history(limit=None):
            idols.append(message.content.split(','))
        return idols

    async def add_player_to_channel(self, guild, user_id, player_name, tribe_name):
        database_players_channel = guild.get_channel(database_players_channel_id)
        await database_players_channel.send(f"{user_id},{player_name},{tribe_name}")

    async def update_advantage(self, guild, player, advantage_type, new_amount):
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        messages = []
        async for message in database_advantages_channel.history(limit=None):
            if message.content.startswith(f"{player}"):
                messages.append(message)

        if messages:
            await messages[0].edit(content=f"{player},{advantage_type},{new_amount}")
        else:
            await self.add_advantage_to_channel(guild, player, advantage_type, new_amount)

    async def add_advantage_to_channel(self, guild, player, advantage_type, amount):
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        updated = False
        messages = []
        async for message in database_advantages_channel.history(limit=None):
            if message.content.startswith(f"{player}"):
                messages.append(message)

        if messages:
            for message in messages:
                if f"{advantage_type}" in message.content:
                    current_amount = int(message.content.split(',')[2])
                    new_amount = current_amount + int(amount)
                    await message.edit(content=f"{player},{advantage_type},{new_amount}")
                    updated = True
                else:
                    await message.edit(content=f"{message.content},{advantage_type},{int(amount)}")
                    updated = True


        if not updated:
            await database_advantages_channel.send(f"{player},{advantage_type},{amount}")

    async def is_in_correct_channel(self, interaction):
        player_display_name = interaction.user.display_name.lower()
        player_game_channel_name = f"{player_display_name.replace(' ', '-')}-משחק"
        current_channel_name = interaction.channel.name.lower()
        player_game_channel = discord.utils.get(interaction.guild.text_channels, name=player_game_channel_name)
        return current_channel_name == player_game_channel_name, player_game_channel

    async def add_idol_to_channel(self, guild, idol_name, idol_tribe, idol_image_url, found):
        database_idol_channel = guild.get_channel(database_idol_channel_id)
        await database_idol_channel.send(f"{idol_name},{idol_tribe},{idol_image_url},{found}")

    async def transfer_advantage(self, interaction, selected_advantage, amount, target_player):
        user_name = interaction.user.display_name
        advantages = await self.fetch_advantages(interaction.guild)

        user_advantages = {adv[1]: int(adv[2]) for adv in advantages if adv[0] == user_name}
        target_advantages = {adv[1]: int(adv[2]) for adv in advantages if adv[0] == target_player}

        if selected_advantage not in user_advantages or user_advantages[selected_advantage] < amount:
            await interaction.followup.send("אין מספיק יתרונות להעברה.", ephemeral=True)
            return

        await self.update_advantage(interaction.guild, user_name, selected_advantage, user_advantages[selected_advantage] - amount)

        if selected_advantage in target_advantages:
            new_amount = target_advantages[selected_advantage] + amount
        else:
            new_amount = amount

        await self.update_advantage(interaction.guild, target_player, selected_advantage, new_amount)

        # confirmation to transferring player
        new_amount_user = user_advantages[selected_advantage] - amount
        embed = discord.Embed(
            title="",
            description=f"העברת {amount} {selected_advantage} ל {target_player}\nנשארו לך {new_amount_user} {selected_advantage}",
            color=await self.get_player_tribe_color(interaction.guild, user_name)
        )
        file = discord.File("chips.png", filename="chips.png")
        embed.set_image(url="attachment://chips.png")
        await interaction.followup.send(file=file, embed=embed, ephemeral=False)

        # confirmation to target player
        target_channel_name = f"{target_player.replace(' ', '-').lower()}-משחק"
        target_channel = discord.utils.get(interaction.guild.text_channels, name=target_channel_name)
        if target_channel:
            new_amount_target = target_advantages[selected_advantage] + amount
            embed = discord.Embed(
                title="מזל טוב!",
                description=f"קיבלת {amount} {selected_advantage} מ-{user_name}\nעכשיו יש לך {new_amount_target} {selected_advantage}",
                color=await self.get_player_tribe_color(interaction.guild, target_player)
            )
            file = discord.File("chips.png", filename="chips.png")
            embed.set_image(url="attachment://chips.png")
            await target_channel.send(file=file, embed=embed)

        # log transfer
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="",
                description=f"{target_player} העביר {amount} {selected_advantage} ל {user_name}\nל {user_name} יש עכשיו {new_amount_user} {selected_advantage}\nל {target_player} יש עכשיו {new_amount_target} {selected_advantage}",
                color=await self.get_player_tribe_color(interaction.guild, user_name)
            )
            file = discord.File("chips.png", filename="chips.png")
            embed.set_image(url="attachment://chips.png")
            await log_channel.send(file=file, embed=embed)

    async def get_player_tribe(self, guild, player_name):
        players = await self.fetch_players_with_details(guild)
        for user_id, name, tribe in players:
            if name == player_name:
                return tribe
        return None
    async def get_tribe_colors(self, guild):
        database_tribes_channel = guild.get_channel(database_tribes_channel_id)
        tribe_colors = {}
        async for message in database_tribes_channel.history(limit=None):
            parts = message.content.split(',')
            if len(parts) == 2:
                tribe_name, color_hex = parts
                try:
                    tribe_colors[tribe_name.strip()] = discord.Color(int(color_hex.strip().replace('#', ''), 16))
                except ValueError:
                    continue
        return tribe_colors

    async def get_tribe_color_by_name(self, guild, tribe_name):
        database_tribes_channel = guild.get_channel(database_tribes_channel_id)
        async for message in database_tribes_channel.history(limit=None):
            tribe, color_hex = message.content.split(',')
            if tribe == tribe_name:
                return discord.Color(int(color_hex.lstrip('#'), 16))
        return discord.Color.default()


    def create_embeds_for_players(self, tribes_dict, advantages_dict, tribe_colors):
        embeds = []
        for tribe, players in tribes_dict.items():
            player_list = ""
            for index, (user_id, player_name) in enumerate(players, start=1):
                advantages = advantages_dict.get(player_name, [])  # Match by player name
                advantages_str = ", ".join([f"{adv} ({amt})" for adv, amt in advantages])
                player_list += f"{index}. {player_name} - {advantages_str if advantages_str else 'אין יתרונות'}\n"

            embed = discord.Embed(
                title=f"שבט {tribe}",
                description=f"{player_list if player_list else 'No players'}",
                color=tribe_colors.get(tribe, discord.Color.blue())  # Use the tribe color, default to blue
            )
            embeds.append(embed)
        return embeds

    async def fetch_player_data(self, guild):
        players = await self.fetch_players_with_details(guild)
        tribes_dict = defaultdict(list)
        for user_id, player_name, tribe_name in players:
            tribes_dict[tribe_name].append((user_id, player_name))
        return tribes_dict

    async def fetch_advantages_data(self, guild):
        advantages = await self.fetch_advantages(guild)
        advantages_dict = defaultdict(list)
        for player_name, advantage_name, amount in advantages:
            advantages_dict[player_name.strip()].append((advantage_name.strip(), amount.strip()))
        return advantages_dict

    async def get_player_roles_and_tribes(self, guild):
        players = await self.fetch_players(guild)
        players_roles = {player_name: player_name for user_id, player_name, tribe_name in players}
        players_tribes = {player_name: tribe_name for user_id, player_name, tribe_name in players}
        return players_roles, players_tribes

    async def get_player_tribe_color(self, guild, player):
        players = await self.fetch_players_with_details(guild)
        player_tribe = None
        for uid, player_name, tribe_name in players:
            if player_name == player:
                player_tribe = tribe_name
                break
        tribe_colors = await self.get_tribe_colors(guild)
        return tribe_colors.get(player_tribe)

    async def create_alliance_channels(self, guild, category_name, alliance_name, selected_players_roles):
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name, overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False, view_channels=False)
            })

        alliance_text_channel = discord.utils.get(guild.text_channels, name=alliance_name)
        if not alliance_text_channel:
            alliance_text_channel = await guild.create_text_channel(alliance_name, category=category, overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False, view_channel=False)
            })

        alliance_voice_channel = discord.utils.get(guild.voice_channels, name=alliance_name)
        if not alliance_voice_channel:
            alliance_voice_channel = await guild.create_voice_channel(alliance_name, category=category, overwrites={
                guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False)
            })

        for role_name in selected_players_roles:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                await alliance_text_channel.set_permissions(role, read_messages=True, send_messages=True)
                await alliance_voice_channel.set_permissions(role, connect=True, speak=True, view_channel=True)

        return alliance_name

    async def send_alliance_log(self, guild, alliance_name, selected_players):
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            players_list = ", ".join(selected_players)
            embed = discord.Embed(
                title="ברית נוצרה",
                description=f"הברית {alliance_name} המכילה את {players_list} נוצרה בהצלחה.",
                color=discord.Color.from_rgb(r=255,g=255,b=255)
            )
            await log_channel.send(embed=embed)

    async def get_player_advantages(self, player_name, guild):
        advantages = await self.fetch_advantages(guild)
        player_advantages = [adv for adv in advantages if adv[0].lower() == player_name.lower()]
        return player_advantages

    async def is_in_correct_channel(self, interaction):
        player_display_name = interaction.user.display_name.lower()
        player_game_channel_name = f"{player_display_name.replace(' ', '-')}-משחק"
        current_channel_name = interaction.channel.name.lower()
        player_game_channel = discord.utils.get(interaction.guild.text_channels, name=player_game_channel_name)
        return current_channel_name == player_game_channel_name, player_game_channel

    async def find_idol_in_tribe(self, guild, tribe, idol_guess):
        idols = await self.fetch_idols(guild)
        for idol_name, idol_tribe, idol_image_url, found in idols:
            if idol_tribe == tribe and str(idol_guess) == idol_name and found.lower() == 'false':
                return idol_name, idol_image_url
        return None, None

    async def update_idol_status(self, guild, idol_name, status):
        database_idol_channel = guild.get_channel(database_idol_channel_id)
        messages = []
        async for message in database_idol_channel.history(limit=None):
            if message.content.startswith(f"{idol_name},"):
                messages.append(message)

        if messages:
            idol_details = messages[0].content.split(',')
            idol_details[3] = str(status).lower()
            await messages[0].edit(content=','.join(idol_details))





    @app_commands.command(name="players", description="מציג רשימה של כל השחקנים והשבטים שלהם.")
    @commands.has_role('Host')
    async def players(self, interaction: discord.Interaction):
        tribes_dict = await self.fetch_player_data(interaction.guild)
        advantages_dict = await self.fetch_advantages_data(interaction.guild)
        tribe_colors = await self.get_tribe_colors(interaction.guild)
        embeds = self.create_embeds_for_players(tribes_dict, advantages_dict, tribe_colors)

        if embeds:
            await interaction.response.send_message(embeds=embeds)
        else:
            await interaction.response.send_message("אין שחקנים רשומים כרגע.")

    @app_commands.command(name="alliance", description="יצירת ברית חדשה, וערוץ טקסט וערוץ קול עבור הברית.")
    @app_commands.describe(alliance_name="שם הברית (אופציונלי)")
    async def create_alliance(self, interaction: discord.Interaction, alliance_name: Optional[str] = None):
        class PlayerSelect(discord.ui.Select):
            def __init__(self, players, cog, original_interaction):
                self.cog = cog
                self.original_interaction = original_interaction
                options = [discord.SelectOption(label=player) for player in players if player]
                super().__init__(placeholder="בחר שחקנים", min_values=1, max_values=len(players), options=options)

            async def callback(self, select_interaction: discord.Interaction):
                await select_interaction.response.defer()
                selected_players = self.values
                guild = select_interaction.guild
                member = select_interaction.user
                selected_players.append(member.display_name)

                if not alliance_name:
                    alliance_name_generated = "-".join(selected_players)
                else:
                    alliance_name_generated = alliance_name

                players_roles, players_tribes = await self.cog.get_player_roles_and_tribes(guild)

                selected_players_roles = [players_roles.get(player) for player in selected_players if player in players_roles]
                selected_players_tribes = [players_tribes.get(player) for player in selected_players if player in players_tribes]

                if not selected_players_roles or len(selected_players_roles) != len(selected_players):
                    await select_interaction.followup.send("אחד או יותר מהשחקנים שנבחרו אינם תקפים.", ephemeral=True)
                    return

                if all(tribe == selected_players_tribes[0] for tribe in selected_players_tribes):
                    category_name = f"{selected_players_tribes[0]} - בריתות"
                else:
                    category_name = "בריתות בין שבטיות"

                alliance_name_final = await self.cog.create_alliance_channels(guild, category_name, alliance_name_generated, selected_players_roles)

                embed = discord.Embed(
                    title="הברית נוצרה",
                    description=f"הברית {alliance_name_final} נוצרה בהצלחה.",
                    color=await self.cog.get_player_tribe_color(interaction.guild, interaction.user.display_name)
                )
                await select_interaction.followup.send(embed=embed, ephemeral=True)
                await self.cog.send_alliance_log(guild, alliance_name_final, selected_players)

                # Delete the initial "בחר שחקנים לברית:" message
                try:
                    await self.original_interaction.delete_original_response()
                except Exception as e:
                    pass

        class PlayerSelectView(discord.ui.View):
            def __init__(self, players, cog, original_interaction):
                super().__init__()
                self.add_item(PlayerSelect(players, cog, original_interaction))

        players = await self.fetch_players(interaction.guild)
        player_names = [player_name for _, player_name, _ in players if player_name != interaction.user.display_name]

        if player_names:
            view = PlayerSelectView(player_names, self, interaction)
            await interaction.response.defer()
            await interaction.followup.send("בחר שחקנים לברית:", view=view)
        else:
            await interaction.response.send_message("אין שחקנים זמינים לברית.")


    @app_commands.command(name="show_advantages", description="מציג את היתרונות של השחקן (זמין רק בערוץ המשחק)")
    async def show_advantages(self, interaction: discord.Interaction):
        # Check if the command is used in the player's private game channel
        in_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not in_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return

        # Get the player's advantages
        player_display_name = interaction.user.display_name
        player_advantages = await self.get_player_advantages(player_display_name, interaction.guild)

        # Format the advantages for display
        advantages_text = "\n".join([f"{adv[1]}: {adv[2]}" for adv in player_advantages]) if player_advantages else "אין לך יתרונות."

        # Create and send the embed message
        embed = discord.Embed(
            title="היתרונות שלך:",
            description=advantages_text,
            color= await self.get_player_tribe_color(interaction.guild, player_display_name)
        )
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="transfer_chips", description="מעביר צ'יפים משחקן אחד לאחר.")
    async def transfer_chips(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return

        user_name = interaction.user.display_name
        advantages = await self.fetch_advantages(interaction.guild)
        user_advantages = {adv[1]: int(adv[2]) for adv in advantages if adv[0] == user_name}

        if "צ'יפים" not in user_advantages:
            embed = discord.Embed(
            title="",
            description="אין לך צ'יפים להעביר.",
            color= await self.get_player_tribe_color(interaction.guild, user_name)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        class ChipsAmountModal(discord.ui.Modal):
            chips_amount = discord.ui.TextInput(label="מספר צ'יפים", placeholder="כמה צ'יפים להעביר?", min_length=1, max_length=5, required=True)

            def __init__(self, cog, interaction, selected_advantage):
                super().__init__(title="בחר כמות להעברה")
                self.cog = cog
                self.interaction = interaction
                self.selected_advantage = selected_advantage

            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    amount = int(self.chips_amount.value)
                except ValueError:
                    await modal_interaction.response.send_message("כמות לא תקינה.", ephemeral=True)
                    return

                if amount > user_advantages[self.selected_advantage]:
                    await modal_interaction.response.send_message("אין מספיק צ'יפים להעברה.", ephemeral=True)
                    return

                players = await self.cog.fetch_players(modal_interaction.guild)
                player_names = [player[1] for player in players if player[1] != user_name]

                class TargetPlayerSelect(discord.ui.Select):
                    def __init__(self, player_names, cog, amount, interaction):
                        self.cog = cog
                        self.amount = amount
                        self.interaction = interaction
                        options = [discord.SelectOption(label=player, value=player) for player in player_names]
                        super().__init__(placeholder="בחר שחקן להעברה", min_values=1, max_values=1, options=options)

                    async def callback(self, target_interaction: discord.Interaction):
                        target_player = self.values[0]

                        await self.cog.transfer_advantage(self.interaction, "צ'יפים", self.amount, target_player)

                        try:
                            if self.interaction.message:
                                await self.interaction.message.delete()
                        except Exception as e:
                            logger.error(f"Error deleting original interaction message: {e}")

                view = discord.ui.View()
                view.add_item(TargetPlayerSelect(player_names, self.cog, amount, self.interaction))

                await modal_interaction.response.defer()
                response_message = await modal_interaction.followup.send("בחר שחקן להעברה:", view=view, ephemeral=False)

                try:
                    self.interaction.message = response_message
                except Exception as e:
                    logger.error(f"Error assigning message to interaction: {e}")

        modal = ChipsAmountModal(self, interaction, "צ'יפים")
        await interaction.response.send_modal(modal)

    @app_commands.command(name="transfer_idol", description="מעביר אליל משחקן אחד לאחר.")
    async def transfer_idol(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}",
                                                    ephemeral=True)
            return

        user_name = interaction.user.display_name
        advantages = await self.fetch_advantages(interaction.guild)
        user_advantages = {adv[1]: int(adv[2]) for adv in advantages if adv[0] == user_name}

        if "אליל" not in user_advantages:
            await interaction.response.send_message("אין לך אליל להעביר.", ephemeral=True)
            return

        class IdolAmountModal(discord.ui.Modal):
            idol_amount = discord.ui.TextInput(label="מספר אלילים", placeholder="כמה אלילים להעביר?",
                                               min_length=1, max_length=5, required=True)

            def __init__(self, cog, interaction, selected_advantage):
                super().__init__(title="בחר כמות להעברה")
                self.cog = cog
                self.interaction = interaction
                self.selected_advantage = selected_advantage

            async def on_submit(self, modal_interaction: discord.Interaction):
                try:
                    amount = int(self.idol_amount.value)
                except ValueError:
                    await modal_interaction.response.send_message("כמות לא תקינה.", ephemeral=True)
                    return

                if amount > user_advantages[self.selected_advantage]:
                    await modal_interaction.response.send_message("אין מספיק אלילים להעברה.", ephemeral=True)
                    return

                players = await self.cog.fetch_players(modal_interaction.guild)
                player_names = [player[1] for player in players if player[1] != user_name]

                class TargetPlayerSelect(discord.ui.Select):
                    def __init__(self, player_names, cog, amount, interaction):
                        self.cog = cog
                        self.amount = amount
                        self.interaction = interaction
                        options = [discord.SelectOption(label=player, value=player) for player in player_names]
                        super().__init__(placeholder="בחר שחקן להעברה", min_values=1, max_values=1, options=options)

                    async def callback(self, target_interaction: discord.Interaction):
                        target_player = self.values[0]
                        await self.cog.transfer_advantage(self.interaction, "אליל", self.amount, target_player)

                        if self.interaction.message:
                            await self.interaction.message.delete()

                view = discord.ui.View()
                view.add_item(TargetPlayerSelect(player_names, self.cog, amount, self.interaction))
                await modal_interaction.response.send_message("בחר שחקן להעברה:", view=view, ephemeral=False)

        modal = IdolAmountModal(self, interaction, "אליל")
        await interaction.response.send_modal(modal)

    @app_commands.command(name="find_idol", description="מחפש את האליל בשבט שלך.")
    async def find_idol(self, interaction: discord.Interaction):
        user_name = interaction.user.display_name
        file = None
        in_correct_channel, _ = await self.is_in_correct_channel(interaction)
        if not in_correct_channel:
            embed = discord.Embed(
                title="שגיאה",
                description="הפקודה עובדת רק בערוץ המשחק",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=False)
            return

        user_tribe = await self.get_player_tribe(interaction.guild, user_name)
        if not user_tribe:
            await interaction.response.send_message("שגיאה: לא נמצא שבט לשחקן.", ephemeral=True)
            return

        class IdolGuessModal(discord.ui.Modal):
            idol_name = discord.ui.TextInput(label="נחש את שם האליל", placeholder="הזן את שם האליל", required=True)

            def __init__(self, cog, interaction, user_name, user_tribe):
                super().__init__(title="נחש את שם האליל")
                self.cog = cog
                self.interaction = interaction
                self.user_name = user_name
                self.user_tribe = user_tribe
                self.file = file


            async def on_submit(self, modal_interaction: discord.Interaction):
                idol_name = self.idol_name.value
                found_idol = False
                # Read the image file


                idol_name_correct, idol_image = await self.cog.find_idol_in_tribe(modal_interaction.guild, self.user_tribe, idol_name)
                self.file = discord.File(idol_image, filename=idol_image)
                idol_image_url = f"attachment://{idol_image}"
                if idol_name_correct:
                    await self.cog.update_idol_status(modal_interaction.guild, idol_name_correct, True)
                    await self.cog.add_advantage_to_channel(modal_interaction.guild, self.user_name, idol_name_correct, "1")
                    found_idol = True

                    embed = discord.Embed(
                        title="אליל נמצא!",
                        description=f"מצאת את האליל {idol_name_correct} מהשבט {self.user_tribe}.",
                        color=discord.Color.green()
                    )
                    embed.set_image(url=idol_image_url)

                    # Send a log message
                    log_channel = modal_interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        log_embed = discord.Embed(
                            title="אליל נמצא",
                            description=f"{self.user_name} מצא את האליל {idol_name_correct} מהשבט {self.user_tribe}.",
                            color=discord.Color.green()
                        )
                        log_embed.set_image(url=idol_image_url)
                        await log_channel.send(file=file, embed=log_embed)
                else:
                    embed = discord.Embed(
                        title="ניסיון נכשל",
                        description="לא הצלחת למצוא את האליל.",
                        color=discord.Color.red()
                    )
                if found_idol:
                    await modal_interaction.response.send_message(file=self.file, embed=embed, ephemeral=False)
                else:
                    await modal_interaction.response.send_message(embed=embed, ephemeral=False)

        modal = IdolGuessModal(self, interaction, user_name, user_tribe)
        await interaction.response.send_modal(modal)

    @app_commands.command(name="commands", description="מציג רשימת פקודות לשחקנים")
    async def show_commands(self, interaction: discord.Interaction):
        embed = discord.Embed(
                    title=f"\u202Bפקודות לשחקנים:",
                    description=f"",
                    color=discord.Color.from_rgb(r=255,g=255,b=255)
                )
        embed.add_field(name="/players", value='\u202Bמציג רשימה של כל השחקנים והשבטים שלהם', inline=False)
        embed.add_field(name="/alliance [שם ברית]", value="\u202Bיצירת ברית חדשה, ויצירת ערוץ טקסט וערוץ קול עבור הברית.", inline=False)
        embed.add_field(name="/show_advantages", value="\u202Bמציג את היתרונות של השחקן (זמין רק בערוצים פרטיים של השחקן).", inline=False)
        embed.add_field(name="/transfer_chips", value="\u202Bמעביר צ'יפים לשחקן אחר.", inline=False)
        embed.add_field(name="/transfer_idol", value="\u202Bמעביר אליל לשחקן אחר.", inline=False)
        embed.add_field(name="/find_idol", value="\u202Bפותח חלון לחיפוש האליל, שבו יש להזין את שם המפורסם.", inline=False)
        
        await interaction.response.send_message(embed=embed)

# Host-only commands

    @app_commands.command(name="host_commands", description="מציג רשימת פקודות למנהלים")
    async def show_hostcommands(self, interaction: discord.Interaction):
        embed = discord.Embed(
                    title=f"פקודות למנהלים:",
                    description=f"",
                    color=discord.Color.from_rgb(r=255,g=255,b=255)
                )
        embed.add_field(name="/add\_player [שם שחקן]", value="\u202Bמוסיף שחקן חדש ומקצה לו תפקיד ושבט. יוצר ערוצים פרטיים עבור השחקן.", inline=False)
        embed.add_field(name="/add\_tribe [שם שבט]", value="\u202Bמוסיף שבט חדש ומקצה לו תפקיד. יוצר ערוץ צ'אט תחת הקטגוריה 'שבטים' עם הרשאות מתאימות.", inline=False)
        embed.add_field(name="/change_tribe", value="\u202Bפותח חלון לבחירת שחקן ואז חלון נוסף לבחירת שבט חדש עבור השחקן.", inline=False)
        embed.add_field(name="/expel", value="\u202Bפותח חלון לבחירת שחקן להדחה ואז חלון נוסף לבחירת תפקיד חדש (מודח או מושבע).", inline=False)
        embed.add_field(name="/add_chips", value="\u202Bמוסיף צ'יפים לשחקן", inline=False)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="add_player",
                          description="מוסיף שחקן חדש ומקצה לו תפקיד ושבט.")
    @app_commands.describe(player_name="שם השחקן להוספה")
    @commands.has_role('Host')
    async def add_player(self, interaction: discord.Interaction, player_name: str):
        tribes = await self.fetch_tribes(interaction.guild)

        class TribeSelect(discord.ui.Select):
            def __init__(self, tribes, player_name, interaction, cog):
                self.player_name = player_name
                self.interaction = interaction
                self.cog = cog
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

                    await self.cog.add_player_to_channel(select_interaction.guild, user_id, player_name, tribe_name)

                    # Create or get the "ערוצים אישיים" category
                    category_name = "ערוצים אישיים"
                    category = discord.utils.get(select_interaction.guild.categories, name=category_name)
                    if not category:
                        category = await select_interaction.guild.create_category(category_name)

                    # Create channels for the player under the "ערוצים אישיים" category
                    for channel_name in [f"{player_name} - וידויים", f"{player_name} - משחק"]:
                        channel = await category.create_text_channel(channel_name)
                        await channel.set_permissions(member, read_messages=True, send_messages=True)
                        await channel.set_permissions(select_interaction.guild.default_role, read_messages=False)

                    await select_interaction.followup.send(f"השחקן {player_name} נוסף בהצלחה לשבט {tribe_name}.")

                    # Log the addition of the player
                    log_channel = select_interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="הוספת שחקן",
                            description=f"השחקן {player_name} נוסף בהצלחה לשבט {tribe_name}.",
                            color=discord.Color.green()
                        )
                        await log_channel.send(embed=embed)

                    # Delete the initial "בחר שבט לשחקן:" message
                    await self.interaction.delete_original_response()

                except Exception as e:
                    await select_interaction.followup.send(f"שגיאה התרחשה: {str(e)}")

        if tribes:
            view = discord.ui.View()
            view.add_item(TribeSelect(tribes, player_name, interaction, self))
            await interaction.response.send_message("בחר שבט לשחקן:", view=view)
        else:
            await interaction.response.send_message("אין שבטים זמינים.")

    @app_commands.command(name="change_tribe",
                          description="מעביר שחקן לשבט חדש")
    @app_commands.describe(player_name="שם השחקן", tribe_name="שם השבט")
    @commands.has_role('Host')
    async def change_tribe(self, interaction: discord.Interaction, player_name: str, tribe_name: str):
        database_players_channel = interaction.guild.get_channel(database_players_channel_id)
        async for message in database_players_channel.history(limit=None):
            if player_name in message.content:
                player_data = message.content.split(',')
                if player_data[1].lower() != player_name.lower():
                    continue
                player_data[2] = tribe_name
                await message.edit(content=','.join(player_data))

        embed = discord.Embed(
            title="מעבר שבט",
            description=f"{player_name} עבר לשבט {tribe_name}.",
            color=await self.get_tribe_color_by_name(interaction.guild, tribe_name)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(embed=embed)


    @app_commands.command(name="add_chips", description="מוסיף צ'יפים לשחקן נבחר")
    @commands.has_role('Host')
    async def add_chips(self, interaction: discord.Interaction):
        class PlayerSelect(discord.ui.Select):
            def __init__(self, players, cog):
                self.cog = cog
                options = [discord.SelectOption(label=player_name, value=player_name) for user_id, player_name, tribe_name in players if player_name]
                super().__init__(placeholder="בחר שחקן", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                selected_player = self.values[0]

                class ChipsModal(discord.ui.Modal, title="כמה צ'יפים להוסיף?"):
                    chips = discord.ui.TextInput(label="מספר צ'יפים", placeholder="כמה צ'יפים להוסיף",
                                                 min_length=1, max_length=5, required=True)

                    def __init__(self, cog, selected_player):
                        super().__init__()
                        self.cog = cog
                        self.selected_player = selected_player

                    async def on_submit(self, modal_interaction: discord.Interaction):
                        try:
                            chips_amount = int(self.chips.value)
                            if chips_amount <= 0:
                                raise ValueError("מספר הצ'יפים חייב להיות חיובי.")
                        except ValueError:
                            await modal_interaction.response.send_message(
                                "מספר צ'יפים לא תקין. אנא נסה שוב.", ephemeral=True)
                            return

                        advantages = await self.cog.fetch_advantages(interaction.guild)
                        found = False
                        for advantage in advantages:
                            if advantage[0] == self.selected_player and advantage[1] == "צ'יפים":
                                new_amount = str(int(advantage[2]) + chips_amount)
                                await self.cog.update_advantage(interaction.guild, self.selected_player, "צ'יפים", new_amount)
                                found = True
                                break

                        if not found:
                            await self.cog.add_advantage_to_channel(interaction.guild, self.selected_player, "צ'יפים", str(chips_amount))

                        await modal_interaction.response.send_message(
                            f"נוספו {chips_amount} צ'יפים לשחקן {self.selected_player}.", ephemeral=True)

                        # Log the addition
                        log_channel = interaction.guild.get_channel(log_channel_id)
                        if log_channel:
                            embed = discord.Embed(
                                title="הוספת צ'יפים",
                                description=f"נוספו {chips_amount} צ'יפים ל {self.selected_player}\nל {self.selected_player} יש עכשיו {new_amount} צ'יפים",
                                color=await self.cog.get_player_tribe_color(interaction.guild, selected_player)
                            )
                            file = discord.File("chips.png", filename="chips.png")
                            embed.set_image(url="attachment://chips.png")
                            await log_channel.send(file=file, embed=embed)

                        # Send an embed message to the player's private channel
                        player_channel_name = f"{self.selected_player.replace(' ', '-')}-משחק".lower()
                        player_channel = discord.utils.get(interaction.guild.text_channels, name=player_channel_name)
                        if player_channel:
                            player_embed = discord.Embed(
                                title="מזל טוב!",
                                description=f"נוספו לך {chips_amount} צ'יפים\nעכשיו יש לך {new_amount} צ'יפים",
                                color=await self.cog.get_player_tribe_color(interaction.guild, selected_player)
                            )
                            file = discord.File("chips.png", filename="chips.png")
                            player_embed.set_image(url="attachment://chips.png")
                            await player_channel.send(file=file, embed=player_embed)

                await select_interaction.response.send_modal(ChipsModal(self.cog, selected_player))

        players = await self.fetch_players(interaction.guild)
        if players:
            view = discord.ui.View()
            view.add_item(PlayerSelect(players, self))
            await interaction.response.send_message("בחר שחקן:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("אין שחקנים זמינים.", ephemeral=True)

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

    @app_commands.command(name="add_idol", description="מוסיף אליל למאגר")
    @app_commands.describe(idol_name="שם האליל", idol_tribe="השבט של האליל")
    async def add_idol(self, interaction: discord.Interaction, idol_name: str, idol_tribe: str):
        class IdolImageModal(discord.ui.Modal):
            idol_image_url = discord.ui.TextInput(label="נתיב לתמונת האליל", placeholder="הזן את הנתיב לתמונת האליל",
                                                  required=True)

            def __init__(self, cog, interaction, idol_name, idol_tribe):
                super().__init__(title="הזן את נתיב לתמונת האליל")
                self.cog = cog
                self.interaction = interaction
                self.idol_name = idol_name
                self.idol_tribe = idol_tribe

            async def on_submit(self, modal_interaction: discord.Interaction):
                idol_image_path = self.idol_image_url.value
                found = False

                # Read the image file
                try:
                    file = discord.File(idol_image_path, filename="idol_image.png")
                except FileNotFoundError:
                    await modal_interaction.response.send_message("הקובץ לא נמצא. אנא נסה שוב.", ephemeral=True)
                    return

                idol_image_url = "attachment://idol_image.png"

                await self.cog.add_idol_to_channel(modal_interaction.guild, self.idol_name, self.idol_tribe,
                                                   idol_image_path, found)

                tribe_color = await self.cog.get_tribe_color_by_name(modal_interaction.guild, self.idol_tribe)

                embed = discord.Embed(
                    title="האליל נוסף",
                    description=f"אליל בשם {self.idol_name} מהשבט {self.idol_tribe} נוסף בהצלחה.",
                    color=tribe_color
                )
                embed.set_image(url=idol_image_url)
                await modal_interaction.response.send_message(file=file, embed=embed, ephemeral=True)

                log_channel = modal_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(file=file, embed=embed)

        modal = IdolImageModal(self, interaction, idol_name, idol_tribe)
        await interaction.response.send_modal(modal)


async def setup(bot):
    await bot.add_cog(PlayerManagement(bot))