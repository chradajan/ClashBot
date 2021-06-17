from config import *
from discord.ext import commands
import discord
import clash_utils
import datetime
import db_utils

######################################################
#                                                    #
#     _____                _              _          #
#    / ____|              | |            | |         #
#   | |     ___  _ __  ___| |_ __ _ _ __ | |_ ___    #
#   | |    / _ \| '_ \/ __| __/ _` | '_ \| __/ __|   #
#   | |___| (_) | | | \__ \ || (_| | | | | |_\__ \   #
#    \_____\___/|_| |_|___/\__\__,_|_| |_|\__|___/   #
#                                                    #
######################################################

RESET_TIME = datetime.time(9, 33)
SIX_DAY_MASK = 0x3FFFF
ONE_DAY_MASK = 0x7

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


#########################################
#     _____ _               _           #
#    / ____| |             | |          #
#   | |    | |__   ___  ___| | _____    #
#   | |    | '_ \ / _ \/ __| |/ / __|   #
#   | |____| | | |  __/ (__|   <\__ \   #
#    \_____|_| |_|\___|\___|_|\_\___/   #
#                                       #
#########################################


async def is_admin(member: discord.Member) -> bool:
    return (SPECIAL_ROLES[ADMIN_ROLE_NAME] in member.roles) or member.guild_permissions.administrator

def is_leader_command_check():
    async def predicate(ctx):
        return (NORMAL_ROLES[LEADER_ROLE_NAME] in ctx.author.roles) or (SPECIAL_ROLES[ADMIN_ROLE_NAME] in ctx.author.roles)
    return commands.check(predicate)

def is_admin_command_check():
    async def predicate(ctx):
        return await is_admin(ctx.author)
    return commands.check(predicate)

def channel_check(CHANNEL_NAME):
    async def predicate(ctx):
        return ctx.message.channel.name == CHANNEL_NAME
    return commands.check(predicate)


###########################################
#                                         #
#    _    _      _                        #
#   | |  | |    | |                       #
#   | |__| | ___| |_ __   ___ _ __ ___    #
#   |  __  |/ _ \ | '_ \ / _ \ '__/ __|   #
#   | |  | |  __/ | |_) |  __/ |  \__ \   #
#   |_|  |_|\___|_| .__/ \___|_|  |___/   #
#                 | |                     #
#                 |_|                     #
#                                         #
###########################################



async def send_rules_message(ctx, user_to_purge: discord.ClientUser):
    rules_channel = discord.utils.get(ctx.guild.channels, name=RULES_CHANNEL)
    await rules_channel.purge(limit=10, check=lambda message: message.author == user_to_purge)
    new_react_message = await rules_channel.send(content="@everyone After you've read the rules, react to this message for roles.")
    await new_react_message.add_reaction(u"\u2705")


async def deck_usage_reminder(bot, US_time: bool=None, message: str=DEFAULT_REMINDER_MESSAGE, automated: bool=True):
    reminder_list = clash_utils.get_remaining_decks_today()
    vacation_list = db_utils.get_vacation_list()
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    channel = discord.utils.get(guild.channels, name=REMINDER_CHANNEL)

    if len(reminder_list) == 0:
        return

    member_string = ""
    non_member_string = ""

    check_time_zones = (US_time != None)
    time_zone_list = []

    if check_time_zones:
        time_zone_list = db_utils.get_members_in_time_zone(US_time)
        if time_zone_list == None:
            check_time_zones = False

    for player_name, decks_remaining in reminder_list:
        if player_name in vacation_list:
            continue

        if check_time_zones and (player_name not in time_zone_list):
            continue

        member = discord.utils.get(channel.members, display_name=player_name)

        if member == None:
            non_member_string += f"{player_name} - Decks left: {decks_remaining}" + "\n"
        else:
            member_string += f"{member.mention} - Decks left: {decks_remaining}" + "\n"

    if (len(member_string) == 0) and (len(non_member_string) == 0):
        if check_time_zones:
            zone = "US" if US_time else "EU"
            no_reminder_string = f"Everyone that receives {zone} reminders has already used all their decks today. Good job!"
            await channel.send(no_reminder_string)
        else:
            await channel.send("Everyone has already used all their decks today. Good job!")
        return

    reminder_string = message + "\n" + member_string + non_member_string

    if automated:
        automated_message = ''
        if US_time:
            automated_message = 'This is an automated reminder. If this reminder is in the middle of the night for you, consider switching your reminder time to 7PM GMT with command "!set_reminder_time EU"'
        else:
            automated_message = 'This is an automated reminder. If this reminder is in the middle of the day for you, consider switching your reminder time to 6PM PDT with command "!set_reminder_time US"'
        reminder_string += "\n\n" + automated_message

    await channel.send(reminder_string)


async def update_member(member: discord.Member, player_tag: str = None) -> bool:
    if member.bot:
        return False

    if player_tag == None:
        player_tag = db_utils.get_player_tag(member.display_name)

    if player_tag == None:
        return False

    discord_name = member.name + "#" + member.discriminator
    clash_data = clash_utils.get_clash_user_data(player_tag, discord_name)

    if clash_data == None:
        return False

    member_status = db_utils.update_user(clash_data, member.display_name)

    if not await is_admin(member):
        if clash_data["player_name"] != member.display_name:
            await member.edit(nick = clash_data["player_name"])

        roles_to_remove = [NORMAL_ROLES[MEMBER_ROLE_NAME], NORMAL_ROLES[VISITOR_ROLE_NAME], NORMAL_ROLES[ELDER_ROLE_NAME]]
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(NORMAL_ROLES[member_status])

        if clash_data["clan_role"] == "elder":
            await member.add_roles(NORMAL_ROLES[ELDER_ROLE_NAME])

    return True


# [(most_recent_usage, day_string), (second_most_recent_usage, day_string), ...]
def break_down_usage_history(deck_usage: int, command_time: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)) -> list:
    time_delta = None

    if command_time.time() > RESET_TIME:
        time_delta = datetime.timedelta(days=1)
    else:
        time_delta = datetime.timedelta(days=2)

    usage_history = []

    for i in range(7):
        temp_usage = deck_usage & ONE_DAY_MASK
        deck_usage >>= 3
        temp_date = (command_time - time_delta).date()
        date_string = temp_date.strftime("%a") + ", " +  temp_date.strftime("%b") + " " + str(temp_date.day).zfill(2)
        usage_history.append((temp_usage, date_string))
        time_delta += datetime.timedelta(days=1)

    return usage_history


# (should_receive_strike, decks_used)
def should_receive_strike(deck_usage: int, completed_saturday: bool) -> tuple:
    usage_history_list = break_down_usage_history(deck_usage)
    decks_required = 10 if completed_saturday else 14
    decks_used_in_race = 0

    for i in range(1, 4):
        decks_used_in_race += usage_history_list[i][0]

    if not completed_saturday:
        decks_used_in_race += usage_history_list[0][0]

    return (decks_used_in_race < decks_required, decks_used_in_race)
