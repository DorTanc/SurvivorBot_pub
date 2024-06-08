import discord
from discord.ext import commands
from discord import app_commands
import os
from typing import Optional
from collections import defaultdict
import logging
from PIL import Image, ImageDraw, ImageFont
import io
import arabic_reshaper
from bidi.algorithm import get_display

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

log_channel_id = 1248637078481145878
database_players_channel_id = 1248636683784818689
database_tribes_channel_id = 1248636758934028370
database_idol_channel_id = 1248636824901910539
database_menu_channel_id = 1248636904593948692
commands_locked = False

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

class ColorSelect(discord.ui.Select):
    def __init__(self, callback):
        self.dynamic_callback = callback
        options = [
            discord.SelectOption(label="אדום", value="Red"),
            discord.SelectOption(label="ירוק", value="Green"),
            discord.SelectOption(label="כחול", value="Blue"),
            discord.SelectOption(label="צהוב", value="Yellow"),
            discord.SelectOption(label="ורוד", value="Pink"),
            discord.SelectOption(label="סגול", value="Purple"),
            discord.SelectOption(label="כתום", value="Orange"),
            discord.SelectOption(label="אפור", value="Gray"),
            discord.SelectOption(label="שחור", value="Black"),
            discord.SelectOption(label="לבן", value="White")
        ]
        super().__init__(placeholder="בחר צבע", min_values=1, max_values=1, options=options)

    def color_name_to_hex(self, color_name):
        colors = {
            "Red": "#FF0000",
            "Green": "#00FF00",
            "Blue": "#0000FF",
            "Yellow": "#FFFF00",
            "Pink": "#FFC0CB",
            "Purple": "#800080",
            "Orange": "#FFA500",
            "Gray": "#808080",
            "Black": "#000000",
            "White": "#FFFFFF"
        }
        return colors.get(color_name, "#000000")

    async def callback(self, select_interaction: discord.Interaction):
        selected_color_name = self.values[0]
        selected_color_hex = self.color_name_to_hex(selected_color_name)
        await self.dynamic_callback(select_interaction, selected_color_name, selected_color_hex)
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

class AllianceName(discord.ui.Modal):
    alliance_name = discord.ui.TextInput(label="שם הברית", placeholder="הזן את שם הברית", required=False)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="ברית חדשה")

    async def on_submit(self, modal_interaction: discord.Interaction):
        alliance_name = self.alliance_name.value
        await self.dynamic_callback(modal_interaction, alliance_name)

class TribeName(discord.ui.Modal):
    tribe_name = discord.ui.TextInput(label="שם השבט", placeholder="הזן את שם השבט", required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="שבט חדש")

    async def on_submit(self, modal_interaction: discord.Interaction):
        await self.dynamic_callback(modal_interaction, self.tribe_name.value)

class PlayerName(discord.ui.Modal):
    player_name = discord.ui.TextInput(label="שם השחקן", placeholder="הזן את שם השחקן", required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="שחקן חדש")

    async def on_submit(self, modal_interaction: discord.Interaction):
        await self.dynamic_callback(modal_interaction, self.player_name.value)

class AdvantageName(discord.ui.Modal):
    advantage_name = discord.ui.TextInput(label="שם היתרון", placeholder="הזן את שם היתרון", required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="יתרון חדש")

    async def on_submit(self, modal_interaction: discord.Interaction):
        await self.dynamic_callback(modal_interaction, self.advantage_name.value)

class IdolGuess(discord.ui.Modal):
    guessed_name = discord.ui.TextInput(label="נחש את שם האליל", placeholder="הזן את שם האליל", required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="נחש את שם האליל")

    async def on_submit(self, modal_interaction: discord.Interaction):
        guessed_name = self.guessed_name.value
        await self.dynamic_callback(modal_interaction, guessed_name)

class NewIdol(discord.ui.Modal):
    idol_name = discord.ui.TextInput(label="שם האליל", placeholder="הזן את שם האליל", required=True)
    image_file= discord.ui.TextInput(label="קובץ התמונה של האליל", placeholder="הזן את שם הקובץ (כולל סיומת)", required=True)
    clue1 = discord.ui.TextInput(label="1 קובץ התמונה של רמז", placeholder="הזן את שם הקובץ (כולל סיומת)", required=True)
    clue2 = discord.ui.TextInput(label="2 קובץ התמונה של רמז", placeholder="הזן את שם הקובץ (כולל סיומת)", required=True)
    clue3 = discord.ui.TextInput(label="3 קובץ התמונה של רמז", placeholder="הזן את שם הקובץ (כולל סיומת)", required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="אליל חדש")

    async def on_submit(self, modal_interaction: discord.Interaction):
        clues = [self.clue1.value, self.clue2.value, self.clue3.value]
        await self.dynamic_callback(modal_interaction, self.idol_name.value, self.image_file.value, clues)

class NewMenuItem(discord.ui.Modal):
    advantage_name = discord.ui.TextInput(label="שם הפריט", placeholder="הזן את שם הפריט", required=True)
    price= discord.ui.TextInput(label="מחיר הפריט", placeholder="הזן את מחיר הפריט", required=True)
    amount = discord.ui.TextInput(label="כמות במלאי", placeholder="הזן את כמות הפריט במלאי", required=True)
    image_file = discord.ui.TextInput(label="קובץ התמונה של הפריט", placeholder="הזן את שם הקובץ (כולל סיומת)", required=True)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="פריט חדש")

    async def on_submit(self, modal_interaction: discord.Interaction):
        await self.dynamic_callback(modal_interaction, self.advantage_name.value, self.price.value, self.amount.value, self.image_file.value,)

class Parchment(discord.ui.Modal):
    font_name = discord.ui.TextInput(label="פונט", placeholder="(באנגלית) הזן את שם הפונט", required=False)
    font_size = discord.ui.TextInput(label="גודל הטקסט", placeholder="הזן את גודל הטקסט", required=False)
    font_color = discord.ui.TextInput(label="צבע הטקסט", placeholder="הזן את צבע הטקסט (באנגלית)", required=False)
    caption = discord.ui.TextInput(label="טקסט נוסף", placeholder="הזן טקסט נוסף שיופיע מתחת לשם", required=False)
    def __init__(self, callback):
        self.dynamic_callback = callback
        super().__init__(title="עצב את הפתק שלך")

    async def on_submit(self, modal_interaction: discord.Interaction):
        if not self.font_name.value:
            font_name = "arial"
        else: font_name = self.font_name.value.lower()
        try:
            font_size = int(self.font_size.value)
        except ValueError:
            font_size = 80  
        if font_size < 20:
            font_size = 20
        if font_size > 80:
            font_size = 80
        if self.font_color.value.lower() not in ["black","white","red","yellow","blue","green","purple","pink","orange","brown","grey"]:
            font_color = "black"
        else: font_color = self.font_color.value.lower()
        if self.caption.value:
            # Reshape and convert RTL text to the correct display order
            caption = arabic_reshaper.reshape(self.caption.value)
            caption = get_display(caption)
        await self.dynamic_callback(modal_interaction, font_name, font_size, font_color, caption)

class CommandButton(discord.ui.Button):
    def __init__(self, style, label, emoji, row, callback):
        self.btn_callback = callback
        super().__init__(style=style, label=label, emoji=emoji, row=row)

    async def callback(self, btn_interaction: discord.Interaction):
        await self.btn_callback(btn_interaction)
        if btn_interaction.message:
            await btn_interaction.message.delete()

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
        player_list = await self.get_players_list(guild)
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

    # Get player data

    async def fetch_players(self, guild):
        database_players_channel = guild.get_channel(database_players_channel_id)
        players = []
        async for message in database_players_channel.history(limit=None):
            players.append(message.content.split(','))
        return players

    def get_player_data(self, database, player_name):
        players_data = next((row for row in database if row[1].lower() == player_name.lower()))
        player_dict = {
            'user_id': players_data[0],
            'tribe': players_data[2],
            'chips': int(players_data[3]),
            'advantages': players_data[4:]
        }
        return player_dict

    async def get_player_user_id(self, guild, player_name):
        players = await self.fetch_players(guild)
        players_data = next((row for row in players if row[1].lower() == player_name.lower()))
        return players_data[0]

    async def get_player_tribe(self, guild, player_name):
        players = await self.fetch_players(guild)
        players_data = next((row for row in players if row[1].lower() == player_name.lower()))
        return players_data[2]
    
    async def get_player_chips(self, guild, player_name):
        chips = await self.fetch_players(guild)
        players_data = next((row for row in chips if row[1].lower() == player_name.lower()))
        return int(players_data[3])
    
    async def get_player_advantages(self, guild, player_name):
        advantages = await self.fetch_players(guild)
        players_data = next((row for row in advantages if row[1].lower() == player_name.lower()))
        player_advantages = players_data[4:]
        return player_advantages

    async def get_player_tribe_color(self, guild, player):
        player_tribe = await self.get_player_tribe(guild, player)
        tribe_color = await self.get_tribe_color(guild, player_tribe)
        return tribe_color

    async def get_players_list(self, guild, excluded_player=None):
        players = await self.fetch_players(guild)
        players_list = [player[1] for player in players]
        if excluded_player:
            players_list.remove(excluded_player)
        return players_list

    # Player management

    async def add_player_to_database(self, guild, user_id, player_name, tribe_name):
        database_players_channel = guild.get_channel(database_players_channel_id)
        await database_players_channel.send(f"{user_id},{player_name},{tribe_name},0")

    async def remove_player_from_database(self, guild, player_name):
        database_players_channel = guild.get_channel(database_players_channel_id)
        async for msg in database_players_channel.history(limit=None):
            if msg.content.split(',')[1] == player_name:
                await msg.delete()
                break

    async def update_tribe(self, guild, player, new_tribe):
        database_players_channel = guild.get_channel(database_players_channel_id)
        # search for the corresponding message
        async for message in database_players_channel.history(limit=None):
            list = message.content.split(',')
            if list[1] == player:
                list[2] = new_tribe
                await message.edit(content=f",".join(list))
                break

    async def update_chips(self, guild, player, new_amount):
        database_players_channel = guild.get_channel(database_players_channel_id)
        # search for the corresponding message
        async for message in database_players_channel.history(limit=None):
            list = message.content.split(',')
            if list[1] == player:
                list[3] = str(new_amount)
                await message.edit(content=f",".join(list))
                break

    async def remove_advantage(self, guild, player, advantage):
        database_players_channel = guild.get_channel(database_players_channel_id)
        # search for the corresponding message
        async for message in database_players_channel.history(limit=None):
            list = message.content.split(',')
            if list[1] == player:
                list.remove(advantage)
                await message.edit(content=f",".join(list))
                break

    async def add_advantage(self, guild, player, advantage):
        database_players_channel = guild.get_channel(database_players_channel_id)
        # search for the corresponding message
        async for message in database_players_channel.history(limit=None):
            list = message.content.split(',')
            if list[1] == player:
                list.append(advantage)
                await message.edit(content=f",".join(list))
                break

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

    async def show_players(self, interaction: discord.Interaction):
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

    async def show_chips(self, interaction: discord.Interaction):
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

    async def create_alliance(self, interaction: discord.Interaction):
        # define what happens upon name submission
        async def create_alliance_callback(modal_interaction: discord.Interaction, alliance_name):
            player_name = modal_interaction.user.display_name
            players_list = await self.get_players_list(modal_interaction.guild, player_name)

            # define what happens upon selection
            async def create_alliance_callback2(select_interaction: discord.Interaction, selected_players):
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
                if duplicate:
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

                # log alliance
                log_channel = guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="ברית נוצרה",
                        description=f"הברית {alliance_name} המכילה את {', '.join(selected_players)} נוצרה בהצלחה.",
                        color=discord.Color.from_rgb(r=255,g=255,b=255)
                    )
                    await log_channel.send(embed=embed)

            view = discord.ui.View()
            view.add_item(PlayerMultiSelect(players_list, create_alliance_callback2))
            await modal_interaction.response.defer()
            await modal_interaction.followup.send("בחר שחקנים לברית:", view=view, ephemeral=True)
        
        await interaction.response.send_modal(AllianceName(create_alliance_callback))

    async def transfer_chips(self, interaction: discord.Interaction):
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

            players_list = await self.get_players_list(modal_interaction.guild, player_name)
            
            # define what happens upon selection
            async def transfer_chips_callback2(select_interaction: discord.Interaction, selected_player):
                # update amounts for both players
                target_chips = await self.get_player_chips(select_interaction.guild, selected_player)
                new_amount_user = player_chips - chips_amount
                new_amount_target = target_chips + chips_amount
                await self.update_chips(select_interaction.guild, player_name, new_amount_user)
                await self.update_chips(select_interaction.guild, selected_player, new_amount_target)

                # confirmation to transferring player
                embed = discord.Embed(
                    title="",
                    description=f"העברת {chips_amount} צ'יפים ל{selected_player}\n נשארו לך {new_amount_user} צ'יפים",
                    color=await self.get_player_tribe_color(select_interaction.guild, player_name)
                )
                file = discord.File("chips.png", filename="chips.png")
                embed.set_image(url="attachment://chips.png")
                await select_interaction.response.send_message(file=file, embed=embed, ephemeral=False)

                # confirmation to target player
                target_channel_name = f"{selected_player.replace(' ', '-').lower()}-משחק"
                target_channel = discord.utils.get(select_interaction.guild.text_channels, name=target_channel_name)
                if target_channel:
                    embed = discord.Embed(
                        title="מזל טוב!",
                        description=f"קיבלת {chips_amount} צ'יפים מ{player_name}\n עכשיו יש לך {new_amount_target} צ'יפים",
                        color=await self.get_player_tribe_color(select_interaction.guild, selected_player)
                    )
                    file = discord.File("chips.png", filename="chips.png")
                    embed.set_image(url="attachment://chips.png")
                    await target_channel.send(file=file, embed=embed)

                # log transfer
                log_channel = select_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="",
                        description=f"{player_name} העביר {chips_amount} צ'יפים ל {selected_player}\nל {player_name} יש עכשיו {new_amount_user} צ'יפים\nל {selected_player} יש עכשיו {new_amount_target} צ'יפים",
                        color=await self.get_player_tribe_color(select_interaction.guild, player_name)
                    )
                    file = discord.File("chips.png", filename="chips.png")
                    embed.set_image(url="attachment://chips.png")
                    await log_channel.send(file=file, embed=embed)

            view = discord.ui.View()
            view.add_item(PlayerSelect(players_list, transfer_chips_callback2))
            await modal_interaction.response.send_message("בחר שחקן להעברה:", view=view, ephemeral=False)

        await interaction.response.send_modal(ChipsAmount(transfer_chips_callback))

    async def transfer_advantage(self, interaction: discord.Interaction):
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
            players_list = await self.get_players_list(select_interaction.guild, user_name)

            # define what happens upon player selection
            async def transfer_advantage_callback2(select_interaction: discord.Interaction, selected_player):
                filename = "advantage.png"
                adv_type = "יתרון"
                # check if the advantage was an idol
                idols = await self.fetch_idols(select_interaction.guild)
                is_idol = any(selected_advantage in row for row in idols)
                if is_idol:
                    filename = await self.get_idol_image(select_interaction.guild, selected_advantage)
                    adv_type = "אליל"

                # remove advantage from player and add it to target player
                await self.remove_advantage(select_interaction.guild, user_name, selected_advantage)
                await self.add_advantage(select_interaction.guild, selected_player, selected_advantage)

                # confirmation to transferring player
                embed = discord.Embed(
                    title="",
                    description=f"העברת {adv_type} בשם {selected_advantage} ל {selected_player}",
                    color=await self.get_player_tribe_color(select_interaction.guild, user_name)
                )
                file = discord.File(filename, filename=filename)
                embed.set_image(url=f"attachment://{filename}")
                await select_interaction.response.send_message(file=file, embed=embed, ephemeral=False)

                # confirmation to target player
                target_channel_name = f"{selected_player.replace(' ', '-').lower()}-משחק"
                target_channel = discord.utils.get(select_interaction.guild.text_channels, name=target_channel_name)
                if target_channel:
                    embed = discord.Embed(
                        title="מזל טוב!",
                        description=f"קיבלת {adv_type} בשם {selected_advantage} מ-{user_name}",
                        color=await self.get_player_tribe_color(select_interaction.guild, selected_player)
                    )
                    file = discord.File(filename, filename=filename)
                    embed.set_image(url=f"attachment://{filename}")
                    await target_channel.send(file=file, embed=embed)

                # log transfer
                log_channel = select_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="",
                        description=f"השחקן {user_name} העביר {adv_type} בשם {selected_advantage} ל {selected_player}",
                        color=await self.get_player_tribe_color(select_interaction.guild, user_name)
                    )
                    file = discord.File(filename, filename=filename)
                    embed.set_image(url=f"attachment://{filename}")
                    await log_channel.send(file=file, embed=embed)

            view = discord.ui.View()
            view.add_item(PlayerSelect(players_list, transfer_advantage_callback2))
            await select_interaction.response.send_message("בחר שחקן להעברה:", view=view, ephemeral=False)

        view = discord.ui.View()
        view.add_item(AdvantageSelect(advantages_list, transfer_advantage_callback))
        await interaction.response.send_message("בחר יתרון להעברה:", view=view, ephemeral=False)

    async def buy_advantage(self, interaction: discord.Interaction):
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

    async def find_idol(self, interaction: discord.Interaction):
        player_name = interaction.user.display_name
        tribe = await self.get_player_tribe(interaction.guild, player_name)
        
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

    async def create_parchment(self, interaction: discord.Interaction):
        user = interaction.user.display_name
        tribe = await self.get_player_tribe(interaction.guild, user)
        players_list = await self.get_tribe_members(interaction.guild, tribe)
        players_list.remove(user)

        # define what happens upon selection
        async def create_parchment_callback(select_interaction: discord.Interaction, selected_player):

            # define what happens upon submission
            async def create_parchment_callback2(modal_interaction: discord.Interaction, font_name, font_size, font_color, caption):
                # Load an image
                image = Image.open('parchment.png')
                draw = ImageDraw.Draw(image)
                # Try to use the specified font, fallback to Arial if it fails
                try:
                    font = ImageFont.truetype(f"{font_name}.ttf", font_size)
                except IOError:
                    font_name = "arial"
                    font = ImageFont.truetype('arial.ttf', font_size)
                # Get the size of the image
                image_width, image_height = image.size
                # Get the bounding box of the text
                text_bbox = draw.textbbox((0, 0), selected_player, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                # Calculate the position
                text_x = (image_width - text_width) // 2
                text_y = (image_height - text_height) // 2
                text_position = (text_x, text_y)
                # Reshape and convert RTL text to the correct display order
                name = arabic_reshaper.reshape(selected_player)
                name = get_display(name)
                # Add text to the image
                draw.text(text_position, name, font=font, fill=font_color)
                if caption:
                    caption_font = ImageFont.truetype(f"{font_name}.ttf", font_size // 2)
                    # Get the bounding box of the caption
                    caption_bbox = draw.textbbox((0, 0), caption, font=caption_font)
                    caption_width = caption_bbox[2] - caption_bbox[0]
                    # Calculate the position of caption
                    caption_x = (image_width - caption_width) // 2
                    caption_y = text_y + text_height + 20
                    caption_position = (caption_x, caption_y)
                    # Add caption to the image
                    draw.text(caption_position, caption, font=caption_font, fill=font_color)
                # Save the image to a BytesIO object
                with io.BytesIO() as image_binary:
                    image.save(image_binary, 'PNG')
                    image_binary.seek(0)
                    await modal_interaction.response.send_message(file=discord.File(fp=image_binary, filename='parchment_with_text.png'))
            
            await select_interaction.response.send_modal(Parchment(create_parchment_callback2))

        view = discord.ui.View()
        view.add_item(PlayerSelect(players_list, create_parchment_callback))
        await interaction.response.send_message("בחר שחקן שברצונך להצביע נגדו:", view=view, ephemeral=False)

    @app_commands.command(name="command_menu", description="תפריט פקודות לשחקנים")
    async def command_menu(self, interaction: discord.Interaction):
        is_correct_channel, player_game_channel = await self.is_in_correct_channel(interaction)
        if not is_correct_channel:
            embed = discord.Embed(
            title="",description=f"הפקודות זמינות רק בערוץ {player_game_channel.mention}",color= discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        if commands_locked:
            embed = discord.Embed(
            title="",description=f"באופן זמני לא ניתן להשתמש בפקודות. המנהלים יפתחו את הפקודות מחדש בקרוב.",color= discord.Color.red())
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = discord.Embed(title='תפריט פקודות', description='איך אפשר לעזור לך?', color=0xffffff)
        view = discord.ui.View()
        blurple = discord.ButtonStyle.blurple
        view.add_item(CommandButton(blurple, "רשימת שחקנים", "⛹️‍♂️", 0, self.show_players))
        view.add_item(CommandButton(blurple, "כמות הצ'יפים שלי", "🤑", 0, self.show_chips))
        view.add_item(CommandButton(blurple, "ברית חדשה", "🤝", 1, self.create_alliance))
        view.add_item(CommandButton(blurple, "העברת צ'יפים", "💸", 1, self.transfer_chips))
        view.add_item(CommandButton(blurple, "העברת יתרון", "🎁", 2, self.transfer_advantage))
        view.add_item(CommandButton(blurple, "קניית יתרון", "🛒", 2, self.buy_advantage))
        view.add_item(CommandButton(blurple, "חיפוש אליל", "🔍", 3, self.find_idol))
        view.add_item(CommandButton(blurple, "פתק הצבעה", "✍", 3, self.create_parchment))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # Host-only commands

    async def players_data(self, interaction: discord.Interaction):
        database = await self.fetch_players(interaction.guild)
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
                data = self.get_player_data(database, player)
                advantages = data['advantages']
                advantages_str = ", ".join([f"{adv}" for adv in advantages])
                chips = data['chips']
                embed.add_field(name=f"{player}", value=f"צ'יפים: {str(chips)}, יתרונות: {advantages_str if advantages_str else 'אין'}", inline=False)
            embeds.append(embed)

        if embeds:
            await interaction.followup.send(embeds=embeds)
        else:
            await interaction.followup.send("אין שחקנים רשומים כרגע.")

    async def add_player(self, interaction: discord.Interaction):
        # define what happens upon name submission
        async def add_player_callback(modal_interaction: discord.Interaction, player_name):
            tribes = await self.fetch_tribes(modal_interaction.guild)
            tribe_list = [row[0] for row in tribes]

            # define what happens upon selection
            async def add_player_callback2(select_interaction: discord.Interaction, selected_tribe):
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
                    category_name = "ערוצים אישיים 🔒"
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

            view = discord.ui.View()
            view.add_item(TribeSelect(tribe_list, add_player_callback2))
            await modal_interaction.response.send_message("בחר שבט לשחקן:", view=view)

        await interaction.response.send_modal(PlayerName(add_player_callback))

    async def add_tribe(self, interaction: discord.Interaction):
        # Define what happens upon name submission
        async def add_tribe_callback(modal_interaction: discord.Interaction, tribe_name):
            tribes = await self.fetch_tribes(modal_interaction.guild)
            tribe_list = [row[0] for row in tribes]
            if tribe_name in tribe_list:
                await modal_interaction.response.send_message(f"השבט {tribe_name} כבר קיים.", ephemeral=True)
                return

            # Define what happens upon color selection
            async def add_tribe_callback2(select_interaction: discord.Interaction, selected_color, hex_code):
                # Create the tribe role
                tribe_role = await select_interaction.guild.create_role(name=tribe_name, color=discord.Color.from_str(hex_code), mentionable=True)

                # Create the tribe channel
                cat_name = "ערוצים שבטיים 🚩"
                category = discord.utils.get(select_interaction.guild.categories, name=cat_name)
                if not category:
                    category = await select_interaction.guild.create_category(cat_name)

                await select_interaction.guild.create_text_channel(tribe_name, category=category, overwrites={
                    select_interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    tribe_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                })

                # Add tribe to database
                database_tribes_channel = select_interaction.guild.get_channel(database_tribes_channel_id)
                await database_tribes_channel.send(f"{tribe_name},{hex_code}")

                # Send a log message to the log channel
                log_channel = select_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title = "שבט נוצר בהצלחה",
                        description = f"השבט {tribe_name} נוצר בהצלחה עם הצבע {selected_color}.",
                        color = discord.Color.from_str(hex_code)
                    )
                    await log_channel.send(embed=embed)

                await select_interaction.response.send_message(f"השבט {tribe_name} נוסף בהצלחה עם הצבע {selected_color}.", ephemeral=True)

            view = discord.ui.View()
            view.add_item(ColorSelect(add_tribe_callback2))
            await modal_interaction.response.send_message("בחר צבע לשבט:", view=view, ephemeral=True)

        await interaction.response.send_modal(TribeName(add_tribe_callback))

    async def change_tribe(self, interaction: discord.Interaction):
        players_list = await self.get_players_list(interaction.guild)

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
                old_tribe = await self.get_player_tribe(select_interaction.guild, selected_player)
                await self.update_tribe(select_interaction.guild, selected_player, selected_tribe)
                # Fetch the user by their ID
                user_id = await self.get_player_user_id(select_interaction.guild, selected_player)
                user = interaction.guild.get_member(int(user_id))

                if user:
                    # Get the current tribe roles and the new tribe role
                    current_roles = [role for role in user.roles if old_tribe in role.name]
                    new_tribe_role = discord.utils.get(select_interaction.guild.roles, name=selected_tribe)

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
                        color=await self.get_tribe_color(select_interaction.guild, selected_tribe)
                    )
                    await select_interaction.response.send_message(embed=embed, ephemeral=True)

                    # log change
                    log_channel = select_interaction.guild.get_channel(log_channel_id)
                    if log_channel:
                        await log_channel.send(embed=embed)
            
            view = discord.ui.View()
            view.add_item(TribeSelect(tribe_list, change_tribe_callback2))
            await select_interaction.response.send_message("בחר שבט חדש לשחקן", view=view, ephemeral=True)

        view = discord.ui.View()
        view.add_item(PlayerSelect(players_list, change_tribe_callback))
        await interaction.response.send_message("בחר שחקן שיעבור שבט:", view=view, ephemeral=True)

    async def add_chips(self, interaction: discord.Interaction):
        players_list = await self.get_players_list(interaction.guild)

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

        view = discord.ui.View()
        view.add_item(PlayerSelect(players_list, add_chips_callback))
        await interaction.response.send_message("בחר שחקן שיקבל את הצ'יפים:", view=view, ephemeral=True)

    async def give_advantage(self, interaction: discord.Interaction):
        players_list = await self.get_players_list(interaction.guild)

        # define what happens upon selection
        async def give_advantage_callback(select_interaction: discord.Interaction, selected_player):
            # define what happens upon name submission
            async def give_advantage_callback2(modal_interaction: discord.Interaction, advantage_name):
                filename = "advantage.png"

                # update advantage database
                await self.add_advantage(modal_interaction.guild, selected_player, advantage_name)
                await modal_interaction.response.send_message(f"השחקן {selected_player} קיבל {advantage_name}.", ephemeral=True)

                # Send an embed message to the player's private channel
                player_channel_name = f"{selected_player.replace(' ', '-')}-משחק".lower()
                player_channel = discord.utils.get(modal_interaction.guild.text_channels, name=player_channel_name)
                if player_channel:
                    player_embed = discord.Embed(
                        title="מזל טוב!",
                        description=f"קיבלת יתרון {advantage_name}",
                        color=await self.get_player_tribe_color(modal_interaction.guild, selected_player)
                    )
                    file = discord.File("advantage.png", filename=filename)
                    player_embed.set_image(url="attachment://advantage.png")
                    await player_channel.send(file=file, embed=player_embed)

                # Log the addition
                log_channel = modal_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="הוספת יתרון",
                        description=f"השחקן {selected_player} קיבל יתרון {advantage_name}.",
                        color=await self.get_player_tribe_color(interaction.guild, selected_player)
                    )
                    file = discord.File("advantage.png", filename=filename)
                    embed.set_image(url="attachment://advantage.png")
                    await log_channel.send(file=file, embed=embed)

            await select_interaction.response.send_modal(AdvantageName(give_advantage_callback2))

        view = discord.ui.View()
        view.add_item(PlayerSelect(players_list, give_advantage_callback))
        await interaction.response.send_message("בחר שחקן שיקבל את היתרון:", view=view, ephemeral=True)

    async def retire_advantage(self, interaction: discord.Interaction):
        players_list = await self.get_players_list(interaction.guild)

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

        view = discord.ui.View()
        view.add_item(PlayerSelect(players_list, retire_advantage_callback))
        await interaction.response.send_message("בחר את השחקן שהשתמש ביתרון:", view=view, ephemeral=True)

    async def expel(self, interaction: discord.Interaction):
        players_list = await self.get_players_list(interaction.guild)

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

        view=discord.ui.View()
        view.add_item(PlayerSelect(players_list, expel_callback))
        await interaction.response.send_message("בחר שחקן להדחה:", view=view, ephemeral=True)

    async def add_idol(self, interaction: discord.Interaction):
        tribes = await self.fetch_tribes(interaction.guild)
        tribe_list = [row[0] for row in tribes]

        # define what happens upon selection
        async def add_idol_callback(select_interaction: discord.Interaction, selected_tribe):

            # define what happens upon submission
            async def add_idol_callback2(modal_interaction: discord.Interaction, idol_name, image_file, clues):
                # add idol to database
                database_idol_channel = modal_interaction.guild.get_channel(database_idol_channel_id)
                await database_idol_channel.send(f"{idol_name},{selected_tribe},{image_file},{False}")

                # add clues to menu
                clue_price = 50 # can be modified later
                clue_amount = 20 # based on cast size, can be modified later
                database_menu_channel = interaction.guild.get_channel(database_menu_channel_id)
                for index, clue in enumerate(clues):
                    if clue:
                        await database_menu_channel.send(f"רמז {index+1} {selected_tribe},{clue_price},{clue_amount},{clue}")

                # confirm addition
                file = discord.File(image_file, filename=image_file)
                embed = discord.Embed(
                    title="אליל חדש הוחבא",
                    description=f"אליל בשם {idol_name} הוחבא בהצלחה בשבט {selected_tribe}",
                    color= await self.get_tribe_color(modal_interaction.guild, selected_tribe)
                )
                embed.set_image(url=f"attachment://{image_file}")
                await modal_interaction.response.send_message(file=file, embed=embed, ephemeral=True)

                # log addition
                log_channel = modal_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    await log_channel.send(file=file, embed=embed)

            await select_interaction.response.send_modal(NewIdol(add_idol_callback2))

        view = discord.ui.View()
        view.add_item(TribeSelect(tribe_list, add_idol_callback))
        await interaction.response.send_message("בחר שבט שבו יוחבא האליל:", view=view, ephemeral=True)
    
    async def add_menu_item(self, interaction: discord.Interaction):
        # define what happens upon submission
        async def add_menu_item_callback(modal_interaction: discord.Interaction, advantage_name, price, amount, image_file):
            database_menu_channel = modal_interaction.guild.get_channel(database_menu_channel_id)
            await database_menu_channel.send(f"{advantage_name},{price},{amount},{image_file}")
            file = discord.File(image_file, filename=image_file)

            # confirm addition
            embed = discord.Embed(
                title="פריט נוסף",
                description=f"פריט בשם {advantage_name} נוסף בהצלחה לתפריט.\nמחיר: {price}\nכמות במלאי: {amount} ",
                color=discord.Color.from_rgb(r=255,g=255,b=255)
                )
            embed.set_image(url=f"attachment://{image_file}")
            await modal_interaction.response.send_message(file=file, embed=embed, ephemeral=True)
            
            # log addition
            log_channel = modal_interaction.guild.get_channel(log_channel_id)
            if log_channel:
                await log_channel.send(file=file, embed=embed)
        
        await interaction.response.send_modal(NewMenuItem(add_menu_item_callback))

    async def create_tribal(self, interaction: discord.Interaction):
        category = discord.utils.get(interaction.guild.categories, name="מועצות שבט 🔥")
        tribals = [channel for channel in category.channels if isinstance(channel, discord.TextChannel)]
        tribal_number = len(tribals) + 1
        tribes = await self.fetch_tribes(interaction.guild)
        tribe_list = [row[0] for row in tribes]

        # Define what happens upon tribe selection
        async def create_tribal_callback(select_interaction: discord.Interaction, selected_tribe):
            tribe_role = discord.utils.get(select_interaction.guild.roles, name=selected_tribe)
            members_num = len(await self.get_tribe_members(select_interaction.guild, selected_tribe))

            # Create the tribal channel
            tribal_channel = await select_interaction.guild.create_text_channel(f"מועצת-שבט-{tribal_number}-{selected_tribe}", 
                category=category, overwrites={
                select_interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                tribe_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            })

            # Add tribal messages
            await tribal_channel.send(f"שלום שבט {tribe_role.mention} -הגעתם למועצת השבט ה {tribal_number} של המשחק!\nלפניכם פתק הצבעה, עליו תצטרכו לכתוב/לצייר את הצבעתכם. יש לשלוח את ההצבעה בערוץ המשחק שלכם עד מחר ב-22:00.\nשימו לב שאפשר לשנות הצבעה, אבל ההצבעה האחרונה שנקבל מכם עד השעה 22:00 היא זו שתיחשב.\nמחר לאורך היום נשלח לכם שאלות עליהן תצטרכו לענות, ואת התשובות הנבחרות נפרסם כאן רגע לפני הקראת הקולות\nכל פעם שנקבל קולות אנחנו נעדכן כאן בדרך הבאה: **1/{members_num}**")
            file = discord.File("tribalgif.gif", filename="tribalgif.gif")
            await tribal_channel.send(file=file)
            file = discord.File("parchment.png", filename="parchment.png")
            await tribal_channel.send(file=file)
            await tribal_channel.send(f"**0/{members_num}**")

            # Send a log message to the log channel
            log_channel = select_interaction.guild.get_channel(log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title = "מועצת שבט נפתחה",
                    description = f"ערוץ מועצה נפתח לשבט {selected_tribe}",
                    color = await self.get_tribe_color(select_interaction.guild, selected_tribe)
                )
                await log_channel.send(embed=embed)

            await select_interaction.response.send_message(f"ערוץ מועצה נפתח לשבט {selected_tribe}", ephemeral=True)

        view = discord.ui.View()
        view.add_item(TribeSelect(tribe_list, create_tribal_callback))
        await interaction.response.send_message("בחר איזה שבט הולך למועצה:", view=view, ephemeral=True)

    async def lock_commands(self, interaction: discord.Interaction):
        global commands_locked
        if commands_locked: return
        commands_locked = True
        # confirm
        embed = discord.Embed(
            title="",
            description=f"כל הפקודות לשחקנים נעולות",
            color= discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def unlock_commands(self, interaction: discord.Interaction):
        global commands_locked
        if not commands_locked: return
        commands_locked = False
        # confirm
        embed = discord.Embed(
            title="",
            description=f"כל הפקודות לשחקנים זמינות",
            color= discord.Color.default()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="host_command_menu", description="תפריט פקודות למנהלים")
    @commands.has_role('Host')
    async def host_command_menu(self, interaction: discord.Interaction):
        embed = discord.Embed(title='תפריט פקודות', description='איך אפשר לעזור לך?', color=0xffffff)
        view = discord.ui.View()
        blurple = discord.ButtonStyle.blurple
        green = discord.ButtonStyle.green
        red = discord.ButtonStyle.red
        view.add_item(CommandButton(blurple, "רשימת שחקנים", "⛹️‍♂️", 0, self.players_data))
        view.add_item(CommandButton(green, "שחקן חדש", "➕", 1, self.add_player))
        view.add_item(CommandButton(green, "שבט חדש", "➕", 1, self.add_tribe))
        view.add_item(CommandButton(green, "אליל חדש", "➕", 1, self.add_idol))
        view.add_item(CommandButton(green, "פריט חדש", "➕", 1, self.add_menu_item))
        view.add_item(CommandButton(blurple, "שנה שבט", "🚩", 2, self.change_tribe))
        view.add_item(CommandButton(blurple, "הוסף צ'יפים", "💵", 2, self.add_chips))
        view.add_item(CommandButton(blurple, "הוסף יתרון", "🎁", 2, self.give_advantage))
        view.add_item(CommandButton(red, "הסר יתרון", "➖", 3, self.retire_advantage))
        view.add_item(CommandButton(red, "הסר שחקן", "💀", 3, self.expel))
        view.add_item(CommandButton(blurple, "מועצת שבט", "🔥", 4, self.create_tribal))
        view.add_item(CommandButton(blurple, "נעל פקודות", "🔒", 4, self.lock_commands))
        view.add_item(CommandButton(blurple, "פתח פקודות", "🔓", 4, self.unlock_commands))
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="measure_time", description="מדידת זמן בין שתי הודעות")
    @app_commands.describe(id1="הודעת התחלה", id2="הודעת סיום")
    @commands.has_role('Host')
    async def measure_time(self, interaction: discord.Interaction, id1: str, id2: str):
        message1 = await interaction.channel.fetch_message(id1)
        message2 = await interaction.channel.fetch_message(id2)

        # Convert snowflake IDs to timestamps
        timestamp1 = message1.created_at
        timestamp2 = message2.created_at

        # Calculate the time difference
        time_difference = timestamp2 - timestamp1
        
        # inform player
        embed = discord.Embed(
            title="הזמן שלך נמדד",
            description=f"הזמן שלך במשימה הוא {time_difference}",
            color=discord.Color.from_rgb(r=255,g=255,b=255)
            )
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot):
    await bot.add_cog(PlayerManagement(bot))