from credentials import BOT_TOKEN, GUILD_NAME
from clash_utils import GetClashUserData
from db_utils import AddNewUser, CommitRoles, GetRolesFromDB, GetVacationStatus, OutputToCSV, RemoveUser, UpdateVacationForUser
import discord
from discord.ext import commands
import os

# Create bot
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

SPECIAL_ROLES = {
    "Leader": None,
    "New": None,
    "Check Rules": None
}

NORMAL_ROLES = {
    "Visitor": None,
    "Member": None,
    "Elder": None
}

TIME_OFF_CHANNEL = "time-off"
LEADER_CHANNEL = "leader-commands"
RULES_CHANNEL = "rules"


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD_NAME:
            SPECIAL_ROLES["Leader"] = discord.utils.get(guild.roles, name="Leader")
            SPECIAL_ROLES["New"] = discord.utils.get(guild.roles, name="New")
            SPECIAL_ROLES["Check Rules"] = discord.utils.get(guild.roles, name="Check Rules")
            NORMAL_ROLES["Visitor"] = discord.utils.get(guild.roles, name="Visitor")
            NORMAL_ROLES["Member"] = discord.utils.get(guild.roles, name="Member")
            NORMAL_ROLES["Elder"] = discord.utils.get(guild.roles, name="Elder")
    print("Bot Ready")


@bot.event
async def on_member_join(member):
    if member.bot:
        return

    await member.add_roles(SPECIAL_ROLES["New"])


@bot.event
async def on_member_remove(member):
    RemoveUser(member.display_name)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if (message.channel.name == "welcome"):
        discord_name = message.author.name + "#" + message.author.discriminator
        clashData = GetClashUserData(message.content, discord_name)
        if (clashData != None):
            if (AddNewUser(clashData)):
                await message.author.edit(nick=clashData["player_name"])
                await message.author.add_roles(SPECIAL_ROLES["Check Rules"])
                await message.author.remove_roles(SPECIAL_ROLES["New"])
        await message.delete()

    await bot.process_commands(message)


@bot.command()
async def vacation(ctx, *args):
    if (ctx.message.channel.name != TIME_OFF_CHANNEL):
        return

    name = ctx.author.display_name
    vacationStatus = UpdateVacationForUser(name)
    vacationStatusString = ("NOT " if not vacationStatus else "") + "ON VACATION"
    reply = f"New vacation status for {ctx.author.mention}: {vacationStatusString}"
    await ctx.send(reply)


@bot.command()
async def set_vacation(ctx, player_name, status):
    if (ctx.message.channel.name != TIME_OFF_CHANNEL) or (SPECIAL_ROLES["Leader"] not in ctx.author.roles):
        return

    member = discord.utils.get(ctx.guild.members, display_name=player_name)
    if (member == None):
        await ctx.send(f"Could not find user: {player_name}")

    vacationStatus = UpdateVacationForUser(player_name, status)
    vacationStatusString = ("NOT " if not vacationStatus else "") + "ON VACATION"
    await ctx.send(f"Updated vacation status of {member.mention} to: {vacationStatusString}")


@bot.command()
async def vacation_list(ctx, *args):
    if (ctx.message.channel.name != TIME_OFF_CHANNEL) or (SPECIAL_ROLES["Leader"] not in ctx.author.roles):
        return

    vacationList = GetVacationStatus()
    vacationString = '\n'.join(vacationList)

    await ctx.send(f"This is the list of players currently on vacation:\n{vacationString}")


@bot.command()
async def export(ctx, *args):
    if (ctx.message.channel.name != LEADER_CHANNEL) or (SPECIAL_ROLES["Leader"] not in ctx.author.roles):
        return

    OutputToCSV("members.csv")
    await ctx.send(file=discord.File("members.csv"))


@bot.command()
async def force_rules_check(ctx, *args):
    if (ctx.message.channel.name != LEADER_CHANNEL) or (SPECIAL_ROLES["Leader"] not in ctx.author.roles):
        return

    membersList = [member for member in ctx.guild.members if ((len(set(SPECIAL_ROLES.values()).intersection(set(member.roles))) == 0) and (not member.bot))]
    rolesToRemoveList = list(NORMAL_ROLES.values())

    for member in membersList:
        roleStringsToCommit = [ role.name for role in list(set(NORMAL_ROLES.values()).intersection(set(member.roles))) ]
        CommitRoles(member.display_name, roleStringsToCommit)
        await member.remove_roles(*rolesToRemoveList)
        await member.add_roles(SPECIAL_ROLES["Check Rules"])

    rulesChannel = discord.utils.get(ctx.guild.channels, name=RULES_CHANNEL)
    await rulesChannel.purge(limit=5, check=lambda message: message.author == bot.user)
    newReactMessage = await rulesChannel.send(content="React to this message for roles.")
    await newReactMessage.add_reaction(u"\u2705")


@bot.event
async def on_raw_reaction_add(payload):
    guild = bot.get_guild(payload.guild_id)
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    member = guild.get_member(payload.user_id)

    if ((channel.name != RULES_CHANNEL) or (SPECIAL_ROLES["Check Rules"] not in member.roles) or (member == bot.user) or (member.bot)):
        return

    await member.remove_roles(SPECIAL_ROLES["Check Rules"])
    dbRoles = GetRolesFromDB(member.display_name)
    savedRoles = []
    for role in dbRoles:
        savedRoles.append(NORMAL_ROLES[role])
    await member.add_roles(*savedRoles)


bot.run(BOT_TOKEN)