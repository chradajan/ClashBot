from discord import player
from config import PRIMARY_CLAN_TAG
from credentials import IP, USERNAME, PASSWORD, DB_NAME
import blacklist
import bot_utils
import clash_utils
import csv
import datetime
import os
import pymysql

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


# clash_data = {
#     player_tag: str,
#     player_name: str,
#     discord_name: str,
#     clan_role: str,
#     clan_name: str,
#     clan_tag: str
# }
def add_new_user(clash_data: dict) -> bool:
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

    # Check if player already exists in table.
    cursor.execute("SELECT * FROM users WHERE player_tag = %(player_tag)s", clash_data)
    query_result = cursor.fetchone()

    if query_result != None:
        if query_result["status"] == 'ACTIVE':
            db.rollback()
            db.close()
            return False
        else:
            update_query = "UPDATE users SET player_name = %(player_name)s,\
                            discord_name = %(discord_name)s,\
                            clan_role = %(clan_role)s,\
                            clan_id = %(clan_id)s,\
                            status = %(status)s\
                            WHERE player_tag = %(player_tag)s"
            cursor.execute(update_query, clash_data)
    else:
        insert_user_query = "INSERT INTO users VALUES (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, %(clan_role)s, TRUE, FALSE, 0, 0, %(status)s, %(clan_id)s)"
        cursor.execute(insert_user_query, clash_data)

    # Get id of newly inserted user.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", clash_data)
    query_result = cursor.fetchone()
    user_id = query_result["id"]

    # Check for match_history and create entry if necessary.
    cursor.execute("SELECT user_id FROM match_history WHERE user_id = %s", (user_id))
    query_result = cursor.fetchone()

    if query_result == None:
        battle_time = bot_utils.datetime_to_battletime(datetime.datetime.now(datetime.timezone.utc))
        cursor.execute("INSERT INTO match_history VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (user_id, battle_time))

    # Check if new user is member or visitor. Get id of relevant discord_role.
    role_string = "Member" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "Visitor"
    cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role_string))
    query_result = cursor.fetchone()
    discord_role_id = query_result["id"]

    # Add new role into assigned_roles table.
    insert_assigned_roles_query = "INSERT INTO assigned_roles VALUES (%s, %s)"
    cursor.execute(insert_assigned_roles_query, (user_id, discord_role_id))

    if (clash_data["clan_role"] == "elder") and (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) and (clash_data["player_name"] not in blacklist.blacklist):
        role_string = "Elder"
        cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role_string))
        query_result = cursor.fetchone()
        discord_role_id = query_result["id"]
        cursor.execute(insert_assigned_roles_query, (user_id, discord_role_id))

    db.commit()
    db.close()
    return True


def add_new_unregistered_user(player_tag: str):
    """
    Add an unregistered player (active in clan but not Discord) to the database.

    Args:
        player_tag(str): Player tag of player to insert.
    """
    db, cursor = connect_to_db()

    # Get their data
    clash_data = clash_utils.get_clash_user_data(player_tag, "UNREGISTERED" + player_tag)

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
    clash_data["status"] = "UNREGISTERED"

    # Insert them
    insert_user_query = "INSERT INTO users VALUES (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, %(clan_role)s, TRUE, FALSE, 0, 0, %(status)s, %(clan_id)s)"
    cursor.execute(insert_user_query, clash_data)

    # Create match_history entry.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", clash_data)
    query_result = cursor.fetchone()
    battle_time = bot_utils.datetime_to_battletime(datetime.datetime.now(datetime.timezone.utc))
    cursor.execute("INSERT INTO match_history VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (query_result["id"], battle_time))

    db.commit()
    db.close()

# Update existing user.
# clash_data = {
#     player_tag: str,
#     player_name: str,
#     discord_name: str,
#     clan_role: str,
#     clan_name: str,
#     clan_tag: str
# }
def update_user(clash_data: dict, original_player_name: str) -> str:
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
    clash_data["original_player_name"] = original_player_name
    clash_data["status"] = "ACTIVE" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "INACTIVE"

    update_query = "UPDATE users SET player_tag = %(player_tag)s,\
                    player_name = %(player_name)s,\
                    discord_name = %(discord_name)s,\
                    clan_role = %(clan_role)s,\
                    clan_id = %(clan_id)s,\
                    status = %(status)s\
                    WHERE player_name = %(original_player_name)s"
    cursor.execute(update_query, clash_data)

    db.commit()
    db.close()

    return "Member" if (clash_data["clan_tag"] == PRIMARY_CLAN_TAG) else "Visitor"


# player_data = {
#     player_tag: str,
#     player_name: str,
#     discord_name: str,
#     clan_role: str,
#     clan_name: str,
#     clan_tag: str,
#     vacation: bool,
#     strikes: int,
#     usage_history: int,
#     status: str
# }
def get_user_data(player_name: str) -> dict:
    db, cursor = connect_to_db()

    user_data = {}
    cursor.execute("SELECT * FROM users WHERE player_name = %s", (player_name))
    query_result = cursor.fetchone()

    if query_result == None:
        db.close()
        return None

    user_data["player_name"] = player_name
    user_data["player_tag"] = query_result["player_tag"]
    user_data["discord_name"] = query_result["discord_name"]
    user_data["clan_role"] = query_result["clan_role"]
    user_data["vacation"] = query_result["vacation"]
    user_data["strikes"] = query_result["strikes"]
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


# Add strike to user. Return new number of strikes.
def give_strike(player_tag: str) -> int:
    db, cursor = connect_to_db()

    strike_count = 0
    cursor.execute("SELECT * FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()

    # Add unregistered user if they aren't in the users table.
    if query_result == None:
        add_new_unregistered_user(player_tag)
        strike_count = 1

    cursor.execute("UPDATE users SET strikes = strikes + 1 WHERE player_tag = %s", (player_tag))

    if query_result != None:
        strike_count = query_result["strikes"] + 1

    db.commit()
    db.close()

    return strike_count

def get_strikes(player_name: str) -> int:
    db, cursor = connect_to_db()

    cursor.execute("SELECT strikes FROM users WHERE player_name = %s", (player_name))
    query_result = cursor.fetchone()

    if query_result == None:
        return None

    strikes = query_result["strikes"]
    db.close()
    return strikes

def reset_strikes():
    db, cursor = connect_to_db()

    cursor.execute("UPDATE users SET strikes = 0")
    db.commit()
    db.close()

# (previous_strike_count, new_strike_count)
def set_strikes(player_name: str, strike_count: int) -> tuple:
    db, cursor = connect_to_db()

    cursor.execute("SELECT strikes FROM users WHERE player_name = %s", (player_name))
    query_result = cursor.fetchone()

    if query_result == None:
        db.close()
        return None

    previous_strike_count = query_result["strikes"]

    cursor.execute("UPDATE users SET strikes = %s WHERE player_name = %s", (strike_count, player_name))
    cursor.execute("SELECT strikes FROM users WHERE player_name = %s", (player_name))
    query_result = cursor.fetchone()

    if (query_result == None):
        db.close()
        return None

    new_strike_count = query_result["strikes"]

    db.commit()
    db.close()

    return (previous_strike_count, new_strike_count)


# [(player_name, strikes),]
def get_strike_report() -> list:
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_name, strikes FROM users WHERE strikes > 0")
    query_result = cursor.fetchall()

    strike_list = []

    if query_result != None:
        strike_list = [ (user["player_name"], user["strikes"]) for user in query_result ]

    strike_list.sort(key = lambda x : (x[1], x[0].lower()))

    db.close()
    return strike_list


def save_race_completion_status(status: bool):
    db, cursor = connect_to_db()

    cursor.execute("UPDATE race_status SET completed_saturday = %s", (status))

    db.commit()
    db.close()


def race_completed_saturday() -> bool:
    db, cursor = connect_to_db()

    cursor.execute("SELECT completed_saturday FROM race_status")
    query_result = cursor.fetchone()

    if query_result == None:
        return None

    db.close()
    return query_result["completed_saturday"]


def get_player_tag(player_name: str) -> str:
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users WHERE player_name = %s", (player_name))
    query_result = cursor.fetchone()

    if (query_result == None):
        db.close()
        return None

    player_tag = query_result["player_tag"]

    db.close()
    return player_tag


# Remove user from DB along with any roles assigned to them.
def remove_user(player_name: str):
    db, cursor = connect_to_db()

    # Get user_id from player_name.
    cursor.execute("SELECT id FROM users WHERE player_name = %s", (player_name))
    query_result = cursor.fetchone()

    if (query_result == None):
        db.close()
        return

    user_id = query_result["id"]

    cursor.execute("DELETE FROM assigned_roles WHERE user_id = %s", (user_id))
    active_members = clash_utils.get_active_members_in_clan()
    player_tag = get_player_tag(player_name)

    if player_tag in active_members:
        cursor.execute("UPDATE users SET discord_name = %s, status = 'UNREGISTERED', usage_history = 0 WHERE id = %s",
                       (f"UNREGISTERED{player_tag}", user_id))
    else:
        cursor.execute("UPDATE users SET discord_name = %s, status = 'DEPARTED', usage_history = 0 WHERE id = %s",
                       (f"DEPARTED{player_tag}", user_id))

    db.commit()
    db.close()


# Drop all users and assigned roles.
def remove_all_users():
    db, cursor = connect_to_db()

    cursor.execute("DELETE FROM assigned_roles")
    cursor.execute("DELETE FROM match_history")
    cursor.execute("DELETE FROM users")

    db.commit()
    db.close()


# Set user to opposite of their current vacation status. Return new status.
def update_vacation_for_user(player_name: str, status=None) -> bool:
    db, cursor = connect_to_db()

    if (type(status) == bool):
        update_vacation_query = "UPDATE users SET vacation = %s WHERE player_name = %s"
        cursor.execute(update_vacation_query, (status, player_name))
    else:
        update_vacation_query = "UPDATE users SET vacation = NOT vacation WHERE player_name = %s"
        cursor.execute(update_vacation_query, (player_name))

    cursor.execute("SELECT * FROM users WHERE player_name = %s", (player_name))
    query_result = cursor.fetchone()

    if (query_result == None):
        return False

    db.commit()
    db.close()

    return query_result["vacation"]


# Return a list of player_names currently on vacation.
def get_vacation_list() -> list:
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_name FROM users WHERE vacation = TRUE")
    query_result = cursor.fetchall()

    if query_result == None:
        db.close()
        return []

    vacation_list = [ user["player_name"] for user in query_result ]

    db.close()

    return vacation_list


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

# Return a list of discord role_names corresponding to a user.
def get_roles(player_name: str) -> list:
    db, cursor = connect_to_db()

    # Get user_id.
    cursor.execute("SELECT id FROM users WHERE player_name = %s", (player_name))
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


# Get current normal roles possesed by user.
def commit_roles(player_name: str, roles: list):
    db, cursor = connect_to_db()

    # Get user_id from player_name.
    cursor.execute("SELECT id FROM users WHERE player_name = %s", (player_name))
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


# True = US, False = EU
def update_time_zone(player_name: str, US_time: bool):
    db, cursor = connect_to_db()

    cursor.execute("UPDATE users SET US_time = %s WHERE player_name = %s", (US_time, player_name))

    db.commit()
    db.close()


def get_members_in_time_zone(US_time: bool) -> list:
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_name FROM users WHERE US_time = %s", (US_time))
    query_result = cursor.fetchall()

    if query_result == None:
        db.close()
        return None

    member_list = [ user["player_name"] for user in query_result ]

    db.close()
    return member_list


# (player_tag, decks_used_today)
def record_deck_usage_today(deck_usage_list: list):
    db, cursor = connect_to_db()

    for player_tag, decks_used_today in deck_usage_list:
        cursor.execute("SELECT player_name, usage_history, status, discord_name FROM users WHERE player_tag = %s", (player_tag))
        query_result = cursor.fetchone()

        if query_result == None:
            add_new_unregistered_user(player_tag)
            query_result = {"usage_history": 0}
        elif query_result["status"] == 'INACTIVE':
            clash_data = clash_utils.get_clash_user_data(player_tag, query_result["discord_name"])
            update_user(clash_data, query_result["player_name"])

        updated_history = ((query_result["usage_history"] & SIX_DAY_MASK) << 3) | (decks_used_today & ONE_DAY_MASK)
        cursor.execute("UPDATE users SET usage_history = %s WHERE player_tag = %s", (updated_history, player_tag))

    db.commit()
    db.close()


# [(player_name, player_tag, deck_usage)]
def get_all_user_deck_usage_history() -> list:
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_name, player_tag, usage_history FROM users")
    query_result = cursor.fetchall()

    usage_list = []

    if query_result != None:
        usage_list = [ (user["player_name"], user["player_tag"], user["usage_history"]) for user in query_result ]

    usage_list.sort(key = lambda x : x[0].lower())
    db.close()
    return usage_list


def clean_up_db():
    """
    Checks that every user in the database has an appropriate status.
    ACTIVE users that are no longer active members of the clan are moved to INACTIVE.
    UNREGISTERED users that are no longer active members of the clan are moved to DEPARTED.
    INACTIVE users that are now part of the clan are moved to ACTIVE.
    DEPARTED users that are now part of the clan are moved to UNREGISTERED.
    """
    db, cursor = connect_to_db()

    active_members = clash_utils.get_active_members_in_clan()
    cursor.execute("SELECT player_name, player_tag, discord_name, status FROM users")
    query_result = cursor.fetchall()

    for user in query_result:
        player_name = user["player_name"]
        player_tag = user["player_tag"]
        discord_name = user["discord_name"]
        status = user["status"]

        if player_tag not in active_members:
            if status == 'UNREGISTERED':
                clash_data = clash_utils.get_clash_user_data(player_tag, discord_name)
                update_user(clash_data, player_name)
                cursor.execute("UPDATE users SET discord_name = %s, status = 'DEPARTED', usage_history = 0 WHERE player_tag = %s",
                               (f"DEPARTED{player_tag}", player_tag))
            elif status == 'ACTIVE':
                clash_data = clash_utils.get_clash_user_data(player_tag, discord_name)
                update_user(clash_data, player_name)
                cursor.execute("UPDATE users SET usage_history = 0 WHERE player_tag = %s",
                               (player_tag))
        else:
            if status == 'INACTIVE':
                clash_data = clash_utils.get_clash_user_data(player_tag, discord_name)
                update_user(clash_data, player_name)
                cursor.execute("UPDATE users SET usage_history = 0 WHERE player_tag = %s",
                               (player_tag))
            elif status == 'DEPARTED':
                clash_data = clash_utils.get_clash_user_data(player_tag, discord_name)
                update_user(clash_data, player_name)
                cursor.execute("UPDATE users SET discord_name = %s, status = 'UNREGISTERED', usage_history = 0 WHERE player_tag = %s",
                               (f"UNREGISTERED{player_tag}", player_tag))

    db.commit()
    db.close()


def get_and_update_match_history_fame_and_battle_time(player_tag: str, fame: int):
    """
    Get a user's fame and time when their battlelog was last checked. Then store their updated fame and current time.

    Args:
        player_tag(str): Player to get/set fame for.
        fame(int): Current fame value.

    Returns:
        tuple(fame(int), last_battle_time(datetime.datetime)): Previous fame value and battle time.
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT last_battle_time, fame FROM match_history WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)", (player_tag))
    query_result = cursor.fetchone()

    if query_result == None:
        add_new_unregistered_user(player_tag)
        cursor.execute("SELECT last_battle_time, fame FROM match_history WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)", (player_tag))
        query_result = cursor.fetchone()

    fame_and_time = (query_result["fame"], bot_utils.battletime_to_datetime(query_result["last_battle_time"]))

    cursor.execute("UPDATE match_history SET last_battle_time = %s, fame = %s WHERE user_id IN (SELECT id FROM users WHERE player_tag = %s)",
                   (bot_utils.datetime_to_battletime(datetime.datetime.now(datetime.timezone.utc)), fame, player_tag))

    db.commit()
    db.close()
    return fame_and_time


def update_match_history(user_performance_list: list):
    """
    Add each player's game stats to the match_history table.

    Args:
        user_performance_list(list[dict]): List of user dictionaries with their river race results.
    """
    db, cursor = connect_to_db()

    for user in user_performance_list:
        if not user:
            continue

        cursor.execute("UPDATE match_history SET\
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


def prepare_match_history(last_battle_time: datetime.datetime):
    """
    Needs to run every Thursday when river race starts. Resets decks_used, fame, and boat_attacks fields. Also sets last_battle_time
    to current time.

    Args:
        last_battle_time(datetime.datetime): When match performance is next calculated, do not look at games before this time.
    """
    db, cursor = connect_to_db()

    last_battle_time = bot_utils.datetime_to_battletime(last_battle_time)
    cursor.execute("UPDATE match_history SET last_battle_time = %s, fame = 0", (last_battle_time))

    db.commit()
    db.close()

def get_match_performance_dict(player_name: str) -> dict:
    """
    Get a dict containing a specified user's match performance.

    Args:
        player_name(str): Player name to get stats for.

    Returns:
        dict {str: dict{str: int/float}}: dict containing specified player's stats.
            {
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
    """
    db, cursor = connect_to_db()

    cursor.execute("SELECT battle_wins, battle_losses, special_battle_wins, special_battle_losses, boat_attack_wins, boat_attack_losses, duel_match_wins, duel_match_losses, duel_series_wins, duel_series_losses\
                    FROM match_history WHERE user_id IN (SELECT id FROM users WHERE player_name = %s)", (player_name))

    match_performance = cursor.fetchone()
    match_performance_dict = {}

    # Regular battles
    regular_wins = match_performance["battle_wins"]
    regular_losses = match_performance["battle_losses"]
    total_regular_battles = regular_wins + regular_losses
    regular_battle_win_rate = "0.00%" if total_regular_battles == 0 else "{:.2%}".format(regular_wins / total_regular_battles)
    match_performance_dict["regular"] = {"wins": regular_wins,
                                         "losses": regular_losses,
                                         "total": total_regular_battles,
                                         "win_rate": regular_battle_win_rate}

    # Special battles
    special_wins = match_performance["special_battle_wins"]
    special_losses = match_performance["special_battle_losses"]
    total_special_battles = special_wins + special_losses
    special_battle_win_rate = "0.00%" if total_special_battles == 0 else "{:.2%}".format(special_wins / total_special_battles)
    match_performance_dict["special"] = {"wins": special_wins,
                                         "losses": special_losses,
                                         "total": total_special_battles,
                                         "win_rate": special_battle_win_rate}

    # Duel matches
    duel_match_wins = match_performance["duel_match_wins"]
    duel_match_losses = match_performance["duel_match_losses"]
    total_duel_matches = duel_match_wins + duel_match_losses
    duel_match_win_rate = "0.00%" if total_duel_matches == 0 else "{:.2%}".format(duel_match_wins / total_duel_matches)
    match_performance_dict["duel_matches"] = {"wins": duel_match_wins,
                                              "losses": duel_match_losses,
                                              "total": total_duel_matches,
                                              "win_rate": duel_match_win_rate}

    # Duel series
    duel_series_wins = match_performance["duel_series_wins"]
    duel_series_losses = match_performance["duel_series_losses"]
    total_duel_series = duel_series_wins + duel_series_losses
    duel_series_win_rate = "0.00%" if total_duel_series == 0 else "{:.2%}".format(duel_series_wins / total_duel_series)
    match_performance_dict["duel_series"] = {"wins": duel_series_wins,
                                             "losses": duel_series_losses,
                                             "total": total_duel_series,
                                             "win_rate": duel_series_win_rate}

    # Boat attacks
    boat_attack_wins = match_performance["boat_attack_wins"]
    boat_attack_losses = match_performance["boat_attack_losses"]
    total_boat_attacks = boat_attack_wins + boat_attack_losses
    boat_attack_win_rate = "0.00%" if total_boat_attacks == 0 else "{:.2%}".format(boat_attack_wins / total_boat_attacks)
    match_performance_dict["boat_attacks"] = {"wins": boat_attack_wins,
                                              "losses": boat_attack_losses,
                                              "total": total_boat_attacks,
                                              "win_rate": boat_attack_win_rate}

    # Combined
    total_pvp_wins = regular_wins + special_wins + duel_match_wins
    total_pvp_losses = regular_losses + special_losses + duel_match_losses
    total_pvp_matches = total_pvp_wins + total_pvp_losses
    overall_win_rate = "0.00%" if total_pvp_matches == 0 else "{:.2%}".format(total_pvp_wins / total_pvp_matches)
    match_performance_dict["combined_pvp"] = {"wins": total_pvp_wins,
                                              "losses": total_pvp_losses,
                                              "total": total_pvp_matches,
                                              "win_rate": overall_win_rate}

    db.close()
    return match_performance_dict


def get_file_path() -> str:
    path = 'export_files'
    files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    files.sort(key = lambda x : os.path.getmtime(x))

    if len(files) >= 5:
        os.remove(files[0])

    file_name = "members_" + str(datetime.datetime.now().date()) + ".csv"
    new_path = os.path.join(path, file_name)

    return new_path


def output_to_csv(primary_clan_only: bool, include_deck_usage_history: bool, include_match_performance_history: bool) -> str:
    """
    """
    # Before doing anything, update the database.
    clean_up_db()

    db, cursor = connect_to_db()

    # Get clan info.
    clans = None
    primary_clan_id = None

    if primary_clan_only:
        cursor.execute("SELECT * FROM clans WHERE clan_tag = %s", (PRIMARY_CLAN_TAG))
        clans = cursor.fetchall()
        primary_clan_id = clans[0]["id"]
    else:
        cursor.execute("SELECT * FROM clans")
        clans = cursor.fetchall()

    if clans == None:
        return None

    clans_dict = {}

    for clan in clans:
        clans_dict[clan["id"]] = {"Clan Tag": clan["clan_tag"], "Clan Name": clan["clan_name"]}

    # Get users.
    if primary_clan_only:
        cursor.execute("SELECT * FROM users WHERE clan_id = %s", (primary_clan_id))
    else:
        cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()

    if users == None:
        return None

    # Get path to new file and open it.
    file_path = get_file_path()

    with open(file_path, 'w', newline='') as csv_file:
        fields_list = list(users[0].keys())

        # Remove keys that aren't relevant outside the database.
        fields_list.remove("id")
        fields_list.remove("clan_id")
        fields_list.remove("usage_history")

        # Swap order of player_name and player_tag.
        fields_list[0], fields_list[1] = fields_list[1], fields_list[0]

        # Capitalize field names and replace underscores with spaces
        fields_list = [' '.join(field.split('_')).title() for field in fields_list]

        # Add extra fields that aren't columns in users table.
        fields_list.append("Clan Tag")
        fields_list.append("Clan Name")
        fields_list.append("RoyaleAPI")

        # Add deck usage statistic fields.
        deck_usage_today = {}
        now = datetime.datetime.now(datetime.timezone.utc)
        now_date = now.date()
        now_field_name = now_date.strftime("%a") + ", " +  now_date.strftime("%b") + " " + str(now_date.day).zfill(2)

        if include_deck_usage_history:
            day_fields = bot_utils.break_down_usage_history(users[0]["usage_history"], now)
            for day in day_fields[::-1]:
                fields_list.append(day[1])

            fields_list.append(now_field_name)
            deck_usage_today = clash_utils.get_deck_usage_today_dict()

        # Add match performance fields.
        match_performance_dict = {}

        if include_match_performance_history:
            match_performance_dict = {user["player_name"]: get_match_performance_dict(user["player_name"]) for user in users}

            fields_list.extend(["Regular PvP Wins", "Regular PvP Losses", "Regular PvP Win Rate",
                                "Special PvP Wins", "Special PvP Losses", "Special PvP Win Rate",
                                "Duel Match Wins", "Duel Match Losses", "Duel Match Win Rate",
                                "Duel Series Wins", "Duel Series Losses", "Duel Series Win Rate",
                                "Combined PvP Wins", "Combined PvP Losses", "Combined PvP Win Rate",
                                "Boat Attack Wins", "Boat Attack Losses", "Boat Attack Win Rate"])

        # Prepare CSV file.
        writer = csv.DictWriter(csv_file, fieldnames=fields_list)
        headers = dict((n,n) for n in fields_list)
        writer.writerow(headers)

        # Iterate through users to log info in CSV.
        for user in users:
            user.pop("id")
            clan_id = user.pop("clan_id")
            usage_history = user.pop("usage_history")

            keys_list = list(user.keys())
            for key in keys_list:
                user[' '.join(key.split('_')).title()] = user.pop(key)

            user["Clan Tag"] = clans_dict[clan_id]["Clan Tag"]
            user["Clan Name"] = clans_dict[clan_id]["Clan Name"]
            user["RoyaleAPI"] = ("https://royaleapi.com/player/" + user["Player Tag"][1:])

            if include_deck_usage_history:
                usage_history_list = bot_utils.break_down_usage_history(usage_history, now)
                for usage, day in usage_history_list:
                    user[day] = usage

                usage_today = deck_usage_today.get(user["Player Name"])

                if usage_today == None:
                    usage_today = clash_utils.get_user_decks_used_today(user["Player Tag"])

                user[now_field_name] = usage_today

            if include_match_performance_history:
                user["Regular PvP Wins"] = match_performance_dict[user["Player Name"]]["regular"]["wins"]
                user["Regular PvP Losses"] = match_performance_dict[user["Player Name"]]["regular"]["losses"]
                user["Regular PvP Win Rate"] = float(match_performance_dict[user["Player Name"]]["regular"]["win_rate"][:-1]) / 100
                user["Special PvP Wins"] = match_performance_dict[user["Player Name"]]["special"]["wins"]
                user["Special PvP Losses"] = match_performance_dict[user["Player Name"]]["special"]["losses"]
                user["Special PvP Win Rate"] = float(match_performance_dict[user["Player Name"]]["special"]["win_rate"][:-1]) / 100
                user["Duel Match Wins"] = match_performance_dict[user["Player Name"]]["duel_matches"]["wins"]
                user["Duel Match Losses"] = match_performance_dict[user["Player Name"]]["duel_matches"]["losses"]
                user["Duel Match Win Rate"] = float(match_performance_dict[user["Player Name"]]["duel_matches"]["win_rate"][:-1]) / 100
                user["Duel Series Wins"] = match_performance_dict[user["Player Name"]]["duel_series"]["wins"]
                user["Duel Series Losses"] = match_performance_dict[user["Player Name"]]["duel_series"]["losses"]
                user["Duel Series Win Rate"] = float(match_performance_dict[user["Player Name"]]["duel_series"]["win_rate"][:-1]) / 100
                user["Combined PvP Wins"] = match_performance_dict[user["Player Name"]]["combined_pvp"]["wins"]
                user["Combined PvP Losses"] = match_performance_dict[user["Player Name"]]["combined_pvp"]["losses"]
                user["Combined PvP Win Rate"] = float(match_performance_dict[user["Player Name"]]["combined_pvp"]["win_rate"][:-1]) / 100
                user["Boat Attack Wins"] = match_performance_dict[user["Player Name"]]["boat_attacks"]["wins"]
                user["Boat Attack Losses"] = match_performance_dict[user["Player Name"]]["boat_attacks"]["losses"]
                user["Boat Attack Win Rate"] = float(match_performance_dict[user["Player Name"]]["boat_attacks"]["win_rate"][:-1]) / 100

            writer.writerow(user)

    db.close()
    return file_path