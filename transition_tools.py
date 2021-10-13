from config import PRIMARY_CLAN_TAG
from credentials import IP, USERNAME, PASSWORD, DB_NAME
import bot_utils
import clash_utils
import db_utils
import pymysql

def connect_to_db():
    db = pymysql.connect(host=IP, user=USERNAME, password=PASSWORD, database=DB_NAME, charset='utf8mb4')
    cursor = db.cursor(pymysql.cursors.DictCursor)
    return (db, cursor)

def perform_transition():
    move_unregistered_users()
    update_statuses()

def move_unregistered_users():
    unregistered_users_dict = clash_utils.get_active_members_in_clan()
    db, cursor = connect_to_db()

    cursor.execute("SELECT player_tag FROM users")
    query_result = cursor.fetchall()

    for member in query_result:
        if member["player_tag"] in unregistered_users_dict.keys():
            unregistered_users_dict.pop(member["player_tag"])

    for unregistered_user_tag in unregistered_users_dict:
        clash_data = clash_utils.get_clash_user_data(unregistered_user_tag, "UNKNOWN" + unregistered_user_tag)
        db_utils.add_new_user(clash_data)
        cursor.execute("UPDATE users SET status = 'UNREGISTERED' WHERE player_tag = %s", (unregistered_user_tag))

    db.commit()
    db.close()

def update_statuses():
    db, cursor = connect_to_db()

    cursor.execute("UPDATE users SET status = 'INACTIVE' WHERE status = 'ACTIVE' AND clan_id != 1")

    db.commit()
    db.close()
