"""Miscellanous utility functions that interface with the database."""

import datetime
import os
from typing import Dict, List, Set, Tuple, Union

import pymysql
import xlsxwriter

# Config
from config.blacklist import BLACKLIST
from config.config import PRIMARY_CLAN_TAG
from config.credentials import (
    IP,
    USERNAME,
    PASSWORD,
    DB_NAME
)

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
from utils.logging_utils import LOG, log_message
from utils.role_utils import RoleNames
from utils.util_types import (
    CombinedData,
    DatabaseClan,
    DatabaseData,
    DatabaseDataExtended,
    RaceStats,
    ReminderTime,
    ResetTimes,
    RiverRaceStats,
    Status
)


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


def connect_to_db() -> Tuple[pymysql.Connection, pymysql.cursors.DictCursor]:
    """Establish connection to database.

    Returns:
        Database connection and cursor.
    """
    database = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME, charset='utf8mb4')
    cursor = database.cursor(pymysql.cursors.DictCursor)
    return (database, cursor)


def get_clan_id(clan_tag: str, clan_name: str, cursor: pymysql.cursors.DictCursor) -> int:
    """Get id of clan from clans table. If the clan doesn't exist, insert it.

    Requires an existing database connection. Does not commit changes to database.

    Args:
        clan_tag: Tag of clan to get id of.
        clan_name: Name of clan to get id of.
        cursor: Cursor of existing database connection.

    Returns:
        id from clans table of specified clan.
    """
    cursor.execute("SELECT id FROM clans WHERE clan_tag = %s", (clan_tag))
    query_result = cursor.fetchone()

    if query_result is None:
        LOG.debug(log_message("Inserting new clan into clans table", clan_name=clan_name, clan_tag=clan_tag))
        cursor.execute("INSERT INTO clans VALUES (DEFAULT, %s, %s)", (clan_tag, clan_name))
        cursor.execute("SELECT id FROM clans WHERE clan_tag = %s", (clan_tag))
        query_result = cursor.fetchone()

    return query_result['id']

def add_new_user(user_data: CombinedData) -> bool:
    """Add a new user to the database. Only used for users that just joined the Discord server.

    Args:
        combined_data: Relevant Clash Royale and Discord data.

    Returns:
        Whether player was successfully inserted into database.
    """
    database, cursor = connect_to_db()

    # Add extra fields to user_data needed for query.
    user_data['clan_id'] = get_clan_id(user_data['clan_tag'], user_data['clan_name'], cursor)
    user_data['status_str'] = user_data['status'].value
    user_data['first_joined'] = bot_utils.get_current_battletime() if user_data['status'] == Status.ACTIVE else None

    # Check if the user has previously joined the server with a different player tag.
    # If they have, set their previous associated account's discord_id to NULL and create a new entry.
    cursor.execute("SELECT * FROM users WHERE discord_id = %(discord_id)s", user_data)
    query_result = cursor.fetchone()

    if query_result is not None:
        LOG.debug(log_message("User rejoined server with different player tag", previous_player_tag=query_result['player_tag']))
        cursor.execute("UPDATE users SET discord_id = NULL WHERE discord_id = %(discord_id)s", user_data)

    # Check if player already exists in table.
    cursor.execute("SELECT * FROM users WHERE player_tag = %(player_tag)s", user_data)
    query_result = cursor.fetchone()

    if query_result is not None:
        if Status(query_result['status']) in {Status.ACTIVE, Status.INACTIVE}:
            database.rollback()
            database.close()
            return False

        LOG.debug(log_message("User joined as a previously UNREGISTERED/DEPARTED user", previous_status=query_result['status']))
        cursor.execute("UPDATE users SET\
                        player_name = %(player_name)s,\
                        discord_name = %(discord_name)s,\
                        discord_id = %(discord_id)s,\
                        clan_role = %(role)s,\
                        clan_id = %(clan_id)s,\
                        status = %(status_str)s\
                        WHERE player_tag = %(player_tag)s",
                        user_data)
        cursor.execute("UPDATE users SET first_joined = %(first_joined)s\
                        WHERE first_joined IS NULL AND player_tag = %(player_tag)s",
                        user_data)
    else:
        cursor.execute("INSERT INTO users VALUES\
                        (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, %(discord_id)s,\
                        %(role)s, 'US', FALSE, 0, 0, 0, %(status_str)s, %(first_joined)s, %(clan_id)s)",
                        user_data)

    # Get id of newly inserted user.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", user_data)
    query_result = cursor.fetchone()
    user_id = query_result['id']

    # Check for match_history and create entries if necessary.
    cursor.execute("SELECT user_id FROM match_history_all WHERE user_id = %s", (user_id))
    query_result = cursor.fetchone()

    if query_result is None:
        last_check_time = get_last_check_time()
        tracked_since = bot_utils.get_current_battletime() if (is_war_time() and (user_data['status'] == Status.ACTIVE)) else None
        cursor.execute("INSERT INTO match_history_recent VALUES (%s, %s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
                       (user_id, last_check_time, tracked_since))
        cursor.execute("INSERT INTO match_history_all VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (user_id))

    # Check if new user is member or visitor. Get id of relevant discord_role.
    role_string = RoleNames.MEMBER.value if (user_data['status'] == Status.ACTIVE) else RoleNames.VISITOR.value
    cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role_string))
    query_result = cursor.fetchone()
    discord_role_id = query_result['id']

    # Add new role into assigned_roles table.
    insert_assigned_roles_query = "INSERT INTO assigned_roles VALUES (%s, %s)"
    cursor.execute(insert_assigned_roles_query, (user_id, discord_role_id))

    if (user_data["role"] in {"elder", "coLeader", "leader"}
            and user_data["status"] == Status.ACTIVE
            and user_data["player_tag"] not in BLACKLIST):
        role_string = "Elder"
        cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role_string))
        query_result = cursor.fetchone()
        discord_role_id = query_result['id']
        cursor.execute(insert_assigned_roles_query, (user_id, discord_role_id))

    database.commit()
    database.close()
    return True


def add_new_unregistered_user(player_tag: str) -> bool:
    """Add an unregistered player (active in clan but not Discord) to the database.

    Args:
        player_tag: Player tag of player to insert.

    Returns:
        Whether the user was successfully added.
    """
    database, cursor = connect_to_db()

    # Get their data.
    user_data = bot_utils.get_combined_data(player_tag)
    LOG.debug(log_message("Inserting new unregistered user", user_data=user_data))

    if user_data is None:
        return False

    # Add extra fields to user_data needed for query.
    user_data['clan_id'] = get_clan_id(user_data['clan_tag'], user_data['clan_name'], cursor)
    user_data['status_str'] = user_data['status'].value
    user_data['first_joined'] = bot_utils.get_current_battletime()

    # Insert them
    cursor.execute("INSERT INTO users VALUES\
                    (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, NULL,\
                    %(role)s, 'US', FALSE, 0, 0, 0, %(status_str)s, %(first_joined)s, %(clan_id)s)",
                    user_data)

    # Create match_history entries.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", user_data)
    query_result = cursor.fetchone()
    last_check_time = get_last_check_time()
    tracked_since = bot_utils.get_current_battletime() if (is_war_time() and user_data['status'] == Status.UNREGISTERED) else None
    cursor.execute("INSERT INTO match_history_recent VALUES (%s, %s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
                   (query_result['id'], last_check_time, tracked_since))
    cursor.execute("INSERT INTO match_history_all VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)",
                   (query_result['id']))

    database.commit()
    database.close()
    return True


def update_user(user_data: CombinedData):
    """Update a user in the database to reflect any changes to their Clash Royale or Discord statuses.

    Args:
        user_data: Relevant Clash Royale and Discord data.
    """
    database, cursor = connect_to_db()

    LOG.debug(log_message("Updating user in database", user_data=user_data))

    # Add extra fields to user_data needed for query.
    user_data['clan_id'] = get_clan_id(user_data['clan_tag'], user_data['clan_name'], cursor)
    user_data['status_str'] = user_data['status'].value

    cursor.execute("UPDATE users SET\
                    player_tag = %(player_tag)s,\
                    player_name = %(player_name)s,\
                    discord_name = %(discord_name)s,\
                    clan_role = %(role)s,\
                    clan_id = %(clan_id)s,\
                    status = %(status_str)s\
                    WHERE player_tag = %(player_tag)s",
                    user_data)

    if user_data['status'] in {Status.ACTIVE, Status.UNREGISTERED}:
        user_data['first_joined'] = bot_utils.get_current_battletime()
        cursor.execute("UPDATE users SET first_joined = %(first_joined)s\
                        WHERE first_joined IS NULL AND player_tag = %(player_tag)s",
                        user_data)

        if is_war_time():
            last_check_time = get_last_check_time()
            tracked_since = bot_utils.get_current_battletime()
            cursor.execute("UPDATE match_history_recent SET\
                            last_check_time = %s,\
                            tracked_since = %s\
                            WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s) AND tracked_since IS NULL",
                            (last_check_time, tracked_since, user_data["player_tag"]))

    database.commit()
    database.close()


def get_user_data(player_tag: str) -> DatabaseDataExtended:
    """Get a user's information from the users table.

    Args:
        player_tag(str): Player tag of user to get info about.

    Returns:
        Dictionary of user's info from database.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT * FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()

    if query_result is None:
        return None

    user_data: DatabaseDataExtended = {
        'player_tag': query_result['player_tag'],
        'player_name': query_result['player_name'],
        'discord_name': query_result['discord_name'],
        'discord_id': query_result['discord_id'],
        'role': query_result['clan_role'],
        'clan_tag': "",
        'clan_name': "",
        'vacation': query_result['vacation'],
        'strikes': query_result['strikes'],
        'permanent_strikes': query_result['permanent_strikes'],
        'usage_history': query_result['usage_history'],
        'status': Status(query_result['status'])
    }

    clan_id = query_result["clan_id"]
    cursor.execute("SELECT * FROM clans WHERE id = %s", (clan_id))
    query_result = cursor.fetchone()

    if query_result is None:
        database.close()
        return None

    user_data['clan_tag'] = query_result['clan_tag']
    user_data['clan_name'] = query_result['clan_name']

    database.close()
    return user_data


def update_strikes(player_tag: str, delta: int) -> Tuple[int, int, int, int]:
    """Add or remove strikes from user. If player tag does not exist in database, add them as an unregistered user.

    Args:
        player_tag: Player to give strike to.
        delta: Number of strikes to add or remove from current strikes for user.

    Returns:
        Tuple of old strike count, new strike count, old permanent strike count, and new permanent strike count. All values will be
            None if an error occurred.
    """
    database, cursor = connect_to_db()

    old_strike_count = None
    new_strike_count = None
    old_permanent_strike_count = None
    new_permanent_strike_count = None
    cursor.execute("SELECT strikes, permanent_strikes FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()

    if query_result is None:
        if not add_new_unregistered_user(player_tag):
            database.close()
            return (old_strike_count, new_strike_count, old_permanent_strike_count, new_permanent_strike_count)

        old_strike_count = 0
        old_permanent_strike_count = 0

        if delta < 0:
            new_strike_count = 0
            new_permanent_strike_count = 0
        else:
            new_strike_count = delta
            new_permanent_strike_count = delta
    else:
        old_strike_count = query_result["strikes"]
        old_permanent_strike_count = query_result["permanent_strikes"]

        if old_strike_count + delta < 0:
            new_strike_count = 0
        else:
            new_strike_count = old_strike_count + delta

        if old_permanent_strike_count + delta < 0:
            new_permanent_strike_count = 0
        else:
            new_permanent_strike_count = old_permanent_strike_count + delta

    cursor.execute("UPDATE users SET strikes = %s, permanent_strikes = %s WHERE player_tag = %s",
                   (new_strike_count, new_permanent_strike_count, player_tag))

    database.commit()
    database.close()
    LOG.debug(log_message("Updated strikes for user",
                          player_tag=player_tag,
                          delta=delta,
                          strikes=f"{old_strike_count}->{new_strike_count}",
                          permanent_strikes=f"{old_permanent_strike_count}->{new_permanent_strike_count}"))

    return (old_strike_count, new_strike_count, old_permanent_strike_count, new_permanent_strike_count)


def get_strikes(discord_id: int) -> int:
    """Get the current number of non-permanent strikes a user has.

    Args:
        discord_id: Unique Discord id of a member.

    Returns:
        Number of non-permanent strikes the specified user currently has.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT strikes FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    database.close()

    if query_result is None:
        return None

    return query_result["strikes"]


def reset_strikes():
    """Reset non-permanent strikes for all users"""
    database, cursor = connect_to_db()

    cursor.execute("UPDATE users SET strikes = 0")
    database.commit()
    database.close()


def get_users_with_strikes() -> List[Tuple[str, str, int]]:
    """Get all users in the database that have non-permanent strikes.

    Returns:
        List of player tags, player names, and non-permanent strikes.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT player_name, player_tag, strikes FROM users WHERE strikes > 0")
    query_result = cursor.fetchall()
    database.close()

    if query_result is None:
        return {}

    strikes_list = [ (user["player_tag"], user["player_name"], user["strikes"]) for user in query_result ]
    strikes_list.sort(key = lambda x : (x[2], x[0].lower()))

    return strikes_list


def get_users_with_strikes_dict() -> Dict[str, int]:
    """Get all users in the database that have non-permanent strikes.

    Returns:
        Dictionary mapping player tag to non-permanent strikes.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT player_tag, strikes FROM users WHERE strikes > 0")
    query_result = cursor.fetchall()
    database.close()

    if query_result is None:
        return {}

    strikes_dict = {user["player_tag"]: user["strikes"] for user in query_result}
    return strikes_dict


def set_completed_saturday_status(status: bool):
    """Update database to indicate whether the primary clan has crossed the finish line early.

    Args:
        status: New status to set completed_saturday to.
    """
    database, cursor = connect_to_db()

    cursor.execute("UPDATE race_status SET completed_saturday = %s", (status))

    database.commit()
    database.close()


def is_completed_saturday() -> bool:
    """Return whether the primary clan crossed the finish line early.

    Returns:
        Completed Saturday status.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT completed_saturday FROM race_status")
    query_result = cursor.fetchone()

    database.close()
    return query_result["completed_saturday"]


def set_colosseum_week_status(status: bool):
    """Update database to indicate whether or not it's colosseum week.

    Args:
        status: New status to set colosseum_week to.
    """
    database, cursor = connect_to_db()

    cursor.execute("UPDATE race_status SET colosseum_week = %s", (status))

    database.commit()
    database.close()


def is_colosseum_week() -> bool:
    """Return whether it's colosseum week.

    Returns:
        Colosseum week status.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT colosseum_week FROM race_status")
    query_result = cursor.fetchone()

    database.close()
    return query_result["colosseum_week"]


def set_war_time_status(status: bool):
    """Update database to indicate whether or not it's war time.

    Args:
        status: New status to set war_time to.
    """
    database, cursor = connect_to_db()

    cursor.execute("UPDATE race_status SET war_time = %s", (status))

    database.commit()
    database.close()


def is_war_time() -> bool:
    """Return whether it's war time.

    Returns:
        War time status.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT war_time FROM race_status")
    query_result = cursor.fetchone()

    database.close()
    return query_result["war_time"]


def set_last_check_time(last_check_time: datetime.datetime):
    """Update database to indicate when the last win rate tracking check occurred.

    Args:
        last_check_time: Last check time in datetime format.
    """
    database, cursor = connect_to_db()

    last_check_time = bot_utils.datetime_to_battletime(last_check_time)
    cursor.execute("UPDATE race_status SET last_check_time = %s", (last_check_time))

    database.commit()
    database.close()


def get_last_check_time() -> str:
    """Get the time when the last win rate tracking check occurred.

    Returns:
        Time of last win rate tracking check, formatted as Clash Royale API battleTime.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT last_check_time FROM race_status")
    query_result = cursor.fetchone()

    database.close()
    return query_result["last_check_time"]


def set_reset_time(reset_time: datetime.datetime):
    """Save most recent daily reset time to database.

    Args:
        reset_time: Most recent reset time.
    """
    database, cursor = connect_to_db()

    reset_time_str = bot_utils.datetime_to_battletime(reset_time)
    cursor.execute("UPDATE race_status SET reset_time = %s", (reset_time_str))

    river_race_days = {4: 'thursday', 5: 'friday', 6: 'saturday', 0: 'sunday'}
    weekday = river_race_days.get(reset_time.weekday(), None)

    if weekday is not None:
        cursor.execute(f"UPDATE race_reset_times SET {weekday} = %s", (reset_time_str))

    database.commit()
    database.close()


def get_reset_time() -> datetime.datetime:
    """Get the most recent daily reset time from the database.

    Returns:
        Most recent reset time.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT reset_time FROM race_status")
    query_result = cursor.fetchone()
    reset_time = bot_utils.battletime_to_datetime(query_result["reset_time"])

    database.close()
    return reset_time


def get_river_race_reset_times() -> ResetTimes:
    """Get the reset time of each day during the most recent river race.

    Returns:
        Dictionary of weekday and reset time pairs.
            {
                "thursday": datetime.datetime,
                "friday": datetime.datetime,
                "saturday": datetime.datetime,
                "sunday": datetime.datetime
            }
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT * FROM race_reset_times")
    query_result = cursor.fetchone()
    database.close()

    reset_times: ResetTimes = {
        "thursday":  bot_utils.battletime_to_datetime(query_result["thursday"]),
        "friday":    bot_utils.battletime_to_datetime(query_result["friday"]),
        "saturday":  bot_utils.battletime_to_datetime(query_result["saturday"]),
        "sunday":    bot_utils.battletime_to_datetime(query_result["sunday"])
    }

    return reset_times


def find_user_in_db(search_key: Union[int, str]) -> List[Tuple[str, str, str]]:
    """Find a user(s) in the database corresponding to the search key.

    First try searching for a user where discord_id == search_key if key is an int, otherwise where player_tag == search_key. If no
    results are found, then try searching where player_name == search_key. Player names are not unique and could result in finding
    multiple users. If this occurs, all users that were found are returned.

    Args:
        Key to search for in database. Can be discord id, player tag, or player name.

    Returns:
        List of tuples of (player_name, player_tag, clan_name).
    """
    database, cursor = connect_to_db()

    if isinstance(search_key, int):
        cursor.execute("SELECT users.player_name, users.player_tag, clans.clan_name FROM users\
                        INNER JOIN clans ON users.clan_id = clans.id WHERE discord_id = %s",
                        (search_key))
        query_result = cursor.fetchall()
    else:
        cursor.execute("SELECT users.player_name, users.player_tag, clans.clan_name FROM users\
                        INNER JOIN clans ON users.clan_id = clans.id WHERE player_tag = %s",
                        (search_key))
        query_result = cursor.fetchall()

    if not query_result:
        cursor.execute("SELECT users.player_name, users.player_tag, clans.clan_name FROM users\
                        INNER JOIN clans ON users.clan_id = clans.id WHERE player_name = %s",
                        (search_key))
        query_result = cursor.fetchall()

    search_results = [(user["player_name"], user["player_tag"], user["clan_name"]) for user in query_result]

    database.close()
    return search_results


def get_member_id(player_tag: str) -> int:
    """Return the Discord ID corresponding to the specified player tag, or None if member is not on Discord.

    Args:
        player_tag: Player tag of user to find Discord ID of.

    Returns:
        Discord ID of specified user, or None if not found.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT discord_id FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()
    database.close()

    if query_result is None:
        return None

    return query_result["discord_id"]


def remove_user(discord_id: int):
    """Remove a user's assigned roles and change their status to either UNREGISTERED or DEPARTED.

    Args:
        discord_id: Unique Discord id of a member.
    """
    database, cursor = connect_to_db()

    # Get id and player_tag of user.
    cursor.execute("SELECT id, player_tag FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    if query_result is None:
        database.close()
        return

    user_id = query_result['id']
    player_tag = query_result['player_tag']

    # Delete any assigned Discord roles associated with the user.
    cursor.execute("DELETE FROM assigned_roles WHERE user_id = %s", (user_id))
    active_members = clash_utils.get_active_members_in_clan()

    # If the user is still an active member of the primary clan, change their status to UNREGISTERED.
    # Otherwise change it to DEPARTED.
    if player_tag in active_members:
        new_status = Status.UNREGISTERED
    else:
        new_status = Status.DEPARTED

    cursor.execute("UPDATE users SET discord_name = %s, status = %s WHERE id = %s",
                   (f"{new_status.value}{player_tag}", new_status.value, user_id))

    database.commit()
    database.close()


def remove_all_users():
    """Remove all users and their data from the database."""
    database, cursor = connect_to_db()

    cursor.execute("DELETE FROM assigned_roles")
    cursor.execute("DELETE FROM match_history_recent")
    cursor.execute("DELETE FROM match_history_all")
    cursor.execute("DELETE FROM kicks")
    cursor.execute("DELETE FROM users")

    database.commit()
    database.close()


def update_vacation_for_user(discord_id: int, status: bool=None) -> bool:
    """Toggle a user's vacation status.

    Args:
        discord_id: Unique Discord id of a member.
        status: What to set specified user's vacation status to. If None, set status to opposite of current status.

    Returns:
        The specified user's updated vacation status.
    """
    database, cursor = connect_to_db()

    if isinstance(status, bool):
        cursor.execute("UPDATE users SET vacation = %s WHERE discord_id = %s", (status, discord_id))
    else:
        cursor.execute("UPDATE users SET vacation = NOT vacation WHERE discord_id = %s", (discord_id))

    cursor.execute("SELECT vacation FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    if query_result is None:
        database.close()
        return False

    database.commit()
    database.close()
    return query_result["vacation"]


def get_users_on_vacation() -> Dict[str, str]:
    """Get a dict of active members that are currently on vacation.

    Returns:
        Dictionary mapping player tags to player names of users that are on vacation.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT player_name, player_tag FROM users WHERE vacation = TRUE")
    query_result = cursor.fetchall()
    database.close()

    if query_result is None:
        return {}

    active_members = clash_utils.get_active_members_in_clan()
    users_on_vacation = {user['player_tag']: user['player_name'] for user in query_result if user['player_tag'] in active_members}
    return users_on_vacation


def clear_all_vacation():
    """Set all users to not on vacation."""
    database, cursor = connect_to_db()

    cursor.execute("UPDATE users SET vacation = FALSE")

    database.commit()
    database.close()


def set_reminder_status(status: bool):
    """Set automated reminders on or off.

    Args:
        status: Whether automated reminders should be on or off.
    """
    database, cursor = connect_to_db()

    cursor.execute("UPDATE automation_status SET send_reminders = %s", (status))

    database.commit()
    database.close()


def get_reminder_status() -> bool:
    """Get status of automated reminders.

    Returns:
        Whether automated reminders are on or off.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT send_reminders FROM automation_status")
    query_result = cursor.fetchone()

    if query_result is None:
        database.close()
        return False

    status = query_result["send_reminders"]
    database.close()
    return status


def set_strike_status(status: bool):
    """Set automated strikes on or off.

    Args:
        status: Whether automated strikes should be on or off.
    """
    database, cursor = connect_to_db()

    cursor.execute("UPDATE automation_status SET send_strikes = %s", (status))

    database.commit()
    database.close()


def get_strike_status() -> bool:
    """Get status of automated strikes.

    Returns:
        Whether automated strikes are on or off.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT send_strikes FROM automation_status")
    query_result = cursor.fetchone()

    status = query_result["send_strikes"]
    database.close()
    return status


def get_roles(discord_id: int) -> List[str]:
    """Get the list of roles currently assigned to a user.

    Args:
        discord_id: Unique Discord id of a member.

    Returns:
        List of role names assigned to the specified user.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT discord_roles.role_name FROM discord_roles\
                    INNER JOIN assigned_roles on discord_roles.id = assigned_roles.discord_role_id\
                    INNER JOIN users ON assigned_roles.user_id = users.id\
                    WHERE users.discord_id = %s",
                    (discord_id))

    query_result = cursor.fetchall()
    database.close()

    roles = [role["role_name"] for role in query_result]
    return roles


def commit_roles(discord_id: int, roles: List[str]):
    """Delete the roles currently assigned to a user. Then record their new roles.

    Args:
        discord_id: Unique Discord id of a member.
        roles: List of new roles to assign to user.
    """
    database, cursor = connect_to_db()

    cursor.execute("DELETE FROM assigned_roles WHERE user_id IN (SELECT id FROM users WHERE discord_id = %s)", (discord_id))

    for role in roles:
        cursor.execute("INSERT INTO assigned_roles VALUES\
                        ((SELECT id FROM users WHERE discord_id = %s), (SELECT id FROM discord_roles WHERE role_name = %s))",
                        (discord_id, role))

    database.commit()
    database.close()

def update_time_zone(discord_id: int, time_zone: ReminderTime):
    """Change a user's preferred time for receiving automated reminders.

    Args:
        discord_id: Unique Discord id of a member.
        time_zone (ReminderTime): Preferred time zone.
    """
    database, cursor = connect_to_db()

    cursor.execute("UPDATE users SET time_zone = %s WHERE discord_id = %s", (time_zone.value, discord_id))

    database.commit()
    database.close()


def get_members_in_time_zone(time_zone: ReminderTime) -> Set[str]:
    """Get the members in the specified time zone.

    Args:
        time_zone (ReminderTime): Get members from this time zone.

    Returns:
        Set of player tags of users in specified time zone.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users WHERE time_zone = %s", (time_zone.value))
    query_result = cursor.fetchall()
    database.close()

    if query_result is None:
        return set()

    members = {user["player_tag"] for user in query_result}
    return members


def record_deck_usage_today(deck_usage: Dict[str, int]):
    """Record deck usage for each user in the database.

    Users in the passed in dictionary from the primary clan have their usage from the dictionary recorded. All other users in the
    database have 0 decks used recorded. If deck_usage is empty, then each user in the database will have 7 decks recorded to
    indicate that real data is missing for that day.

    Args:
        Dictionary mapping player tags to number of decks used by that player today.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users")
    query_result = cursor.fetchall()
    db_users = set()

    if query_result is not None:
        db_users = {user["player_tag"] for user in query_result}

    default_deck_usage = 0

    if deck_usage is None:
        deck_usage = {}
        default_deck_usage = 7

    for player_tag in deck_usage:
        db_users.discard(player_tag)
        cursor.execute("SELECT player_tag, usage_history FROM users WHERE player_tag = %s", (player_tag))
        query_result = cursor.fetchone()

        if query_result is None:
            if not add_new_unregistered_user(player_tag):
                continue
            query_result = {"usage_history": 0}

        updated_history = ((query_result["usage_history"] & SIX_DAY_MASK) << 3) | (deck_usage[player_tag] & ONE_DAY_MASK)
        cursor.execute("UPDATE users SET usage_history = %s WHERE player_tag = %s", (updated_history, player_tag))

    for player_tag in db_users:
        cursor.execute("SELECT usage_history FROM users WHERE player_tag = %s", (player_tag))
        query_result = cursor.fetchone()

        updated_history = ((query_result["usage_history"] & SIX_DAY_MASK) << 3) | (default_deck_usage & ONE_DAY_MASK)
        cursor.execute("UPDATE users SET usage_history = %s WHERE player_tag = %s", (updated_history, player_tag))

    database.commit()
    database.close()


def get_all_user_deck_usage_history() -> List[Tuple[str, str, int, int, datetime.datetime]]:
    """Get usage history of all users in database.

    Returns:
        List of player names, player tags, discord IDs, usage histories, and tracked since dates.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT id, player_name, player_tag, discord_id, usage_history FROM users")
    users = cursor.fetchall()

    usage_list = []

    for user in users:
        cursor.execute("SELECT tracked_since FROM match_history_recent WHERE user_id = %s", (user["id"]))
        tracked_since = cursor.fetchone()["tracked_since"]

        if tracked_since is not None:
            tracked_since = bot_utils.battletime_to_datetime(tracked_since)

        usage_list.append((user["player_name"], user["player_tag"], user["discord_id"], user["usage_history"], tracked_since))

    usage_list.sort(key = lambda x : x[0].lower())
    database.close()
    return usage_list


def clean_up_db() -> bool:
    """Updates database to ensure status column is up to date.

    Checks that every user in the database has an appropriate status.
    ACTIVE users that are no longer active members of the clan are moved to INACTIVE.
    UNREGISTERED users that are no longer active members of the clan are moved to DEPARTED.
    INACTIVE users that are now part of the clan are moved to ACTIVE.
    DEPARTED users that are now part of the clan are moved to UNREGISTERED.

    Returns:
        Whether clean up operation was successful.
    """
    database, cursor = connect_to_db()

    LOG.info("Cleaning up database")
    active_members = clash_utils.get_active_members_in_clan()

    if not active_members:
        return False

    cursor.execute("SELECT player_name, player_tag, discord_name, status FROM users")
    query_result = cursor.fetchall()

    for user in query_result:
        player_tag = user['player_tag']
        discord_name = user['discord_name']
        status = Status(user['status'])

        if player_tag in active_members:
            if status in {Status.INACTIVE, Status.DEPARTED}:
                LOG.debug(log_message("Active user with incorrect status detected", player_tag=player_tag, status=status))
                user_data = bot_utils.get_combined_data(player_tag)
                user_data['discord_name'] = discord_name

                if user_data is None:
                    continue

                if status == Status.DEPARTED:
                    user_data['discord_name'] = f"{Status.UNREGISTERED.value}{player_tag}"
                    user_data['status'] = Status.UNREGISTERED
                else:
                    user_data['discord_name'] = discord_name
                    user_data['status'] = Status.ACTIVE

                update_user(user_data)
        else:
            if status in {Status.ACTIVE, Status.UNREGISTERED}:
                LOG.debug(log_message("Non active user with incorrect status detected", player_tag=player_tag, status=status))
                user_data = bot_utils.get_combined_data(player_tag)

                if user_data is None:
                    continue

                if status == Status.UNREGISTERED:
                    user_data['discord_name'] = f"{Status.DEPARTED.value}{player_tag}"
                    user_data['status'] = Status.DEPARTED
                else:
                    user_data['discord_name'] = discord_name
                    user_data['status'] = Status.INACTIVE

                update_user(user_data)

    database.commit()
    database.close()
    LOG.info("Database cleanup complete")
    return True


def get_server_members_info() -> Dict[int, DatabaseData]:
    """Get database information of all members in the server.

    Returns:
        Dictionary mapping Discord id to database data of a user..
            {
                discord_id: {
                    "player_tag": str,
                    "player_name": str,
                    "discord_id": int,
                    "discord_name": str,
                    "clan_role": str
                }
            }
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT player_tag, player_name, discord_id, discord_name, clan_role FROM users WHERE discord_id IS NOT NULL")
    query_result = cursor.fetchall()
    database.close()

    if query_result is None:
        return {}

    player_info = {
        user["discord_id"]: {
            'player_tag': user['player_tag'],
            'player_name': user['player_name'],
            'discord_name': user['discord_name'],
            'discord_id': user['discord_id'],
            'role': user['clan_role']
        }
        for user in query_result
    }

    return player_info


def get_and_update_match_history_info(player_tag: str,
                                      fame: int,
                                      new_check_time: datetime.datetime) -> Tuple[int, datetime.datetime]:
    """Get a user's fame and time when their battlelog was last checked. Then store their updated fame and current time.

    Args:
        player_tag: Player to get/set fame for.
        fame: Current fame value.
        new_check_time: Current time to set last_check_time to.

    Returns:
        Specified user's previous fame and check time.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT last_check_time, fame FROM match_history_recent\
                    WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)",
                    (player_tag))
    query_result = cursor.fetchone()
    fame_and_time = (None, None)

    if query_result is None:
        if not add_new_unregistered_user(player_tag):
            database.close()
            return fame_and_time
        fame_and_time = (0, bot_utils.battletime_to_datetime(get_last_check_time()))
    else:
        fame_and_time = (query_result["fame"], bot_utils.battletime_to_datetime(query_result["last_check_time"]))

    cursor.execute("UPDATE match_history_recent SET last_check_time = %s, fame = %s\
                    WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)",
                   (bot_utils.datetime_to_battletime(new_check_time), fame, player_tag))

    database.commit()
    database.close()
    return fame_and_time


def set_users_last_check_time(player_tag: str, last_check_time: datetime.datetime):
    """Sets the last check time of a specific user.

    Args:
        player_tag: Player to update.
        last_check_time: Time to set for specified user.
    """
    database, cursor = connect_to_db()

    last_check_time = bot_utils.datetime_to_battletime(last_check_time)
    cursor.execute("UPDATE match_history_recent SET last_check_time = %s\
                    WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)",
                   (last_check_time, player_tag))

    database.commit()
    database.close()


def update_match_history(user_performance_list: List[RaceStats]):
    """Add each player's game stats to the match_history tables.

    Args:
        List of user dictionaries with their river race results.
    """
    database, cursor = connect_to_db()

    user_performance_list = [user for user in user_performance_list if user]

    cursor.executemany("UPDATE match_history_recent SET\
                        battle_wins = battle_wins + %(battle_wins)s,\
                        battle_losses = battle_losses + %(battle_losses)s,\
                        special_battle_wins = special_battle_wins + %(special_battle_wins)s,\
                        special_battle_losses = special_battle_losses + %(special_battle_losses)s,\
                        boat_attack_wins = boat_attack_wins + %(boat_attack_wins)s,\
                        boat_attack_losses = boat_attack_losses + %(boat_attack_losses)s,\
                        duel_match_wins = duel_match_wins + %(duel_match_wins)s,\
                        duel_match_losses = duel_match_losses + %(duel_match_losses)s,\
                        duel_series_wins  = duel_series_wins + %(duel_series_wins)s,\
                        duel_series_losses = duel_series_losses + %(duel_series_losses)s\
                        WHERE user_id IN (SELECT id FROM users WHERE player_tag = %(player_tag)s)", user_performance_list)

    cursor.executemany("UPDATE match_history_all SET\
                        battle_wins = battle_wins + %(battle_wins)s,\
                        battle_losses = battle_losses + %(battle_losses)s,\
                        special_battle_wins = special_battle_wins + %(special_battle_wins)s,\
                        special_battle_losses = special_battle_losses + %(special_battle_losses)s,\
                        boat_attack_wins = boat_attack_wins + %(boat_attack_wins)s,\
                        boat_attack_losses = boat_attack_losses + %(boat_attack_losses)s,\
                        duel_match_wins = duel_match_wins + %(duel_match_wins)s,\
                        duel_match_losses = duel_match_losses + %(duel_match_losses)s,\
                        duel_series_wins  = duel_series_wins + %(duel_series_wins)s,\
                        duel_series_losses = duel_series_losses + %(duel_series_losses)s\
                        WHERE user_id IN (SELECT id FROM users WHERE player_tag = %(player_tag)s)", user_performance_list)

    database.commit()
    database.close()


def prepare_for_river_race(last_check_time: datetime.datetime):
    """Configure the database at the start of a river race.

    Needs to run every Thursday when river race starts. Resets fame to 0 and sets last_check_time to current time. Set tracked_since
    to current time for active members and NULL for everyone else. Also sets the relevant race_status fields.

    Args:
        last_check_time: Do not look at games before this time when match performance is next calculated
    """
    LOG.info("Preparing for river race")
    set_completed_saturday_status(False)
    set_war_time_status(True)
    set_last_check_time(last_check_time)

    database, cursor = connect_to_db()

    last_check_time = bot_utils.datetime_to_battletime(last_check_time)
    cursor.execute("UPDATE match_history_recent SET\
                    last_check_time = %s,\
                    tracked_since = NULL,\
                    fame = 0,\
                    battle_wins = 0,\
                    battle_losses = 0,\
                    special_battle_wins = 0,\
                    special_battle_losses = 0,\
                    boat_attack_wins = 0,\
                    boat_attack_losses = 0,\
                    duel_match_wins = 0,\
                    duel_match_losses = 0,\
                    duel_series_wins  = 0,\
                    duel_series_losses = 0", (last_check_time))

    cursor.execute("UPDATE match_history_recent SET tracked_since = %s WHERE\
                    user_id IN (SELECT id FROM users WHERE status IN (%s, %s))",
                    (last_check_time, Status.ACTIVE.value, Status.UNREGISTERED.value))

    clans = clash_utils.get_clans_in_race(False)
    reset_clans = False

    for clan in clans:
        cursor.execute("SELECT clan_tag FROM river_race_clans WHERE clan_tag = %s", (clan['clan_tag']))
        if cursor.fetchone() is None:
            reset_clans = True
            break

    colosseum_week = is_colosseum_week

    if colosseum_week or reset_clans:
        LOG.debug(log_message("Resetting saved clan data", colosseum_week=colosseum_week, reset_clans=reset_clans))
        cursor.execute("DELETE FROM river_race_clans")
        cursor.executemany("INSERT INTO river_race_clans VALUES (%(clan_tag)s, %(clan_name)s, 0, 0, %(total_decks_used)s, 0, 0)",
                           clans)
    else:
        cursor.executemany("UPDATE river_race_clans SET fame = 0, total_decks_used = %(total_decks_used)s\
                            WHERE clan_tag = %(clan_tag)s",
                            clans)

    database.commit()
    database.close()
    set_colosseum_week_status(False)
    LOG.info("Preparations for river race complete")


def save_clans_in_race_info(post_race: bool):
    """Update river_race_clans table with clans' current fame and deck usage.

    Args:
        post_race: Whether this info is being saved after the river race has concluded.
    """
    database, cursor = connect_to_db()
    clans = clash_utils.get_clans_in_race(post_race)
    saved_clan_info = get_saved_clans_in_race_info()
    colosseum_week = is_colosseum_week()

    for clan in clans:
        tag = clan['clan_tag']
        current_fame = clan['fame']
        fame_earned_today = clan['fame'] - saved_clan_info[tag]['fame']
        total_decks_used = clan['total_decks_used']
        war_decks_used_today = total_decks_used - saved_clan_info[tag]['total_decks_used']

        if colosseum_week:
            cursor.execute("UPDATE river_race_clans SET\
                            total_fame = total_fame + %s,\
                            total_decks_used = %s,\
                            war_decks_used = war_decks_used + %s,\
                            num_days = num_days + 1\
                            WHERE clan_tag = %s",
                           (fame_earned_today, total_decks_used, war_decks_used_today, tag))
        else:
            if post_race and clan['completed']:
                continue

            cursor.execute("UPDATE river_race_clans SET\
                            fame = %s,\
                            total_fame = total_fame + %s,\
                            total_decks_used = %s,\
                            war_decks_used = war_decks_used + %s,\
                            num_days = num_days + 1\
                            WHERE clan_tag = %s",
                           (current_fame, fame_earned_today, total_decks_used, war_decks_used_today, tag))

    database.commit()
    database.close()


def get_saved_clans_in_race_info() -> Dict[str, DatabaseClan]:
    """Get saved clans fame and decks used.

    Returns:
        Dictionary mapping clan tags to dictionary containing saved data from that clan.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT * FROM river_race_clans")
    query_result = cursor.fetchall()

    clans_info = {clan['clan_tag']: clan for clan in query_result}

    database.close()
    return clans_info


def get_match_performance_dict(player_tag: str) -> RiverRaceStats:
    """Get a dictionary containing a user's river race statistics.

    Args:
        player_tag: Player tag of user to get stats of.

    Returns:
        Dictionary containing specified users's stats.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT * FROM match_history_recent WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)", (player_tag))
    match_performance_recent = cursor.fetchone()

    cursor.execute("SELECT * FROM match_history_all WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)", (player_tag))
    match_performance_all = cursor.fetchone()

    if (match_performance_recent is None) or (match_performance_all is None):
        database.close()
        return None

    db_info_dict = {"recent": match_performance_recent, "all": match_performance_all}
    tracked_since = match_performance_recent["tracked_since"]

    if tracked_since is not None:
        tracked_since = bot_utils.battletime_to_datetime(tracked_since)

    match_performance_dict = {"recent": {"fame": match_performance_recent["fame"], "tracked_since": tracked_since},
                              "all": {}}

    for k in db_info_dict:
        # Regular battles
        regular_wins = db_info_dict[k]["battle_wins"]
        regular_losses = db_info_dict[k]["battle_losses"]
        total_regular_battles = regular_wins + regular_losses
        regular_battle_win_rate = "0.00%" if total_regular_battles == 0 else "{:.2%}".format(regular_wins / total_regular_battles)
        match_performance_dict[k]["regular"] = {"wins": regular_wins,
                                                "losses": regular_losses,
                                                "total": total_regular_battles,
                                                "win_rate": regular_battle_win_rate}

        # Special battles
        special_wins = db_info_dict[k]["special_battle_wins"]
        special_losses = db_info_dict[k]["special_battle_losses"]
        total_special_battles = special_wins + special_losses
        special_battle_win_rate = "0.00%" if total_special_battles == 0 else "{:.2%}".format(special_wins / total_special_battles)
        match_performance_dict[k]["special"] = {"wins": special_wins,
                                                "losses": special_losses,
                                                "total": total_special_battles,
                                                "win_rate": special_battle_win_rate}

        # Duel matches
        duel_match_wins = db_info_dict[k]["duel_match_wins"]
        duel_match_losses = db_info_dict[k]["duel_match_losses"]
        total_duel_matches = duel_match_wins + duel_match_losses
        duel_match_win_rate = "0.00%" if total_duel_matches == 0 else "{:.2%}".format(duel_match_wins / total_duel_matches)
        match_performance_dict[k]["duel_matches"] = {"wins": duel_match_wins,
                                                     "losses": duel_match_losses,
                                                     "total": total_duel_matches,
                                                     "win_rate": duel_match_win_rate}

        # Duel series
        duel_series_wins = db_info_dict[k]["duel_series_wins"]
        duel_series_losses = db_info_dict[k]["duel_series_losses"]
        total_duel_series = duel_series_wins + duel_series_losses
        duel_series_win_rate = "0.00%" if total_duel_series == 0 else "{:.2%}".format(duel_series_wins / total_duel_series)
        match_performance_dict[k]["duel_series"] = {"wins": duel_series_wins,
                                                    "losses": duel_series_losses,
                                                    "total": total_duel_series,
                                                    "win_rate": duel_series_win_rate}

        # Boat attacks
        boat_attack_wins = db_info_dict[k]["boat_attack_wins"]
        boat_attack_losses = db_info_dict[k]["boat_attack_losses"]
        total_boat_attacks = boat_attack_wins + boat_attack_losses
        boat_attack_win_rate = "0.00%" if total_boat_attacks == 0 else "{:.2%}".format(boat_attack_wins / total_boat_attacks)
        match_performance_dict[k]["boat_attacks"] = {"wins": boat_attack_wins,
                                                     "losses": boat_attack_losses,
                                                     "total": total_boat_attacks,
                                                     "win_rate": boat_attack_win_rate}

        # Combined
        total_pvp_wins = regular_wins + special_wins + duel_match_wins
        total_pvp_losses = regular_losses + special_losses + duel_match_losses
        total_pvp_matches = total_pvp_wins + total_pvp_losses
        overall_win_rate = "0.00%" if total_pvp_matches == 0 else "{:.2%}".format(total_pvp_wins / total_pvp_matches)
        match_performance_dict[k]["combined_pvp"] = {"wins": total_pvp_wins,
                                                     "losses": total_pvp_losses,
                                                     "total": total_pvp_matches,
                                                     "win_rate": overall_win_rate}

    database.close()
    return match_performance_dict


def get_non_active_participants() -> Set[str]:
    """Get a set of player tags of users who were tracked in the most recent river race but are not currently active members.

    Returns:
        Set of player tags.
    """
    active_members = clash_utils.get_active_members_in_clan(PRIMARY_CLAN_TAG)

    if not active_members:
        return set()

    database, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users\
                    WHERE id IN (SELECT user_id FROM match_history_recent WHERE tracked_since IS NOT NULL)")
    query_result = cursor.fetchall()
    database.close()

    former_participants = set()

    for user in query_result:
        if user['player_tag'] not in active_members:
            former_participants.add(user['player_tag'])

    return former_participants


def add_unregistered_users() -> bool:
    """Add any active members of the primary clan not in the database as UNREGISTERED users.

    Returns:
        Whether adding users was successful.
    """
    LOG.info("Adding any unregistered users to database")
    active_members = clash_utils.get_active_members_in_clan().copy()

    if not active_members:
        return False

    database, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users")
    query_result = cursor.fetchall()
    database.close()

    if query_result is None:
        return False

    for user in query_result:
        active_members.pop(user['player_tag'], None)

    all_users_successfully_inserted = True

    for player_tag in active_members:
        if not add_new_unregistered_user(player_tag):
            all_users_successfully_inserted = False

    LOG.info(log_message("All unregistered users added", all_users_successfully_inserted=all_users_successfully_inserted))
    return all_users_successfully_inserted


def kick_user(player_tag: str) -> Tuple[int, str]:
    """Insert a kick entry for the specified user.

    Args:
        player_tag: Player tag of user to kick.

    Returns:
        Tuple of total number of kicks and last time user was kicked.
    """
    kick_time = bot_utils.get_current_battletime()
    database, cursor = connect_to_db()

    cursor.execute("SELECT id FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()

    if query_result is None:
        database.close()
        add_new_unregistered_user(player_tag)
        database, cursor = connect_to_db()
        cursor.execute("SELECT id FROM users WHERE player_tag = %s", (player_tag))
        query_result = cursor.fetchone()

    user_id = query_result['id']
    cursor.execute("INSERT INTO kicks VALUES (%s, %s)", (user_id, kick_time))

    database.commit()
    database.close()

    kicks = get_kicks(player_tag)
    total_kicks = len(kicks)
    last_kick_date = None

    if total_kicks == 1:
        last_kick_date = "Today"
    else:
        last_kick_date = kicks[-2]

    return (total_kicks, last_kick_date)


def undo_kick(player_tag: str) -> str:
    """Undo the latest kick of the specified user.

    Args:
        player_tag: Player tag of user to undo kick for.

    Returns:
        Time of undone kick, or None if user has not been kicked before.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT id FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()
    user_id = query_result["id"]

    cursor.execute("SELECT kick_time FROM kicks WHERE user_id = %s", (user_id))
    query_result = cursor.fetchall()

    if not query_result:
        database.close()
        return None

    kicks = [kick["kick_time"] for kick in query_result]
    kicks.sort()
    latest_kick_time = kicks[-1]

    cursor.execute("DELETE FROM kicks WHERE user_id = %s AND kick_time = %s", (user_id, latest_kick_time))
    latest_kick_time = bot_utils.battletime_to_datetime(latest_kick_time).strftime("%Y-%m-%d")

    database.commit()
    database.close()
    return latest_kick_time


def get_kicks(player_tag: str) -> List[str]:
    """Get a list of times a user was kicked.

    Args:
        player_tag: Player tag of user to get kicks for.

    Returns:
        List of times the user was kicked.
    """
    database, cursor = connect_to_db()

    cursor.execute("SELECT kick_time FROM kicks WHERE user_id = (SELECT id FROM users WHERE player_tag = %s)", (player_tag))
    query_result = cursor.fetchall()
    kicks = []

    for kick in query_result:
        kick_time = bot_utils.battletime_to_datetime(kick["kick_time"])
        kicks.append(kick_time.strftime("%Y-%m-%d"))

    kicks.sort()
    database.close()
    return kicks


def get_file_path() -> str:
    """Get path of new CSV file that should be created during export process.

    Returns:
        Path to new CSV file.
    """
    path = 'export_files'

    if not os.path.exists(path):
        os.makedirs(path)

    files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    files.sort(key=os.path.getmtime)

    if len(files) >= 5:
        os.remove(files[0])

    file_name = "members_" + str(datetime.datetime.now().date()) + ".xlsx"
    new_path = os.path.join(path, file_name)

    return new_path


def export(primary_clan_only: bool, include_card_levels: bool) -> str:
    """Create Excel spreadsheet containing relevant information from the database.

    Args:
        primary_clan_only: Whether to include only members of the primary clan or all users in database.
        include_card_levels: Whether to include sheet containing information about each user's card levels.

    Returns:
        Path to generated spreadsheet.
    """
    LOG.info(log_message("Exporting relevant data from database to spreadsheet",
                         primary_clan_only=primary_clan_only,
                         include_card_levels=include_card_levels))
    # Clean up the database and add any members of the clan to it that aren't already in it.
    clean_up_db()
    add_unregistered_users()

    database, cursor = connect_to_db()

    # Get clan info.
    clans = None

    if primary_clan_only:
        cursor.execute("SELECT * FROM clans WHERE clan_tag = %s", (PRIMARY_CLAN_TAG))
        clans = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM clans")
        clans = cursor.fetchall()

    if clans is None:
        return None

    clans_dict = {}

    for clan in clans:
        clans_dict[clan['id']] = clan

    # Get users.
    if primary_clan_only:
        cursor.execute("SELECT * FROM users WHERE status IN (%s, %s)", (Status.ACTIVE.value, Status.UNREGISTERED.value))
    else:
        cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()

    if users is None:
        return None

    database.close()

    # Create Excel workbook
    file_path = get_file_path()
    workbook = xlsxwriter.Workbook(file_path)
    info_sheet = workbook.add_worksheet("Info")
    history_sheet = workbook.add_worksheet("History")
    kicks_sheet = workbook.add_worksheet("Kicks")
    recent_stats_sheet = workbook.add_worksheet("Recent Stats")
    all_stats_sheet = workbook.add_worksheet("All Stats")
    card_levels_quantity_sheet = None
    card_levels_percentile_sheet = None
    LOG.debug(f"Exporting data to {file_path}")

    if include_card_levels:
        card_levels_quantity_sheet = workbook.add_worksheet("Card Level Quantities")
        card_levels_percentile_sheet = workbook.add_worksheet("Card Level Percentiles")

    # Info sheet headers
    info_headers = ["Player Name", "Player Tag", "Discord Name", "Clan Role", "Time Zone", "On Vacation", "Strikes",
                    "Permanent Strikes", "Kicks", "Status", "Initial Join Date", "Clan Name", "Clan Tag", "RoyaleAPI"]
    info_sheet.write_row(0, 0, info_headers)

    # History sheet headers
    history_headers = ["Player Name", "Player Tag"]
    now = datetime.datetime.now(datetime.timezone.utc)
    now_date = None

    if now.time() < get_reset_time().time():
        now_date = (now - datetime.timedelta(days=1)).date()
    else:
        now_date = now.date()

    today_header = now_date.strftime("%a, %b %d")

    for _, day in bot_utils.break_down_usage_history(users[0]['usage_history'], now)[::-1]:
        history_headers.append(day)
    history_headers.append(today_header)

    history_sheet.write_row(0, 0, history_headers)

    # Kicks sheet headers
    kicks_headers = ["Player Name", "Player Tag"]
    kicks_sheet.write_row(0, 0, kicks_headers)

    # Stat sheets headers
    recent_stats_headers = ["Player Name", "Player Tag", "Fame", "Decks Used", "Tracked Since",
                            "Regular PvP Wins", "Regular PvP Losses", "Regular PvP Win Rate",
                            "Special PvP Wins", "Special PvP Losses", "Special PvP Win Rate",
                            "Duel Match Wins", "Duel Match Losses", "Duel Match Win Rate",
                            "Duel Series Wins", "Duel Series Losses", "Duel Series Win Rate",
                            "Combined PvP Wins", "Combined PvP Losses", "Combined PvP Win Rate",
                            "Boat Attack Wins", "Boat Attack Losses", "Boat Attack Win Rate"]

    recent_stats_sheet.write_row(0, 0, recent_stats_headers)

    all_stats_headers = ["Player Name", "Player Tag",
                         "Regular PvP Wins", "Regular PvP Losses", "Regular PvP Win Rate",
                         "Special PvP Wins", "Special PvP Losses", "Special PvP Win Rate",
                         "Duel Match Wins", "Duel Match Losses", "Duel Match Win Rate",
                         "Duel Series Wins", "Duel Series Losses", "Duel Series Win Rate",
                         "Combined PvP Wins", "Combined PvP Losses", "Combined PvP Win Rate",
                         "Boat Attack Wins", "Boat Attack Losses", "Boat Attack Win Rate"]

    all_stats_sheet.write_row(0, 0, all_stats_headers)

    # Card levels headers
    if include_card_levels:
        card_levels_headers = ["Player Name", "Player Tag"] + list(range(14, 0, -1))
        card_levels_quantity_sheet.write_row(0, 0, card_levels_headers)
        card_levels_percentile_sheet.write_row(0, 0, card_levels_headers)

    # Get data
    deck_usage_today = clash_utils.get_deck_usage_today()

    # Write data
    row = 1

    for user in users:
        # Get info
        clan_id = user['clan_id']
        kicks = get_kicks(user['player_tag'])
        first_joined = user['first_joined']

        if first_joined is None:
            first_joined = "N/A"
        else:
            first_joined = bot_utils.battletime_to_datetime(first_joined).strftime("%Y-%m-%d %H:%M")

        info_row = [user['player_name'], user['player_tag'], user['discord_name'], user['clan_role'], user['time_zone'],
                     "Yes" if user['vacation'] else "No",
                     user['strikes'], user['permanent_strikes'], len(kicks), user['status'], first_joined,
                     clans_dict[clan_id]['clan_name'], clans_dict[clan_id]['clan_tag'],
                     bot_utils.royale_api_url(user['player_tag'])]

        # Get history
        user_history = bot_utils.break_down_usage_history(user['usage_history'], now)
        history_row = [user['player_name'], user['player_tag']]

        for usage, _ in user_history[::-1]:
            history_row.append(usage)

        usage_today = deck_usage_today.get(user['player_tag'])

        if usage_today is None:
            usage_today = 0

        history_row.append(usage_today)

        # Kicks
        kicks_row = [user['player_name'], user['player_tag']]
        kicks_row.extend(kicks)

        # Get stats
        match_performance = get_match_performance_dict(user['player_tag'])

        decks_used = (match_performance['recent']['combined_pvp']['wins'] + match_performance['recent']['combined_pvp']['losses'] +
                      match_performance['recent']['boat_attacks']['wins'] + match_performance['recent']['boat_attacks']['losses'])

        tracked_since = match_performance["recent"]["tracked_since"]

        if tracked_since is None:
            tracked_since = "N/A"
        else:
            tracked_since = tracked_since.strftime("%Y-%m-%d %H:%M")

        recent_stats_row = [user['player_name'], user['player_tag'], match_performance['recent']['fame'], decks_used, tracked_since,
                            match_performance['recent']['regular']['wins'],
                            match_performance['recent']['regular']['losses'],
                            (float(match_performance['recent']['regular']['win_rate'][:-1]) / 100),
                            match_performance['recent']['special']['wins'],
                            match_performance['recent']['special']['losses'],
                            (float(match_performance['recent']['special']['win_rate'][:-1]) / 100),
                            match_performance['recent']['duel_matches']['wins'],
                            match_performance['recent']['duel_matches']['losses'],
                            (float(match_performance['recent']['duel_matches']['win_rate'][:-1]) / 100),
                            match_performance['recent']['duel_series']['wins'],
                            match_performance['recent']['duel_series']['losses'],
                            (float(match_performance['recent']['duel_series']['win_rate'][:-1]) / 100),
                            match_performance['recent']['combined_pvp']['wins'],
                            match_performance['recent']['combined_pvp']['losses'],
                            (float(match_performance['recent']['combined_pvp']['win_rate'][:-1]) / 100),
                            match_performance['recent']['boat_attacks']['wins'],
                            match_performance['recent']['boat_attacks']['losses'],
                            (float(match_performance['recent']['boat_attacks']['win_rate'][:-1]) / 100)]

        all_stats_row = [user['player_name'], user['player_tag'],
                         match_performance['all']['regular']['wins'],
                         match_performance['all']['regular']['losses'],
                         (float(match_performance['all']['regular']['win_rate'][:-1]) / 100),
                         match_performance['all']['special']['wins'],
                         match_performance['all']['special']['losses'],
                         (float(match_performance['all']['special']['win_rate'][:-1]) / 100),
                         match_performance['all']['duel_matches']['wins'],
                         match_performance['all']['duel_matches']['losses'],
                         (float(match_performance['all']['duel_matches']['win_rate'][:-1]) / 100),
                         match_performance['all']['duel_series']['wins'],
                         match_performance['all']['duel_series']['losses'],
                         (float(match_performance['all']['duel_series']['win_rate'][:-1]) / 100),
                         match_performance['all']['combined_pvp']['wins'],
                         match_performance['all']['combined_pvp']['losses'],
                         (float(match_performance['all']['combined_pvp']['win_rate'][:-1]) / 100),
                         match_performance['all']['boat_attacks']['wins'],
                         match_performance['all']['boat_attacks']['losses'],
                         (float(match_performance['all']['boat_attacks']['win_rate'][:-1]) / 100)]

        # Card levels
        card_levels_quantity_row = [user['player_name'], user['player_tag']]
        card_levels_percentiles_row = [user['player_name'], user['player_tag']]

        if include_card_levels:
            clash_data = clash_utils.get_clash_data(user['player_tag'])

            if clash_data is not None:
                percentile = 0

                for i in range(14, 0, -1):
                    percentile += clash_data['cards'][i] / clash_data['found_cards']
                    percentage = round(percentile * 100)
                    card_levels_quantity_row.append(clash_data['cards'][i])
                    card_levels_percentiles_row.append(percentage)

        # Write data to spreadsheet
        info_sheet.write_row(row, 0, info_row)
        history_sheet.write_row(row, 0, history_row)
        kicks_sheet.write_row(row, 0, kicks_row)
        recent_stats_sheet.write_row(row, 0, recent_stats_row)
        all_stats_sheet.write_row(row, 0, all_stats_row)

        if include_card_levels:
            card_levels_quantity_sheet.write_row(row, 0, card_levels_quantity_row)
            card_levels_percentile_sheet.write_row(row, 0, card_levels_percentiles_row)

        row += 1

    workbook.close()
    LOG.info("Export complete")
    return file_path
