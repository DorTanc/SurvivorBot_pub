import csv
import discord

def get(file, col, cond=''):
    with open(file) as f:
        col -= 1
        if cond:
            for line in f:
                data = line.strip().split(',')
                if cond in data:
                    return data[col]
        else:
            data = [line.strip().split(',')[col] for line in f]
            return data

def write_player(player_data):
    with open('players.csv', 'a', newline='') as csvfile:
        player_writer = csv.writer(csvfile)
        player_writer.writerow(player_data)

def write(file, data, delete=False):
    mode = 'w' if delete else 'a'
    with open(file, mode, newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(data)

def get_player_object(ctx, player):
    if isinstance(player, Player):
        user_id = player.user_id
    elif '#' in player:
        user_id = player[:-5]
    else:
        user_id = player
    return discord.utils.get(ctx.guild.members, id=user_id)

def get_role_object(ctx, role):
    return discord.utils.get(ctx.guild.roles, name=role)

async def remove_player(client, ctx, nick, role):
    player = Player(get("players.csv", 1, nick))
    player.destroy()
    user = get_player_object(ctx, player)
    spec = get_role_object(ctx, role)
    try:
        await client.replace_roles(user, spec)
    except discord.errors.Forbidden:
        await ctx.send("Unable to replace role.")
    except AttributeError:
        await ctx.send("Unable to replace role.")
