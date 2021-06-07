from config import *
from credentials import BOT_TOKEN
from discord.ext import commands
from prettytable import PrettyTable
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


def is_leader_command_check():
    async def predicate(ctx):
        return (NORMAL_ROLES["Leader"] in ctx.author.roles) or (SPECIAL_ROLES["Admin"] in ctx.author.roles)
    return commands.check(predicate)

def is_admin_command_check():
    async def predicate(ctx):
        return SPECIAL_ROLES["Admin"] in ctx.author.roles
    return commands.check(predicate)

def channel_check(CHANNEL_NAME):
    async def predicate(ctx):
        return ctx.message.channel.name == CHANNEL_NAME
    return commands.check(predicate)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD_NAME:
            SPECIAL_ROLES["Admin"] = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)
            SPECIAL_ROLES["New"] = discord.utils.get(guild.roles, name=NEW_ROLE_NAME)
            SPECIAL_ROLES["Check Rules"] = discord.utils.get(guild.roles, name=CHECK_RULES_ROLE_NAME)
            NORMAL_ROLES["Visitor"] = discord.utils.get(guild.roles, name=VISITOR_ROLE_NAME)
            NORMAL_ROLES["Member"] = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
            NORMAL_ROLES["Elder"] = discord.utils.get(guild.roles, name=ELDER_ROLE_NAME)
            NORMAL_ROLES["Leader"] = discord.utils.get(guild.roles, name=LEADER_ROLE_NAME)

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
                if SPECIAL_ROLES["Admin"] not in message.author.roles:
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

    await member.remove_roles(SPECIAL_ROLES["Check Rules"])

    if SPECIAL_ROLES["Admin"] in member.roles:
        rolesToAdd = list(NORMAL_ROLES.values())
        await member.add_roles(*rolesToAdd)
        await member.remove_roles(NORMAL_ROLES["Visitor"])
        return

    dbRoles = db_utils.GetRoles(member.display_name)
    savedRoles = []
    for role in dbRoles:
        savedRoles.append(NORMAL_ROLES[role])
    await member.add_roles(*savedRoles)


# Update

@bot.command()
async def update(ctx, player_tag: str):
    "Update yourself with information associated with given player tag (include # symbol). Updates your Clash username, Discord username, and clan role in database. Changes your nickname to Clash username. Use this command if you've updated your Discord username or Clash username, or your clan role has changed."
    discord_name = ctx.author.name + "#" + ctx.author.discriminator
    clashData = clash_utils.GetClashUserData(player_tag, discord_name)

    if clashData == None:
        await ctx.send("Something went wrong. Your information has not been updated.")
        return

    memberStatus = db_utils.UpdateUser(clashData)

    if SPECIAL_ROLES["Admin"] in ctx.author.roles:
        if clashData["player_name"] != ctx.author.display_name:
            await ctx.send(f"{ctx.author.display_name} has been updated in the database, but their in-game name no longer matches their Discord nickname. {ctx.author.mention} Admins need to update their nicknames manually due to permissions.")
    else:
        rolesToRemoveList = [NORMAL_ROLES["Member"], NORMAL_ROLES["Visitor"]]
        await ctx.author.remove_roles(*rolesToRemoveList)
        await ctx.author.add_roles(NORMAL_ROLES[memberStatus])
        await ctx.author.edit(nick=clashData["player_name"])

    await ctx.send("Your information has been updated.")

@update.error
async def update_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing argument. Command should be formatted as:  !update <player_tag>")
    elif isinstance(error, commands.errors.CommandInvokeError):
        await ctx.send("Something went wrong. Make sure the player tag you entered doesn't belong to another user in this server. Command should be formatted as:  !update <player_tag>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !update <player_tag>")
        raise error


# Update user

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def update_user(ctx, member: discord.Member, player_tag: str):
    "Leader/Admin only. Update selected user to use information associated with given player tag (include # symbol). Updates Clash username, Discord username, and clan data in database. Changes nickname to Clash username."
    discord_name = member.name + "#" + member.discriminator
    clashData = clash_utils.GetClashUserData(player_tag, discord_name)

    if clashData == None:
        await ctx.send(f"Something went wrong retrieving Clash information from player tag {player_tag}. Information for {member.display_name} has not been updated.")
        return

    db_utils.RemoveUser(member.display_name)

    rolesToRemoveList = list(NORMAL_ROLES.values())
    rolesToRemoveList.append(SPECIAL_ROLES["New"])
    rolesToRemoveList.append(SPECIAL_ROLES["Check Rules"])
    await member.remove_roles(*rolesToRemoveList)

    if not db_utils.AddNewUser(clashData):
        await ctx.send(f"{member.display_name} was removed from database but there was an issue adding them back with new player tag. They might need to be reset now.")
        return

    dbRoles = db_utils.GetRoles(clashData["player_name"])
    savedRoles = []
    for role in dbRoles:
        savedRoles.append(NORMAL_ROLES[role])
    await member.add_roles(*savedRoles)

    if (SPECIAL_ROLES["Admin"] in member.roles) or (member.guild_permissions.administrator):
        if clashData["player_name"] != member.display_name:
            await ctx.send(f"{member.display_name} has been updated in the database, but their in-game name no longer matches their Discord nickname. {member.mention} Admins need to update their nicknames manually due to permissions.")
    else:
        await member.edit(nick=clashData["player_name"])

    await ctx.send(f"{member.display_name} has been updated. If they were a leader or elder, they must be reassigned those roles manually.")

@update_user.error
async def update_user_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    elif isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!update_user command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !update_user <member> <player_tag>")
    elif isinstance(error, commands.errors.CommandInvokeError):
        await ctx.send("Something went wrong. Make sure the player tag you entered doesn't belong to another user in this server. Command should be formatted as:  !update <player_tag>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !update_user <member> <player_tag>")
        raise error


# Reset user

@bot.command()
@is_admin_command_check()
@channel_check(COMMANDS_CHANNEL)
async def reset_user(ctx, member: discord.Member):
    "Admin only. Delete selected user from database. Set their role to New."
    await ResetUser(member, True)
    await ctx.send(f"{member.display_name} has been reset.")

@reset_user.error
async def reset_user_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    elif isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!reset_user command can only be sent in {channel.mention} by Admins.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !reset_user <member>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !reset_user <member>")
        raise error


# Reset all users

@bot.command()
@is_admin_command_check()
@channel_check(COMMANDS_CHANNEL)
async def reset_all_users(ctx, confirmation: str):
    "Admin only. Deletes all users from database, removes roles, and assigns New role. Leaders retain Leader role. Leaders must still resend player tag in welcome channel and react to rules message."
    confirmationMessage = "Yes, I really want to drop all players from the database and reset roles."

    if (confirmation != confirmationMessage):
        await ctx.send("Users NOT reset. Must type the following confirmation message exactly, in quotes, along with reset_all_users command:\n" + confirmationMessage)
        return

    await ctx.send("Deleting all users from database... This might take a couple minutes.")

    db_utils.RemoveAllUsers()

    for member in ctx.guild.members:
        await ResetUser(member, False)

    await SendRulesMessage(ctx)

    adminRole = SPECIAL_ROLES["Admin"]
    await ctx.send(f"All users have been reset. If you are a {adminRole.mention}, please send your player tag in the welcome channel to be re-added to the database. Then, react to the rules message to automatically get all roles back. Finally, update your Discord nickname to match your in-game username.")

@reset_all_users.error
async def reset_all_users_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!reset_all_users command can only be sent in {channel.mention} by Admins.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing confirmation. Command should be formatted as:  !reset_all_users <confirmation>. Make sure to enclose the confirmation message in quotes.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !reset_all_users <confirmation>. Make sure to enclose the confirmation message in quotes.")
        raise error


# Vacation

@bot.command()
@channel_check(TIME_OFF_CHANNEL)
async def vacation(ctx):
    "Toggles vacation status."
    vacationStatus = db_utils.UpdateVacationForUser(ctx.author.display_name)
    vacationStatusString = ("NOT " if not vacationStatus else "") + "ON VACATION"
    await ctx.send(f"New vacation status for {ctx.author.mention}: {vacationStatusString}.")

@vacation.error
async def vacation_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.members, name=TIME_OFF_CHANNEL)
        await ctx.send(f"!vacation command can only be sent in {channel.mention}.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !vacation")
        raise error


# Set vacation

@bot.command()
@is_leader_command_check()
async def set_vacation(ctx, member: discord.Member, status: bool):
    "Leader/Admin only. Sets vacation status of target user."
    channel = discord.utils.get(ctx.guild.channels, TIME_OFF_CHANNEL)
    vacationStatus = db_utils.UpdateVacationForUser(player_name, status)
    vacationStatusString = ("NOT " if not vacationStatus else "") + "ON VACATION"
    await channel.send(f"Updated vacation status of {member.mention} to: {vacationStatusString}.")

@set_vacation.error
async def set_vacation_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    elif isinstance(error, commands.errors.CheckFailure):
        await ctx.send(f"!set_vacation command can only be sent by Leaders/Admins.")
    elif isinstance(error, commands.errors.BadBoolArgument):
        await ctx.send(f"Invalid second argument. Valid statuses: on or off")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !set_vacation <member> <status>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !set_vacation <member> <status>")
        raise error


# Vacation List

@bot.command()
@is_leader_command_check()
async def vacation_list(ctx):
    "Leader/Admin only. Gets list of all users currently on vacation."
    vacationList = db_utils.GetVacationStatus()
    table = PrettyTable()
    table.field_names = ["Member"]
    embed = discord.Embed()

    for user in vacationList:
        table.add_row([user])

    embed.add_field(name="Vacation List", value="```\n" + table.get_string() + "```")

    try:
        await ctx.send(embed=embed)
    except:
        await ctx.send("Vacation List\n" + "```\n" + table.get_string() + "```")

@vacation_list.error
async def vacation_list_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send(f"!vacation_list command can only be sent by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !vacation_list")
        raise error


# Export

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def export(ctx, UpdateBeforeExport: bool=True, FalseLogicOnly: bool=True):
    "Leader/Admin only. Export database to csv file. Optionally specify whether to update users in database before exporting and whether to only export False Logic users. These are both enabled by default"
    if (UpdateBeforeExport):
        await ctx.send("Starting export and updating all player information. This might take a minute.")
        for member in ctx.guild.members:
            await UpdateUser(ctx, member)

    db_utils.OutputToCSV("members.csv", FalseLogicOnly)
    await ctx.send(file=discord.File("members.csv"))

@export.error
async def export_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!export command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.BadBoolArgument):
        await ctx.send(f"Invalid argument. Valid arguments: yes or no")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !export <UpdateBeforeExport (optional)> <FalseLogicOnly (optional)>")
        raise error


# Force rules check

@bot.command()
@is_admin_command_check()
@channel_check(COMMANDS_CHANNEL)
async def force_rules_check(ctx):
    "Admin only. Strip roles from all non-leaders until they acknowledge new rules. Clash bot will send message to react to in rules channel."
    # Get a list of members in guild without any special roles (New, Check Rules, or Admin) and that aren't bots.
    membersList = [member for member in ctx.guild.members if ((len(set(SPECIAL_ROLES.values()).intersection(set(member.roles))) == 0) and (not member.bot))]
    rolesToRemoveList = list(NORMAL_ROLES.values())

    for member in membersList:
        # Get a list of normal roles (Visitor, Member, Elder, or Leader) that a member current has. These will be restored after reacting to rules message.
        roleStringsToCommit = [ role.name for role in list(set(NORMAL_ROLES.values()).intersection(set(member.roles))) ]
        db_utils.CommitRoles(member.display_name, roleStringsToCommit)
        await member.remove_roles(*rolesToRemoveList)
        await member.add_roles(SPECIAL_ROLES["Check Rules"])

    await SendRulesMessage(ctx)

@force_rules_check.error
async def force_rules_check_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!force_rules_check command can only be sent in {channel.mention} by Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !force_rules_check")
        raise error


# Set strike count

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def set_strike_count(ctx, member: discord.Member, strikes: int):
    "Leader/Admin only. Set specified user's strike count to specified value."
    strikeTuple = db_utils.SetStrikes(member.display_name, strikes)

    if strikeTuple == None:
        await ctx.send("Player not found in database. No strike adjustments have been made.")
        return

    channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
    await channel.send(f"Strikes updated for {member.mention}.  {strikeTuple[0]} -> {strikeTuple[1]}")

@set_strike_count.error
async def set_strike_count_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    elif isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!set_stike_count command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error,commands.errors.BadArgument):
        await ctx.send("Invalid strikes value. Strikes must be an integer value.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !set_strike_count <member> <strikes>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !set_strike_count <member> <strikes>")
        raise error


@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def give_strike(ctx, members: commands.Greedy[discord.Member]):
    "Leader/Admin only. Specify a list of members and increment each user's strike count by 1."
    channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
    strikeString = "The following members have each received a strike:\n"
    memberString = ""

    for member in members:
        newStrikeCount = db_utils.AddStrike(member.display_name)
        if newStrikeCount == 0:
            continue

        memberString += f"{member.mention}: {newStrikeCount - 1} -> {newStrikeCount}" + "\n"

    if len(memberString) == 0:
        await ctx.send("You either didn't specify any members, or none of the members you specified exist in the database. No strikes have been assigned.")
        return

    strikeString += memberString
    await channel.send(strikeString)

@give_strike.error
async def give_strike_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!mention_users command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !give_strike <members>")
        raise error


# Strikes

@bot.command()
async def strikes(ctx):
    "Get your current strike count."
    strikes = db_utils.GetStrikes(ctx.author.display_name)
    message = ""

    if strikes == None:
        message = "Error, you were not found in the database."
    else:
        message = f"You currently have {strikes} strikes."

    await ctx.send(message)

@strikes.error
async def strikes_error(ctx, error):
    await ctx.send("Something went wrong. Command should be formatted as:  !strikes")
    raise error


# Reset all strikes

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def reset_all_strikes(ctx):
    "Leader/Admin only. Reset each member's strikes to 0."
    db_utils.ResetStrikes()
    channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
    await channel.send("Strikes for all members have been reset to 0.")

@reset_all_strikes.error
async def reset_all_strikes_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!send_reminder command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !reset_all_strikes")
        raise error


# Strike report

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def status_report_strikes(ctx):
    "Leader/Admin only. Get a report of players with strikes."
    strikeList = db_utils.GetStrikes()
    table = PrettyTable()
    table.field_names = ["Member", "Strikes"]
    embed = discord.Embed(title="Status Report")

    for player_name, strikes in strikeList:
        table.add_row([player_name, strikes])

    embed.add_field(name="Players with at least 1 strike", value = "```\n" + table.get_string() + "```")

    try:
        await ctx.send(embed=embed)
    except:
        await ctx.send("Players with at least 1 strike\n" + "```\n" + table.get_string() + "```")

@status_report_strikes.error
async def status_report_strikes_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!status_report_strikes command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !status_report_strikes")
        raise error


# Send reminder

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def send_reminder(ctx, *message):
    "Leader/Admin only. Send message to reminders channel tagging users who still have battles to complete. Excludes members currently on vacation. Optionally specify the message you want sent with the reminder."
    reminderMessage = ' '.join(message)
    if len(reminderMessage) == 0:
        reminderMessage = DEFAULT_REMINDER_MESSAGE
    await DeckUsageReminder(None, reminderMessage, False)

@send_reminder.error
async def send_reminder_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!send_reminder command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !send_reminder <message (optional)>")
        raise error


# Status report decks

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def status_report_decks(ctx):
    "Leader/Admin only. Get a report of players with decks remaining today."
    usageList = clash_utils.GetDeckUsageToday()
    vacationList = db_utils.GetVacationStatus()
    table = PrettyTable()
    table.field_names = ["Member", "Decks"]
    embed = discord.Embed(title="Status Report", footer="Users on vacation are not included in this list")

    for player_name, decks_remaining in usageList:
        if player_name in vacationList:
            continue

        table.add_row([player_name, decks_remaining])

    embed.add_field(name="Players with decks remaining", value = "```\n" + table.get_string() + "```")

    try:
        await ctx.send(embed=embed)
    except:
        await ctx.send("Players with decks remaining\n" + "```\n" + table.get_string() + "```")

@status_report_decks.error
async def status_report_decks_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!status_report_decks command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !status_report_decks")
        raise error

# Set automated reminders

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def set_automated_reminders(ctx, status: bool):
    "Leader/Admin only. Set whether automated reminders should be sent."
    db_utils.SetReminderStatus(status)
    await ctx.channel.send("Automated deck usage reminders are now " + ("ENABLED" if status else "DISABLED") + ".")

@set_automated_reminders.error
async def set_automated_reminders_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!set_automated_reminders command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.BadBoolArgument):
        await ctx.send("Invalid argument. Valid statuses are: on or off")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !set_automated_reminders <status>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !set_automated_reminders <status>")
        raise error


# Set automated strikes

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def set_automated_strikes(ctx, status: bool):
    "Leader/Admin only. Set whether automated strikes should be given."
    db_utils.SetStrikeStatus(status)
    await ctx.channel.send("Automated strikes for low deck usage are now " + ("ENABLED" if status else "DISABLED") + ".")

@set_automated_strikes.error
async def set_automated_strikes_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!set_automated_strikes command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.BadBoolArgument):
        await ctx.send("Invalid argument. Valid statuses are: on or off")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !set_automated_strikes <status>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !set_automated_strikes <status>")
        raise error


# Get automation status

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def get_automation_status(ctx):
    "Leader/Admin only. Get status of whether automated strikes and reminders are enabled."
    strikeStatus = "ENABLED" if db_utils.GetStrikeStatus() else "DISABLED"
    reminderStatus = "ENABLED" if db_utils.GetReminderStatus() else "DISABLED"
    statusString = f"Automated reminders are currently {reminderStatus}" + "\n" + f"Automated strikes are currently {strikeStatus}"
    await ctx.send(statusString)

@get_automation_status.error
async def get_automation_status_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!get_automation_status command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !get_automation_status")
        raise error


# Top fame

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def top_fame(ctx):
    "Leader/Admin only. Send a list of top users by fame in the fame channel."
    await TopFame()

@top_fame.error
async def top_fame_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!top_fame command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !top_fame")
        raise error


# Fame check

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def fame_check(ctx, threshold: int):
    "Leader/Admin only. Mention users below the specified fame threshold. Ignores users on vacation."
    hallOfShame = clash_utils.GetHallOfShame(threshold)
    vacationList = db_utils.GetVacationStatus()
    channel = discord.utils.get(guild.channels, name=REMINDER_CHANNEL)

    memberString = ""
    nonMemberString = ""

    for player_name, fame in hallOfShame:
        if player_name in vacationList:
            continue

        member = discord.utils.get(channel.members, display_name=player_name)

        if member == None:
            nonMemberString += f"{player_name} - Fame: {fame}" + "\n"
        else:
            memberString += f"{member.mention} - Fame: {fame}" + "\n"

    if (len(memberString) == 0) and (len(nonMemberString) == 0):
        await ctx.send("There are currently no members currently below the threshold you specified.")
        return

    fameString = f"The following members are below {threshold} fame:" + "\n" + memberString + nonMemberString

    await channel.send(fameString)

@fame_check.error
async def fame_check_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!fame_check command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.BadArgument):
        await ctx.send("Invalid fame threshold. Fame must be an integer value.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !fame_check <threshold>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !fame_check <threshold>")
        raise error


# Status report fame

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def status_report_fame(ctx, threshold: int):
    "Leader/Admin only. Get a report of players below specifiec fame threshold. Ignores users on vacation. Users are not mentioned."
    hallOfShame = clash_utils.GetHallOfShame(threshold)
    vacationList = db_utils.GetVacationStatus()
    table = PrettyTable()
    table.field_names = ["Member", "Fame"]
    embed = discord.Embed(title="Status Report", footer="Users on vacation are not included in this list")

    for player_name, fame in hallOfShame:
        if player_name in vacationList:
            continue

        table.add_row([player_name, fame])

    embed.add_field(name="Players below fame threshold", value = "```\n" + table.get_string() + "```")

    try:
        await ctx.send(embed=embed)
    except:
        await ctx.send("Players below fame threshold\n" + "```\n" + table.get_string() + "```")

@status_report_fame.error
async def status_report_fame_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!status_report_fame command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !status_report_fame <threshold>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !status_report_fame <threshold>")
        raise error


# Mention users

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def mention_users(ctx, members: commands.Greedy[discord.Member], channel: discord.TextChannel, message: str):
    "Leader/Admin only. Send message to channel mentioning specified users. Message must be enclosed in quotes."
    messageString = ""

    for member in members:
        messageString += member.mention + " "
    
    messageString += "\n" + message

    await channel.send(messageString)

@mention_users.error
async def mention_users_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!mention_users command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.CommandInvokeError):
        await ctx.send("Clash bot needs permission to send messages to the specified channel.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !mention_users <members> <channel> <message>")
        raise error


# River race status

@bot.command()
async def river_race_status(ctx):
    "Send a list of clans in the current river race and their number of decks remaining today."
    clanList = clash_utils.GetOtherClanDecksRemaining()
    embed = discord.Embed(title="Current River Race Status")

    table = PrettyTable()
    table.field_names = ["Clan", "Decks"]

    for clan in clanList:
        table.add_row([clan[0], clan[1]])

    embed.add_field(name="Remaining decks for each clan", value="```\n" + table.get_string() + "```")

    await ctx.send(embed=embed)

@river_race_status.error
async def river_race_status_error(ctx, error):
    await ctx.send("Something went wrong. Command should be formatted as:  !current_river_race_status")
    raise error


@bot.command()
async def set_reminder_time(ctx, reminder_time: str):
    "Set reminder time to either US or EU. US reminders go out at 01:00 UTC. EU reminders go out at 17:00 UTC."
    timeZone = None
    if reminder_time == "US":
        timeZone = True
    elif reminder_time == "EU":
        timeZone = False
    else:
        await ctx.send("Invalid time zone. Valid reminder times are US or EU")
        return

    db_utils.UpdateTimeZone(ctx.author.display_name, timeZone)
    await ctx.send("Your reminder time preference has been updated.")

@set_reminder_time.error
async def set_reminder_time_error(ctx, error):
    if isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("You need to specify a reminder time. Valid reminder times are US or EU")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !set_reminder_time <reminder_time>")
        raise error


# Send reminder every Monday and Tuesday at 19:00 UTC (Monday and Tuesday at 7pm GMT)
@aiocron.crontab('0 19 * * 1,2')
async def AutomatedReminderEU():
    if (db_utils.GetReminderStatus()):
        await DeckUsageReminder(US_time=False)


# Send reminder every Tuesday and Wednesday at 01:00 UTC (Monday and Tuesday at 6pm PDT)
@aiocron.crontab('0 1 * * 2,3')
async def AutomatedReminderUS():
    if (db_utils.GetReminderStatus()):
        await DeckUsageReminder(US_time=True)

# Assign strikes, clear vacation
# Occurs every Wednesday 10:00 UTC (Wednesday 3:00am PDT)
@aiocron.crontab('32 9 * * 3')
async def AssignStrikesAndClearVacation():
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    vacationChannel = discord.utils.get(guild.channels, name=TIME_OFF_CHANNEL)
    strikesChannel = discord.utils.get(guild.channels, name=STRIKES_CHANNEL)
    savedMessage = ""

    if db_utils.GetStrikeStatus():
        vacationList = db_utils.GetVacationStatus()
        deckUsageList = clash_utils.GetDeckUsage()

        memberString = ""
        nonMemberString = ""

        for player_name, deck_usage in deckUsageList:
            if player_name in vacationList:
                continue

            member = discord.utils.get(strikesChannel.members, display_name=player_name)
            strikes = db_utils.AddStrike(player_name)

            if member == None:
                prevStrikes = 0 if strikes == 0 else strikes - 1
                nonMemberString += f"{player_name} - Decks used: {deck_usage},  Strikes: {prevStrikes} -> {strikes}" + "\n"
            else:
                memberString += f"{member.mention} - Decks used: {deck_usage},  Strikes: {strikes - 1} -> {strikes}" + "\n"

        if (len(memberString) == 0) and (len(nonMemberString) == 0):
            savedMessage = "Everyone completed their battles this week. Good job!"
        else:
            savedMessage = "The following members have received strikes for failing to complete 8 battles:\n" + memberString + nonMemberString
    else:
        savedMessage = "Automated strikes are currently disabled so no strikes have been given out."

    db_utils.SetSavedMessage(savedMessage)
    db_utils.ClearAllVacation()
    await vacationChannel.send("Vacation status for all users has been set to false. Make sure to use !vacation before the next war if you're going to miss it.")


# Send saved message of who received automated strikes
# Occurs every Wednesday 18:00 UTC (Wednesday 11:00am PDT)
@aiocron.crontab('0 18 * * 3')
async def SendSavedMessage():
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    strikesChannel = discord.utils.get(guild.channels, name=STRIKES_CHANNEL)
    message = db_utils.GetSavedMessage()
    db_utils.SetSavedMessage("")
    await strikesChannel.send(message)


async def DeckUsageReminder(US_time: bool=None, message: str=DEFAULT_REMINDER_MESSAGE, automated: bool=True):
    reminderList = clash_utils.GetDeckUsageToday()
    vacationList = db_utils.GetVacationStatus()
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    channel = discord.utils.get(guild.channels, name=REMINDER_CHANNEL)

    if len(reminderList) == 0:
        return

    memberString = ""
    nonMemberString = ""

    checkTimeZones = (US_time != None)
    timeZoneList = []

    if checkTimeZones:
        timeZoneList = db_utils.GetMembersInTimezone(US_time)
        if timeZoneList == None:
            checkTimeZones = False

    for player_name, decks_remaining in reminderList:
        if player_name in vacationList:
            continue

        if (checkTimeZones and (player_name not in timeZoneList)):
            continue

        member = discord.utils.get(channel.members, display_name=player_name)

        if member == None:
            nonMemberString += f"{player_name} - Decks left: {decks_remaining}" + "\n"
        else:
            memberString += f"{member.mention} - Decks left: {decks_remaining}" + "\n"

    if (len(memberString) == 0) and (len(nonMemberString) == 0):
        if checkTimeZones:
            zone = "US" if US_time else "EU"
            noReminderString = f"Everyone that receives {zone} reminders has already used all their decks today. Good job!"
            await channel.send(noReminderString)
        else:
            await channel.send("Everyone has already used all their decks today. Good job!")
        return

    reminderString = message + "\n" + memberString + nonMemberString

    if automated:
        automatedMessage = ''
        if US_time:
            automatedMessage = 'This is an automated reminder. If this reminder is in the middle of the night for you, consider switching your reminder time to 7PM GMT with command "!set_reminder_time EU"'
        else:
            automatedMessage = 'This is an automated reminder. If this reminder is in the middle of the day for you, consider switching your reminder time to 6PM PDT with command "!set_reminder_time US"'
        reminderString += "\n\n" + automatedMessage

    await channel.send(reminderString)


async def TopFame():
    topUsers = clash_utils.GetTopFameUsers()
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    channel = discord.utils.get(guild.channels, name=FAME_CHANNEL)
    table = PrettyTable()
    table.field_names = ["Member", "Fame"]
    embed = discord.Embed()

    for user in topUsers:
        table.add_row([user[0], user[1]])

    embed.add_field(name="Top members by fame", value="```\n" + table.get_string() + "```")

    try:
        await channel.send(embed=embed)
    except:
        await channel.send("Top members by fame\n" + "```\n" + table.get_string() + "```")


async def UpdateUser(ctx, member: discord.Member, player_tag = None) -> bool:
    if (member.bot or player_tag == None):
        player_tag = db_utils.GetPlayerTag(member.display_name)

    if (player_tag == None):
        return False

    discord_name = member.name + "#" + member.discriminator
    clashData = clash_utils.GetClashUserData(player_tag, discord_name)

    if clashData == None:
        return False

    db_utils.UpdateUser(clashData)

    if (SPECIAL_ROLES["Admin"] in member.roles) or (member.guild_permissions.administrator):
        if clashData["player_name"] != member.display_name:
            await ctx.send(f"{member.display_name} has been updated in the database, but their in-game name no longer matches their Discord nickname. {member.mention} Admins need to update their nicknames manually due to permissions.")
    else:
        await member.edit(nick=clashData["player_name"])

    return True


async def ResetUser(member: discord.Member, removeFromDB: bool):
    if member.bot:
        return

    rolesToRemoveList = list(NORMAL_ROLES.values())
    rolesToRemoveList.append(SPECIAL_ROLES["Check Rules"])
    await member.remove_roles(*rolesToRemoveList)
    await member.add_roles(SPECIAL_ROLES["New"])

    if (removeFromDB):
        db_utils.RemoveUser(member.display_name)


async def SendRulesMessage(ctx):
    rulesChannel = discord.utils.get(ctx.guild.channels, name=RULES_CHANNEL)
    await rulesChannel.purge(limit=10, check=lambda message: message.author == bot.user)
    newReactMessage = await rulesChannel.send(content="@everyone After you've read the rules, react to this message for roles.")
    await newReactMessage.add_reaction(u"\u2705")


bot.run(BOT_TOKEN)