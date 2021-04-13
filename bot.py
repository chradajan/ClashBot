from config.config import GUILD_NAME, ADMIN_ROLE_NAME, LEADER_ROLE_NAME, ELDER_ROLE_NAME, MEMBER_ROLE_NAME, VISITOR_ROLE_NAME, CHECK_RULES_ROLE_NAME, NEW_ROLE_NAME
from config.credentials import BOT_TOKEN
from discord.ext import commands
import aiocron
import asyncio
import clash_utils
import db_utils
import discord
import os

# Create bot
help_command = commands.DefaultHelpCommand(no_category="Clash Bot Commands")
intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', help_command=help_command, intents=intents)

SPECIAL_ROLES = {
    "Admin": None,
    "New": None,
    "Check Rules": None
}

NORMAL_ROLES = {
    "Visitor": None,
    "Member": None,
    "Elder": None,
    "Leader": None
}

TIME_OFF_CHANNEL = "time-off"
COMMANDS_CHANNEL = "leader-commands"
RULES_CHANNEL = "rules"
REMINDER_CHANNEL = "reminders"
STRIKES_CHANNEL = "strikes"


def is_leader_command_check(CHANNEL_NAME):
    async def predicate(ctx):
        return ((ctx.message.channel.name == CHANNEL_NAME) and (SPECIAL_ROLES["Leader"] in ctx.author.roles))
    return commands.check(predicate)

def is_admin_command_check(CHANNEL_NAME):
    async def predicate(ctx):
        return ((ctx.message.channel.name == CHANNEL_NAME) and (SPECIAL_ROLES["Admin"] in ctx.author.roles))
    return commands.check(predicate)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD_NAME:
            SPECIAL_ROLES["Admin"] = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)
            SPECIAL_ROLES["Leader"] = discord.utils.get(guild.roles, name=LEADER_ROLE_NAME)
            SPECIAL_ROLES["New"] = discord.utils.get(guild.roles, name=NEW_ROLE_NAME)
            SPECIAL_ROLES["Check Rules"] = discord.utils.get(guild.roles, name=CHECK_RULES_ROLE_NAME)
            NORMAL_ROLES["Visitor"] = discord.utils.get(guild.roles, name=VISITOR_ROLE_NAME)
            NORMAL_ROLES["Member"] = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
            NORMAL_ROLES["Elder"] = discord.utils.get(guild.roles, name=ELDER_ROLE_NAME)

    print("Bot Ready")


@bot.event
async def on_member_join(member):
    if member.bot:
        return

    await member.add_roles(SPECIAL_ROLES["New"])


@bot.event
async def on_member_remove(member):
    db_utils.RemoveUser(member.display_name)


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.name == "welcome":
        discord_name = message.author.name + "#" + message.author.discriminator
        clashData = clash_utils.GetClashUserData(message.content, discord_name)
        if clashData != None:
            if db_utils.AddNewUser(clashData):
                if SPECIAL_ROLES["Leader"] not in message.author.roles:
                    await message.author.edit(nick=clashData["player_name"])
                await message.author.add_roles(SPECIAL_ROLES["Check Rules"])
                await message.author.remove_roles(SPECIAL_ROLES["New"])
        await message.delete()

    await bot.process_commands(message)


@bot.event
async def on_raw_reaction_add(payload):
    guild = bot.get_guild(payload.guild_id)
    channel = await bot.fetch_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    member = guild.get_member(payload.user_id)

    if (channel.name != RULES_CHANNEL) or (SPECIAL_ROLES["Check Rules"] not in member.roles) or (member == bot.user) or (member.bot):
        return

    if SPECIAL_ROLES["Admin"] in member.roles:
        await member.remove_roles(SPECIAL_ROLES["Check Rules"])
        rolesToAdd = list(NORMAL_ROLES.values())
        await member.add_roles(*rolesToAdd)
        return

    await member.remove_roles(SPECIAL_ROLES["Check Rules"])
    dbRoles = db_utils.GetRoles(member.display_name)
    savedRoles = []
    for role in dbRoles:
        savedRoles.append(NORMAL_ROLES[role])
    await member.add_roles(*savedRoles)


@bot.command()
@is_leader_command_check(COMMANDS_CHANNEL)
async def update_user(ctx, member: discord.Member, player_tag: str):
    "Leader/Admin only. Update selected user to use information associated with given player_tag. Change information in database and update Discord nickname"
    await UpdateUser(ctx, member, player_tag)
    await ctx.send(f"{player_name} has been updated.")

@update_user.error
async def update_user_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    else:
        await ctx.send("Error. Command should be formatted as:\n!update_user (user) (player_tag)")


@bot.command()
@is_admin_command_check(COMMANDS_CHANNEL)
async def reset_user(ctx, member: discord.Member):
    "Admin only. Delete selected user from database. Reset their role to New."
    await ResetUser(member, True)
    await ctx.send(f"{player_name} has been reset.")

@reset_user.error
async def reset_user_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    else:
        await ctx.send("Error. Command should be formatted as:\n!reset_user (user)")


@bot.command()
@is_admin_command_check(COMMANDS_CHANNEL)
async def reset_all_users(ctx, safety_message):
    "Admin only. Deletes all users from database, removes roles, and assigns New role. Leaders retain Leader role. Leaders must still resend player tag in welcome channel and react to rules message."
    confirmationMessage = "Yes, I really want to drop all players from the database and reset roles."

    if (safety_message != confirmationMessage):
        await ctx.send("Users NOT reset. Must type the following confirmation message exactly, in quotes, along with reset_all_users command:\n" + confirmationMessage)
        return

    db_utils.RemoveAllUsers()

    for member in ctx.guild.members:
        await ResetUser(member, False)

    await ctx.send("All users have been reset.")

@reset_all_users.error
async def reset_all_users_error(ctx, error):
    await ctx.send("Error. Command should be formatted as:\n!reset_all_users (confirmation message)")


@bot.command()
async def vacation(ctx):
    "Toggles vacation status."
    if (ctx.message.channel.name != TIME_OFF_CHANNEL):
        return

    vacationStatus = db_utils.UpdateVacationForUser(ctx.author.display_name)
    vacationStatusString = ("NOT " if not vacationStatus else "") + "ON VACATION"
    await ctx.send(f"New vacation status for {ctx.author.mention}: {vacationStatusString}.")


@bot.command()
@is_leader_command_check(TIME_OFF_CHANNEL)
async def set_vacation(ctx, member: discord.Member, status: bool):
    "Leader/Admin only. Sets vacation status of target user."
    vacationStatus = db_utils.UpdateVacationForUser(player_name, status)
    vacationStatusString = ("NOT " if not vacationStatus else "") + "ON VACATION"
    await ctx.send(f"Updated vacation status of {member.mention} to: {vacationStatusString}.")

@set_vacation.error
async def set_vacation_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    else:
        await ctx.send("Error. Command should be formatted as:\n!set_vacation (user) (yes or no)")


@bot.command()
@is_leader_command_check(TIME_OFF_CHANNEL)
async def vacation_list(ctx):
    "Leader/Admin only. Gets list of all users currently on vacation. Used in time off channel."
    vacationList = db_utils.GetVacationStatus()
    vacationString = '\n'.join(vacationList)
    await ctx.send(f"This is the list of players currently on vacation:\n{vacationString}")


@bot.command()
@is_leader_command_check(COMMANDS_CHANNEL)
async def export(ctx, UpdateBeforeExport: bool=True, FalseLogicOnly: bool=True):
    "Leader/Admin only. Export database to csv file."
    if (UpdateBeforeExport):
        for member in ctx.guild.members:
            await UpdateUser(ctx, member)

    db_utils.OutputToCSV("members.csv", FalseLogicOnly)
    await ctx.send(file=discord.File("members.csv"))

@export.error
async def export_error(ctx, error):
    await ctx.send("Error. Command should be formatted as:\n!export (update DB before export)")


@bot.command()
@is_admin_command_check(COMMANDS_CHANNEL)
async def force_rules_check(ctx):
    "Admin only. Strip roles from all non-leaders until they acknowledge new rules."
    # Get a list of members in guild without any special roles (New, Check Rules, or Admin) and that aren't bots.
    membersList = [member for member in ctx.guild.members if ((len(set(SPECIAL_ROLES.values()).intersection(set(member.roles))) == 0) and (not member.bot))]
    rolesToRemoveList = list(NORMAL_ROLES.values())

    for member in membersList:
        # Get a list of normal roles (Visitor, Member, Elder, or Leader) that a member current has. These will be restored after reacting to rules message.
        roleStringsToCommit = [ role.name for role in list(set(NORMAL_ROLES.values()).intersection(set(member.roles))) ]
        db_utils.CommitRoles(member.display_name, roleStringsToCommit)
        await member.remove_roles(*rolesToRemoveList)
        await member.add_roles(SPECIAL_ROLES["Check Rules"])

    rulesChannel = discord.utils.get(ctx.guild.channels, name=RULES_CHANNEL)
    await rulesChannel.purge(limit=10, check=lambda message: message.author == bot.user)
    newReactMessage = await rulesChannel.send(content="@everyone After you've read the rules, react to this message for roles.")
    await newReactMessage.add_reaction(u"\u2705")


@bot.command()
@is_leader_command_check(COMMANDS_CHANNEL)
async def set_strike_count(ctx, member: discord.Member, strikes: int):
    "Leader/Admin only. Set specified user's strike count to target value."
    newStrikeCount = db_utils.SetStrikes(member.display_name, strikes)
    await ctx.send(f"New strike count for {member.display_name}: {newStrikeCount}")

@set_strike_count.error
async def set_strike_count_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    else:
        await ctx.send("Error. Command should be formatted as:\n!set_strike_count (user) (count)")


@bot.command()
@is_leader_command_check(COMMANDS_CHANNEL)
async def send_reminder(ctx):
    "Leader/Admin only. Send message to reminders channel tagging users who still have battles to complete."
    await DeckUsageReminder()


@bot.command()
@is_admin_command_check(COMMANDS_CHANNEL)
async def set_automated_reminders(ctx, status: bool):
    "Admin only. Set whether automated reminders should be sent."
    db_utils.SetReminderStatus(status)
    await ctx.channel.send("Automated deck usage reminders are now " + ("ENABLED" if status else "DISABLED") + ".")

@set_automated_reminders.error
async def set_automated_reminders_error(ctx, error):
    await ctx.send("Error. Command should be formatted as:\n!set_automated_reminders (yes or no)")


@bot.command()
@is_admin_command_check(COMMANDS_CHANNEL)
async def set_automated_strikes(ctx, status: bool):
    "Admin only. Set whether automated strikes should be given."
    db_utils.SetStrikeStatus(status)
    await ctx.channel.send("Automated strikes for low deck usage are now " + ("ENABLED" if status else "DISABLED") + ".")

@set_automated_strikes.error
async def set_automated_strikes_error(ctx, error):
    await ctx.send("Error. Command should be formatted as:\n!set_automated_strikes (yes or no)")


# Send reminder every Tuesday and Wednesday at 00:00 UTC (Monday and Tuesday at 5pm PDT)
@aiocron.crontab('0 0 * * 2,3')
async def AutomatedReminder():
    if (db_utils.GetReminderStatus()):
        await DeckUsageReminder()


# Turn off vacation for all users and assign strikes to members that have not completed battles.
@aiocron.crontab('0 19 * * 3')
async def AssignStrikesAndClearVacation():
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    vacationChannel = discord.utils.get(guild.channels, name=TIME_OFF_CHANNEL)

    if db_utils.GetStrikeStatus():
        vacationList = db_utils.GetVacationStatus()
        lowDeckUsageList = clash_utils.GetDeckUsage()
        membersToStrike = []
        otherMembersToStrike = []
        strikeChannel = discord.utils.get(guild.channels, name=STRIKES_CHANNEL)

        for nameTuple in lowDeckUsageList:
            if (nameTuple[0] not in vacationList):
                strikeCount = db_utils.AddStrike(nameTuple[0])
                member = discord.utils.get(strikeChannel.members, display_name=nameTuple[0])

                if member == None:
                    otherMembersToStrike.append(f"{nameTuple[0]} - Decks used: {nameTuple[1]}")
                else:
                    membersToStrike.append(f"{member.mention} Decks used: {nameTuple[1]}   Total strikes: {strikeCount}")

        strikeString = "The following members have received a strike for failing to complete their battles:\n" + '\n'.join(membersToStrike)

        if len(otherMembersToStrike) > 0:
            strikeString += "\n\nMembers that failed to complete their battles not in this channel:\n" + '\n'.join(otherMembersToStrike)

        await strikeChannel.send(strikeString)

    db_utils.ClearAllVacation()
    await vacationChannel.send("Vacation status for all users has been set to false. Make sure to use !vacation before the next war if you're going to miss it.")


async def DeckUsageReminder():
    reminderList = clash_utils.GetDeckUsageToday()
    currentVacationList = db_utils.GetVacationStatus()
    membersToRemind = []
    otherMembersToRemind = []
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    channel = discord.utils.get(guild.channels, name=REMINDER_CHANNEL)

    if len(reminderList) == 0:
        return

    for nameTuple in reminderList:
        if (nameTuple[0] in currentVacationList):
            continue

        member = discord.utils.get(channel.members, display_name=nameTuple[0])

        if member == None:
            otherMembersToRemind.append(f"{nameTuple[0]} - Decks used today: {nameTuple[1]}")
        else:
            membersToRemind.append(f"{member.mention} Decks used today: {nameTuple[1]}")

    reminderString = "Please complete your battles by the end of the day:\n" + '\n'.join(membersToRemind)

    if len(otherMembersToRemind) > 0:
        reminderString += "\n\nMembers that need to complete battles not in this channel:\n" + '\n'.join(otherMembersToRemind)

    await channel.send(reminderString)


async def UpdateUser(ctx, member: discord.Member, player_tag = None):
    if (player_tag == None):
        player_tag = db_utils.GetPlayerTag(member.display_name)

    if (player_tag == None):
        return

    discord_name = member.name + "#" + member.discriminator
    clashData = clash_utils.GetClashUserData(player_tag, discord_name)
    db_utils.UpdateUser(clashData)

    await member.edit(nick=clashData["player_name"])


async def ResetUser(member: discord.Member, removeFromDB: bool):
    if member.bot:
        return

    rolesToRemoveList = list(NORMAL_ROLES.values())
    rolesToRemoveList.append(SPECIAL_ROLES["Check Rules"])
    await member.remove_roles(*rolesToRemoveList)
    await member.add_roles(SPECIAL_ROLES["New"])

    if (removeFromDB):
        db_utils.RemoveUser(member.display_name)


bot.run(BOT_TOKEN)