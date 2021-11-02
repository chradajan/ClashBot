from config import *
from discord.ext import commands
import blacklist
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

SPECIAL_ROLES = {}
NORMAL_ROLES = {}


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

def not_welcome_or_rules_check():
    async def predicate(ctx):
        return (ctx.message.channel.name != NEW_CHANNEL) and (ctx.message.channel.name != RULES_CHANNEL)
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


def full_name(member: discord.Member) -> str:
    """
    Get the full Discord name of a member.

    Args:
        member: Member to get name of.

    Returns:
        str: Full name in the form of "name#1234"
    """
    return member.name + "#" + member.discriminator


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
    if member.bot or (SPECIAL_ROLES[NEW_ROLE_NAME] in member.roles) or (SPECIAL_ROLES[CHECK_RULES_ROLE_NAME] in member.roles):
        return False

    if player_tag == None:
        player_tag = db_utils.get_player_tag(member.id)

    if player_tag == None:
        return False

    discord_name = full_name(member)
    clash_data = clash_utils.get_clash_user_data(player_tag, discord_name, member.id)

    if clash_data == None:
        return False

    member_status = db_utils.update_user(clash_data)

    if not await is_admin(member):
        if clash_data["player_name"] != member.display_name:
            await member.edit(nick = clash_data["player_name"])

        roles_to_remove = [NORMAL_ROLES[MEMBER_ROLE_NAME], NORMAL_ROLES[VISITOR_ROLE_NAME], NORMAL_ROLES[ELDER_ROLE_NAME]]
        await member.remove_roles(*roles_to_remove)
        await member.add_roles(NORMAL_ROLES[member_status])

        if (clash_data["clan_role"] in {"elder", "coLeader", "leader"}) and (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) and (clash_data["player_name"] not in blacklist.blacklist):
            await member.add_roles(NORMAL_ROLES[ELDER_ROLE_NAME])

    return True


async def update_all_members(guild: discord.Guild):
    """
    Update all members of the server that need to be updated. This does not guarantee that all members actually will be updated. For
    example, a visitor who has switched clans (but not to the primary clan), will not be updated since that switch would not affect
    their roles on the server. A visitor who has switched to the primary clan on the other hand will be updated.

    Args:
        guild(discord.Guild): Guild to update members in.
    """
    active_members = clash_utils.get_active_members_in_clan()
    db_info = db_utils.get_server_members_info()

    for member in guild.members:
        if member.bot or member.id not in db_info:
            continue

        player_tag = db_info[member.id]["player_tag"]
        current_discord_name = full_name(member)

        if current_discord_name != db_info[member.id]["discord_name"]:
            await update_member(member, player_tag)
        elif player_tag in active_members:
            if ((member.display_name != active_members[player_tag]["name"]) or
                (db_info[member.id]["clan_role"] != active_members[player_tag]["role"]) or
                (NORMAL_ROLES[VISITOR_ROLE_NAME] in member.roles)):
                await update_member(member, player_tag)
        elif NORMAL_ROLES[MEMBER_ROLE_NAME] in member.roles:
            await update_member(member, player_tag)


# [(most_recent_usage, day_string), (second_most_recent_usage, day_string), ...]
def break_down_usage_history(deck_usage: int, command_time: datetime.datetime = datetime.datetime.now(datetime.timezone.utc)) -> list:
    time_delta = None

    if command_time.time() > RESET_TIME:
        time_delta = datetime.timedelta(days=1)
    else:
        time_delta = datetime.timedelta(days=2)

    usage_history = []

    for _ in range(7):
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


def battletime_to_datetime(battle_time: str) -> datetime.datetime:
    """
    Convert a Clash Royale API battleTime string to a datetime object.

    Args:
        battle_time(str): API battleTime string in the format "yyyymmddThhmmss.000Z".
    
    Returns:
        datetime: Converted datetime object.
    """
    year = int(battle_time[:4])
    month = int(battle_time[4:6])
    day = int(battle_time[6:8])
    hour = int(battle_time[9:11])
    minute = int(battle_time[11:13])
    second = int(battle_time[13:15])

    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc)


def datetime_to_battletime(time: datetime.datetime) -> str:
    """
    Convert a datetime object to a Clash Royale API battleTime string.

    Args:
        time(datetime.datetime): datetime object to convert.

    Returns:
        str: Converted API battleTime string in the format "yyyymmddThhmmss.000Z".
    """
    return f"{time.year}{time.month:02}{time.day:02}T{time.hour:02}{time.minute:02}{time.second:02}.000Z"


def create_match_performance_embed(player_name: str, player_tag: str) -> discord.Embed:
    """
    Create a Discord Embed object displaying a user's River Race stats.

    Args:
        player_name(str): Player name of player to display stats of.
        player_tag(str): Player tag of player to display stats of.

    Returns:
        discord.Embed: Sendable embed containing the specified user's stats.
    """
    history = db_utils.get_match_performance_dict(player_tag)
    embed = discord.Embed(title=f"{player_name}'s River Race Stats")

    embed.add_field(name="Regular PvP", value = f"``` Wins:   {history['all']['regular']['wins']} \n Losses: {history['all']['regular']['losses']} \n Total:  {history['all']['regular']['total']} \n Win rate: {history['all']['regular']['win_rate']} ```")
    embed.add_field(name="Special PvP", value = f"``` Wins:   {history['all']['special']['wins']} \n Losses: {history['all']['special']['losses']} \n Total:  {history['all']['special']['total']} \n Win rate: {history['all']['special']['win_rate']} ```")
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    embed.add_field(name="Duel (individual matches)",
                    value = f"``` Wins:   {history['all']['duel_matches']['wins']} \n Losses: {history['all']['duel_matches']['losses']} \n Total:  {history['all']['duel_matches']['total']} \n Win rate: {history['all']['duel_matches']['win_rate']} ```",
                    inline=True)
    embed.add_field(name="Duel (series)",
                    value = f"``` Wins:   {history['all']['duel_series']['wins']} \n Losses: {history['all']['duel_series']['losses']} \n Total:  {history['all']['duel_series']['total']} \n Win rate: {history['all']['duel_series']['win_rate']} ```",
                    inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    embed.add_field(name="Combined PvP matches", value = f"``` Wins:   {history['all']['combined_pvp']['wins']} \n Losses: {history['all']['combined_pvp']['losses']} \n Total:  {history['all']['combined_pvp']['total']} \n Win rate: {history['all']['combined_pvp']['win_rate']} ```", inline=False)
    embed.add_field(name="Boat attacks", value = f"``` Wins:   {history['all']['boat_attacks']['wins']} \n Losses: {history['all']['boat_attacks']['losses']} \n Total:  {history['all']['boat_attacks']['total']} \n Win rate: {history['all']['boat_attacks']['win_rate']} ```")

    return embed