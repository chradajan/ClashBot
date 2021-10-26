from config import GUILD_NAME
from credentials import BOT_TOKEN
from discord.ext import commands
import bot_utils
import clash_utils
import datetime
import db_utils
import discord
import pymysql


def update_tables():
    db, cursor = db_utils.connect_to_db()

    cursor.execute("ALTER TABLE match_history DROP COLUMN decks_used,\
                                              DROP COLUMN boat_attacks")

    cursor.execute("ALTER TABLE users DROP INDEX clash_name_UNIQUE")
    cursor.execute("ALTER TABLE clans DROP INDEX clan_name")

    cursor.execute("ALTER TABLE users ADD COLUMN discord_id BIGINT UNSIGNED UNIQUE AFTER discord_name")

    db.commit()
    db.close()


def clear_match_history():
    db, cursor = db_utils.connect_to_db()

    cursor.execute("UPDATE match_history SET\
                    battle_wins = 0,\
                    battle_losses = 0,\
                    duel_match_wins = 0,\
                    duel_match_losses = 0,\
                    duel_series_wins = 0,\
                    duel_series_losses = 0,\
                    boat_attack_wins = 0,\
                    boat_attack_losses = 0,\
                    special_battle_wins = 0,\
                    special_battle_losses = 0")

    db.commit()
    db.close()


def add_discord_id(member: discord.Member):
    db, cursor = db_utils.connect_to_db()
    print(f"Updating id for {member.display_name}\t{member.id}")
    cursor.execute("UPDATE users SET discord_id = %s WHERE player_name = %s", (member.id, member.display_name))

    db.commit()
    db.close()


intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD_NAME:
            for member in guild.members:
                if not member.bot:
                    add_discord_id(member)
    print("Done")


if __name__ =='__main__':
    update_tables()
    clear_match_history()
    bot.run(BOT_TOKEN)