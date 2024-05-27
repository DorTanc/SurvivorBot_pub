import discord
from discord.ext import commands
from discord import app_commands
import csv
log_channel_id = 1243911112978858075
database_tribes_channel_id = 1244328239086829712
class TribeManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_tribes_data(self, guild):
        database_tribes_channel = guild.get_channel(database_tribes_channel_id)
        tribes = []
        async for message in database_tribes_channel.history(limit=None):
            tribe_name, tribe_color = message.content.split(',')
            tribes.append((tribe_name, tribe_color))
        return tribes

    async def add_tribe_to_channel(self, guild, tribe_name, tribe_color):
        database_tribes_channel = guild.get_channel(database_tribes_channel_id)
        await database_tribes_channel.send(f"{tribe_name},{tribe_color}")

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

    @app_commands.command(name="add_tribe", description="מוסיף שבט חדש ומקצה לו תפקיד.")
    @app_commands.describe(tribe_name="שם השבט")
    @commands.has_role('Host')
    async def add_tribe(self, interaction: discord.Interaction, tribe_name: str):
        existing_tribes = await self.fetch_tribes_data(interaction.guild)
        if any(tribe_name == tribe[0] for tribe in existing_tribes):
            await interaction.response.send_message(f"השבט {tribe_name} כבר קיים.", ephemeral=True)
            return

        class ColorSelect(discord.ui.Select):
            def __init__(self, color_name_to_hex, add_tribe_to_channel):
                self.color_name_to_hex = color_name_to_hex
                self.add_tribe_to_channel = add_tribe_to_channel
                options = [
                    discord.SelectOption(label="Red", value="Red"),
                    discord.SelectOption(label="Green", value="Green"),
                    discord.SelectOption(label="Blue", value="Blue"),
                    discord.SelectOption(label="Yellow", value="Yellow"),
                    discord.SelectOption(label="Pink", value="Pink"),
                    discord.SelectOption(label="Purple", value="Purple"),
                    discord.SelectOption(label="Orange", value="Orange"),
                    discord.SelectOption(label="Gray", value="Gray"),
                    discord.SelectOption(label="Black", value="Black"),
                    discord.SelectOption(label="White", value="White")
                ]
                super().__init__(placeholder="בחר צבע לשבט", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                selected_color_name = self.values[0]
                tribe_color = self.color_name_to_hex(selected_color_name)
                rgb_color = discord.Color.from_str(tribe_color)

                # Create the tribe role
                tribe_role = await select_interaction.guild.create_role(name=tribe_name, color=rgb_color, mentionable=True)

                # Create the tribe channel
                category = discord.utils.get(select_interaction.guild.categories, name="שבטים")
                if not category:
                    category = await select_interaction.guild.create_category("שבטים")

                await select_interaction.guild.create_text_channel(tribe_name, category=category, overwrites={
                    select_interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    tribe_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                })

                await self.add_tribe_to_channel(select_interaction.guild, tribe_name, tribe_color)

                # Send a log message to the log channel
                log_channel = select_interaction.guild.get_channel(log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="שבט נוצר בהצלחה",
                        description=f"השבט {tribe_name} נוצר בהצלחה עם הצבע {selected_color_name}.",
                        color=rgb_color
                    )
                    await log_channel.send(embed=embed)

                await select_interaction.response.send_message(f"השבט {tribe_name} נוסף בהצלחה עם הצבע {selected_color_name}.", ephemeral=False)

        view = discord.ui.View()
        view.add_item(ColorSelect(self.color_name_to_hex, self.add_tribe_to_channel))

        await interaction.response.send_message("בחר צבע לשבט:", view=view, ephemeral=True)


async def setup(bot):
    await bot.add_cog(TribeManagement(bot))
