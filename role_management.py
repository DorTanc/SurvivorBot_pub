async def list_roles(ctx):
    guild = ctx.guild
    roles = guild.roles
    for role in roles:
        await ctx.send(role.name)
