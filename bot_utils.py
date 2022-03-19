from config import *
from difflib import SequenceMatcher
from discord.ext import commands
from enum import Enum
from prettytable import PrettyTable
from typing import List, Tuple
import blacklist
import cv2
import discord
import clash_utils
import datetime
import db_utils
import numpy
import os
import pytesseract
import re

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

SIX_DAY_MASK = 0x3FFFF
ONE_DAY_MASK = 0x7

SPECIAL_ROLES = {}
NORMAL_ROLES = {}

class ReminderTime(Enum):
    US = "US"
    EU = "EU"
    ALL = "ALL"

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

def disallowed_command_check():
    async def predicate(ctx):
        return False
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

strike_messages = {}


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


async def deck_usage_reminder(bot, time_zone: ReminderTime=ReminderTime.ALL, message: str=DEFAULT_REMINDER_MESSAGE, automated: bool=True):
    reminder_list = clash_utils.get_remaining_decks_today()
    users_on_vacation = db_utils.get_users_on_vacation()
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    channel = discord.utils.get(guild.channels, name=REMINDER_CHANNEL)
    member_string = ""
    non_member_string = ""
    check_time_zones = (time_zone != ReminderTime.ALL)
    time_zone_set = set()

    if check_time_zones:
        time_zone_set = db_utils.get_members_in_time_zone(time_zone)
        if len(time_zone_set) == 0:
            check_time_zones = False

    for player_name, player_tag, decks_remaining in reminder_list:
        if player_tag in users_on_vacation:
            continue

        if check_time_zones and (player_tag not in time_zone_set):
            continue

        member = None
        discord_id = db_utils.get_member_id(player_tag)

        if discord_id is not None:
            member = discord.utils.get(channel.members, id=discord_id)

        if member is None:
            non_member_string += f"{player_name} - Decks left: {decks_remaining}" + "\n"
        else:
            member_string += f"{member.mention} - Decks left: {decks_remaining}" + "\n"

    if (len(member_string) == 0) and (len(non_member_string) == 0):
        if check_time_zones:
            no_reminder_string = f"Everyone that receives {time_zone.value} reminders has already used all their decks today. Good job!"
            await channel.send(no_reminder_string)
        else:
            await channel.send("Everyone has already used all their decks today. Good job!")
        return

    reminder_string = message + "\n" + member_string + non_member_string

    if automated:
        automated_message = ''
        if time_zone == ReminderTime.US:
            automated_message = 'This is an automated reminder. If this reminder is in the middle of the night for you, consider switching your reminder time to 19:00 UTC with command `!set_reminder_time EU`'
        elif time_zone == ReminderTime.EU:
            automated_message = 'This is an automated reminder. If this reminder is in the middle of the day for you, consider switching your reminder time to 02:00 UTC with command `!set_reminder_time US`'
        else:
            automated_message = 'This is an automated reminder. All members with remaining decks are receiving this regardless of time zone preference.'
        reminder_string += "\n" + automated_message

    await channel.send(reminder_string)


async def update_member(member: discord.Member, player_tag: str = None) -> bool:
    if member.bot or (SPECIAL_ROLES[NEW_ROLE_NAME] in member.roles) or (SPECIAL_ROLES[CHECK_RULES_ROLE_NAME] in member.roles):
        return False

    if player_tag == None:
        player_tag = db_utils.get_player_tag(member.id)

    if player_tag is None:
        return False

    discord_name = full_name(member)
    clash_data = clash_utils.get_clash_user_data(player_tag, discord_name, member.id)

    if clash_data is None:
        return False

    member_status = db_utils.update_user(clash_data)

    if not await is_admin(member):
        if clash_data["player_name"] != member.display_name:
            await member.edit(nick = clash_data["player_name"])

        current_roles = set(member.roles).intersection({NORMAL_ROLES[MEMBER_ROLE_NAME], NORMAL_ROLES[VISITOR_ROLE_NAME], NORMAL_ROLES[ELDER_ROLE_NAME]})
        correct_roles = { NORMAL_ROLES[member_status] }

        if (clash_data["clan_role"] in {"elder", "coLeader", "leader"}) and (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) and (clash_data["player_tag"] not in blacklist.blacklist):
            correct_roles.add(NORMAL_ROLES[ELDER_ROLE_NAME])

        if correct_roles != current_roles:
            await member.remove_roles(*list(current_roles - correct_roles))
            await member.add_roles(*list(correct_roles))

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
    db_utils.clean_up_db(active_members)
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

    if command_time.time() > db_utils.get_reset_time().time():
        time_delta = datetime.timedelta(days=1)
    else:
        time_delta = datetime.timedelta(days=2)

    usage_history = []

    for _ in range(7):
        temp_usage = deck_usage & ONE_DAY_MASK
        deck_usage >>= 3
        temp_date = (command_time - time_delta).date()
        date_string = temp_date.strftime("%a, %b %d")
        usage_history.append((temp_usage, date_string))
        time_delta += datetime.timedelta(days=1)

    return usage_history


def should_receive_strike(deck_usage: int, completed_saturday: bool, tracked_since: datetime.datetime, reset_times: dict) -> Tuple[bool, int, int, bool]:
    """
    Based on deck usage and race completion date, determine whether user should receive strike.

    Args:
        deck_usage(int): Concatenated deck usage history value from database.
        completed_saturday(bool): Whether race completed early or not.
        tracked_since(datetime.datetime): Time that bot started tracking user.
        reset_times(dict{str: datetime.datetime}): Dict of river race reset times.

    Returns:
        Tuple[should_receive_strike(bool), decks_used(int), decks_required(int), missing_data(bool)]
    """
    usage_history_list = break_down_usage_history(deck_usage)
    decks_required = 0
    decks_used = 0
    missing_data = False

    if tracked_since is None:
        decks_required = 16
    elif tracked_since <= reset_times["thursday"]:
        decks_required = 16
    elif tracked_since <= reset_times["friday"]:
        decks_required = 12
    elif tracked_since <= reset_times["saturday"]:
        decks_required = 8
    else:
        decks_required = 4

    if completed_saturday:
        decks_required -= 4

    for i in range(1, 4):
        temp_usage = usage_history_list[i][0]

        if temp_usage == 7:
            missing_data = True
            decks_required -= 4
        else:
            decks_used += temp_usage

    if not completed_saturday:
        temp_usage = usage_history_list[0][0]

        if temp_usage == 7:
            missing_data = True
            decks_required -= 4
        else:
            decks_used += temp_usage

    return (decks_used < decks_required, decks_used, decks_required, missing_data)


def upcoming_strikes(use_race_reset_times: bool) -> List[Tuple[str, str, int, int, int]]:
    """
    Get a list of all users who will receive strike or who would have received strikes in the previous war.
    
    Args:
        use_race_reset_times(bool): If true, decide the number of required decks for users individually based on when they joined
                                    the river race. Otherwise, expect max decks possible regardless of join time.

    Returns:
        List[Tuple[player_name(str), player_tag(str), decks_used(int), decks_required(int), current_strikes(int)]]
    """
    deck_usage_list = db_utils.get_all_user_deck_usage_history()
    strikes_dict = db_utils.get_users_with_strikes_dict()
    active_members = clash_utils.get_active_members_in_clan()
    is_war_time = db_utils.is_war_time()
    completed_saturday = db_utils.is_completed_saturday()
    last_reset_time = db_utils.get_reset_time()
    now = datetime.datetime.now(datetime.timezone.utc)
    upcoming_strikes = []
    race_reset_times: dict
    war_days_to_check: int
    starting_index: int

    if len(active_members) == 0:
        return []

    if use_race_reset_times:
        race_reset_times = db_utils.get_river_race_reset_times()

    if not is_war_time:
        if now.time() < last_reset_time.time():
            starting_index = now.weekday() - 1
        else:
            starting_index = now.weekday()

        if completed_saturday:
            starting_index += 1
            war_days_to_check = 3
        else:
            war_days_to_check = 4
    else:
        starting_index = 0

        if now.weekday() == 0:
            war_days_to_check = 3
        elif now.time() > last_reset_time.time():
            war_days_to_check = now.weekday() - 3
        else:
            war_days_to_check = now.weekday() - 4

    if war_days_to_check == 0:
        return []

    for player_name, player_tag, _, history, tracked_since in deck_usage_list:
        if player_tag not in active_members:
            continue

        usage_history = break_down_usage_history(history, now)
        decks_required: int
        decks_used: int

        if not use_race_reset_times or tracked_since is None:
            decks_required = 4 * war_days_to_check
        elif is_war_time:
            decks_required = 4 * (now - tracked_since).days
        else:
            if tracked_since <= race_reset_times["thursday"]:
                decks_required = 16
            elif tracked_since <= race_reset_times["friday"]:
                decks_required = 12
            elif tracked_since <= race_reset_times["saturday"]:
                decks_required = 8
            else:
                decks_required = 4

        decks_used = 0

        for i in range(starting_index, starting_index + war_days_to_check):
            temp_usage = usage_history[i][0]

            if temp_usage == 7:
                decks_required -= 4
            else:
                decks_used += temp_usage

        if decks_used < decks_required:
            upcoming_strikes.append((player_name, player_tag, decks_used, decks_required, strikes_dict.get(player_tag, 0)))

    return upcoming_strikes


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


def get_current_battletime() -> str:
    """
    Get the current time as a Clash Royale API battleTime string.

    Returns:
        str: Current battleTime.
    """
    return datetime_to_battletime(datetime.datetime.utcnow())


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


def average_fame_per_deck(win_rate: float) -> float:
    """
    Get the average fame per deck value at the specified win rate. Assumes the player always plays 4 battles by playing a duel
    followed by normal matches (no boat battles). It's also assumed that win rate is the same in duels and normal matches.

    Fame per deck of a player that completes 4 battles with these assumptions can be calculated as
    F(p) = -25p^3 + 25p^2 + 125p + 100 where F(p) is fame per deck and p is probability of winning any given match (win rate). This
    was determined by calculating the expected number of duel matches played in a Bo3 at a given win rate, then subtracting that
    from 4 to determine how many normal matches are played. These quantities are then multiplied by the average amount of fame a
    deck is worth in each game mode. This is equal to f = 250p + 100(1-p) for duels and f = 200p + 100(1-p) for normal matches.

    Args:
        win_rate(float): Player win rate in PvP matches.
    
    Returns:
        float: Average fame per deck used.
    """
    return (-25 * win_rate**3) + (25 * win_rate**2) + (125 * win_rate) + 100


def calculate_win_rate_from_average_fame(avg_fame_per_deck: float) -> float:
    """
    Solve the polynomial described in average_fame_per_deck in order to calculate the win rate needed to achieve the specified fame
    per deck. All assumptions made in calculating average fame per deck are relevant to this calculation too.

    Args:
        avg_fame_per_deck(float): Average fame per deck to calculate win rate for.

    Returns:
        float: Win rate needed to achieve the specified average fame per deck.
    """
    roots = numpy.roots([-25, 25, 125, (100 - avg_fame_per_deck)])
    win_rate = None

    for root in roots:
        if 0 <= root <= 1:
            win_rate = root

    return win_rate


def predict_race_outcome(use_historical_win_rates: bool, use_historical_deck_usage: bool) -> Tuple[List[tuple], dict, dict]:
    """
    Predict the final standings at the end of the day.

    Args:
        use_historical_win_rates(bool): Calculate each clan's win rate based on performance since start of war, otherwise assume 50%.
        use_historical_deck_usage(bool): Made predictions based off average number of decks each clan uses per day, otherwise assume
                                         each clan uses all remaining decks.

    Returns:
        Tuple[List[tuple], dict, dict]: (predicted_outcomes, completed_clans, catch_up_requirements)
            predicted_outcomes = [ Tuple[clan_name(str), clan_tag(str), predicted_score(int), win_rate(float), expected_decks_to_use(int)], ... ]
            completed_clans = {clan_tag(str): clan_name(str)}
            catch_up_requirements = {"decks": int, "win_rate": float}
    """
    clans = clash_utils.get_clans_in_race(False)
    saved_clan_info = db_utils.get_saved_clans_in_race_info()

    if use_historical_win_rates:
        now = datetime.datetime.now(datetime.timezone.utc)
        race_reset_times = db_utils.get_river_race_reset_times()

        if (now - race_reset_times["thursday"]).days > 5:
            win_rates = clash_utils.calculate_river_race_win_rates(db_utils.get_reset_time())
        else:
            win_rates = clash_utils.calculate_river_race_win_rates(race_reset_times["thursday"]  - datetime.timedelta(days=1))

        if len(win_rates) == 0:
            win_rates = {clan["tag"]: 0.50 for clan in clans}
    else:
        win_rates = {clan["tag"]: 0.50 for clan in clans}

    expected_deck_usage = {}

    if use_historical_deck_usage:
        for clan in clans:
            tag = clan["tag"]

            if saved_clan_info[tag]["num_days"] == 0:
                expected_decks_to_use = 200 - clan["decks_used_today"]
            else:
                avg_deck_usage = round(saved_clan_info[tag]["war_decks_used"] / saved_clan_info[tag]["num_days"])
                current_deck_usage = clan["decks_used_today"]

                if current_deck_usage > avg_deck_usage:
                    expected_decks_to_use = round((200 - current_deck_usage) * 0.25)
                else:
                    expected_decks_to_use = avg_deck_usage - current_deck_usage

            expected_deck_usage[tag] = expected_decks_to_use
    else:
        for clan in clans:
            tag = clan["tag"]
            expected_decks_to_use = 200 - clan["decks_used_today"]
            expected_deck_usage[tag] = expected_decks_to_use

    predicted_outcomes = []
    completed_clans = {}
    catch_up_requirements = {}

    for clan in clans:
        tag = clan["tag"]

        if clan["completed"]:
            completed_clans[tag] = clan["name"]

        win_rate = win_rates[tag]
        saved_fame = saved_clan_info.get(tag, {"fame": 0})["fame"]
        fame_earned_today = clan["fame"] - saved_fame
        fame_per_deck = average_fame_per_deck(win_rate)
        expected_decks_to_use = expected_deck_usage[tag]
        predicted_score = 50 * round((fame_earned_today + (expected_decks_to_use * fame_per_deck)) / 50)
        predicted_outcomes.append((clan["name"], tag, predicted_score, win_rate, expected_decks_to_use))

    predicted_outcomes.sort(key = lambda x : x[2], reverse=True)

    if len(predicted_outcomes) > 0 and predicted_outcomes[0][1] != PRIMARY_CLAN_TAG:
        for clan in clans:
            if clan["tag"] == PRIMARY_CLAN_TAG:
                decks_available = 200 - clan["decks_used_today"]
                current_fame = clan["fame"] - saved_clan_info.get(clan["tag"], {"fame": 0})["fame"]
                break

        fame_to_catch_up = predicted_outcomes[0][2] - current_fame
        avg_fame_needed_per_deck = fame_to_catch_up / decks_available
        needed_win_rate = calculate_win_rate_from_average_fame(avg_fame_needed_per_deck)

        if needed_win_rate is not None:
            needed_win_rate = round(needed_win_rate * 100, 2)

        catch_up_requirements = {"decks": decks_available, "win_rate": needed_win_rate}

    return (predicted_outcomes, completed_clans, catch_up_requirements)


def create_prediction_embeds(predicted_outcomes: List[tuple], completed_clans: dict, catch_up_requirements: dict, use_table: bool)\
    -> Tuple[discord.Embed, discord.Embed, discord.Embed]:
    """
    Create 3 embeds from the prediction data.

    Args:
        predicted_outcomes(List[tuple]): Predicted outcomes in order for today.
        completed_clans(dict): Dict of clans that have already crossed the finish line.
        catch_up_requirements(dict): Requirements to match predicted score of first place if primary clan is not predicted to win.
        use_table(bool): Display predicted standings in table instead of embed fields.

    Returns:
        Tuple[discord.Embed, discord.Embed, discord.Embed]: (predictions_embed, completed_clans_embed, catch_up_embed)
    """
    primary_clan_placement = 1

    for _, tag, _, _, _ in predicted_outcomes:
        if tag == PRIMARY_CLAN_TAG:
            break
        primary_clan_placement += 1

    if PRIMARY_CLAN_TAG in completed_clans and not db_utils.is_colosseum_week() or primary_clan_placement == 1:
        predictions_color = discord.Color.green()
    elif primary_clan_placement == 2:
        predictions_color = 0xFFFF00
    elif primary_clan_placement == 3:
        predictions_color = discord.Color.orange()
    elif primary_clan_placement == 4:
        predictions_color = discord.Color.red()
    elif primary_clan_placement == 5:
        predictions_color = discord.Color.dark_red()

    if use_table:
        table = PrettyTable()
        table.field_names = ["Clan", "Score"]
        predictions_embed = discord.Embed(color=predictions_color)
    else:
        predictions_embed = discord.Embed(title="Predicted Outcomes Today", color = predictions_color)

    placement = 1

    for name, tag, score, win_rate, decks_to_use in predicted_outcomes:
        if tag in completed_clans and not db_utils.is_colosseum_week():
            continue

        if use_table:
            table.add_row([name, score])
        else:
            predictions_embed.add_field(name=f"{placement}. {name}",
                                        value=f"```Score: {score}\nWin Rate: {round(win_rate * 100, 2)}%\nDecks: {decks_to_use}```",
                                        inline=False)
        
        placement += 1

    if use_table:
        predictions_embed.add_field(name="Predicted outcomes today", value="```\n" + table.get_string() + "```")
        predictions_embed.set_footer(text="Assuming each clan uses all remaining decks at a 50% winrate")

    completed_clans_embed = None
    catch_up_embed = None

    if len(completed_clans) > 0:
        clans_str = "\n".join(clan_name for clan_name in completed_clans.values())
        completed_clans_embed = discord.Embed(title=f"{clans_str} has already crossed the finish line and is excluded from the predicted standings.",
                                              color=discord.Color.blue())

    if len(catch_up_requirements) > 0:
        win_rate = catch_up_requirements["win_rate"]
        decks = catch_up_requirements["decks"]
        if win_rate is not None:
            catch_up_embed = discord.Embed(title=f"{PRIMARY_CLAN_NAME} needs to use all {decks} remaining decks at a {win_rate}% win rate to catch up to the predicted score of first place.",
                                           color=discord.Color.blue())
        else:
            catch_up_embed = discord.Embed(title=f"{PRIMARY_CLAN_NAME} cannot reach the predicted score of first place.",
                                            color=discord.Color.red())

    return (predictions_embed, completed_clans_embed, catch_up_embed)


def kick(player_name: str, player_tag: str) -> discord.Embed:
    """
    Kick the specified player and return an embed confirming the kick.

    Args:
        player_name(str): Name of player to kick.
        player_tag(str): Tag of player to kick.

    Returns:
        discord.Embed: Embed object with details about the kick.
    """
    total_kicks, last_kick_date = db_utils.kick_user(player_tag)
    embed = discord.Embed(title="Kick Logged")
    embed.add_field(name=player_name, value=f"```Times kicked: {total_kicks}\nLast kicked: {last_kick_date}```")

    return embed


def parse_image_text(text: str) -> Tuple[str, str]:
    """
    Parse text for a player tag and/or player name.

    Args:
        text(str): Text parsed from a screenshot.

    Returns:
        Tuple[str, str]: (player_tag, player_name) detected in parsed information.
    """
    tag = re.search(r"(#[A-Z0-9]+)", text)

    if tag is not None:
        tag = tag.group(1)
    else:
        tag = None

    name = re.search(r"(?i)kick (.*) out of the clan\?", text)

    if name is not None:
        name = name.group(1)
    else:
        name = None

    return (tag, name)


async def get_player_info_from_image(image: discord.Attachment) -> Tuple[str, str]:
    """
    Parse a kick screenshot for a player name and/or player tag.

    Args:
        image(discord.Attachment): Image of in-game kick screenshot.

    Returns:
        Tuple[str, str]: (player_tag, player_name) Closest matching player tag and player name in screenshot.
    """
    participants = None
    if db_utils.is_war_time():
        participants = clash_utils.get_river_race_participants()
    else:
        participants = clash_utils.get_last_river_race_participants()

    file_path = 'kick_images'

    if not os.path.exists(file_path):
        os.makedirs(file_path)

    file_path += '/' + image.filename
    await image.save(file_path)

    img = cv2.imread(file_path)
    text = pytesseract.image_to_string(img)
    os.remove(file_path)

    tag, name = parse_image_text(text)
    closest_tag = None
    closest_name = None
    highest_tag_similarity = 0
    highest_name_similarity = 0

    for participant in participants:
        active_tag = participant["tag"]
        active_name = participant["name"]

        if tag is not None:
            temp_tag_similarity = SequenceMatcher(None, tag, active_tag).ratio()
            if temp_tag_similarity > highest_tag_similarity:
                highest_tag_similarity = temp_tag_similarity
                closest_tag = active_tag

                if name is None:
                    closest_name = active_name
        
        if name is not None:
            temp_name_similarity = SequenceMatcher(None, name, active_name).ratio()

            if temp_name_similarity > highest_name_similarity:
                highest_name_similarity = temp_name_similarity
                closest_name = active_name

                if tag is None:
                    closest_tag = active_tag

    return_info = (closest_tag, closest_name)

    if (tag is not None) and (name is not None):
        for participant in participants:
            if participant["tag"] != closest_tag:
                continue
            if participant["name"] != closest_name:
                return_info = (None, None)
            break

    return return_info


async def send_new_member_info(info_channel: discord.TextChannel, clash_data: dict):
    """
    Send an informational message to leaders when a new member joins the server.

    Args:
        info_channel(discord.TextChannel): Channel to send message to.
        clash_data(dict): Dict containing info about new member.
    """
    card_level_data = clash_utils.get_card_levels(clash_data['player_tag'])

    if card_level_data is None:
        return

    url = f"https://royaleapi.com/player/{clash_data['player_tag'][1:]}"
    embed = discord.Embed(title=f"{clash_data['player_name']} just joined the server!", url=url)

    embed.add_field(name=f"About {clash_data['player_name']}",
                    value="```Level: {expLevel}\nTrophies: {trophies}\nBest Trophies: {bestTrophies}\nCards Owned: {foundCards}/{totalCards}```".format(**card_level_data),
                    inline=False)

    found_cards = card_level_data["foundCards"]
    card_level_string = ""
    percentile = 0

    for i in range(14, 0, -1):
        percentile += card_level_data["cards"][i] / found_cards
        percentage = round(percentile * 100)

        if 0 < percentage < 5:
            card_level_string += f"{i:02d}: {'▪':<20}  {percentage:02d}%\n"
        else:
            card_level_string += f"{i:02d}: {(percentage // 5) * '■':<20}  {percentage:02d}%\n"

        if percentage == 100:
            break

    embed.add_field(name="Card Levels", value=f"```{card_level_string}```", inline=False)

    try:
        await info_channel.send(embed=embed)
    except:
        return


async def strike_former_participant(player_name: str,
                                    player_tag: str,
                                    decks_used: int,
                                    decks_required: int,
                                    tracked_since: str,
                                    strikes_channel: discord.TextChannel,
                                    commands_channel: discord.TextChannel):
    """
    Send an embed to the commands channel that can be used to assign a strike to members who participated in the most recent river
    race, did not participate fully, and are no longer an active member of the clan.

    Args:
        player_name(str): Player name of user to potentially strike.
        player_tag(str): Player tag of user to potentially strike.
        decks_used(int): How many decks the user used in the river race.
        decks_required(int): How many decks were expected from the user to not get a strike.
        tracked_since(str): Human readable string of time that bot started tracking the user.
        strikes_channel(discord.TextChannel): Channel to send strike message to if a strike is given.
        commands_channel(discord.TextChannel): Channel to send this embed to.
    """
    global strike_messages

    embed = discord.Embed()
    embed.add_field(name=f"Should {player_name} receive a strike?",
                    value=f"```Decks: {decks_used}/{decks_required}\nDate: {tracked_since}```")

    strike_message = await commands_channel.send(embed=embed)
    await strike_message.add_reaction('✅')
    await strike_message.add_reaction('❌')
    strike_messages[strike_message.id] = (player_tag, player_name, decks_used, decks_required, tracked_since, strikes_channel)
