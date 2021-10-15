from config import PRIMARY_CLAN_TAG
from credentials import IP, USERNAME, PASSWORD, DB_NAME
import bot_utils
import clash_utils
import datetime
import db_utils
import pymysql

def connect_to_db():
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME, charset='utf8mb4')
    cursor = db.cursor(pymysql.cursors.DictCursor)
    return (db, cursor)

def perform_transition():
    move_unregistered_users()
    update_statuses()
    create_match_history()

def move_unregistered_users():
    db, cursor = connect_to_db()
    active_members = clash_utils.get_active_members_in_clan()

    cursor.execute("SELECT player_tag FROM users")
    query_result = cursor.fetchall()

    for member in query_result:
        if member["player_tag"] in active_members:
            active_members.pop(member["player_tag"])

    for unregistered_user in active_members:
        clash_data = clash_utils.get_clash_user_data(unregistered_user, "UNREGISTERED" + unregistered_user)
        db_utils.add_new_user(clash_data)
        cursor.execute("SELECT strikes, usage_history FROM unregistered_users WHERE player_name = %s", (active_members[unregistered_user]))
        query_result = cursor.fetchone()
        strikes = 0
        usage_history = 0

        if query_result != None:
            strikes = query_result["strikes"]
            usage_history = query_result["usage_history"]

        cursor.execute("UPDATE users SET strikes = %s, usage_history = %s, status = 'UNREGISTERED' WHERE player_tag = %s", (strikes, usage_history, unregistered_user))

    db.commit()
    db.close()

def update_statuses():
    db, cursor = connect_to_db()

    cursor.execute("UPDATE users SET status = 'INACTIVE' WHERE clan_id != 1")
    cursor.execute("UPDATE users SET status = 'ACTIVE' WHERE clan_id = 1")

    db.commit()
    db.close()

def create_match_history():
    db, cursor = connect_to_db()

    cursor.execute("SELECT id FROM users WHERE status != 'UNREGISTERED'")
    query_result = cursor.fetchall()

    now = bot_utils.datetime_to_battletime(datetime.datetime.now(datetime.timezone.utc))

    for user in query_result:
        cursor.execute("INSERT INTO match_history VALUES (%s, %s, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)", (user["id"], now))

    db.commit()
    db.close()

if __name__ =='__main__':
    perform_transition()