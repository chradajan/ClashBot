from credentials import IP, USERNAME, PASSWORD, DB_NAME
from clash_utils import GetClashUserData
import csv
import pymysql


# clashData = {
#     player_tag: str,
#     player_name: str,
#     discord_name: str,
#     clan_role: str,
#     clan_name: str,
#     clan_tag: str
# }
def AddNewUser(clashData: dict) -> bool:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    # Get clan_id if clan exists. It clan doesn't exist, add to clans table.
    cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clashData)
    queryResult = cursor.fetchone()

    if (queryResult == None):
        insertClanQuery = "INSERT INTO clans VALUES (DEFAULT, %(clan_tag)s, %(clan_name)s)"
        cursor.execute(insertClanQuery, clashData)
        cursor.execute("SELECT id FROM clans WHERE clan_tag = %(clan_tag)s", clashData)
        queryResult = cursor.fetchone()

    # Add clan_id to clashData for use in user insertion.
    clashData["clan_id"] = queryResult["id"]

    # Check if player already exists in users table. If they do, return. Otherwise, add them.
    cursor.execute("SELECT * FROM users WHERE player_tag = %(player_tag)s", clashData)

    if (cursor.fetchone() != None):
        db.rollback()
        db.close()
        return False

    insertUserQuery = "INSERT INTO users VALUES (DEFAULT, %(player_tag)s, %(player_name)s, %(discord_name)s, %(clan_role)s, FALSE, 0, %(clan_id)s)"
    cursor.execute(insertUserQuery, clashData)

    # Get id of newly inserted user.
    cursor.execute("SELECT id FROM users WHERE player_tag = %(player_tag)s", clashData)
    queryResult = cursor.fetchone()
    user_id = queryResult["id"]

    # Check if new user is member or visitor. Get id of relevant discord_role.
    roleString = "Member" if (clashData["clan_name"] == "False Logic") else "Visistor"
    cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (roleString))
    queryResult = cursor.fetchone()
    discord_role_id = queryResult["id"]

    # Add new role into assigned_roles table.
    insertAssignedRolesQuery = "INSERT INTO assigned_roles VALUES (%s, %s)"
    cursor.execute(insertAssignedRolesQuery, (user_id, discord_role_id))

    db.commit()
    db.close()
    return True


# Update existing user.
def UpdateUser(clashData: dict):
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    updateQuery = "UPDATE users SET player_name = %(player_name)s, discord_name = %(discord_name)s, clan_role = %(clan_role)s WHERE player_tag = %(player_tag)s"
    cursor.execute(updateQuery, clashData)

    db.commit()
    db.close()


# Add strike to user.
def AddStrike(player_name: str) -> int:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("UPDATE users SET strikes = strikes + 1 WHERE player_name = %s", (player_name))
    cursor.execute("SELECT * FROM users WHERE player_name = %s", (player_name))
    queryResult = cursor.fetchone()

    if (queryResult == None):
        return 0

    db.commit()
    db.close()

    return queryResult["strikes"]


def SetStrikes(player_name: str, strike_count: int) -> int:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("UPDATE users SET strikes = %s WHERE player_name = %s", (strike_count, player_name))
    cursor.execute("SELECT * FROM users WHERE player_name = %s", (player_name))
    queryResult = cursor.fetchone()

    if (queryResult == None):
        return 0

    db.commit()
    db.close()

    return queryResult["strikes"]


def GetPlayerTag(player_name: str) -> str:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT player_tag FROM users WHERE player_name = %s", (player_name))
    queryResult = cursor.fetchone()

    if (queryResult == None):
        db.close()
        return None

    player_tag = queryResult["player_tag"]

    db.close()
    return player_tag


# Remove user from DB along with any roles assigned to them.
def RemoveUser(player_name: str):
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    # Get user_id from player_name.
    cursor.execute("SELECT id FROM users WHERE player_name = %s", (player_name))
    queryResult = cursor.fetchone()

    if (queryResult == None):
        db.close()
        return
    
    user_id = queryResult["id"]

    cursor.execute("DELETE FROM assigned_roles WHERE user_id = %s", (user_id))
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id))
    db.commit()
    db.close()


# Drop all users and assigned roles.
def RemoveAllUsers():
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("DELETE FROM assigned_roles")
    cursor.execute("DELETE FROM users")

    db.commit()
    db.close()


# Set user to opposite of their current vacation status. Returns new status.
def UpdateVacationForUser(player_name: str, status=None) -> bool:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    if (type(status) == bool):
        updateVacationQuery = "UPDATE users SET vacation = %s WHERE player_name = %s"
        cursor.execute(updateVacationQuery, (status, player_name))
    else:
        updateVacationQuery = "UPDATE users SET vacation = NOT vacation WHERE player_name = %s"
        cursor.execute(updateVacationQuery, (player_name))

    cursor.execute("SELECT * FROM users WHERE player_name = %s", (player_name))
    queryResult = cursor.fetchone()

    if (queryResult == None):
        return False

    db.commit()
    db.close()

    return queryResult["vacation"]


# Return a list of player_names currently on vacation.
def GetVacationStatus() -> list:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT player_name FROM users WHERE vacation = TRUE")
    vacationDict = cursor.fetchall()

    vacationList = [ user["player_name"] for user in vacationDict ]

    db.close()

    return vacationList


# Set vacation to false for all users.
def ClearAllVacation():
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("UPDATE users SET vacation = FALSE")

    db.commit()
    db.close()


# Set whether to send deck usage reminders.
def SetReminderStatus(status: bool):
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("UPDATE automation_status SET send_reminders = %s", (status))

    db.commit()
    db.close()


# Return current reminder status.
def GetReminderStatus() -> bool:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT * FROM automation_status")
    queryResult = cursor.fetchone()

    if queryResult == None:
        db.close()
        return False

    status = queryResult["send_reminders"]
    db.close()
    return status


# Set whether to send strikes automatically.
def SetStrikeStatus(status: bool):
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("UPDATE automation_status SET send_strikes = %s", (status))

    db.commit()
    db.close()


# Return current strike status.
def GetStrikeStatus() -> bool:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT * FROM automation_status")
    queryResult = cursor.fetchone()

    status = queryResult["send_strikes"]
    db.close()
    return status

# Return a list of discord role_names corresponding to a user.
def GetRoles(player_name: str) -> list:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    # Get user_id.
    cursor.execute("SELECT id FROM users WHERE player_name = %s", (player_name))
    queryResult = cursor.fetchone()

    if (queryResult == None):
        db.close()
        return []

    user_id = queryResult["id"]

    # Get list of discord_role_ids corresponding to user_id.
    cursor.execute("SELECT discord_role_id FROM assigned_roles WHERE user_id = %s", (user_id))
    queryResult = cursor.fetchall()

    if (queryResult == None):
        db.close()
        return []

    discord_role_ids = []

    for entry in queryResult:
        discord_role_ids.append(entry["discord_role_id"])

    # Get list of role_names.
    roles = []

    for discord_role_id in discord_role_ids:
        cursor.execute("SELECT role_name FROM discord_roles WHERE id = %s", (discord_role_id))
        queryResult = cursor.fetchone()

        if (queryResult == None):
            continue

        roles.append(queryResult["role_name"])

    return roles


# Get current normal roles possesed by user.
def CommitRoles(player_name: str, roles: list):
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    # Get user_id from player_name.
    cursor.execute("SELECT id FROM users WHERE player_name = %s", (player_name))
    queryResult = cursor.fetchone()

    if (queryResult == None):
        db.close()
        return
    
    user_id = queryResult["id"]

    cursor.execute("DELETE FROM assigned_roles WHERE user_id = %s", (user_id))

    for role in roles:
        cursor.execute("SELECT id FROM discord_roles WHERE role_name = %s", (role))
        queryResult = cursor.fetchone()

        if (queryResult == None):
            continue

        discord_role_id = queryResult["id"]

        cursor.execute("INSERT INTO assigned_roles VALUES (%s, %s)", (user_id, discord_role_id))

    db.commit()
    db.close()


def OutputToCSV(file_path: str, false_logic_only: bool) -> bool:
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME)
    cursor = db.cursor(pymysql.cursors.DictCursor)

    clans = None
    falseLogicId = None

    if false_logic_only:
        cursor.execute("SELECT * FROM clans WHERE clan_name = %s", ("False Logic"))
        clans = cursor.fetchall()
        falseLogicId = clans[0]["id"]
    else:
        cursor.execute("SELECT * FROM clans")
        clans = cursor.fetchall()

    if false_logic_only:
        cursor.execute("SELECT * FROM users WHERE clan_id = %s", (falseLogicId))
    else:
        cursor.execute("SELECT * FROM users")

    users = cursor.fetchall()

    if users == None:
        return False

    clansDict = {}
    for clan in clans:
        clansDict[clan["id"]] = {"Clan Tag": clan["clan_tag"], "Clan Name": clan["clan_name"]}

    with open(file_path, 'w', newline='') as csvfile:
        fieldsList = list(users[0].keys())
        fieldsList.remove("id")
        fieldsList.remove("clan_id")
        fieldNames = []

        for field in fieldsList:
            fieldNames.append(' '.join(field.split('_')).title())

        fieldNames.append("Clan Tag")
        fieldNames.append("Clan Name")
        fieldNames.append("RoyaleAPI")

        writer = csv.DictWriter(csvfile, fieldnames=fieldNames)
        headers = dict( (n,n) for n in fieldNames)
        writer.writerow(headers)

        for user in users:
            user.pop("id")
            clanId = user.pop("clan_id")

            keysList = list(user.keys())
            for key in keysList:
                user[' '.join(key.split('_')).title()] = user.pop(key)
            
            user["Clan Tag"] = clansDict[clanId]["Clan Tag"]
            user["Clan Name"] = clansDict[clanId]["Clan Name"]
            user["RoyaleAPI"] = ("https://royaleapi.com/player/" + user["Player Tag"][1:])

            writer.writerow(user)

    return True