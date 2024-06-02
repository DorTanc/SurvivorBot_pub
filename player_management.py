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
database_chips_channel_id = 1245695980058316840
database_idol_channel_id = 1244710921482535042
database_menu_channel_id = 1246080834184810527

# Custom Modal Classes

class PlayerSelect(discord.ui.Select):
    def __init__(self, players_list, callback):
        self.dynamic_callback = callback
        options = [discord.SelectOption(label=player_name, value=player_name) for player_name in players_list if player_name]
        super().__init__(placeholder="בחר שחקן", min_values=1, max_values=1, options=options)

    async def callback(self, select_interaction: discord.Interaction):
        selected_player = self.values[0]
        await self.dynamic_callback(select_interaction, selected_player)
        if select_interaction.message:
            await select_interaction.message.delete()

class PlayerMultiSelect(discord.ui.Select):
    def __init__(self, players_list, callback):
        self.dynamic_callback = callback
        options = [discord.SelectOption(label=player_name, value=player_name) for player_name in players_list if player_name]
        super().__init__(placeholder="בחר שחקנים", min_values=1, max_values=len(players_list), options=options)

    async def callback(self, select_interaction: discord.Interaction):
        selected_players = self.values
        await self.dynamic_callback(select_interaction, selected_players)
        if select_interaction.message:
            await select_interaction.message.delete()

class TribeSelect(discord.ui.Select):
    def __init__(self, tribe_list, callback):
        self.dynamic_callback = callback
        options = [discord.SelectOption(label=tribe, value=tribe) for tribe in tribe_list if tribe]
        super().__init__(placeholder="בחר שבט", min_values=1, max_values=1, options=options)

    async def callback(self, select_interaction: discord.Interaction):
        selected_tribe = self.values[0]
        await self.dynamic_callback(select_interaction, selected_tribe)
        if select_interaction.message:
            await select_interaction.message.delete()

class AdvantageSelect(discord.ui.Select):
    def __init__(self, advantage_list, callback):
        self.dynamic_callback = callback
        options = [discord.SelectOption(label=advantage, value=advantage) for advantage in advantage_list]
        super().__init__(placeholder="בחר יתרון", min_values=1, max_values=1, options=options)

    async def callback(self, select_interaction: discord.Interaction):
        selected_advantage = self.values[0]
        await self.dynamic_callback(select_interaction, selected_advantage)
        if select_interaction.message:
            await select_interaction.message.delete()

class RoleSelect(discord.ui.Select):
    def __init__(self, callback):
        self.dynamic_callback = callback
        options = [discord.SelectOption(label="מושבע"),discord.SelectOption(label="מודח")]
        super().__init__(placeholder="בחר תפקיד", min_values=1, max_values=1, options=options)

    async def callback(self, select_interaction: discord.Interaction):
        selected_role = self.values[0]
        await self.dynamic_callback(select_interaction, selected_role)
        if select_interaction.message:
            await select_interaction.message.delete()

class ChipsAmount(discord.ui.Modal):
    amount = discord.ui.TextInput(label="מספר צ'יפים", placeholder="בחר כמות צ'יפים", min_length=1, max_length=5, required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="בחר כמות צ'יפים")

    async def on_submit(self, modal_interaction: discord.Interaction):
        amount = int(self.amount.value)
        try:
            if amount <= 0:
                raise ValueError("מספר הצ'יפים חייב להיות חיובי.")
        except ValueError:
            await modal_interaction.response.send_message("מספר צ'יפים לא תקין. אנא נסה שוב.", ephemeral=True)
            return
        await self.dynamic_callback(modal_interaction, amount)

class IdolGuess(discord.ui.Modal):
    guessed_name = discord.ui.TextInput(label="נחש את שם האליל", placeholder="הזן את שם האליל", required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="נחש את שם האליל")

    async def on_submit(self, modal_interaction: discord.Interaction):
        guessed_name = self.guessed_name.value
        await self.dynamic_callback(modal_interaction, guessed_name)

class PlayerManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Helper Commands

    async def is_in_correct_channel(self, interaction):
        player_display_name = interaction.user.display_name.lower()
        player_game_channel_name = f"{player_display_name.replace(' ', '-')}-משחק"
        current_channel_name = interaction.channel.name.lower()
        player_game_channel = discord.utils.get(interaction.guild.text_channels, name=player_game_channel_name)
        return current_channel_name == player_game_channel_name, player_game_channel

    async def check_alliance_duplicates(self, guild, selected_players):
        data = await self.fetch_players(guild)
        player_list = [player[1] for player in data]
        alliance_categories = [category for category in guild.categories if 'בריתות' in category.name]
        for category in alliance_categories:
            for channel in category.text_channels:
                alliance_members = [member.display_name for member in channel.members if member.display_name in player_list]
                if set(alliance_members) == set(selected_players):
                    return channel
        return False

    async def create_alliance_channels(self, guild, category_name, alliance_name, selected_players):
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            category = await guild.create_category(category_name, overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False, view_channel=False)
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

        for player_name in selected_players:
            role = discord.utils.get(guild.roles, name=player_name)
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
    
    # Get tribe data

    async def fetch_tribes(self, guild):
        database_tribes_channel = guild.get_channel(database_tribes_channel_id)
        tribes = []
        async for message in database_tribes_channel.history(limit=None):
            tribes.append(message.content.split(','))
        return tribes

    async def get_tribe_color(self, guild, tribe_name):
        database_tribes_channel = guild.get_channel(database_tribes_channel_id)
        async for message in database_tribes_channel.history(limit=None):
            tribe, color_hex = message.content.split(',')
            if tribe == tribe_name:
                return discord.Color(int(color_hex.lstrip('#'), 16))
        return discord.Color.default()

    async def get_tribe_members(self, guild, tribe_name):
        players = await self.fetch_players(guild)
        # restructure the list into a dictionary of player/tribe pairs
        players_data = {row[1]: row[2] for row in players}
        members_list = [player for player, tribe in players_data.items() if tribe == tribe_name]
        return members_list

    async def is_tribe_overlap(self, guild, players_list):
        data = await self.fetch_players(guild)
        # filter data of selected players
        relevant_data = [row for row in data if any(player_name in row for player_name in players_list)]
        # create set of tribes and check amount of unique tribes
        relevant_tribes = {row[2] for row in relevant_data} 
        if len(relevant_tribes) == 1:
            return relevant_tribes.pop()
        else: return False

    # Player management

    async def add_player_to_database(self, guild, user_id, player_name, tribe_name):
        database_players_channel = guild.get_channel(database_players_channel_id)
        await database_players_channel.send(f"{user_id},{player_name},{tribe_name}")
        database_chips_channel = guild.get_channel(database_chips_channel_id)
        await database_chips_channel.send(f"{player_name},0")
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        await database_advantages_channel.send(f"{player_name}")

    async def remove_player_from_database(self, guild, player_name):
        # Remove from player database
        database_players_channel = guild.get_channel(database_players_channel_id)
        async for msg in database_players_channel.history(limit=None):
            if msg.content.split(',')[1] == player_name:
                await msg.delete()
                break
        # Remove from chips database
        database_chips_channel = guild.get_channel(database_chips_channel_id)
        async for msg in database_chips_channel.history(limit=None):
            if msg.content.split(',')[0] == player_name:
                await msg.delete()
                break
        # Remove from advantages database
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        async for msg in database_advantages_channel.history(limit=None):
            if msg.content.split(',')[0] == player_name:
                await msg.delete()
                break

    async def fetch_players(self, guild):
        database_players_channel = guild.get_channel(database_players_channel_id)
        players = []
        async for message in database_players_channel.history(limit=None):
            players.append(message.content.split(','))
        return players

    async def get_player_tribe(self, guild, player_name):
        players = await self.fetch_players(guild)
        players_data = next((row for row in players if row[1].lower() == player_name.lower()))
        # return the tribe name (third element in the row)
        return players_data[2]
    
    async def get_player_chips(self, guild, player_name):
        chips = await self.fetch_chips(guild)
        player_chips = next((row for row in chips if row[0].lower() == player_name.lower()))
        # return the number of chips (second element in the row)
        chips_number = player_chips[1]
        return int(chips_number)
    
    async def get_player_advantages(self, guild, player_name):
        advantages = await self.fetch_advantages(guild)
        player_advantages = next((row for row in advantages if row[0].lower() == player_name.lower()))
        # return list of advantage names (remove first element)
        player_advantages.pop(0)
        return player_advantages

    async def get_player_tribe_color(self, guild, player):
        player_tribe = await self.get_player_tribe(guild, player)
        tribe_color = await self.get_tribe_color(guild, player_tribe)
        return tribe_color

    # Chips management

    async def fetch_chips(self, guild):
        database_chips_channel = guild.get_channel(database_chips_channel_id)
        chips = []
        async for message in database_chips_channel.history(limit=None):
            chips.append(message.content.split(','))
        return chips

    async def update_chips(self, guild, player, new_amount):
        database_chips_channel = guild.get_channel(database_chips_channel_id)
        # search for the corresponding message
        async for msg in database_chips_channel.history(limit=None):
            list = msg.content.split(',')
            if list[0] == player:
                message = msg
                break
        await message.edit(content=f"{player},{new_amount}")

    async def complete_chips_transfer(self, interaction, amount, target_player):
        user_name = interaction.user.display_name
        user_chips = await self.get_player_chips(interaction.guild, user_name)
        target_chips = await self.get_player_chips(interaction.guild, target_player)

        new_amount_user = user_chips - amount
        new_amount_target = target_chips + amount

        # update amounts for both players
        await self.update_chips(interaction.guild, user_name, new_amount_user)
        await self.update_chips(interaction.guild, target_player, new_amount_target)

        # confirmation to transferring player
        embed = discord.Embed(
            title="",
            description=f"העברת {amount} צ'יפים ל{target_player}\n נשארו לך {new_amount_user} צ'יפים",
            color=await self.get_player_tribe_color(interaction.guild, user_name)
        )
        file = discord.File("chips.png", filename="chips.png")
        embed.set_image(url="attachment://chips.png")
        await interaction.response.send_message(file=file, embed=embed, ephemeral=False)

        # confirmation to target player
        target_channel_name = f"{target_player.replace(' ', '-').lower()}-משחק"
        target_channel = discord.utils.get(interaction.guild.text_channels, name=target_channel_name)
        if target_channel:
            embed = discord.Embed(
                title="מזל טוב!",
                description=f"קיבלת {amount} צ'יפים מ{user_name}\n עכשיו יש לך {new_amount_target} צ'יפים",
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
                description=f"{user_name} העביר {amount} צ'יפים ל {target_player}\nל {user_name} יש עכשיו {new_amount_user} צ'יפים\nל {target_player} יש עכשיו {new_amount_target} צ'יפים",
                color=await self.get_player_tribe_color(interaction.guild, user_name)
            )
            file = discord.File("chips.png", filename="chips.png")
            embed.set_image(url="attachment://chips.png")
            await log_channel.send(file=file, embed=embed)

    # Advantage management

    async def fetch_advantages(self, guild):
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        advantages = []
        async for message in database_advantages_channel.history(limit=None):
            advantages.append(message.content.split(','))
        return advantages

    async def remove_advantage(self, guild, player, advantage):
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        # search for the corresponding message
        async for msg in database_advantages_channel.history(limit=None):
            list = msg.content.split(',')
            if list[0] == player:
                message = msg
                break
        list = message.content.split(',')
        list.remove(advantage)
        await message.edit(content=f",".join(list))

    async def add_advantage(self, guild, player, advantage):
        database_advantages_channel = guild.get_channel(database_advantages_channel_id)
        # search for the corresponding message
        async for msg in database_advantages_channel.history(limit=None):
            list = msg.content.split(',')
            if list[0] == player:
                message = msg
                break
        list = message.content.split(',')
        list.append(advantage)
        await message.edit(content=f",".join(list))

    async def complete_advantage_transfer(self, interaction, selected_advantage, target_player):
        user_name = interaction.user.display_name
        filename = "advantage.png"
        adv_type = "יתרון"
        # check if the advantage was an idol
        idols = await self.fetch_idols(interaction.guild)
        is_idol = any(selected_advantage in row for row in idols)
        if is_idol:
            filename = await self.get_idol_image(interaction.guild, selected_advantage)
            adv_type = "אליל"

        # remove advantage from player and add it to target player
        await self.remove_advantage(interaction.guild, user_name, selected_advantage)
        await self.add_advantage(interaction.guild, target_player, selected_advantage)

        # confirmation to transferring player
        embed = discord.Embed(
            title="",
            description=f"העברת {adv_type} בשם {selected_advantage} ל {target_player}",
            color=await self.get_player_tribe_color(interaction.guild, user_name)
        )
        file = discord.File(filename, filename=filename)
        embed.set_image(url=f"attachment://{filename}")
        await interaction.response.send_message(file=file, embed=embed, ephemeral=False)

        # confirmation to target player
        target_channel_name = f"{target_player.replace(' ', '-').lower()}-משחק"
        target_channel = discord.utils.get(interaction.guild.text_channels, name=target_channel_name)
        if target_channel:
            embed = discord.Embed(
                title="מזל טוב!",
                description=f"קיבלת {adv_type} בשם {selected_advantage} מ-{user_name}",
                color=await self.get_player_tribe_color(interaction.guild, target_player)
            )
            file = discord.File(filename, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
            await target_channel.send(file=file, embed=embed)

        # log transfer
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="",
                description=f"השחקן {user_name} העביר {adv_type} בשם {selected_advantage} ל {target_player}",
                color=await self.get_player_tribe_color(interaction.guild, user_name)
            )
            file = discord.File(filename, filename=filename)
            embed.set_image(url=f"attachment://{filename}")
            await log_channel.send(file=file, embed=embed)
    
    # Idol management

    async def fetch_idols(self, guild):
        database_idol_channel = guild.get_channel(database_idol_channel_id)
        idols = []
        async for message in database_idol_channel.history(limit=None):
            idols.append(message.content.split(','))
        return idols

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

    async def get_idol_name(self, guild, tribe_name):
        idols = await self.fetch_idols(guild)
        idol_data = next((row for row in idols if row[1].lower() == tribe_name.lower()))
        return idol_data[0]

    async def get_idol_tribe(self, guild, idol_name):
        idols = await self.fetch_idols(guild)
        idol_data = next((row for row in idols if row[0].lower() == idol_name.lower()))
        return idol_data[1]

    async def get_idol_image(self, guild, idol_name):
        idols = await self.fetch_idols(guild)
        idol_data = next((row for row in idols if row[0].lower() == idol_name.lower()))
        return idol_data[2]

    async def get_idol_status(self, guild, idol_name):
        idols = await self.fetch_idols(guild)
        idol_data = next((row for row in idols if row[0].lower() == idol_name.lower()))
        return idol_data[3]

    # Menu management

    async def fetch_menu(self, guild):
        database_menu_channel = guild.get_channel(database_menu_channel_id)
        items = []
        async for message in database_menu_channel.history(limit=None):
            items.append(message.content.split(','))
        return items

    async def get_item_price(self, guild, item_name):
        menu = await self.fetch_menu(guild)
        menu_data = next((row for row in menu if row[0].lower() == item_name.lower()))
        return int(menu_data[1])
    
    async def get_item_amount(self, guild, item_name):
        menu = await self.fetch_menu(guild)
        menu_data = next((row for row in menu if row[0].lower() == item_name.lower()))
        return int(menu_data[2])

    async def get_item_image(self, guild, item_name):
        menu = await self.fetch_menu(guild)
        menu_data = next((row for row in menu if row[0].lower() == item_name.lower()))
        return menu_data[3]

    async def update_menu(self, guild, item_name, new_amount):
        database_menu_channel = guild.get_channel(database_menu_channel_id)
        # search for the corresponding message
        async for msg in database_menu_channel.history(limit=None):
            list = msg.content.split(',')
            if list[0] == item_name:
                message = msg
                break
        item_details = message.content.split(',')
        item_details[2] = str(new_amount)
        await message.edit(content=','.join(item_details))

    # Player commands

    @app_commands.command(name="show_players", description="מציג רשימה של כל השחקנים.")
    async def show_players(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return
        tribes = await self.fetch_tribes(interaction.guild)
        tribe_list = [row[0] for row in tribes]
        embeds = []

        await interaction.response.defer()

        for tribe in tribe_list:
            members_list = ""
            members = await self.get_tribe_members(interaction.guild, tribe)
            for player in members:
                members_list += f"{player}\n"
            embed = discord.Embed(
                title=f"שבט {tribe}",
                description=f"{members_list}",
                color=await self.get_tribe_color(interaction.guild, tribe)
            )
            embeds.append(embed)

        await interaction.followup.send(embeds=embeds)

    @app_commands.command(name="alliance", description="יצירת ברית חדשה, ערוץ טקסט וערוץ קול עבור הברית.")
    @app_commands.describe(alliance_name="שם הברית (אופציונלי)")
    async def create_alliance(self, interaction: discord.Interaction, alliance_name: Optional[str] = None):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return
        
        players = await self.fetch_players(interaction.guild)
        player_name = interaction.user.display_name
        players_list = [player[1] for player in players if player[1] != player_name]

        # define what happens upon selection
        async def create_alliance_callback(select_interaction: discord.Interaction, selected_players):
            await select_interaction.response.defer()
            guild = select_interaction.guild
            selected_players.append(player_name)

            # set alliance name
            if not alliance_name:
                alliance_name_generated = "-".join(selected_players)
            else:
                alliance_name_generated = alliance_name

            # check that selection is valid (why?)
            if not selected_players:
                await select_interaction.followup.send("אחד או יותר מהשחקנים שנבחרו אינם תקפים.", ephemeral=True)
                return

            # set alliance category
            common_tribe =  await self.is_tribe_overlap(guild, selected_players)
            if common_tribe:
                category_name = f"{common_tribe} - בריתות"
            else:
                category_name = "בריתות בין שבטיות"

            # check for duplicates
            duplicate = await self.check_alliance_duplicates(guild, selected_players)
            if  duplicate:
                await select_interaction.followup.send(f"כבר קיים ערוץ ברית לקבוצת השחקנים שבחרת בשם {duplicate.mention}", ephemeral=True)
                return

            # create alliance
            alliance_name_final = await self.create_alliance_channels(guild, category_name, alliance_name_generated, selected_players)
            embed = discord.Embed(
                title="הברית נוצרה",
                description=f"הברית {alliance_name_final} נוצרה בהצלחה.",
                color=await self.get_player_tribe_color(guild, player_name)
            )
            await select_interaction.followup.send(embed=embed, ephemeral=True)
            await self.send_alliance_log(guild, alliance_name_final, selected_players)

        if players_list:
            view = discord.ui.View()
            view.add_item(PlayerMultiSelect(players_list, create_alliance_callback))
            await interaction.response.defer()
            await interaction.followup.send("בחר שחקנים לברית:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("אין שחקנים זמינים לברית.")

    @app_commands.command(name="show_chips", description=".מציג את כמות הצ'יפים שלך (זמין רק בערוץ המשחק)")
    async def show_chips(self, interaction: discord.Interaction):
        # Check if the command is used in the player's private game channel
        in_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not in_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return

        # Get the player's chip
        player_display_name = interaction.user.display_name
        chips_numer = await self.get_player_chips(interaction.guild, player_display_name)

        # Create and send the embed message
        embed = discord.Embed(
            title="",
            description=f"יש לך {chips_numer} צ'יפים",
            color= await self.get_player_tribe_color(interaction.guild, player_display_name)
        )
        file = discord.File("chips.png", filename="chips.png")
        embed.set_image(url="attachment://chips.png")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name="transfer_chips", description="מעביר צ'יפים משחקן אחד לאחר.")
    async def transfer_chips(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return

        # check if player has any chips
        player_name = interaction.user.display_name
        player_chips = await self.get_player_chips(interaction.guild, player_name)
        if player_chips == 0:
            embed = discord.Embed(
            title="",
            description="אין לך צ'יפים להעביר.",
            color= await self.get_player_tribe_color(interaction.guild, player_name)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # define what happens upon amount submission
        async def transfer_chips_callback(modal_interaction: discord.Interaction, chips_amount):
            # check if player has enough chips
            if chips_amount > player_chips:
                embed = discord.Embed(
                title="",
                description="אין לך מספיק צ'יפים להעביר.",
                color= await self.get_player_tribe_color(modal_interaction.guild, player_name)
                )
                await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                return

            players = await self.fetch_players(modal_interaction.guild)
            players_list = [player[1] for player in players if player[1] != player_name]
            
            # define what happens upon selection
            async def transfer_chips_callback2(select_interaction: discord.Interaction, selected_player):
                await self.complete_chips_transfer(select_interaction, chips_amount, selected_player)

            view = discord.ui.View()
            view.add_item(PlayerSelect(players_list, transfer_chips_callback2))
            await modal_interaction.response.send_message("בחר שחקן להעברה:", view=view, ephemeral=False)

        await interaction.response.send_modal(ChipsAmount(transfer_chips_callback))

    @app_commands.command(name="transfer_advantage", description="מעביר יתרון משחקן אחד לאחר.")
    async def transfer_advantage(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}",ephemeral=True)
            return

        user_name = interaction.user.display_name
        advantages_list_with_clues = await self.get_player_advantages(interaction.guild, user_name)
        # filter clues since they can't be transferred
        advantages_list = [adv for adv in advantages_list_with_clues if "רמז" not in adv]
        
        # confirm user has any advantages
        if not advantages_list:
            await interaction.response.send_message("אין לך יתרונות להעביר.", ephemeral=True)
            return
        
        # define what happens upon advantage selection
        async def transfer_advantage_callback(select_interaction: discord.Interaction, selected_advantage):
            players = await self.fetch_players(select_interaction.guild)
            players_list = [player[1] for player in players if player[1] != user_name]

            # define what happens upon player selection
            async def transfer_advantage_callback2(select_interaction: discord.Interaction, selected_player):
                await self.complete_advantage_transfer(select_interaction, selected_advantage, selected_player)

            view = discord.ui.View()
            view.add_item(PlayerSelect(players_list, transfer_advantage_callback2))
            await select_interaction.response.send_message("בחר שחקן להעברה:", view=view, ephemeral=False)

        view = discord.ui.View()
        view.add_item(AdvantageSelect(advantages_list, transfer_advantage_callback))
        await interaction.response.send_message("בחר יתרון להעברה:", view=view, ephemeral=False)

    @app_commands.command(name="buy_advantage", description="קונה יתרון מהתפריט.")
    async def buy_advantage(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return
        
        menu = await self.fetch_menu(interaction.guild)
        player_name = interaction.user.display_name
        player_tribe = await self.get_player_tribe(interaction.guild, player_name)
        player_advantages = await self.get_player_advantages(interaction.guild, player_name)
        player_clues = [adv for adv in player_advantages if "רמז" in adv]
        items_list = [row[0] for row in menu if "רמז" not in row[0]]
        clue_list = [row[0] for row in menu if "רמז" in row[0]]
        # filter unavailable clues
        try:
            clue = next(clue for clue in clue_list if player_tribe in clue and str(len(player_clues)+1) in clue)
        except StopIteration:
            clue = None
        # alias the clue's name to hide its number
        clue_alias = "רמז לאליל החסינות"
        items_list.append(clue_alias)

        # define what happens upon selection
        async def buy_advantage_callback(select_interaction: discord.Interaction, selected_item):
            # reveal true number of clue if bought
            if selected_item == clue_alias:
                selected_item = clue
                # if no available clue
                if not clue:
                    embed = discord.Embed(
                        title="אוי לא!",
                        description="כבר קנית את כל הרמזים לאליל בשבט שלך. פנה למנהלים ובקש שיכינו רמז נוסף\nלאחר מכן תוכל לנסות לקנות רמז שוב",
                        color=discord.Color.red()
                    )
                    await select_interaction.response.send_message(embed=embed, ephemeral=False)
                    return
            user_chips = await self.get_player_chips(select_interaction.guild, player_name)
            price = await self.get_item_price(select_interaction.guild, selected_item)
            amount = await self.get_item_amount(select_interaction.guild, selected_item)
            image = await self.get_item_image(select_interaction.guild, selected_item)
            file = discord.File(image, filename=image)
            
            # check if user has enough chips
            if price > user_chips:
                embed = discord.Embed(
                    title="אוי לא!",
                    description="אין לך מספיק צ'יפים כדי לקנות את היתרון הזה.",
                    color=discord.Color.red()
                )
                await select_interaction.response.send_message(embed=embed, ephemeral=False)
                return

            # check if advantage still available in menu
            if amount == 0:
                embed = discord.Embed(
                    title="אוי לא!",
                    description="היתרון שבחרת אזל במלאי, נסה לבחור יתרון אחר",
                    color=discord.Color.red()
                )
                await select_interaction.response.send_message(embed=embed, ephemeral=False)
                return

            # confirm purchase to buyer
            embed = discord.Embed(
                title="תתחדש!",
                description=f"קנית את היתרון {selected_item} בהצלחה. אחרי הקנייה נשארו לך {user_chips - price} צ'יפים",
                color=await self.get_player_tribe_color(select_interaction.guild, player_name)
                )
            embed.set_image(url=f"attachment://{image}")
            await select_interaction.response.send_message(file=file, embed=embed, ephemeral=False)
            
            # log purchase
            log_channel = select_interaction.guild.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="קנייה התבצעה",
                    description=f"{player_name} קנה {selected_item}\nאחרי הקנייה נשארו לו/לה {user_chips - price} צ'יפים",
                    color=await self.get_player_tribe_color(select_interaction.guild, player_name)
                )
                embed.set_image(url=f"attachment://{image}")
                await log_channel.send(file=file, embed=embed)

            # update menu, remove chips from player and add advantage to player
            await self.update_menu(select_interaction.guild, selected_item, amount - 1)
            await self.update_chips(select_interaction.guild, player_name, user_chips - price)
            await self.add_advantage(select_interaction.guild, player_name, selected_item)

        view = discord.ui.View()
        view.add_item(AdvantageSelect(items_list, buy_advantage_callback))
        await interaction.response.send_message("בחר יתרון שברצונך לקנות:", view=view, ephemeral=False)

    @app_commands.command(name="find_idol", description="מחפש את האליל בשבט שלך.")
    async def find_idol(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            await interaction.response.send_message(f"הפקודה עובדת רק בערוץ {player_game_channel.mention}", ephemeral=True)
            return
        
        player_name = interaction.user.display_name
        tribe = await self.get_player_tribe(interaction.guild, player_name)
        if not tribe:
            await interaction.response.send_message("שגיאה: לא נמצא שבט לשחקן.", ephemeral=True)
            return
        
        # define what happens upon guess submission
        async def find_idol_callback(modal_interaction: discord.Interaction, guessed_name):
            # check if guessed name is correct and idol isn't found
            idol_name = await self.get_idol_name(modal_interaction.guild, tribe)
            idol_status = await self.get_idol_status(modal_interaction.guild, idol_name)
            if idol_name == guessed_name and idol_status == "False":

                # update status and add idol to player's advantages
                await self.update_idol_status(modal_interaction.guild, idol_name, True)
                await self.add_advantage(modal_interaction.guild, player_name, idol_name)
                
                # inform player that they found the idol
                filename = await self.get_idol_image(modal_interaction.guild, idol_name)
                file = discord.File(filename, filename=filename)
                embed = discord.Embed(
                    title="מזל טוב!",
                    description=f"מצאת את האליל {idol_name} של שבט {tribe}.",
                    color= await self.get_player_tribe_color(interaction.guild, player_name)
                )
                embed.set_image(url=f"attachment://{filename}")
                await modal_interaction.response.send_message(file=file, embed=embed, ephemeral=False)

                # Send a log message
                log_channel = modal_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    log_embed = discord.Embed(
                        title="אליל נמצא",
                        description=f"{player_name} מצא את האליל {idol_name} של שבט {tribe}.",
                        color= await self.get_player_tribe_color(interaction.guild, player_name)
                    )
                    log_embed.set_image(url=f"attachment://{filename}")
                    await log_channel.send(file=file, embed=log_embed)
            else:
                # inform player their guess was wrong or idol already found
                embed = discord.Embed(
                    title="חיפוש נכשל",
                    description="השם שהזנת אינו נכון, או שהאליל כבר נמצא על ידי שחקן אחר.",
                    color=discord.Color.red()
                )
                await modal_interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_modal(IdolGuess(find_idol_callback))

    @app_commands.command(name="commands", description="מציג רשימת פקודות לשחקנים")
    async def show_commands(self, interaction: discord.Interaction):
        embed = discord.Embed(
                    title=f"\u202Bפקודות לשחקנים:",
                    description=f"",
                    color=discord.Color.from_rgb(r=255,g=255,b=255)
                )
        embed.add_field(name="/show_players", value='\u202Bמציג רשימה של כל השחקנים', inline=False)
        embed.add_field(name="/alliance [שם ברית]", value="\u202Bיצירת ברית חדשה, ערוץ טקסט וערוץ קול עבור הברית.", inline=False)
        embed.add_field(name="/show_chips", value="\u202Bמציג את כמות הצ'יפים שלך.", inline=False)
        embed.add_field(name="/transfer_chips", value="\u202Bמעביר צ'יפים לשחקן אחר.", inline=False)
        embed.add_field(name="/transfer_advantage", value="\u202Bמעביר אליל או יתרון לשחקן אחר.", inline=False)
        embed.add_field(name="/buy_advantage", value="\u202Bקונה יתרון מהתפריט.", inline=False)
        embed.add_field(name="/find_idol", value="\u202Bפותח חלון לחיפוש האליל, שבו יש להזין את שם המפורסם.", inline=False)
        
        await interaction.response.send_message(embed=embed)

# Host-only commands

    @app_commands.command(name="players_data", description="מציג רשימה של כל השחקנים, מספר הצ'יפים והיתרונות שלהם.")
    @commands.has_role('Host')
    async def players_data(self, interaction: discord.Interaction):
        tribes = await self.fetch_tribes(interaction.guild)
        tribe_list = [row[0] for row in tribes]
        embeds = []

        await interaction.response.defer()

        for tribe in tribe_list:
            embed = discord.Embed(
                title=f"שבט {tribe}",
                description=f"",
                color=await self.get_tribe_color(interaction.guild, tribe)
            )
            members = await self.get_tribe_members(interaction.guild, tribe)
            for player in members:
                advantages = await self.get_player_advantages(interaction.guild, player)
                advantages_str = ", ".join([f"{adv}" for adv in advantages])
                chips = await self.get_player_chips(interaction.guild, player)
                embed.add_field(name=f"{player}", value=f"צ'יפים: {str(chips)}, יתרונות: {advantages_str if advantages_str else 'אין'}", inline=False)
            embeds.append(embed)

        if embeds:
            await interaction.followup.send(embeds=embeds)
        else:
            await interaction.followup.send("אין שחקנים רשומים כרגע.")

    @app_commands.command(name="add_player", description="מוסיף שחקן חדש ומקצה לו תפקיד ושבט.")
    @app_commands.describe(player_name="שם השחקן להוספה")
    @commands.has_role('Host')
    async def add_player(self, interaction: discord.Interaction, player_name: str):
        tribes = await self.fetch_tribes(interaction.guild)
        tribe_list = [row[0] for row in tribes]

        # define what happens upon selection
        async def add_player_callback(select_interaction: discord.Interaction, selected_tribe):
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
                tribe_role = discord.utils.get(select_interaction.guild.roles, name=selected_tribe)
                await member.add_roles(role, tribe_role)

                await self.add_player_to_database(select_interaction.guild, user_id, player_name, selected_tribe)

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

                # Confirm the addition of the player
                await select_interaction.followup.send(f"השחקן {player_name} נוסף בהצלחה לשבט {selected_tribe}.", ephemeral=True)

                # Log the addition of the player
                log_channel = select_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="הוספת שחקן",
                        description=f"השחקן {player_name} נוסף בהצלחה לשבט {selected_tribe}.",
                        color= await self.get_player_tribe_color(select_interaction.guild, player_name)
                    )
                    await log_channel.send(embed=embed)

            except Exception as e:
                await select_interaction.followup.send(f"שגיאה התרחשה: {str(e)}")

        if tribe_list:
            view = discord.ui.View()
            view.add_item(TribeSelect(tribe_list, add_player_callback))
            await interaction.response.send_message("בחר שבט לשחקן:", view=view)
        else:
            await interaction.response.send_message("אין שבטים זמינים.")

    @app_commands.command(name="change_tribe", description="מעביר שחקן לשבט חדש")
    @commands.has_role('Host')
    async def change_tribe(self, interaction: discord.Interaction):
        players = await self.fetch_players(interaction.guild)
        players_list = [row[1] for row in players]

        # define what happens upon player selection
        async def change_tribe_callback(select_interaction: discord.Interaction, selected_player):
            # remove clues from old tribe from player's advantages
            player_advantages = await self.get_player_advantages(interaction.guild, selected_player)
            player_old_tribe = await self.get_player_tribe(interaction.guild, selected_player)
            old_clues = [adv for adv in player_advantages if "רמז" in adv and player_old_tribe in adv]
            for clue in old_clues:
                await self.remove_advantage(interaction.guild, selected_player, clue)

            tribes = await self.fetch_tribes(interaction.guild)
            tribe_list = [row[0] for row in tribes if row[0] != player_old_tribe]

            # define what happens upon tribe selection
            async def change_tribe_callback2(select_interaction: discord.Interaction, selected_tribe):
                database_players_channel = interaction.guild.get_channel(database_players_channel_id)
                old_tribe = ""
                user = None
                async for message in database_players_channel.history(limit=None):
                    if selected_player in message.content:
                        player_data = message.content.split(',')
                        if player_data[1].lower() != selected_player.lower():
                            continue
                        old_tribe = player_data[2]
                        player_data[2] = selected_tribe
                        await message.edit(content=','.join(player_data))

                        # Fetch the user by their ID
                        user_id = int(player_data[0])
                        user = interaction.guild.get_member(user_id)

                if user:
                    # Get the current tribe roles and the new tribe role
                    current_roles = [role for role in user.roles if old_tribe in role.name]
                    new_tribe_role = discord.utils.get(interaction.guild.roles, name=selected_tribe)

                    # Remove current tribe roles
                    if current_roles:
                        await user.remove_roles(*current_roles)

                    # Add the new tribe role
                    if new_tribe_role:
                        await user.add_roles(new_tribe_role)

                    # confirm change
                    embed = discord.Embed(
                        title="מעבר שבט",
                        description=f"{selected_player} עבר לשבט {selected_tribe}.",
                        color=await self.get_tribe_color(interaction.guild, selected_tribe)
                    )
                    await select_interaction.response.send_message(embed=embed, ephemeral=True)

                    # log change
                    log_channel = interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(embed=embed)
            
            view = discord.ui.View()
            view.add_item(TribeSelect(tribe_list, change_tribe_callback2))
            await select_interaction.response.send_message("בחר שבט חדש לשחקן", view=view, ephemeral=True)

        view = discord.ui.View()
        view.add_item(PlayerSelect(players_list, change_tribe_callback))
        await interaction.response.send_message("בחר שחקן שיעבור שבט:", view=view, ephemeral=True)

    @app_commands.command(name="add_chips", description="מוסיף צ'יפים לשחקן נבחר")
    @commands.has_role('Host')
    async def add_chips(self, interaction: discord.Interaction):
        players = await self.fetch_players(interaction.guild)
        players_list = [row[1] for row in players]

        # define what happens upon selection
        async def add_chips_callback(select_interaction: discord.Interaction, selected_player):
            
            # define what happens upon amount submission
            async def add_chips_callback2(modal_interaction: discord.Interaction, chips_amount):
                # update chip database
                current_amount = await self.get_player_chips(interaction.guild, selected_player)
                new_amount = current_amount + chips_amount
                await self.update_chips(interaction.guild, selected_player, new_amount)
                await modal_interaction.response.send_message(f"נוספו {chips_amount} צ'יפים לשחקן {selected_player}.", ephemeral=True)

                # Send an embed message to the player's private channel
                player_channel_name = f"{selected_player.replace(' ', '-')}-משחק".lower()
                player_channel = discord.utils.get(interaction.guild.text_channels, name=player_channel_name)
                if player_channel:
                    player_embed = discord.Embed(
                        title="מזל טוב!",
                        description=f"נוספו לך {chips_amount} צ'יפים\nעכשיו יש לך {new_amount} צ'יפים",
                        color=await self.get_player_tribe_color(interaction.guild, selected_player)
                    )
                    file = discord.File("chips.png", filename="chips.png")
                    player_embed.set_image(url="attachment://chips.png")
                    await player_channel.send(file=file, embed=player_embed)

                # Log the addition
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="הוספת צ'יפים",
                        description=f"נוספו {chips_amount} צ'יפים ל {selected_player}\nל {selected_player} יש עכשיו {new_amount} צ'יפים",
                        color=await self.get_player_tribe_color(interaction.guild, selected_player)
                    )
                    file = discord.File("chips.png", filename="chips.png")
                    embed.set_image(url="attachment://chips.png")
                    await log_channel.send(file=file, embed=embed)

            await select_interaction.response.send_modal(ChipsAmount(add_chips_callback2))

        if players:
            view = discord.ui.View()
            view.add_item(PlayerSelect(players_list, add_chips_callback))
            await interaction.response.send_message("בחר שחקן שיקבל את הצ'יפים:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("אין שחקנים זמינים.", ephemeral=True)

    @app_commands.command(name="give_advantage", description="מוסיף יתרון לשחקן נבחר")
    @app_commands.describe(advantage_name="שם היתרון")
    @commands.has_role('Host')
    async def give_advantage(self, interaction: discord.Interaction, advantage_name: str):
        players = await self.fetch_players(interaction.guild)
        players_list = [row[1] for row in players]

        # define what happens upon selection
        async def give_advantage_callback(select_interaction: discord.Interaction, selected_player):
            filename = "advantage.png"

            # update advantage database
            await self.add_advantage(interaction.guild, selected_player, advantage_name)
            await select_interaction.response.send_message(f"השחקן {selected_player} קיבל {advantage_name}.", ephemeral=True)

            # Send an embed message to the player's private channel
            player_channel_name = f"{selected_player.replace(' ', '-')}-משחק".lower()
            player_channel = discord.utils.get(interaction.guild.text_channels, name=player_channel_name)
            if player_channel:
                player_embed = discord.Embed(
                    title="מזל טוב!",
                    description=f"קיבלת יתרון {advantage_name}",
                    color=await self.get_player_tribe_color(interaction.guild, selected_player)
                )
                file = discord.File("advantage.png", filename=filename)
                player_embed.set_image(url="attachment://advantage.png")
                await player_channel.send(file=file, embed=player_embed)

            # Log the addition
            log_channel = interaction.guild.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="הוספת יתרון",
                    description=f"השחקן {selected_player} קיבל יתרון {advantage_name}.",
                    color=await self.get_player_tribe_color(interaction.guild, selected_player)
                )
                file = discord.File("advantage.png", filename=filename)
                embed.set_image(url="attachment://advantage.png")
                await log_channel.send(file=file, embed=embed)

        if players:
            view = discord.ui.View()
            view.add_item(PlayerSelect(players_list, give_advantage_callback))
            await interaction.response.send_message("בחר שחקן שיקבל את היתרון:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("אין שחקנים זמינים.", ephemeral=True)
    
    @app_commands.command(name="retire_advantage", description="מוריד יתרון לשחקן אחרי שהשתמש בו")
    @commands.has_role('Host')
    async def retire_advantage(self, interaction: discord.Interaction):
        players = await self.fetch_players(interaction.guild)
        players_list = [row[1] for row in players]

        # define what happens upon player selection
        async def retire_advantage_callback(select_interaction: discord.Interaction, selected_player):
            advantages_list_with_clues = await self.get_player_advantages(select_interaction.guild, selected_player)
            # filter clues since they can't be played
            advantages_list = [adv for adv in advantages_list_with_clues if "רמז" not in adv]

            # define what happens upon advantage selection
            async def retire_advantage_callback2(select_interaction: discord.Interaction, selected_advantage):
                filename = "advantage.png"
                adv_type = "יתרון"
                # check if the advantage was an idol
                idols = await self.fetch_idols(select_interaction.guild)
                is_idol = any(selected_advantage in row for row in idols)
                if is_idol:
                    filename = await self.get_idol_image(select_interaction.guild, selected_advantage)
                    adv_type = "אליל"

                # update advantage database
                await self.remove_advantage(interaction.guild, selected_player, selected_advantage)
                await select_interaction.response.send_message(f"השחקן {selected_player} השתמש ב{adv_type} בשם {selected_advantage}.", ephemeral=True)

                # if idol, remove all clues for that idol from database and from players who bought them
                if is_idol:
                    idol_tribe = await self.get_idol_tribe(select_interaction.guild, selected_advantage)
                    database_menu_channel = select_interaction.guild.get_channel(database_menu_channel_id)
                    async for message in database_menu_channel.history(limit=None):
                        if idol_tribe in message.content:
                            await message.delete()
                    tribe_members = await self.get_tribe_members(select_interaction.guild, idol_tribe)
                    for member in tribe_members:
                        member_adv = await self.get_player_advantages(interaction.guild, member)
                        retired_clues = [adv for adv in member_adv if "רמז" in adv and idol_tribe in adv]
                        for clue in retired_clues:
                            await self.remove_advantage(select_interaction.guild, member, clue)

                # Log the removal
                log_channel = interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="הסרת יתרון",
                        description=f"השחקן {selected_player} השתמש ב{adv_type} בשם {selected_advantage}.",
                        color=await self.get_player_tribe_color(interaction.guild, selected_player)
                    )
                    file = discord.File(filename, filename=filename)
                    embed.set_image(url=f"attachment://{filename}")
                    await log_channel.send(file=file, embed=embed)
            
            view = discord.ui.View()
            view.add_item(AdvantageSelect(advantages_list, retire_advantage_callback2))
            await select_interaction.response.send_message("בחר את היתרון ששומש:", view=view, ephemeral=True)

        if players:
            view = discord.ui.View()
            view.add_item(PlayerSelect(players_list, retire_advantage_callback))
            await interaction.response.send_message("בחר את השחקן שהשתמש ביתרון:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("אין שחקנים זמינים.", ephemeral=True)

    @app_commands.command(name="expel", description="פותח חלון לבחירת שחקן להדחה ואז חלון נוסף לבחירת תפקיד חדש (מודח או מושבע).")
    @commands.has_role('Host')
    async def expel(self, interaction: discord.Interaction):
        players = await self.fetch_players(interaction.guild)
        players_list = [player[1] for player in players]

        # define what happens upon player selection
        async def expel_callback(select_interaction: discord.Interaction, selected_player):
            guild = select_interaction.guild
            member = discord.utils.get(guild.members, display_name=selected_player)
            if member:
                # Remove player role and tribe role
                roles_to_remove = []
                tribes = await self.fetch_tribes(interaction.guild)
                tribe_roles = [row[0] for row in tribes]
                player_role = discord.utils.get(guild.roles, name=selected_player)
                for role in member.roles:
                    if role.name in tribe_roles or role == player_role:
                        roles_to_remove.append(role)
                await member.remove_roles(*roles_to_remove)

                # Remove from database
                await self.remove_player_from_database(guild, selected_player)

                # define what happens upon new role selection
                async def expel_callback2(select_interaction: discord.Interaction, new_role):
                    role = discord.utils.get(guild.roles, name=new_role)
                    if not role:
                        role = await guild.create_role(name=new_role)

                    # confirm expulsion
                    await member.add_roles(role)
                    await select_interaction.response.send_message(f"השחקן {selected_player} סומן כ-{new_role}.")

                    # Log the expulsion
                    log_channel = interaction.guild.get_channel(log_channel_id)
                    embed = discord.Embed(
                        title="",
                        description=f"השחקן {selected_player} הודח, וסומן כ-{new_role}.",
                        color= discord.Color.light_grey()
                    )
                    if log_channel:
                        await log_channel.send(embed=embed)

                view=discord.ui.View()
                view.add_item(RoleSelect(expel_callback2))
                await select_interaction.response.send_message("בחר סוג מודח:",view=view)
            else:
                await select_interaction.response.send_message("שחקן לא נמצא.")

        if players_list:
            view=discord.ui.View()
            view.add_item(PlayerSelect(players_list, expel_callback))
            await interaction.response.send_message("בחר שחקן להדחה:", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("אין שחקנים זמינים.")

    @app_commands.command(name="add_idol", description="מחביא אליל חדש")
    @app_commands.describe(idol_name="שם האליל", image_file="קובץ התמונה של האליל")
    @commands.has_role('Host')
    async def add_idol(self, interaction: discord.Interaction, idol_name: str, image_file: str):
        tribes = await self.fetch_tribes(interaction.guild)
        tribe_list = [row[0] for row in tribes]

        # define what happens upon selection
        async def add_idol_callback(select_interaction: discord.Interaction, selected_tribe):
            # add idol to database
            database_idol_channel = select_interaction.guild.get_channel(database_idol_channel_id)
            await database_idol_channel.send(f"{idol_name},{selected_tribe},{image_file},{False}")

            # confirm addition
            file = discord.File(image_file, filename=image_file)
            embed = discord.Embed(
                title="אליל חדש הוחבא",
                description=f"אליל בשם {idol_name} הוחבא בהצלחה בשבט {selected_tribe}",
                color= await self.get_tribe_color(select_interaction.guild, selected_tribe)
            )
            embed.set_image(url=f"attachment://{image_file}")
            await select_interaction.response.send_message(file=file, embed=embed, ephemeral=True)

            # log addition
            log_channel = select_interaction.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(file=file, embed=embed)
        
        view = discord.ui.View()
        view.add_item(TribeSelect(tribe_list, add_idol_callback))
        await interaction.response.send_message("בחר שבט שבו יוחבא האליל:", view=view, ephemeral=True)
    
    @app_commands.command(name="add_menu_item", description="מוסיף יתרון לתפריט")
    @app_commands.describe(advantage_name="שם היתרון", price="מחיר", amount="כמות", image_file="קובץ התמונה של היתרון")
    @commands.has_role('Host')
    async def add_menu_item(self, interaction: discord.Interaction, advantage_name: str, price: str, amount: str, image_file: str):
        database_menu_channel = interaction.guild.get_channel(database_menu_channel_id)
        await database_menu_channel.send(f"{advantage_name},{price},{amount},{image_file}")
        file = discord.File(image_file, filename=image_file)

        # confirm addition
        embed = discord.Embed(
            title="פריט נוסף",
            description=f"פריט בשם {advantage_name} נוסף בהצלחה לתפריט.\nמחיר: {price}\nכמות במלאי: {amount} ",
            color=discord.Color.from_rgb(r=255,g=255,b=255)
            )
        embed.set_image(url=f"attachment://{image_file}")
        await interaction.response.send_message(file=file, embed=embed, ephemeral=True)
        
        # log addition
        log_channel = interaction.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(file=file, embed=embed)

    @app_commands.command(name="host_commands", description="מציג רשימת פקודות למנהלים")
    @commands.has_role('Host')
    async def show_hostcommands(self, interaction: discord.Interaction):
        embed = discord.Embed(
                    title=f"פקודות למנהלים:",
                    description=f"",
                    color=discord.Color.from_rgb(r=255,g=255,b=255)
                )
        embed.add_field(name="/players_data", value="\u202Bמציג רשימה של כל השחקנים, מספר הצ'יפים והיתרונות שלהם.", inline=False)
        embed.add_field(name="/add\_player [שם שחקן]", value="\u202Bמוסיף שחקן חדש ומקצה לו תפקיד ושבט. יוצר ערוצים פרטיים עבור השחקן.", inline=False)
        embed.add_field(name="/add\_tribe [שם שבט]", value="\u202Bמוסיף שבט חדש ומקצה לו תפקיד. יוצר ערוץ צ'אט תחת הקטגוריה 'שבטים' עם הרשאות מתאימות.", inline=False)
        embed.add_field(name="/add_menu_item", value="\u202Bמוסיף יתרון לתפריט", inline=False)
        embed.add_field(name="/add_idol", value="\u202Bמחביא אליל חדש במשחק", inline=False)
        embed.add_field(name="/change_tribe", value="\u202Bמעביר שחקן לשבט אחר.", inline=False)
        embed.add_field(name="/add_chips", value="\u202Bמוסיף צ'יפים לשחקן", inline=False)
        embed.add_field(name="/give_advantage", value="\u202Bמוסיף יתרון לשחקן", inline=False)
        embed.add_field(name="/retire_advantage", value="\u202Bמוריד יתרון לשחקן אחרי שהשתמש בו", inline=False)
        embed.add_field(name="/expel", value="\u202Bפותח חלון לבחירת שחקן להדחה ואז חלון נוסף לבחירת תפקיד חדש (מודח או מושבע).", inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PlayerManagement(bot))