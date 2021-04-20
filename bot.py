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


# Update user

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def update_user(ctx, member: discord.Member, player_tag: str):
    "Leader/Admin only. Update selected user to use information associated with given player_tag. Change information in database and update Discord nickname"
    await UpdateUser(ctx, member, player_tag)
    await ctx.send(f"{member.display_name} has been updated.")

@update_user.error
async def update_user_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    elif isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!update_user command can only be sent in {channel.mention} by Leaders/Admins.")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !update_user <member> <player_tag>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !update_user <member> <player_tag>")
        raise error


# Reset user

@bot.command()
@is_admin_command_check()
@channel_check(COMMANDS_CHANNEL)
async def reset_user(ctx, member: discord.Member):
    "Admin only. Delete selected user from database. Reset their role to New."
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

    if (safety_message != confirmationMessage):
        await ctx.send("Users NOT reset. Must type the following confirmation message exactly, in quotes, along with reset_all_users command:\n" + confirmationMessage)
        return

    await ctx.send("Deleting all users... This might take a minute.")

    db_utils.RemoveAllUsers()

    for member in ctx.guild.members:
        await ResetUser(member, False)

    adminRole = SPECIAL_ROLES["Admin"]
    await ctx.send(f"All users have been reset. If you are a {adminRole.mention}, please send your player tags in the welcome channel to be re-added to the database. Then, react to the rules message to automatically get all roles back.")

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
@channel_check(TIME_OFF_CHANNEL)
async def set_vacation(ctx, member: discord.Member, status: bool):
    "Leader/Admin only. Sets vacation status of target user."
    vacationStatus = db_utils.UpdateVacationForUser(player_name, status)
    vacationStatusString = ("NOT " if not vacationStatus else "") + "ON VACATION"
    await ctx.send(f"Updated vacation status of {member.mention} to: {vacationStatusString}.")

@set_vacation.error
async def set_vacation_error(ctx, error):
    if isinstance(error, commands.errors.MemberNotFound):
        await ctx.send("Member not found.")
    elif isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=TIME_OFF_CHANNEL)
        await ctx.send(f"!set_vacation command can only be sent in {channel.mention} by Leaders/Admins.")
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
@channel_check(TIME_OFF_CHANNEL)
async def vacation_list(ctx):
    "Leader/Admin only. Gets list of all users currently on vacation. Used in time off channel."
    vacationList = db_utils.GetVacationStatus()
    table = PrettyTable()
    table.field_names = ["Member"]
    embed = discord.Embed()

    for user in vacationList:
        table.add_row([user])

    embed.add_field(name="Vacation List", value="```\n" + table.get_string() + "```")

    await ctx.send(embed=embed)

@vacation_list.error
async def vacation_list_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=TIME_OFF_CHANNEL)
        await ctx.send(f"!vacation_list command can only be sent in {channel.mention} by Leaders/Admins.")
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

    rulesChannel = discord.utils.get(ctx.guild.channels, name=RULES_CHANNEL)
    await rulesChannel.purge(limit=10, check=lambda message: message.author == bot.user)
    newReactMessage = await rulesChannel.send(content="@everyone After you've read the rules, react to this message for roles.")
    await newReactMessage.add_reaction(u"\u2705")

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


# Send reminder

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def send_reminder(ctx, *message):
    "Leader/Admin only. Send message to reminders channel tagging users who still have battles to complete. Excludes members currently on vacation. Optionally specify the message you want sent with the reminder."
    reminderMessage = ' '.join(message)
    if len(reminderMessage) == 0:
        reminderMessage = DEFAULT_REMINDER_MESSAGE
    await DeckUsageReminder(reminderMessage)

@send_reminder.error
async def send_reminder_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!send_reminder command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !send_reminder <message (optional)>")
        raise error


# Set automated reminders

@bot.command()
@is_admin_command_check()
@channel_check(COMMANDS_CHANNEL)
async def set_automated_reminders(ctx, status: bool):
    "Admin only. Set whether automated reminders should be sent."
    db_utils.SetReminderStatus(status)
    await ctx.channel.send("Automated deck usage reminders are now " + ("ENABLED" if status else "DISABLED") + ".")

@set_automated_reminders.error
async def set_automated_reminders_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!set_automated_reminders command can only be sent in {channel.mention} by Admins.")
    elif isinstance(error, commands.errors.BadBoolArgument):
        await ctx.send("Invalid argument. Valid statuses are: on or off")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !set_automated_reminders <status>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !set_automated_reminders <status>")
        raise error


# Set automated strikes

@bot.command()
@is_admin_command_check()
@channel_check(COMMANDS_CHANNEL)
async def set_automated_strikes(ctx, status: bool):
    "Admin only. Set whether automated strikes should be given."
    db_utils.SetStrikeStatus(status)
    await ctx.channel.send("Automated strikes for low deck usage are now " + ("ENABLED" if status else "DISABLED") + ".")

@set_automated_strikes.error
async def set_automated_strikes_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!set_automated_strikes command can only be sent in {channel.mention} by Admins.")
    elif isinstance(error, commands.errors.BadBoolArgument):
        await ctx.send("Invalid argument. Valid statuses are: on or off")
    elif isinstance(error, commands.errors.MissingRequiredArgument):
        await ctx.send("Missing arguments. Command should be formatted as:  !set_automated_strikes <status>")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !set_automated_strikes <status>")
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
    "Leader/Admin only. Mention users below fame threshold in the fame channel."
    await FameCheck(threshold)

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


# Get river race status

@bot.command()
@is_leader_command_check()
@channel_check(COMMANDS_CHANNEL)
async def river_race_status(ctx):
    "Leader/Admin only. Send a list of clans in the current river race and their number of decks remaining today."
    clanList = clash_utils.GetOtherClanDecksRemaining()
    channel = discord.utils.get(ctx.guild.channels, name=REMINDER_CHANNEL)
    embed = discord.Embed(title="Current River Race Status")

    table = PrettyTable()
    table.field_names = ["Clan", "Decks"]

    for clan in clanList:
        table.add_row([clan[0], clan[1]])

    embed.add_field(name="Remaining decks for each clan", value="```\n" + table.get_string() + "```")

    await channel.send(embed=embed)

@river_race_status.error
async def river_race_status_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
        await ctx.send(f"!river_race_status command can only be sent in {channel.mention} by Leaders/Admins.")
    else:
        await ctx.send("Something went wrong. Command should be formatted as:  !current_river_race_status")
        raise error



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


async def DeckUsageReminder(message: str=DEFAULT_REMINDER_MESSAGE):
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
            otherMembersToRemind.append(f"{nameTuple[0]} - Decks left: {nameTuple[1]}")
        else:
            membersToRemind.append(f"{member.mention} Decks left: {nameTuple[1]}")

    reminderString = message + "\n" + '\n'.join(membersToRemind)

    if len(otherMembersToRemind) > 0:
        reminderString += "\n\nMembers not in this channel:\n" + '\n'.join(otherMembersToRemind)

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

    await channel.send(embed=embed)


async def FameCheck(threshold: int):
    hallOfShame = clash_utils.GetHallOfShame(threshold)
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    channel = discord.utils.get(guild.channels, name=REMINDER_CHANNEL)

    membersString = ""
    otherMembersString = ""

    for nameTuple in hallOfShame:
        member = discord.utils.get(channel.members, display_name=nameTuple[0])
        if member == None:
            otherMembersString += f"{nameTuple[0]}: - Fame: {nameTuple[1]}" + "\n"
        else:
            membersString += f"{member.mention} Fame: {nameTuple[1]}" + "\n"

    fameString = f"The following members are below the fame threshold of {threshold}:" + "\n" + membersString

    if len(otherMembersString) > 0:
        fameString += "\nMembers below the threshold not in this channel:\n" + otherMembersString

    await channel.send(fameString)


async def UpdateUser(ctx, member: discord.Member, player_tag = None):
    if (player_tag == None):
        player_tag = db_utils.GetPlayerTag(member.display_name)

    if (player_tag == None):
        return

    discord_name = member.name + "#" + member.discriminator
    clashData = clash_utils.GetClashUserData(player_tag, discord_name)
    db_utils.UpdateUser(clashData)

    if SPECIAL_ROLES["Admin"] in member.roles:
        if clashData["player_name"] != member.display_name:
            await ctx.send(f"{member.display_name} has been updated in the database, but their in-game name no longer matches their Discord nickname. {member.mention} Admins need to update their nicknames manually due to permissions.")
    else:
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