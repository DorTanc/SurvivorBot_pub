import discord
from discord.ext import commands
from discord import app_commands
import csv


class TribeManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="add_tribe",
                          description="מוסיף שבט חדש ומקצה לו תפקיד. (זמין רק למשתמשים בעלי תפקיד Host)")
    @app_commands.describe(tribe_name="שם השבט להוספה")
    @commands.has_role('Host')
    async def add_tribe(self, interaction: discord.Interaction, tribe_name: str):
        guild = interaction.guild

        # יצירת התפקיד
        tribe_role = await guild.create_role(name=tribe_name, mentionable=True)

        # בדיקה אם קיימת קטגוריה בשם 'שבטים'
        category = discord.utils.get(guild.categories, name='שבטים')
        if not category:
            category = await guild.create_category('שבטים')

        # יצירת ערוץ צ'אט תחת הקטגוריה 'שבטים'
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            tribe_role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        await guild.create_text_channel(name=tribe_name, category=category, overwrites=overwrites)

        # עדכון קובץ tribes.csv
        try:
            with open('tribes.csv', 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['tribe', tribe_name])
            await interaction.response.send_message(
                f"The tribe '{tribe_name}' and its corresponding text channel have been created successfully.")
        except Exception as e:
            await interaction.response.send_message(f"An error occurred while updating tribes.csv: {str(e)}")


async def setup(bot):
    await bot.add_cog(TribeManagement(bot))
