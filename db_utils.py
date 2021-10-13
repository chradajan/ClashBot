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
                            status = %(status)s,\
                            WHERE player_tag = %(player_tag)s"
            cursor.execute(update_query, clash_data)
    else:
        insert_user_query = "INSERT INTO users VALUES (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, %(clan_role)s, TRUE, FALSE, 0, 0, %(status)s, %(clan_id)s)"
        cursor.execute(insert_user_query, clash_data)

    # Get id of newly inserted user.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", clash_data)
    query_result = cursor.fetchone()
    user_id = query_result["id"]

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

    #Insert them
    insert_user_query = "INSERT INTO users VALUES (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, %(clan_role)s, TRUE, FALSE, 0, 0, %(status)s, %(clan_id)s)"
    cursor.execute(insert_user_query, clash_data)

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
    cursor.execute("UPDATE users SET status = 'DEPARTED', usage_history = 0 WHERE id = %s", (user_id))
    db.commit()
    db.close()


# Drop all users and assigned roles.
def remove_all_users():
    db, cursor = connect_to_db()

    cursor.execute("DELETE FROM assigned_roles")
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


def add_deck_usage_today(player_tag: str, decks_used_today: int):
    db, cursor = connect_to_db()

    cursor.execute("SELECT usage_history FROM users WHERE player_tag = %s", (player_tag))
    query_result = cursor.fetchone()

    if query_result == None:
        add_new_unregistered_user(player_tag)

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
    return usage_list


def clean_unregistered_users():
    db, cursor = connect_to_db()

    active_members = list(clash_utils.get_active_members_in_clan().keys())

    cursor.execute("SELECT player_tag FROM users WHERE status = 'UNREGISTERED'")
    query_result = cursor.fetchall()

    for user in query_result:
        if user["player_tag"] not in active_members:
            cursor.execute("UPDATE users SET status = 'DEPARTED', usage_history = 0 WHERE player_tag = %s", (user["player_tag"]))

    db.commit()
    db.close()


def get_file_path() ->str:
    path = 'export_files'
    files = [os.path.join(path, f) for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    files.sort(key = lambda x : os.path.getmtime(x))

    if len(files) >= 5:
        os.remove(files[0])

    file_name = "members_" + str(datetime.datetime.now().date()) + ".csv"
    new_path = os.path.join(path, file_name)

    return new_path


def output_to_csv(primary_clan_only: bool, include_unregistered_users: bool, include_deck_usage_history: bool) -> str:
    db, cursor = connect_to_db()

    clans = None
    false_logic_id = None

    if primary_clan_only:
        cursor.execute("SELECT * FROM clans WHERE clan_tag = %s", (PRIMARY_CLAN_TAG))
        clans = cursor.fetchall()
        false_logic_id = clans[0]["id"]
    else:
        cursor.execute("SELECT * FROM clans")
        clans = cursor.fetchall()

    if primary_clan_only:
        cursor.execute("SELECT * FROM users WHERE clan_id = %s", (false_logic_id))
    else:
        cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()

    if users == None:
        return None

    unregistered_users = {}

    if include_unregistered_users:
        cursor.execute("SELECT * FROM unregistered_users")
        unregistered_users = cursor.fetchall()

    clans_dict = {}

    for clan in clans:
        clans_dict[clan["id"]] = {"Clan Tag": clan["clan_tag"], "Clan Name": clan["clan_name"]}

    file_path = get_file_path()

    with open(file_path, 'w', newline='') as csv_file:
        fields_list = list(users[0].keys())
        fields_list.remove("id")
        fields_list.remove("clan_id")
        fields_list.remove("usage_history")
        fields_list[0], fields_list[1] = fields_list[1], fields_list[0]
        field_names = []

        for field in fields_list:
            field_names.append(' '.join(field.split('_')).title())

        field_names.append("Clan Tag")
        field_names.append("Clan Name")
        field_names.append("RoyaleAPI")

        time_to_use = datetime.datetime.now(datetime.timezone.utc)
        deck_usage_today = {}
        today_date = datetime.datetime.now(datetime.timezone.utc).date()
        today_date_header = today_date.strftime("%a") + ", " +  today_date.strftime("%b") + " " + str(today_date.day).zfill(2)

        if include_deck_usage_history:
            day_fields = bot_utils.break_down_usage_history(users[0]["usage_history"], time_to_use)
            for day in day_fields[::-1]:
                field_names.append(day[1])

            field_names.append(today_date_header)
            deck_usage_today = clash_utils.get_deck_usage_today_dict()

        writer = csv.DictWriter(csv_file, fieldnames=field_names)
        headers = dict( (n,n) for n in field_names)
        writer.writerow(headers)

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
                usage_history_list = bot_utils.break_down_usage_history(usage_history, time_to_use)
                for usage, day in usage_history_list:
                    user[day] = usage

                usage_today = deck_usage_today.get(user["Player Name"])

                if usage_today == None:
                    usage_today = clash_utils.get_user_decks_used_today(user["Player Tag"])

                if usage_today != None:
                    user[today_date_header] = usage_today

            writer.writerow(user)

        if include_unregistered_users:
            for user in unregistered_users:
                user.pop("id")
                user["Player Name"] = user.pop("player_name")
                user["Strikes"] = user.pop("strikes")
                usage_history = user.pop("usage_history")

                if include_deck_usage_history:
                    usage_history_list = bot_utils.break_down_usage_history(usage_history, time_to_use)
                    for usage, day in usage_history_list:
                        user[day] = usage

                    usage_today = deck_usage_today.get(user["Player Name"])

                    if usage_today != None:
                        user[today_date_header] = usage_today

                writer.writerow(user)

    return file_path