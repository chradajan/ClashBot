from config import PRIMARY_CLAN_TAG
from credentials import IP, USERNAME, PASSWORD, DB_NAME
import bot_utils
import clash_utils
import datetime
import db_utils
import pymysql


def perform_transition():
    update_match_history_table()
    drop_unique_indexes()


def update_match_history_table():
    db, cursor = db_utils.connect_to_db()

    cursor.execute("ALTER TABLE match_history DROP COLUMN decks_used,\
                                              DROP COLUMN boat_attacks")

    db.commit()
    db.close()


def drop_unique_indexes():
    db, cursor = db_utils.connect_to_db()

    cursor.execute("ALTER TABLE users DROP INDEX clash_name_UNIQUE")
    cursor.execute("ALTER TABLE clans DROP INDEX clan_name")

    db.commit()
    db.close()


if __name__ =='__main__':
    perform_transition()