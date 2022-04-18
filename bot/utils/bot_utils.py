"""Miscellaneous bot utility functions."""

import datetime
import os
import re
from difflib import SequenceMatcher
from enum import Enum
from typing import Dict, List, Tuple, Union

import cv2
import discord
import numpy
import pytesseract
from discord.ext import commands
from prettytable import PrettyTable

# Config
from config.blacklist import BLACKLIST
from config.config import (
    PRIMARY_CLAN_NAME,
    PRIMARY_CLAN_TAG,
    DEFAULT_REMINDER_MESSAGE
)

# Utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils
from utils.channel_utils import CHANNEL
from utils.role_utils import ROLE


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

class ReminderTime(Enum):
    """Reminder time options."""
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

def is_elder_or_higher(member: discord.Member) -> bool:
    """Checks if a member is an elder, leader, or admin.

    Args:
        member: Member to check rank of.

    Returns:
        True if member is an elder or higher, false otherwise.
    """
    return (ROLE.elder() in member.roles) or is_leader_or_higher(member)


def is_leader_or_higher(member: discord.Member) -> bool:
    """Checks if a member is a leader or admin.

    Args:
        member: Member to check rank of.

    Returns:
        True if member is a leader or higher, false otherwise.
    """
    return (ROLE.leader() in member.roles) or is_admin(member)


def is_admin(member: discord.Member) -> bool:
    """Checks if a member is an admin.

    Args:
        member: Member to check rank of.

    Returns:
        True if member is an admin, false otherwise.
    """
    return (ROLE.admin() in member.roles) or member.guild_permissions.administrator


def is_elder_command_check():
    """Check if member issuing command is an elder or higher."""
    async def predicate(ctx: commands.Context):
        return is_elder_or_higher(ctx.author)
    return commands.check(predicate)


def is_leader_command_check():
    """Check if member issuing command is a leader or higher."""
    async def predicate(ctx: commands.Context):
        return is_leader_or_higher(ctx.author)
    return commands.check(predicate)


def is_admin_command_check():
    """Check if member issuing command is an admin."""
    async def predicate(ctx: commands.Context):
        return is_admin(ctx.author)
    return commands.check(predicate)


def commands_channel_check():
    """Check if a command is being issued from the commands channel."""
    async def predicate(ctx):
        return ctx.channel == CHANNEL.commands()
    return commands.check(predicate)


def kicks_channel_check():
    """Check if a command is being issued from the kicks channel."""
    async def predicate(ctx):
        return (ctx.channel == CHANNEL.commands()) or (ctx.channel == CHANNEL.kicks())
    return commands.check(predicate)


def time_off_channel_check():
    """Check if a command is being issued from the time off channel."""
    async def predicate(ctx):
        return ctx.channel == CHANNEL.time_off()
    return commands.check(predicate)


def not_welcome_or_rules_check():
    """Check if a command is not being issued from the welcome or rules channels."""
    async def predicate(ctx: commands.Context):
        return (ctx.channel != CHANNEL.welcome()) and (ctx.channel != CHANNEL.rules())
    return commands.check(predicate)


def disallowed_command_check():
    """Disables a command."""
    async def predicate(_ctx: commands.Context):
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

# TODO: move this into dedicated file set for callback messages.
STRIKE_MESSAGES = {}


def full_name(member: discord.Member) -> str:
    """Get the full Discord name of a member.

    Args:
        member: Member to get name of.

    Returns:
        Full name in the form of "name#1234"
    """
    return member.name + "#" + member.discriminator


def royale_api_url(player_tag: str) -> str:
    """Get url of Royale API page of specified player.

    Args:
        player_tag: Player tag of user to get Royale API url.

    Returns:
        Royale API url of page for specified user.
    """
    return f"https://royaleapi.com/player/{player_tag[1:]}"


async def send_rules_message(user_to_purge: discord.ClientUser):
    """Send message in rules channel for users to react to to gain roles.

    Args:
        user_to_purge: Delete any messages by this user in the rules channel before sending message.
    """
    rules_channel = CHANNEL.rules()
    await rules_channel.purge(limit=10, check=lambda message: message.author == user_to_purge)
    new_react_message = await rules_channel.send(content="@everyone After you've read the rules, react to this message for roles.")
    await new_react_message.add_reaction(u"\u2705")


async def deck_usage_reminder(time_zone: ReminderTime=ReminderTime.ALL,
                              message: str=DEFAULT_REMINDER_MESSAGE,
                              automated: bool=True):
    """Send message to reminders channel mentioning users that have remaining decks today.

    Args:
        time_zone (optional): Which time zone of users to mention. Defaults to reminding users in all time zones.
        message (optional): Message to be sent with reminder. Defaults to message set in config.
        automated (optional): Whether to send message indicating this was an automated reminder. Defaults to true.
    """
    reminder_list = clash_utils.get_remaining_decks_today()
    users_on_vacation = db_utils.get_users_on_vacation()
    reminder_channel = CHANNEL.reminder()
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
            member = discord.utils.get(reminder_channel.members, id=discord_id)

        if member is None:
            non_member_string += f"{player_name} - Decks left: {decks_remaining}" + "\n"
        else:
            member_string += f"{member.mention} - Decks left: {decks_remaining}" + "\n"

    if (len(member_string) == 0) and (len(non_member_string) == 0):
        if check_time_zones:
            no_reminder_string = (
                f"Everyone that receives {time_zone.value} reminders has already used all their decks today. "
                "Good job!"
            )
        else:
            no_reminder_string = "Everyone has already used all their decks today. Good job!"

        no_reminder_embed = discord.Embed(title=no_reminder_string, color=discord.Color.green())
        await reminder_channel.send(embed=no_reminder_embed)
        return

    reminder_string = message + "\n" + member_string + non_member_string

    if automated:
        if time_zone == ReminderTime.US:
            automated_message = (
                "This is an automated reminder. If this reminder is in the middle of the night for you, "
                "consider switching your reminder time to 19:00 UTC with command `!set_reminder_time EU`"
            )
        elif time_zone == ReminderTime.EU:
            automated_message = (
                "This is an automated reminder. If this reminder is in the middle of the day for you, "
                "consider switching your reminder time to 02:00 UTC with command `!set_reminder_time US`"
            )
        else:
            automated_message = (
                "This is an automated reminder. "
                "All members with remaining decks are receiving this regardless of time zone preference."
            )

        reminder_string += "\n" + automated_message

    await reminder_channel.send(reminder_string)


async def update_member(member: discord.Member, player_tag: str=None) -> bool:
    """Update a member's database information and adjust their relevant roles as necessary.

    Args:
        member: Member to update.
        player_tag (optional): Player tag of member to update. If no player tag is provided, get the user tag currently associated
            with the member in the database.

    Returns:
        Whether the update was successful or not.
    """
    if member.bot or (ROLE.new() in member.roles) or (ROLE.check_rules() in member.roles):
        return False

    if player_tag is None:
        player_info = db_utils.find_user_in_db(member.id)

        if len(player_info) != 1:
            return False

        _, player_tag, _ = player_info[0]

    discord_name = full_name(member)
    clash_data = clash_utils.get_clash_user_data(player_tag, discord_name, member.id)

    if clash_data is None:
        return False

    member_status = db_utils.update_user(clash_data)

    if not is_admin(member):
        if clash_data["player_name"] != member.display_name:
            await member.edit(nick = clash_data["player_name"])

        current_roles = set(member.roles).intersection({ROLE.member(), ROLE.visitor(), ROLE.elder()})
        correct_roles = {ROLE.get_role_from_name(member_status)}

        if (clash_data["clan_role"] in {"elder", "coLeader", "leader"}
                and clash_data["clan_tag"] == PRIMARY_CLAN_TAG
                and clash_data["player_tag"] not in BLACKLIST):
            correct_roles.add(ROLE.elder())

        if correct_roles != current_roles:
            await member.remove_roles(*list(current_roles - correct_roles))
            await member.add_roles(*list(correct_roles))

    return True


async def update_all_members(guild: discord.Guild):
    """Update all members of the Discord server that need to be updated.

    This does not guarantee all members will actually be updated. For example, visitors are only updated if they have joined the
    primary clan. A visitor that has switched player names or clans (non primary clan to non primary clan) would not be updated.
    Changes in a member's Discord name, moving from/to the primary clan, and primary clan members that have changed their player
    names or clan role will trigger an update.

    Args:
        guild: Update members of this Discord server.
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
            if (member.display_name != active_members[player_tag]["name"]
                    or db_info[member.id]["clan_role"] != active_members[player_tag]["role"]
                    or ROLE.visitor() in member.roles):
                await update_member(member, player_tag)
        elif ROLE.member() in member.roles:
            await update_member(member, player_tag)


def break_down_usage_history(deck_usage: int, command_time: datetime.datetime=None) -> List[Tuple[int, str]]:
    """Break down concatenated deck usage into usage per day.

    Args:
        deck_usage: Last 7 days of deck usage bitwise shifted and or'd together.
        command_time (optional): Time to base day associated with each usage with. If not provided, use current time.

    Returns:
        Last 7 days of deck usage in the form [(decks_used, day), ...] where index 0 represents the most recent day and index 6
            represents the oldest day with recorded deck usage.
    """
    if command_time is None:
        command_time = datetime.datetime.now(datetime.timezone.utc)

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


def should_receive_strike(deck_usage: int,
                          completed_saturday: bool,
                          tracked_since: datetime.datetime,
                          reset_times: Dict[str, datetime.datetime]) -> Tuple[bool, int, int, bool]:
    """Based on deck usage and race completion date, determine whether user should receive strike.

    Args:
        deck_usage: Concatenated deck usage history value from database.
        completed_saturday: Whether race completed early or not.
        tracked_since: Time that bot started tracking user.
        reset_times: Dict of river race reset times.
            {"thursday": datetime, "friday": datetime, "saturday": datetime, "sunday": datetime}

    Returns:
        Whether the user should receive a strike, how many decks they used and should have used, and whether any data was missing.
            (should_receive_strike, decks_used, decks_required, missing_data)
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
    """Get a list of all users who will receive strike or who would have received strikes in the previous war.

    Args:
        use_race_reset_times: If true, decide the number of required decks for users individually based on when they joined
            the river race. Otherwise, expect max decks possible regardless of join time.

    Returns:
        A list of users who will receive or have received a strike in the current/most recent river race.
            (player_name, player_tag, decks_used, decks_required, current_strikes)
    """
    deck_usage_list = db_utils.get_all_user_deck_usage_history()
    strikes_dict = db_utils.get_users_with_strikes_dict()
    active_members = clash_utils.get_active_members_in_clan()
    is_war_time = db_utils.is_war_time()
    completed_saturday = db_utils.is_completed_saturday()
    last_reset_time = db_utils.get_reset_time()
    now = datetime.datetime.now(datetime.timezone.utc)
    upcoming_strikes_list = []
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
            upcoming_strikes_list.append((player_name, player_tag, decks_used, decks_required, strikes_dict.get(player_tag, 0)))

    return upcoming_strikes_list


def battletime_to_datetime(battle_time: str) -> datetime.datetime:
    """Convert a Clash Royale API battleTime string to a datetime.

    Args:
        battle_time: API battleTime string formatted as "yyyymmddThhmmss.000Z" to convert into a datetime.

    Returns:
        Datetime version of battleTime string.
    """
    year = int(battle_time[:4])
    month = int(battle_time[4:6])
    day = int(battle_time[6:8])
    hour = int(battle_time[9:11])
    minute = int(battle_time[11:13])
    second = int(battle_time[13:15])

    return datetime.datetime(year, month, day, hour, minute, second, tzinfo=datetime.timezone.utc)


def datetime_to_battletime(time: datetime.datetime) -> str:
    """Convert a datetime into a Clash Royale API battleTime string.

    Args:
        time: Datetime to convert into battleTime string.

    Returns:
        battleTime string formatted as "yyyymmddThhmmss.000Z".
    """
    return f"{time.year}{time.month:02}{time.day:02}T{time.hour:02}{time.minute:02}{time.second:02}.000Z"


def get_current_battletime() -> str:
    """Get the current time as a Clash Royale API battleTime string.

    Returns:
        Current time formatted as "yyyymmddThhmmss.000Z".
    """
    return datetime_to_battletime(datetime.datetime.utcnow())


def create_match_performance_embed(player_name: str, player_tag: str) -> discord.Embed:
    """Create a Discord Embed displaying a user's River Race stats.

    Args:
        player_name: Player name of player to display stats of.
        player_tag: Player tag of player to display stats of.

    Returns:
        Embed containing the specified user's stats.
    """
    history = db_utils.get_match_performance_dict(player_tag)
    embed = discord.Embed(title=f"{player_name}'s River Race Stats")

    embed.add_field(name="Regular PvP",
                    value=("```"
                           f"Wins:   {history['all']['regular']['wins']} \n"
                           f"Losses: {history['all']['regular']['losses']} \n"
                           f"Total:  {history['all']['regular']['total']} \n"
                           f"Win rate: {history['all']['regular']['win_rate']}"
                           "```"))
    embed.add_field(name="Special PvP",
                    value=("```"
                           f"Wins:   {history['all']['special']['wins']} \n"
                           f"Losses: {history['all']['special']['losses']} \n"
                           f"Total:  {history['all']['special']['total']} \n"
                           f"Win rate: {history['all']['special']['win_rate']}"
                           "```"))
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    embed.add_field(name="Duel (individual matches)",
                    value=("```"
                           f"Wins:   {history['all']['duel_matches']['wins']} \n"
                           f"Losses: {history['all']['duel_matches']['losses']} \n"
                           f"Total:  {history['all']['duel_matches']['total']} \n"
                           f"Win rate: {history['all']['duel_matches']['win_rate']}"
                           "```"),
                    inline=True)
    embed.add_field(name="Duel (series)",
                    value=("```"
                           f"Wins:   {history['all']['duel_series']['wins']} \n"
                           f"Losses: {history['all']['duel_series']['losses']} \n"
                           f"Total:  {history['all']['duel_series']['total']} \n"
                           f"Win rate: {history['all']['duel_series']['win_rate']}"
                           "```"),
                    inline=True)
    embed.add_field(name="\u200b", value="\u200b", inline=False)

    embed.add_field(name="Combined PvP matches",
                    value=("```"
                           f"Wins:   {history['all']['combined_pvp']['wins']} \n"
                           f"Losses: {history['all']['combined_pvp']['losses']} \n"
                           f"Total:  {history['all']['combined_pvp']['total']} \n"
                           f"Win rate: {history['all']['combined_pvp']['win_rate']}"
                           "```"),
                    inline=False)
    embed.add_field(name="Boat attacks",
                    value=("```"
                           f"Wins:   {history['all']['boat_attacks']['wins']} \n"
                           f"Losses: {history['all']['boat_attacks']['losses']} \n"
                           f"Total:  {history['all']['boat_attacks']['total']} \n"
                           f"Win rate: {history['all']['boat_attacks']['win_rate']}"
                           "```"))

    return embed


def average_fame_per_deck(win_rate: float) -> float:
    """Get the average fame per deck value at the specified win rate.

    Assumes the player always plays 4 battles by playing a duel followed by normal matches (no boat battles). It's also assumed that
    win rate is the same in duels and normal matches.

    Fame per deck of a player that completes 4 battles with these assumptions can be calculated as
    F(p) = -25p^3 + 25p^2 + 125p + 100 where F(p) is fame per deck and p is probability of winning any given match (win rate). This
    was determined by calculating the expected number of duel matches played in a Bo3 at a given win rate, then subtracting that
    from 4 to determine how many normal matches are played. These quantities are then multiplied by the average amount of fame a
    deck is worth in each game mode. This is equal to f = 250p + 100(1-p) for duels and f = 200p + 100(1-p) for normal matches.

    Args:
        win_rate: Player win rate in PvP matches.

    Returns:
        Average fame per deck used.
    """
    return (-25 * win_rate**3) + (25 * win_rate**2) + (125 * win_rate) + 100


def calculate_win_rate_from_average_fame(avg_fame_per_deck: Union[float, None]) -> float:
    """Solve the polynomial described in average_fame_per_deck.

    Determine what win rate is needed to achieve the specified fame per deck. All assumptions descibed above hold true here as well.
    If no roots can be determined, then None is returned.

    Args:
        avg_fame_per_deck: Average fame per deck to calculate win rate of.

    Returns:
        Win rate needed to achieve the specified average fame per deck, or None if no solution exists.
    """
    roots = numpy.roots([-25, 25, 125, (100 - avg_fame_per_deck)])
    win_rate = None

    for root in roots:
        if 0 <= root <= 1:
            win_rate = root

    return win_rate


def predict_race_outcome(use_historical_win_rates: bool, use_historical_deck_usage: bool)\
        -> Tuple[List[Tuple[str, str, int, float, int]], Dict[str, str], Dict[str, Union[int, float]]]:
    """Predict the final standings at the end of the day.

    Args:
        use_historical_win_rates: Calculate each clan's win rate based on performance since start of war, otherwise assume 50%.
        use_historical_deck_usage: Made predictions based off average number of decks each clan uses per day, otherwise assume each
            clan uses all remaining decks.

    Returns:
        Predicted outcomes at the end of the current day, any clans that have already crossed the finish line and are omitted from
            the predicted standings, and what the primary clan needs to do in order to reach first place's current predicted score
            if the primary clan is not predicted to get first place.

            Predicted outcomes list in order from first to last place:
                [ (clan_name, clan_tag, predicted_score, win_rate, expected_decks_to_use), ... ]

            Completed clans: { clan_tag: clan_name }

            Catch up requirements: { "decks": int, "win_rate": float }
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


def create_prediction_embeds(predicted_outcomes: List[Tuple[str, str, int, float, int]],
                             completed_clans: Dict[str, str],
                             catch_up_requirements: Dict[str, Union[int, float]],
                             use_table: bool) -> Tuple[discord.Embed, discord.Embed, discord.Embed]:
    """Create 3 embeds from the prediction data.

    predicted_outcomes (ordered first to last): [ (clan_name, clan_tag, predicted_score, win_rate, expected_decks_to_use), ... ]
    completed_clans: { clan_tag: clan_name }
    catch_up_requirements: { "decks": int, "win_rate": float }

    Args:
        predicted_outcomes: Predicted outcomes today ordered from first to last.
        completed_clans: Clans that have already crossed the finish line.
        catch_up_requirements: Requirements to match predicted score of first place if primary clan is not predicted to win.
        use_table: Display predicted standings in table instead of embed fields.

    Returns:
        Tuple of predicted outcomes embed, completed clans embed, and catch up requirements embed.
    """
    primary_clan_placement = 1

    for _, tag, _, _, _ in predicted_outcomes:
        if tag == PRIMARY_CLAN_TAG:
            break
        primary_clan_placement += 1

    if primary_clan_placement == 1 or (PRIMARY_CLAN_TAG in completed_clans and not db_utils.is_colosseum_week()):
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
        completed_clans_embed = discord.Embed(title=(
                                                  f"{clans_str} has already crossed the finish line and "
                                                  "is excluded from the predicted standings."
                                              ),
                                              color=discord.Color.blue())

    if len(catch_up_requirements) > 0:
        win_rate = catch_up_requirements["win_rate"]
        decks = catch_up_requirements["decks"]
        if win_rate is not None:
            catch_up_embed = discord.Embed(title=(
                                               f"{PRIMARY_CLAN_NAME} needs to use all {decks} remaining decks at a {win_rate}% "
                                               "win rate to catch up to the predicted score of first place."
                                           ),
                                           color=discord.Color.blue())
        else:
            catch_up_embed = discord.Embed(title=f"{PRIMARY_CLAN_NAME} cannot reach the predicted score of first place.",
                                            color=discord.Color.red())

    return (predictions_embed, completed_clans_embed, catch_up_embed)


def kick(player_name: str, player_tag: str) -> discord.Embed:
    """Kick the specified player and return an embed confirming the kick.

    Args:
        player_name: Name of player to kick.
        player_tag: Tag of player to kick.

    Returns:
        Embed with details about the kick.
    """
    total_kicks, last_kick_date = db_utils.kick_user(player_tag)
    embed = discord.Embed(title="Kick Logged", color=discord.Color.green())
    embed.add_field(name=player_name, value=f"```Times kicked: {total_kicks}\nLast kicked: {last_kick_date}```")

    return embed


def undo_kick(player_name: str, player_tag: str) -> discord.Embed:
    """Undo the latest kick of the specified user and return an embed with details about the kick.

    Args:
        player_name: Name of player to undo kick for.
        player_tag: Tag of player to undo kick for.

    Returns:
        Embed with info about the kick that was undone.
    """
    removed_kick = db_utils.undo_kick(player_tag)
    embed = discord.Embed(title="Kick Undone", color=discord.Color.green())

    if removed_kick is None:
        embed.add_field(name=player_name, value="This user has no kicks to undo.")
    else:
        embed.add_field(name=player_name, value=f"```Undid kick from: {removed_kick}```")

    return embed


def parse_image_text(text: str) -> Tuple[Union[str, None], Union[str, None]]:
    """Parse text for a player tag and/or player name.

    Args:
        text: Text parsed from a screenshot.

    Returns:
        Tuple of player tag if found (otherwise None) and player name if found (otherwise None).
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
    """Parse a kick screenshot for a player name and/or player tag.

    Args:
        image: Image of in-game kick screenshot.

    Returns:
        Tuple of closest matching player tag and player name from screenshot.
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


async def send_new_member_info(clash_data: Dict[str, Union[str, int]]):
    """Send an informational message to leaders when a new member joins the server.

    Args:
        clash_data: Dict containing info about new member.
    """
    card_level_data = clash_utils.get_card_levels(clash_data['player_tag'])

    if card_level_data is None:
        return

    embed = discord.Embed(title=f"{clash_data['player_name']} just joined the server!",
                          url=royale_api_url(clash_data["player_tag"]))

    embed.add_field(name=f"About {clash_data['player_name']}",
                    value=("```"
                           "Level: {expLevel}\n"
                           "Trophies: {trophies}\n"
                           "Best Trophies: {bestTrophies}\n"
                           "Cards Owned: {foundCards}/{totalCards}"
                           "```").format(**card_level_data),
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
        await CHANNEL.leader_info().send(embed=embed)
    except:
        return


async def strike_former_participant(player_name: str,
                                    player_tag: str,
                                    decks_used: int,
                                    decks_required: int,
                                    tracked_since: str):
    """Allow leaders to optionally strike members not in primary clan at time that automated strikes message gets sent.

    Send an embed to the commands channel that can be used to assign a strike to members who participated in the most recent river
    race, did not participate fully, and are no longer an active member of the clan.

    Args:
        player_name: Player name of user to potentially strike.
        player_tag: Player tag of user to potentially strike.
        decks_used: How many decks the user used in the river race.
        decks_required: How many decks were expected from the user to not get a strike.
        tracked_since: Human readable string of time that bot started tracking the user.
    """
    global STRIKE_MESSAGES

    embed = discord.Embed()
    embed.add_field(name=f"Should {player_name} receive a strike?",
                    value=f"```Decks: {decks_used}/{decks_required}\nDate: {tracked_since}```")

    strike_message = await CHANNEL.commands().send(embed=embed)
    await strike_message.add_reaction('✅')
    await strike_message.add_reaction('❌')
    STRIKE_MESSAGES[strike_message.id] = (player_tag, player_name, decks_used, decks_required, tracked_since)


def duplicate_names_embed(users: List[Tuple[str, str, str]], command_name: str) -> discord.Embed:
    """Create an Embed listing out users with identical names.

    Args:
        users: List of users' player names, player tags, and clan names that have the same player name.
        command_name: Name of command that led to this error.

    Returns:
        Embed listing out users and info about how to proceed.
    """
    embed = discord.Embed(title="Duplicate names detected", color=0xFFFF00)
    embed.add_field(name="Which user did you mean?",
                    value=f"Try reissuing the command with a player tag (e.g., `!{command_name} #ABC123`)",
                    inline=False)

    for player_name, player_tag, clan_name in users:
        embed.add_field(name=f"{player_name}",
                        value=f"```Tag: {player_tag}\nClan: {clan_name}```",
                        inline=False)

    return embed
