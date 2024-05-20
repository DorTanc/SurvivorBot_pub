import discord
from discord import ui, SelectOption
import logging

logger = logging.getLogger(__name__)

async def create_voice_channel(interaction, channel_name, *role_mentions):
    guild = interaction.guild
    voice_category = discord.utils.get(guild.categories, name="Voice Channels")

    if not voice_category:
        await interaction.response.send_message("Voice Channels category not found.", ephemeral=True)
        return

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(connect=False)
    }

    for role_mention in role_mentions:
        role_id = role_mention.strip('<@&>')
        role = guild.get_role(int(role_id))
        if not role:
            await interaction.response.send_message(f"Role '{role_mention}' not found.", ephemeral=True)
            continue

        overwrites[role] = discord.PermissionOverwrite(connect=True, view_channel=True, speak=True)

    await guild.create_voice_channel(channel_name, category=voice_category, overwrites=overwrites)
    await interaction.response.send_message(f"Voice channel '{channel_name}' created successfully.", ephemeral=True)
    await interaction.message.edit(view=None)  # Remove the selection bar

class RoleSelectMenu(ui.Select):
    def __init__(self, roles):
        options = [SelectOption(label=role.name, value=str(role.id)) for role in roles]
        super().__init__(placeholder='Select roles...', min_values=1, max_values=len(roles), options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_roles = [interaction.guild.get_role(int(role_id)) for role_id in self.values]
        channel_name = "-".join([role.name for role in selected_roles])
        await create_voice_channel(interaction, channel_name, *[role.mention for role in selected_roles])

class RoleSelectView(ui.View):
    def __init__(self, roles):
        super().__init__()
        self.add_item(RoleSelectMenu(roles))

async def create_voice_channel_menu(ctx, bot, channel_name=None):
    guild = ctx.guild
    roles = [role for role in ctx.guild.roles if role.name != "@everyone" and role.mentionable]

    if not roles:
        await ctx.send("No mentionable roles found.")
        return

    view = RoleSelectView(roles)
    await ctx.send("Select roles for the voice channel:", view=view)
