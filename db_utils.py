from discord import player
from config import PRIMARY_CLAN_TAG
from credentials import IP, USERNAME, PASSWORD, DB_NAME
from typing import List, Set, Tuple
import blacklist
import bot_utils
import clash_utils
import datetime
import os
import pymysql
import xlsxwriter

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


def connect_to_db():
    """
    Establish connection to database.

    Returns:
        tuple(db, cursor)
    """
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME, charset='utf8mb4')
    cursor = db.cursor(pymysql.cursors.DictCursor)
    return (db, cursor)


def add_new_user(clash_data: dict) -> bool:
    """
    Add a new user to the database. Only used for users that just joined the Discord server.

    Args:
        clash_data(dict): A dictionary of relevant Clash Royale information.
            {
                "player_tag": str,
                "player_name": str,
                "discord_name": str,
                "discord_id": int,
                "clan_role": str,
                "clan_name": str,
                "clan_tag": str
            }

    Returns:
        bool: Whether player was successfully inserted into database.
    """
    db, cursor = connect_to_db()

    # Get clan_id if clan exists. It clan doesn't exist, add to clans table.
    cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clash_data)
    query_result = cursor.fetchone()

    if query_result == None:
        insert_clan_query = "INSERT INTO clans VALUES (DEFAULT, %(clan_tag)s, %(clan_name)s)"
        cursor.execute(insert_clan_query, clash_data)
        cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clash_data)
        query_result = cursor.fetchone()

    # Add clan_id to clash_data for use in user insertion.
    clash_data["clan_id"] = query_result["id"]

    # Set their proper status
    clash_data["status"] = "ACTIVE" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "INACTIVE"

    # Check if the user has previously joined the server with a different player tag.
    # If they have, set their previous associated account's discord_id to NULL and create a new entry.
    cursor.execute("SELECT * FROM users WHERE discord_id = %(discord_id)s", clash_data)
    query_result = cursor.fetchone()

    if query_result != None:
        cursor.execute("UPDATE users SET discord_id = NULL WHERE discord_id = %(discord_id)s", clash_data)

    # Check if player already exists in table.
    cursor.execute("SELECT * FROM users WHERE player_tag = %(player_tag)s", clash_data)
    query_result = cursor.fetchone()

    if query_result is not None:
        if (query_result["status"] == 'ACTIVE') or (query_result["status"] == 'INACTIVE'):
            db.rollback()
            db.close()
            return False
        else:
            update_query = "UPDATE users SET player_name = %(player_name)s,\
                            discord_name = %(discord_name)s,\
                            discord_id = %(discord_id)s,\
                            clan_role = %(clan_role)s,\
                            clan_id = %(clan_id)s,\
                            status = %(status)s\
                            WHERE player_tag = %(player_tag)s"
            cursor.execute(update_query, clash_data)
    else:
        insert_user_query = "INSERT INTO users VALUES (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, %(discord_id)s, %(clan_role)s, TRUE, FALSE, 0, 0, 0, %(status)s, %(clan_id)s)"
        cursor.execute(insert_user_query, clash_data)

    # Get id of newly inserted user.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", clash_data)
    query_result = cursor.fetchone()
    user_id = query_result["id"]

    # Check for match_history and create entries if necessary.
    cursor.execute("SELECT user_id FROM match_history_all WHERE user_id = %s", (user_id))
    query_result = cursor.fetchone()

    if query_result == None:
        last_check_time = get_last_check_time()
        tracked_since = bot_utils.get_current_battletime() if (is_war_time() and (clash_data["status"] == 'ACTIVE')) else None
        cursor.execute("INSERT INTO match_history_recent VALUES (%s, %s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (user_id, last_check_time, tracked_since))
        cursor.execute("INSERT INTO match_history_all VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (user_id))

    # Check if new user is member or visitor. Get id of relevant discord_role.
    role_string = "Member" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "Visitor"
    cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role_string))
    query_result = cursor.fetchone()
    discord_role_id = query_result["id"]

    # Add new role into assigned_roles table.
    insert_assigned_roles_query = "INSERT INTO assigned_roles VALUES (%s, %s)"
    cursor.execute(insert_assigned_roles_query, (user_id, discord_role_id))

    if (clash_data["clan_role"] in {"elder", "coLeader", "leader"}) and (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) and (clash_data["player_tag"] not in blacklist.blacklist):
        role_string = "Elder"
        cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role_string))
        query_result = cursor.fetchone()
        discord_role_id = query_result["id"]
        cursor.execute(insert_assigned_roles_query, (user_id, discord_role_id))

    db.commit()
    db.close()
    return True


def add_new_unregistered_user(player_tag: str) -> bool:
    """
    Add an unregistered player (active in clan but not Discord) to the database.

    Args:
        player_tag(str): Player tag of player to insert.

    Returns:
        bool: Whether the user was successfully added.
    """
    db, cursor = connect_to_db()

    # Get their data
    clash_data = clash_utils.get_clash_user_data(player_tag, player_tag, None)

    if clash_data == None:
        return False

    # Get clan_id if clan exists. It clan doesn't exist, add to clans table.
    cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clash_data)
    query_result = cursor.fetchone()

    if query_result == None:
        insert_clan_query = "INSERT INTO clans VALUES (DEFAULT, %(clan_tag)s, %(clan_name)s)"
        cursor.execute(insert_clan_query, clash_data)
        cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clash_data)
        query_result = cursor.fetchone()

    # Add clan_id to clash_data for use in user insertion.
    clash_data["clan_id"] = query_result["id"]

    # Set their proper status
    clash_data["status"] = "UNREGISTERED" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "DEPARTED"
    clash_data["discord_name"] = f"{clash_data['status']}{player_tag}"

    # Insert them
    insert_user_query = "INSERT INTO users VALUES (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, NULL, %(clan_role)s, TRUE, FALSE, 0, 0, 0, %(status)s, %(clan_id)s)"
    cursor.execute(insert_user_query, clash_data)

    # Create match_history entries.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", clash_data)
    query_result = cursor.fetchone()
    last_check_time = get_last_check_time()
    tracked_since = bot_utils.get_current_battletime() if (is_war_time() and (clash_data["status"] == 'UNREGISTERED')) else None
    cursor.execute("INSERT INTO match_history_recent VALUES (%s, %s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (query_result["id"], last_check_time, tracked_since))
    cursor.execute("INSERT INTO match_history_all VALUES (%s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (query_result["id"]))

    db.commit()
    db.close()

    return True


def update_user(clash_data: dict) -> str:
    """
    Update a user in the database to reflect any changes to their Clash Royale or Discord statuses.

    Args:
        clash_data(dict): A dictionary of relevant Clash Royale information.
            {
                "player_tag": str,
                "player_name": str,
                "discord_name": str,
                "discord_id": int,
                "clan_role": str,
                "clan_name": str,
                "clan_tag": str,
                "status": str (optional)
            }
    """
    db, cursor = connect_to_db()

    # Get clan_id if clan exists. It clan doesn't exist, add to clans table.
    cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clash_data)
    query_result = cursor.fetchone()

    if query_result == None:
        insert_clan_query = "INSERT INTO clans VALUES (DEFAULT, %(clan_tag)s, %(clan_name)s)"
        cursor.execute(insert_clan_query, clash_data)
        cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clash_data)
        query_result = cursor.fetchone()

    clash_data["clan_id"] = query_result["id"]

    if clash_data.get("status") == None:
        clash_data["status"] = "ACTIVE" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "INACTIVE"

    update_query = ""

    if clash_data["discord_id"] == None:
        update_query = "UPDATE users SET player_tag = %(player_tag)s,\
                        player_name = %(player_name)s,\
                        discord_name = %(discord_name)s,\
                        clan_role = %(clan_role)s,\
                        clan_id = %(clan_id)s,\
                        status = %(status)s\
                        WHERE player_tag = %(player_tag)s"
    else:
        update_query = "UPDATE users SET player_tag = %(player_tag)s,\
                        player_name = %(player_name)s,\
                        discord_name = %(discord_name)s,\
                        clan_role = %(clan_role)s,\
                        clan_id = %(clan_id)s,\
                        status = %(status)s\
                        WHERE discord_id = %(discord_id)s"

    cursor.execute(update_query, clash_data)

    db.commit()
    db.close()

    return "Member" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "Visitor"


def get_user_data(search_key: str) -> dict:
    """
    Get a user's information from the users table.

    Args:
        search_key(str): Key to search for in database. First try using as a player tag. If no results, then try as a player name.

    Returns:
        dict: Dict of user's info.
            {
                player_tag: str,
                player_name: str,
                discord_name: str,
                clan_role: str,
                clan_name: str,
                clan_tag: str,
                vacation: bool,
                strikes: int,
                permanent_strikes: int,
                usage_history: int,
                status: str
            }
    """
    db, cursor = connect_to_db()

    user_data = {}
    cursor.execute("SELECT * FROM users WHERE player_tag = %s", (search_key))
    query_result = cursor.fetchone()

    if query_result == None:
        cursor.execute("SELECT * FROM users WHERE player_name = %s", (search_key))
        query_result = cursor.fetchall()

        if len(query_result) != 1:
            db.close()
            return None
        else:
            query_result = query_result[0]

    user_data["player_name"] = query_result["player_name"]
    user_data["player_tag"] = query_result["player_tag"]
    user_data["discord_name"] = query_result["discord_name"]
    user_data["clan_role"] = query_result["clan_role"]
    user_data["vacation"] = query_result["vacation"]
    user_data["strikes"] = query_result["strikes"]
    user_data["permanent_strikes"] = query_result["permanent_strikes"]
    user_data["usage_history"] = query_result["usage_history"]
    user_data["status"] = query_result["status"]

    clan_id = query_result["clan_id"]

    cursor.execute("SELECT * FROM clans WHERE id = %s", (clan_id))
    query_result = cursor.fetchone()

    if query_result == None:
        db.close()
        return None

    user_data["clan_name"] = query_result["clan_name"]
    user_data["clan_tag"] = query_result["clan_tag"]

    db.close()
    return user_data


def give_strike(player_tag: str, delta: int) -> Tuple[int, int, int, int]:
    """
    Give 1 strike to the specified player. Add them as an unregistered user if they don't exist in the database.

    Args:
        player_tag(str): Player to give strike to.
        delta(int): Number of strikes to +/- from current strikes for user.

    Returns:
        Tuple[int, int, int, int]: (old_strike_count, new_strike_count, old_permanent_strike_count, new_permanent_strike_count),
                                   or (None, None, None, None) if something went wrong.
    """
    db, cursor = connect_to_db()

    old_strike_count = None
    new_strike_count = None
    old_permanent_strike_count = None
    new_permanent_strike_count = None
    cursor.execute("SELECT strikes, permanent_strikes FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()

    if query_result is None:
        if not add_new_unregistered_user(player_tag):
            db.close()
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

    db.commit()
    db.close()

    return (old_strike_count, new_strike_count, old_permanent_strike_count, new_permanent_strike_count)


def get_strikes(discord_id: int) -> int:
    """
    Get the current number of strikes a user has.

    Args:
        discord_id(int): Unique Discord id of a member.

    Returns:
        int: Number of strikes the specified user currently has.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT strikes FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    db.close()

    if query_result == None:
        return None

    return query_result["strikes"]

def reset_strikes():
    db, cursor = connect_to_db()

    cursor.execute("UPDATE users SET strikes = 0")
    db.commit()
    db.close()


def get_users_with_strikes() -> List[Tuple[str, str, int]]:
    """
    Get all users in the database that have non-permanent strikes.

    Returns:
        List[Tuple[player_tag(str), player_name(str), strikes(int)]]: List of users with strikes.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_name, player_tag, strikes FROM users WHERE strikes > 0")
    query_result = cursor.fetchall()
    db.close()

    if query_result is None:
        return {}

    strikes_list = [ (user["player_tag"], user["player_name"], user["strikes"]) for user in query_result ]
    strikes_list.sort(key = lambda x : (x[2], x[0].lower()))

    return strikes_list


def set_completed_saturday_status(status: bool):
    """
    Update database to indicate whether the primary clan has crossed the finish line early.

    Args:
        status(bool): New status to set completed_saturday to.
    """
    db, cursor = connect_to_db()

    cursor.execute("UPDATE race_status SET completed_saturday = %s", (status))

    db.commit()
    db.close()


def is_completed_saturday() -> bool:
    """
    Return whether the primary clan crossed the finish line early.

    Returns:
        bool: Completed Saturday status.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT completed_saturday FROM race_status")
    query_result = cursor.fetchone()

    db.close()
    return query_result["completed_saturday"]


def set_colosseum_week_status(status: bool):
    """
    Update database to indicate whether or not it's colosseum week.

    Args:
        status(bool): New status to set colosseum_week to.
    """
    db, cursor = connect_to_db()

    cursor.execute("UPDATE race_status SET colosseum_week = %s", (status))

    db.commit()
    db.close()


def is_colosseum_week() -> bool:
    """
    Return whether it's colosseum week.

    Returns:
        bool: Colosseum week status.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT colosseum_week FROM race_status")
    query_result = cursor.fetchone()

    db.close()
    return query_result["colosseum_week"]


def set_war_time_status(status: bool):
    """
    Update database to indicate whether or not it's war time.

    Args:
        status(bool): New status to set war_time to.
    """
    db, cursor = connect_to_db()

    cursor.execute("UPDATE race_status SET war_time = %s", (status))

    db.commit()
    db.close()


def is_war_time() -> bool:
    """
    Return whether it's war time.

    Returns:
        bool: War time status.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT war_time FROM race_status")
    query_result = cursor.fetchone()

    db.close()
    return query_result["war_time"]


def set_last_check_time(last_check_time: datetime.datetime):
    """
    Update database to indicate when the last win rate tracking check occurred.

    Args:
        last_check_time(datetime.datetime): Last check time in datetime format.
    """
    db, cursor = connect_to_db()

    last_check_time = bot_utils.datetime_to_battletime(last_check_time)
    cursor.execute("UPDATE race_status SET last_check_time = %s", (last_check_time))

    db.commit()
    db.close()


def get_last_check_time() -> str:
    """
    Get the time when the last win rate tracking check occurred.

    Returns:
        str: Time of last win rate tracking check.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT last_check_time FROM race_status")
    query_result = cursor.fetchone()

    db.close()
    return query_result["last_check_time"]


def set_reset_time(reset_time: datetime.datetime):
    """
    Save most recent daily reset time to database.

    Args:
        reset_time(datetime.datetime): Most recent reset time.
    """
    db, cursor = connect_to_db()

    reset_time_str = bot_utils.datetime_to_battletime(reset_time)
    cursor.execute("UPDATE race_status SET reset_time = %s", (reset_time_str))

    river_race_days = {4: 'thursday', 5: 'friday', 6: 'saturday', 0: 'sunday'}
    weekday = river_race_days.get(reset_time.weekday(), None)

    if weekday is not None:
        cursor.execute(f"UPDATE race_reset_times SET {weekday} = %s", (reset_time_str))

    db.commit()
    db.close()


def get_reset_time() -> datetime.datetime:
    """
    Get the most recent daily reset time from the database.

    Returns:
        datetime.datetime: Most recent reset time.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT reset_time FROM race_status")
    query_result = cursor.fetchone()
    reset_time = bot_utils.battletime_to_datetime(query_result["reset_time"])

    db.close()
    return reset_time


def get_river_race_reset_times() -> dict:
    """
    Get the reset time of each day during the most recent river race.

    Returns:
        dict{str: datetime.datetime}: Dict of weekday and reset time pairs.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT * FROM race_reset_times")
    query_result = cursor.fetchone()
    db.close()

    reset_times = {"thursday":  bot_utils.battletime_to_datetime(query_result["thursday"]),
                   "friday":    bot_utils.battletime_to_datetime(query_result["friday"]),
                   "saturday":  bot_utils.battletime_to_datetime(query_result["saturday"]),
                   "sunday":    bot_utils.battletime_to_datetime(query_result["sunday"])}

    return reset_times


def get_player_tag(search_key) -> str:
    """
    Return the player tag corresponding to a Discord member.

    Args:
        search_key: Key to search for in database. First try using as a unique Discord id. If no results, then try as a player name.

    Returns:
        str: Specified member's player tag.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users WHERE discord_id = %s", (search_key))
    query_result = cursor.fetchone()

    if query_result is None:
        cursor.execute("SELECT player_tag FROM users WHERE player_name = %s", (search_key))
        query_result = cursor.fetchall()

        if len(query_result) != 1:
            db.close()
            return None
        else:
            query_result = query_result[0]

    player_tag = query_result["player_tag"]

    db.close()
    return player_tag


def get_member_id(player_tag: str) -> int:
    """
    Return the Discord ID corresponding to the specified player tag, or None if member is not on Discord.

    Args:
        player_tag(str): Player tag of user to find ID of.

    Returns:
        int: Discord ID of specified user, or None if not found.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT discord_id FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()
    db.close()

    if query_result is None:
        return None

    return query_result["discord_id"]



def remove_user(discord_id: int):
    """
    Remove a user's assigned roles and change their status to either UNREGISTERED or DEPARTED.

    Args:
        discord_id(int): Unique Discord id of a member.
    """
    db, cursor = connect_to_db()

    # Get id and player_tag of user.
    cursor.execute("SELECT id, player_tag FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    if (query_result == None):
        db.close()
        return

    user_id = query_result["id"]
    player_tag = query_result["player_tag"]

    # Delete any assigned Discord roles associated with the user.
    cursor.execute("DELETE FROM assigned_roles WHERE user_id = %s", (user_id))
    active_members = clash_utils.get_active_members_in_clan()

    # If the user is still an active member of the primary clan, change their status to UNREGISTERED.
    # Otherwise change it to DEPARTED.
    if player_tag in active_members:
        cursor.execute("UPDATE users SET discord_name = %s, status = 'UNREGISTERED' WHERE id = %s",
                       (f"UNREGISTERED{player_tag}", user_id))
    else:
        cursor.execute("UPDATE users SET discord_name = %s, status = 'DEPARTED' WHERE id = %s",
                       (f"DEPARTED{player_tag}", user_id))

    db.commit()
    db.close()


# Drop all users and assigned roles.
def remove_all_users():
    db, cursor = connect_to_db()

    cursor.execute("DELETE FROM assigned_roles")
    cursor.execute("DELETE FROM match_history_recent")
    cursor.execute("DELETE FROM match_history_all")
    cursor.execute("DELETE FROM kicks")
    cursor.execute("DELETE FROM users")

    db.commit()
    db.close()


def update_vacation_for_user(discord_id: int, status: bool=None) -> bool:
    """
    Toggle a user's vacation status.

    Args:
        discord_id(int): Unique Discord id of a member.
        status(bool): What to set specified user's vacation status to. If None, set status to opposite of current status.

    Returns:
        bool: The specified user's updated vacation status.
    """
    db, cursor = connect_to_db()

    if (type(status) == bool):
        update_vacation_query = "UPDATE users SET vacation = %s WHERE discord_id = %s"
        cursor.execute(update_vacation_query, (status, discord_id))
    else:
        update_vacation_query = "UPDATE users SET vacation = NOT vacation WHERE discord_id = %s"
        cursor.execute(update_vacation_query, (discord_id))

    cursor.execute("SELECT vacation FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    if (query_result == None):
        db.close()
        return False

    db.commit()
    db.close()

    return query_result["vacation"]


def get_users_on_vacation() -> dict:
    """
    Get a dict of active members that are currently on vacation.

    Returns:
        dict{player_tag(str): player_name(str)}: Player names and tags of users on vacation.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_name, player_tag FROM users WHERE vacation = TRUE")
    query_result = cursor.fetchall()
    db.close()

    if query_result is None:
        return {}

    active_members = clash_utils.get_active_members_in_clan()
    users_on_vacation = { user["player_tag"]: user["player_name"] for user in query_result if user["player_tag"] in active_members }
    return users_on_vacation


# Set vacation to false for all users.
def clear_all_vacation():
    db, cursor = connect_to_db()

    cursor.execute("UPDATE users SET vacation = FALSE")

    db.commit()
    db.close()


# Set whether to send deck usage reminders.
def set_reminder_status(status: bool):
    db, cursor = connect_to_db()

    cursor.execute("UPDATE automation_status SET send_reminders = %s", (status))

    db.commit()
    db.close()


# Return current reminder status.
def get_reminder_status() -> bool:
    db, cursor = connect_to_db()

    cursor.execute("SELECT * FROM automation_status")
    query_result = cursor.fetchone()

    if query_result == None:
        db.close()
        return False

    status = query_result["send_reminders"]
    db.close()
    return status


# Set whether to send strikes automatically.
def set_strike_status(status: bool):
    db, cursor = connect_to_db()

    cursor.execute("UPDATE automation_status SET send_strikes = %s", (status))

    db.commit()
    db.close()


# Return current strike status.
def get_strike_status() -> bool:
    db, cursor = connect_to_db()

    cursor.execute("SELECT * FROM automation_status")
    query_result = cursor.fetchone()

    status = query_result["send_strikes"]
    db.close()
    return status


def get_roles(discord_id: int) -> list:
    """
    Get the list of roles currently assigned to a user.

    Args:
        discord_id(int): Unique Discord id of a member.

    Returns:
        list[str]: List of role names assigned to the specified user.
    """
    db, cursor = connect_to_db()

    # Get user_id.
    cursor.execute("SELECT id FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    if (query_result == None):
        db.close()
        return []

    user_id = query_result["id"]

    # Get list of discord_role_ids corresponding to user_id.
    cursor.execute("SELECT discord_role_id FROM assigned_roles WHERE user_id = %s", (user_id))
    query_result = cursor.fetchall()

    if (query_result == None):
        db.close()
        return []

    discord_role_ids = []

    for entry in query_result:
        discord_role_ids.append(entry["discord_role_id"])

    # Get list of role_names.
    roles = []

    for discord_role_id in discord_role_ids:
        cursor.execute("SELECT role_name FROM discord_roles WHERE id = %s", (discord_role_id))
        query_result = cursor.fetchone()

        if (query_result == None):
            continue

        roles.append(query_result["role_name"])

    return roles


def commit_roles(discord_id: int, roles: list):
    """
    Delete the roles currently assigned to a user. Then record their new roles.

    Args:
        discord_id(int): Unique Discord id of a member.
        roles(list): List of new roles to assign to user.
    """
    db, cursor = connect_to_db()

    # Get user_id from player_name.
    cursor.execute("SELECT id FROM users WHERE discord_id = %s", (discord_id))
    query_result = cursor.fetchone()

    if (query_result == None):
        db.close()
        return

    user_id = query_result["id"]

    cursor.execute("DELETE FROM assigned_roles WHERE user_id = %s", (user_id))

    for role in roles:
        cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role))
        query_result = cursor.fetchone()

        if (query_result == None):
            continue

        discord_role_id = query_result["id"]

        cursor.execute("INSERT INTO assigned_roles VALUES (%s, %s)", (user_id, discord_role_id))

    db.commit()
    db.close()


def update_time_zone(discord_id: int, US_time: bool):
    """
    Change a user's preferred time for receiving automated reminders.

    Args:
        discord_id(int): Unique Discord id of a member.
        US_time(bool): Whether user should receive automated reminders on US time (True) or EU time (False).
    """
    db, cursor = connect_to_db()

    cursor.execute("UPDATE users SET US_time = %s WHERE discord_id = %s", (US_time, discord_id))

    db.commit()
    db.close()


def get_members_in_time_zone(US_time: bool) -> Set[str]:
    """
    Get the members in the specified time zone.

    Returns:
        set[player_tag(str)]: Player tags of users in specified time zone.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users WHERE US_time = %s", (US_time))
    query_result = cursor.fetchall()

    if query_result == None:
        db.close()
        return None

    members = { user["player_tag"] for user in query_result }

    db.close()
    return members


def record_deck_usage_today(deck_usage: dict):
    """
    Log how many decks were used today by each member of the primary clan. Any users in the database but not in the primary clan
    will be considered to have used 0 decks today.

    Args:
        deck_usage(dict): dict of users and number of decks used today.
            {player_tag(str): decks_used_today(int)}
    """
    db, cursor = connect_to_db()

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

        if query_result == None:
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

    db.commit()
    db.close()


def get_all_user_deck_usage_history() -> List[Tuple[str, str, int, int, str]]:
    """
    Get usage history of all users in database.

    Returns:
        List[Tuple[str, str, int, str]]: List of player names, tags, discord ids, usage histories, and tracked since dates.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT id, player_name, player_tag, discord_id, usage_history FROM users")
    users = cursor.fetchall()

    usage_list = []

    for user in users:
        cursor.execute("SELECT tracked_since FROM match_history_recent WHERE user_id = %s", (user["id"]))
        tracked_since = cursor.fetchone()["tracked_since"]

        if tracked_since == None:
            tracked_since = "Unknown"
        else:
            tracked_since = bot_utils.battletime_to_datetime(tracked_since)
            tracked_since = (tracked_since.strftime("%a") + ", " +  tracked_since.strftime("%b") + " " + str(tracked_since.day).zfill(2) +
                            " " + tracked_since.strftime("%H:%M") + " UTC")

        usage_list.append((user["player_name"], user["player_tag"], user["discord_id"], user["usage_history"], tracked_since))

    usage_list.sort(key = lambda x : x[0].lower())
    db.close()
    return usage_list


def clean_up_db(active_members: dict=None):
    """
    Checks that every user in the database has an appropriate status.
    ACTIVE users that are no longer active members of the clan are moved to INACTIVE.
    UNREGISTERED users that are no longer active members of the clan are moved to DEPARTED.
    INACTIVE users that are now part of the clan are moved to ACTIVE.
    DEPARTED users that are now part of the clan are moved to UNREGISTERED.
    """
    db, cursor = connect_to_db()

    if active_members == None:
        active_members = clash_utils.get_active_members_in_clan()

    if len(active_members) == 0:
        return

    cursor.execute("SELECT id, player_name, player_tag, discord_name, discord_id, status FROM users")
    query_result = cursor.fetchall()

    for user in query_result:
        id = user["id"]
        player_tag = user["player_tag"]
        discord_name = user["discord_name"]
        discord_id = user["discord_id"]
        status = user["status"]

        if player_tag in active_members:
            if status in {'INACTIVE', 'DEPARTED'}:
                clash_data = clash_utils.get_clash_user_data(player_tag, discord_name, discord_id)
                if clash_data == None:
                    continue

                if status == 'DEPARTED':
                    clash_data["discord_name"] = f"UNREGISTERED{player_tag}"
                    clash_data["status"] = 'UNREGISTERED'

                update_user(clash_data)

                if is_war_time():
                    cursor.execute("SELECT tracked_since FROM match_history_recent WHERE user_id = %s", (id))
                    query_result = cursor.fetchone()
                    if query_result["tracked_since"] == None:
                        last_check_time = get_last_check_time()
                        tracked_since = bot_utils.get_current_battletime()
                        cursor.execute("UPDATE match_history_recent SET last_check_time = %s, tracked_since = %s WHERE user_id = %s",
                                       (last_check_time, tracked_since, id))
        else:
            if status in {'ACTIVE', 'UNREGISTERED'}:
                clash_data = clash_utils.get_clash_user_data(player_tag, discord_name, discord_id)
                if clash_data == None:
                    continue

                if status == 'UNREGISTERED':
                    clash_data["discord_name"] = f"DEPARTED{player_tag}"
                    clash_data["status"] = 'DEPARTED'

                update_user(clash_data)

    db.commit()
    db.close()


def get_server_members_info() -> dict:
    """
    Get database information of all members in the server.

    Returns:
        dict: dict containing info about server members.
            {
                discord_id(int): {
                    player_tag(str),
                    player_name(str),
                    discord_id(int),
                    discord_name(str),
                    clan_role(str)
                }
            }
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_tag, player_name, discord_id, discord_name, clan_role FROM users WHERE discord_id IS NOT NULL")
    query_result = cursor.fetchall()
    db.close()

    if query_result == None:
        return {}

    player_info = {user["discord_id"]: user for user in query_result}

    return player_info


def get_and_update_match_history_info(player_tag: str, fame: int, new_check_time: datetime.datetime) -> Tuple[int, datetime.datetime]:
    """
    Get a user's fame and time when their battlelog was last checked. Then store their updated fame and current time.

    Args:
        player_tag(str): Player to get/set fame for.
        fame(int): Current fame value.
        new_check_time(datetime.datetime): Current time to set last_check_time to.

    Returns:
        tuple(fame(int), last_check_time(datetime.datetime: Previous fame value and battle time.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT last_check_time, fame FROM match_history_recent WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)", (player_tag))
    query_result = cursor.fetchone()
    fame_and_time = (None, None)

    if query_result is None:
        if not add_new_unregistered_user(player_tag):
            db.close()
            return fame_and_time
        fame_and_time = (0, bot_utils.battletime_to_datetime(get_last_check_time()))
    else:
        fame_and_time = (query_result["fame"], bot_utils.battletime_to_datetime(query_result["last_check_time"]))

    cursor.execute("UPDATE match_history_recent SET last_check_time = %s, fame = %s WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)",
                   (bot_utils.datetime_to_battletime(new_check_time), fame, player_tag))

    db.commit()
    db.close()
    return fame_and_time


def set_users_last_check_time(player_tag: str, last_check_time: datetime.datetime):
    """
    Sets the last check time of a specific user.

    Args:
        player_tag(str): Player to update.
        last_check_time(datetime.datetime): Time to set for specified user.
    """
    db, cursor = connect_to_db()
    
    last_check_time = bot_utils.datetime_to_battletime(last_check_time)
    cursor.execute("UPDATE match_history_recent SET last_check_time = %s WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)",
                   (last_check_time, player_tag))

    db.commit()
    db.close()


def update_match_history(user_performance_list: list):
    """
    Add each player's game stats to the match_history tables.

    Args:
        user_performance_list(list[dict]): List of user dictionaries with their river race results.
    """
    db, cursor = connect_to_db()

    for user in user_performance_list:
        if not user:
            continue

        cursor.execute("UPDATE match_history_recent SET\
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
                        WHERE user_id IN (SELECT id FROM users WHERE player_tag = %(player_tag)s)", user)

        cursor.execute("UPDATE match_history_all SET\
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
                        WHERE user_id IN (SELECT id FROM users WHERE player_tag = %(player_tag)s)", user)

    db.commit()
    db.close()


def prepare_for_river_race(last_check_time: datetime.datetime):
    """
    Needs to run every Thursday when river race starts. Resets fame to 0 and sets last_check_time to current time. Set tracked_since
    to current time for active members and NULL for everyone else. Also sets the relevant race_status fields.

    Args:
        last_check_time(datetime.datetime): When match performance is next calculated, do not look at games before this time.
    """
    set_completed_saturday_status(False)
    set_colosseum_week_status(False)
    set_war_time_status(True)
    set_last_check_time(last_check_time)
    clean_up_db()

    db, cursor = connect_to_db()

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
                    user_id IN (SELECT id FROM users WHERE status = 'ACTIVE' OR status = 'UNREGISTERED')",
                    (last_check_time))

    clans_in_race = clash_utils.get_clans_and_fame()
    cursor.execute("DELETE FROM river_race_clans")

    for clan_tag in clans_in_race:
        clan_name, _ = clans_in_race[clan_tag]
        cursor.execute("INSERT INTO river_race_clans VALUES (%s, %s, 0)", (clan_tag, clan_name))

    db.commit()
    db.close()


def save_clans_fame():
    """
    Update river_race_clans table with clans' current accumulated fames.
    """
    db, cursor = connect_to_db()
    clans_in_race = clash_utils.get_clans_and_fame()

    for clan_tag in clans_in_race:
        _, fame = clans_in_race[clan_tag]
        cursor.execute("UPDATE river_race_clans SET fame = %s WHERE clan_tag = %s", (fame, clan_tag))

    db.commit()
    db.close()


def get_saved_clans_and_fame() -> dict:
    """
    Get the clans and their saved fame values from river_race_clans.

    Returns:
        dict{clan_tag: Tuple[clan_name, fame]}: Clans and their saved fame.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT * FROM river_race_clans")
    query_result = cursor.fetchall()

    clans_info = {clan["clan_tag"]: (clan["clan_name"], clan["fame"]) for clan in query_result}

    db.close()
    return clans_info


def get_match_performance_dict(player_tag: str) -> dict:
    """
    Get a dict containing a specified user's match performance.

    Args:
        player_tag(str): Player tag to get stats for.

    Returns:
        dict {str: dict{str: int/float}}: dict containing specified player's stats.
            {
                "all/recent": {
                    "fame": int, (recent only)
                    "tracked_since": datetime.datetime, (recent only)
                    "regular":
                    {
                        "wins": int,
                        "losses": int,
                        "total": int,
                        "win_rate": str
                    },
                    "special":
                    {
                        "wins": int,
                        "losses": int,
                        "total": int,
                        "win_rate": str
                    },
                    "duel_matches":
                    {
                        "wins": int,
                        "losses": int,
                        "total": int,
                        "win_rate": str
                    },
                    "duel_series":
                    {
                        "wins": int,
                        "losses": int,
                        "total": int,
                        "win_rate": str
                    },
                    "combined_pvp":
                    {
                        "wins": int,
                        "losses": int,
                        "total": int,
                        "win_rate": str
                    },
                    "boat_attacks":
                    {
                        "wins": int,
                        "losses": int,
                        "total": int,
                        "win_rate": str
                    }
                }
            }
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT fame, tracked_since, battle_wins, battle_losses, special_battle_wins, special_battle_losses, boat_attack_wins, boat_attack_losses, duel_match_wins, duel_match_losses, duel_series_wins, duel_series_losses\
                    FROM match_history_recent WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)", (player_tag))

    match_performance_recent = cursor.fetchone()

    cursor.execute("SELECT battle_wins, battle_losses, special_battle_wins, special_battle_losses, boat_attack_wins, boat_attack_losses, duel_match_wins, duel_match_losses, duel_series_wins, duel_series_losses\
                    FROM match_history_all WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)", (player_tag))

    match_performance_all = cursor.fetchone()

    if (match_performance_recent == None) or (match_performance_all == None):
        db.close()
        return None

    db_info_dict = {"recent": match_performance_recent, "all": match_performance_all}
    tracked_since = match_performance_recent["tracked_since"]

    if tracked_since != None:
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

    db.close()
    return match_performance_dict


def add_unregistered_users(clan_tag: str=PRIMARY_CLAN_TAG, active_members: dict=None):
    """
    Add any active members not in the database as UNREGISTERED users.

    Args:
        clan_tag(str): Clan to get users from.
    """
    if active_members == None:
        active_members = clash_utils.get_active_members_in_clan(clan_tag)
    else:
        active_members = active_members.copy()

    db, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users")
    query_result = cursor.fetchall()
    db.close()

    if query_result is None:
        return

    for user in query_result:
        active_members.pop(user["player_tag"], None)

    for player_tag in active_members:
        add_new_unregistered_user(player_tag)


def kick_user(player_tag: str) -> Tuple[int, str]:
    """
    Insert a kick entry for the specified user.

    Args:
        player_tag(str): Player tag of user to kick.

    Returns:
        Tuple[int, str]: Tuple of total number of kicks and last time user was kicked.
    """
    kick_time = bot_utils.get_current_battletime()
    db, cursor = connect_to_db()

    cursor.execute("SELECT id FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()
    id = query_result["id"]

    cursor.execute("INSERT INTO kicks VALUES (%s, %s)", (id, kick_time))

    db.commit()
    db.close()

    kicks = get_kicks(player_tag)
    total_kicks = len(kicks)
    last_kick_date = None

    if total_kicks == 1:
        last_kick_date = "Today"
    else:
        last_kick_date = kicks[-2]

    return (total_kicks, last_kick_date)


def undo_kick(player_tag: str) -> str:
    """
    Undo the latest kick of the specified user.

    Args:
        player_tag(str): Player tag of user to undo kick for.

    Returns:
        str: Time of undone kick, or None if user has not been kicked before.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT id FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()
    id = query_result["id"]

    cursor.execute("SELECT kick_time FROM kicks WHERE user_id = %s", (id))
    query_result = cursor.fetchall()

    if len(query_result) == 0:
        db.close()
        return None

    kicks = [ kick["kick_time"] for kick in query_result ]
    kicks.sort()
    latest_kick_time = kicks[-1]

    cursor.execute("DELETE FROM kicks WHERE user_id = %s AND kick_time = %s", (id, latest_kick_time))
    latest_kick_time = bot_utils.battletime_to_datetime(latest_kick_time).strftime("%Y-%m-%d")
    
    db.commit()
    db.close()
    return latest_kick_time


def get_kicks(player_tag: str) -> List[str]:
    """
    Get a list of times a user was kicked.

    Args:
        player_tag(str): Player tag of user to get kicks for.
    
    Returns:
        List[datetime.date]: List of times the user was kicked.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT kick_time FROM kicks WHERE user_id = (SELECT id FROM users WHERE player_tag = %s)", (player_tag))
    query_result = cursor.fetchall()
    kicks = []

    for kick in query_result:
        kick_time = bot_utils.battletime_to_datetime(kick["kick_time"])
        kicks.append(kick_time.strftime("%Y-%m-%d"))

    kicks.sort()

    db.close()
    return kicks


def get_file_path() -> str:
    """
    Get path of new CSV file that should be created during export process.

    Returns:
        str: Path to new CSV file.
    """
    path = 'export_files'

    if not os.path.exists(path):
        os.makedirs(path)

    files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    files.sort(key = lambda x : os.path.getmtime(x))

    if len(files) >= 5:
        os.remove(files[0])

    file_name = "members_" + str(datetime.datetime.now().date()) + ".xlsx"
    new_path = os.path.join(path, file_name)

    return new_path


def export(primary_clan_only: bool) -> str:
    """
    Create Excel spreadsheet containing relevant information from the database.

    Args:
        primary_clan_only(bool)

    Returns:
        str: Path to spreadsheet.
    """
    # Clean up the database and add any members of the clan to it that aren't already in it.
    active_members = clash_utils.get_active_members_in_clan()
    clean_up_db()
    add_unregistered_users(active_members=active_members)

    db, cursor = connect_to_db()

    # Get clan info.
    clans = None

    if primary_clan_only:
        cursor.execute("SELECT * FROM clans WHERE clan_tag = %s", (PRIMARY_CLAN_TAG))
        clans = cursor.fetchall()
    else:
        cursor.execute("SELECT * FROM clans")
        clans = cursor.fetchall()

    if clans == None:
        return None

    clans_dict = {}

    for clan in clans:
        clans_dict[clan["id"]] = clan

    # Get users.
    if primary_clan_only:
        cursor.execute("SELECT * FROM users WHERE status = 'ACTIVE' OR status = 'UNREGISTERED'")
    else:
        cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()

    if users == None:
        return None

    db.close()

    # Create Excel workbook
    file_path = get_file_path()
    workbook = xlsxwriter.Workbook(file_path)
    info_sheet = workbook.add_worksheet("Info")
    history_sheet = workbook.add_worksheet("History")
    kicks_sheet = workbook.add_worksheet("Kicks")
    recent_stats_sheet = workbook.add_worksheet("Recent Stats")
    all_stats_sheet = workbook.add_worksheet("All Stats")

    # Info sheet headers
    info_headers = ["Player Name", "Player Tag", "Discord Name", "Clan Role", "Time Zone", "On Vacation", "Strikes", "Permanent Strikes", "Kicks", "Status", "Clan Name", "Clan Tag", "RoyaleAPI"]
    info_sheet.write_row(0, 0, info_headers)

    # History sheet headers
    history_headers = ["Player Name", "Player Tag"]
    now = datetime.datetime.now(datetime.timezone.utc)
    now_date = None

    if now.time() < get_reset_time().time():
        now_date = (now - datetime.timedelta(days=1)).date()
    else:
        now_date = now.date()

    today_header = now_date.strftime("%a") + ", " +  now_date.strftime("%b") + " " + str(now_date.day).zfill(2)

    for _, day in bot_utils.break_down_usage_history(users[0]["usage_history"], now)[::-1]:
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

    # Get data
    deck_usage_today = clash_utils.get_deck_usage_today(active_members=active_members)

    # Write data
    row = 1

    for user in users:
        # Get info
        clan_id = user["clan_id"]
        kicks = get_kicks(user["player_tag"])
        info_row = [user["player_name"], user["player_tag"], user["discord_name"], user["clan_role"],
                     "US" if user["US_time"] else "EU",
                     "Yes" if user["vacation"] else "No",
                     user["strikes"], user["permanent_strikes"], len(kicks), user["status"],
                     clans_dict[clan_id]["clan_name"], clans_dict[clan_id]["clan_tag"],
                     f"https://royaleapi.com/player/{user['player_tag'][1:]}"]

        # Get history
        user_history = bot_utils.break_down_usage_history(user["usage_history"], now)
        history_row = [user["player_name"], user["player_tag"]]

        for usage, _ in user_history[::-1]:
            history_row.append(usage)

        usage_today = deck_usage_today.get(user["player_tag"])

        if usage_today == None:
            usage_today = 0

        history_row.append(usage_today)

        # Kicks
        kicks_row = [user["player_name"], user["player_tag"]]
        kicks_row.extend(kicks)

        # Get stats
        match_performance = get_match_performance_dict(user["player_tag"])

        decks_used = (match_performance["recent"]["combined_pvp"]["wins"] + match_performance["recent"]["combined_pvp"]["losses"] +
                      match_performance["recent"]["boat_attacks"]["wins"] + match_performance["recent"]["boat_attacks"]["losses"])

        tracked_since = match_performance["recent"]["tracked_since"]

        if tracked_since == None:
            tracked_since = "N/A"
        else:
            tracked_since = (tracked_since.strftime("%a") + ", " +  tracked_since.strftime("%b") + " " + str(tracked_since.day).zfill(2) +
                             " " + tracked_since.strftime("%H:%M"))

        recent_stats_row = [user["player_name"], user["player_tag"], match_performance["recent"]["fame"], decks_used, tracked_since,
                            match_performance["recent"]["regular"]["wins"],
                            match_performance["recent"]["regular"]["losses"],
                            (float(match_performance["recent"]["regular"]["win_rate"][:-1]) / 100),
                            match_performance["recent"]["special"]["wins"],
                            match_performance["recent"]["special"]["losses"],
                            (float(match_performance["recent"]["special"]["win_rate"][:-1]) / 100),
                            match_performance["recent"]["duel_matches"]["wins"],
                            match_performance["recent"]["duel_matches"]["losses"],
                            (float(match_performance["recent"]["duel_matches"]["win_rate"][:-1]) / 100),
                            match_performance["recent"]["duel_series"]["wins"],
                            match_performance["recent"]["duel_series"]["losses"],
                            (float(match_performance["recent"]["duel_series"]["win_rate"][:-1]) / 100),
                            match_performance["recent"]["combined_pvp"]["wins"],
                            match_performance["recent"]["combined_pvp"]["losses"],
                            (float(match_performance["recent"]["combined_pvp"]["win_rate"][:-1]) / 100),
                            match_performance["recent"]["boat_attacks"]["wins"],
                            match_performance["recent"]["boat_attacks"]["losses"],
                            (float(match_performance["recent"]["boat_attacks"]["win_rate"][:-1]) / 100)]

        all_stats_row = [user["player_name"], user["player_tag"],
                         match_performance["all"]["regular"]["wins"],
                         match_performance["all"]["regular"]["losses"],
                         (float(match_performance["all"]["regular"]["win_rate"][:-1]) / 100),
                         match_performance["all"]["special"]["wins"],
                         match_performance["all"]["special"]["losses"],
                         (float(match_performance["all"]["special"]["win_rate"][:-1]) / 100),
                         match_performance["all"]["duel_matches"]["wins"],
                         match_performance["all"]["duel_matches"]["losses"],
                         (float(match_performance["all"]["duel_matches"]["win_rate"][:-1]) / 100),
                         match_performance["all"]["duel_series"]["wins"],
                         match_performance["all"]["duel_series"]["losses"],
                         (float(match_performance["all"]["duel_series"]["win_rate"][:-1]) / 100),
                         match_performance["all"]["combined_pvp"]["wins"],
                         match_performance["all"]["combined_pvp"]["losses"],
                         (float(match_performance["all"]["combined_pvp"]["win_rate"][:-1]) / 100),
                         match_performance["all"]["boat_attacks"]["wins"],
                         match_performance["all"]["boat_attacks"]["losses"],
                         (float(match_performance["all"]["boat_attacks"]["win_rate"][:-1]) / 100)]

        # Write data to spreadsheet
        info_sheet.write_row(row, 0, info_row)
        history_sheet.write_row(row, 0, history_row)
        kicks_sheet.write_row(row, 0, kicks_row)
        recent_stats_sheet.write_row(row, 0, recent_stats_row)
        all_stats_sheet.write_row(row, 0, all_stats_row)
        row += 1

    workbook.close()
    return file_path