import discord
from discord.ext import commands
import csv


class TribeManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='add_tribe')
    @commands.has_role('Host')
    async def add_tribe(self, ctx, tribe_name: str):
        guild = ctx.guild

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
            await ctx.send(
                f"The tribe '{tribe_name}' and its corresponding text channel have been created successfully.")
        except Exception as e:
            await ctx.send(f"An error occurred while updating tribes.csv: {str(e)}")


async def setup(bot):
    await bot.add_cog(TribeManagement(bot))
