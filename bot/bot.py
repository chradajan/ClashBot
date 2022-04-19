"""Creates/starts the bot and handles automated routines."""

import datetime

import aiocron
import discord
from discord.ext import commands
from pretty_help import DefaultMenu, PrettyHelp

# Cogs
from cogs.automation_tools import AutomationTools
from cogs.error_handler import ErrorHandler
from cogs.leader_utils import LeaderUtils
from cogs.listeners import Listeners
from cogs.member_utils import MemberUtils
from cogs.status_reports import StatusReports
from cogs.strikes import Strikes
from cogs.user_updates import UserUpdates
from cogs.vacation import Vacation

# Config
from config.config import GUILD_NAME
from config.credentials import BOT_TOKEN

# Utils
import utils.bot_utils as bot_utils
import utils.clash_utils as clash_utils
import utils.db_utils as db_utils
from utils.channel_utils import CHANNEL, prepare_channels
from utils.role_utils import prepare_roles
from utils.util_types import ReminderTime


########################################################
#                                                      #
#    ____        _      _____      _                   #
#   |  _ \      | |    / ____|    | |                  #
#   | |_) | ___ | |_  | (___   ___| |_ _   _ _ __      #
#   |  _ < / _ \| __|  \___ \ / _ \ __| | | | '_ \     #
#   | |_) | (_) | |_   ____) |  __/ |_| |_| | |_) |    #
#   |____/ \___/ \__| |_____/ \___|\__|\__,_| .__/     #
#                                           | |        #
#                                           |_|        #
#                                                      #
########################################################

menu = DefaultMenu('◀️', '▶️', '❌')
intents = discord.Intents.default()
intents.members = True
activity = discord.Game(name="Clash Royale")
bot = commands.Bot(command_prefix='!',
                   activity=activity,
                   help_command=PrettyHelp(navigation=menu, color=discord.Colour.green()),
                   intents=intents)

bot.add_cog(AutomationTools(bot))
bot.add_cog(LeaderUtils(bot))
bot.add_cog(Listeners(bot))
bot.add_cog(MemberUtils(bot))
bot.add_cog(StatusReports(bot))
bot.add_cog(Strikes(bot))
bot.add_cog(UserUpdates(bot))
bot.add_cog(Vacation(bot))
bot.add_cog(ErrorHandler(bot))

@bot.event
async def on_ready():
    """Get relevant channels and roles on bot startup."""
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    prepare_channels(guild)
    prepare_roles(guild)

    print("Bot Ready")


#########################################################################################
#                                                                                       #
#                  _                        _           _   _______        _            #
#       /\        | |                      | |         | | |__   __|      | |           #
#      /  \  _   _| |_ ___  _ __ ___   __ _| |_ ___  __| |    | | __ _ ___| | _____     #
#     / /\ \| | | | __/ _ \| '_ ` _ \ / _` | __/ _ \/ _` |    | |/ _` / __| |/ / __|    #
#    / ____ \ |_| | || (_) | | | | | | (_| | ||  __/ (_| |    | | (_| \__ \   <\__ \    #
#   /_/    \_\__,_|\__\___/|_| |_| |_|\__,_|\__\___|\__,_|    |_|\__,_|___/_|\_\___/    #
#                                                                                       #
#                                                                                       #
#########################################################################################


@aiocron.crontab('0 19 * * 4,5,6,0')
async def automated_reminder_eu():
    """Send reminder every Thursday, Friday, Saturday, and Sunday at 19:00 UTC."""
    if db_utils.get_reminder_status() and not clash_utils.river_race_completed():
        await bot_utils.deck_usage_reminder(time_zone=ReminderTime.EU)


@aiocron.crontab('0 2 * * 5,6,0,1')
async def automated_reminder_us():
    """Send reminder every Friday, Saturday, Sunday, and Monday at 02:00 UTC."""
    if db_utils.get_reminder_status() and not clash_utils.river_race_completed():
        await bot_utils.deck_usage_reminder(time_zone=ReminderTime.US)


@aiocron.crontab('0 8 * * 5,6,0,1')
async def last_call_automated_reminder():
    """Send a reminder every day ~1.5 hours before reset time (08:00 UTC)."""
    if db_utils.get_reminder_status() and not clash_utils.river_race_completed():
        await bot_utils.deck_usage_reminder()


@aiocron.crontab('0 10 * * 0')
async def record_race_completion_status():
    """Check if the race was completed on Saturday and save result to db."""
    db_utils.set_completed_saturday_status(clash_utils.river_race_completed())


@aiocron.crontab('0 18 * * 1')
async def assign_strikes_and_clear_vacation():
    """Assign strikes and clear vacation every Monday 18:00 UTC (Monday 11:00am PDT)."""
    completed_saturday = db_utils.is_completed_saturday()
    message = ""
    send_missing_data_message = False

    if completed_saturday:
        message = "River Race completed Saturday. Participants with fewer than 12 decks have received strikes.\n"
    else:
        message = "River Race completed Sunday. Participants with fewer than 16 decks have received strikes.\n"

    if db_utils.get_strike_status():
        users_on_vacation = db_utils.get_users_on_vacation()
        deck_usage_list = db_utils.get_all_user_deck_usage_history()
        active_members = clash_utils.get_active_members_in_clan()
        former_participants = db_utils.get_non_active_participants()
        mention_string = ""
        perfect_week = True
        embed_one = discord.Embed(title="The following users have received strikes:")
        embed_two = discord.Embed(title="The following users have received strikes:")
        field_count = 0
        reset_times = db_utils.get_river_race_reset_times()

        for player_name, player_tag, discord_id, deck_usage_history, tracked_since in deck_usage_list:
            if (player_tag not in active_members and player_tag not in former_participants) or (player_tag in users_on_vacation):
                continue

            should_receive_strike, decks_used, decks_required, missing_data = bot_utils.should_receive_strike(deck_usage_history,
                                                                                                              completed_saturday,
                                                                                                              tracked_since,
                                                                                                              reset_times)

            if missing_data:
                send_missing_data_message = True

            if not should_receive_strike:
                continue

            if tracked_since is None:
                tracked_since = "Unknown"
            else:
                tracked_since = tracked_since.strftime("%a, %b %d %H:%M UTC")

            if player_tag in former_participants:
                await bot_utils.strike_former_participant(player_name,
                                                          player_tag,
                                                          decks_used,
                                                          decks_required,
                                                          tracked_since)
                continue

            perfect_week = False
            member = None

            if discord_id is not None:
                member = discord.utils.get(CHANNEL.strikes().members, id=discord_id)

            if member is not None:
                mention_string += f"{member.mention} "

            _, strikes, _, _ = db_utils.update_strikes(player_tag, 1)

            if strikes is None:
                continue

            if field_count < 25:
                embed_one.add_field(name=player_name,
                                    value=f"```Decks: {decks_used}/{decks_required}\nStrikes: {strikes}\nDate: {tracked_since}```",
                                    inline=False)
                field_count += 1
            else:
                embed_two.add_field(name=player_name,
                                    value=f"```Decks: {decks_used}/{decks_required}\nStrikes: {strikes}\nDate: {tracked_since}```",
                                    inline=False)

        if perfect_week:
            message += "Everyone completed their battles this week. Good job!"
        else:
            message += mention_string
    else:
        message = "Automated strikes are currently disabled, so no strikes have been given out for the previous River Race."

    db_utils.clear_all_vacation()
    vacation_embed = discord.Embed()
    vacation_embed.add_field(name="Vacation status has been reset for all users.",
                             value="Make sure to use !vacation before the next war if you're going to miss it.")
    await CHANNEL.time_off().send(embed=vacation_embed)
    await CHANNEL.strikes().send(message)

    if not perfect_week:
        await CHANNEL.strikes().send(embed=embed_one)

        if field_count == 25:
            await CHANNEL.strikes().send(embed=embed_two)

    if send_missing_data_message:
        missing_data_embed = discord.Embed()
        missing_data_embed.add_field(name="Missing Data Warning",
                                     value=("War participation data is missing for one or more days. "
                                            "Threshold for assigning strikes has been adjusted accordingly."))
        await CHANNEL.strikes().send(embed=missing_data_embed)


PREV_DECK_USAGE_SUM = -1
PREV_DECK_USAGE = None
RESET_OCCURRED = False

@aiocron.crontab('20-58 9 * * *')
async def determine_reset_time():
    """Start routines that need to run at reset time.

    Check every minute for a drop in total deck usage to determine that the daily reset has occurred. In addition to saving deck
    usage and reset time each the, extra tasks are performed at the end of the following days:

    Wednesday:
        - prepare_for_river_race: Sets up database to track upcoming river race.

    Thursday, Friday, Saturday:
        - calculate_match_performance: Check match performance of clan members.
        - save_clans_in_race: Save number of decks used by each clan in the river race and their current fame.
    """
    global PREV_DECK_USAGE_SUM
    global PREV_DECK_USAGE
    global RESET_OCCURRED

    if RESET_OCCURRED:
        return

    active_members = clash_utils.get_active_members_in_clan()
    weekday = datetime.datetime.utcnow().date().weekday()
    usage_list = clash_utils.get_deck_usage_today(active_members=active_members)
    current_sum = 0

    if (len(active_members) == 0) or (len(usage_list) == 0):
        return

    for decks_used in usage_list.values():
        current_sum += decks_used

    if current_sum < PREV_DECK_USAGE_SUM:
        RESET_OCCURRED = True
        db_utils.clean_up_db(active_members=active_members)
        db_utils.record_deck_usage_today(PREV_DECK_USAGE)

        if weekday == 3:
            db_utils.prepare_for_river_race(datetime.datetime.now(datetime.timezone.utc))
        elif weekday in {4, 5, 6}:
            clash_utils.calculate_match_performance(False)
            db_utils.save_clans_in_race_info(False)

        db_utils.set_reset_time(datetime.datetime.now(datetime.timezone.utc))
    else:
        PREV_DECK_USAGE_SUM = current_sum
        PREV_DECK_USAGE = usage_list


@aiocron.crontab('59 9 * * *')
async def reset_globals():
    """Reset globals used for daily reset tracking and perform reset tracking routine described above if reset has not occurred."""
    global PREV_DECK_USAGE_SUM
    global PREV_DECK_USAGE
    global RESET_OCCURRED

    if not RESET_OCCURRED:
        active_members = clash_utils.get_active_members_in_clan()
        weekday = datetime.datetime.utcnow().date().weekday()
        db_utils.clean_up_db(active_members=active_members)
        db_utils.record_deck_usage_today(PREV_DECK_USAGE)

        if weekday == 3:
            db_utils.prepare_for_river_race(datetime.datetime.now(datetime.timezone.utc))
        elif weekday in {4, 5, 6}:
            clash_utils.calculate_match_performance(False)
            db_utils.save_clans_in_race_info(False)

        db_utils.set_reset_time(datetime.datetime.now(datetime.timezone.utc))

    PREV_DECK_USAGE_SUM = -1
    PREV_DECK_USAGE = None
    RESET_OCCURRED = False


@aiocron.crontab('30 7,15,23 * * *')
async def update_members():
    """Update all members of the server at 07:30, 15:30, and 23:30 UTC everyday."""
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    await bot_utils.update_all_members(guild)


@aiocron.crontab('0 10-23 * * 4,5,6,0')
async def night_match_performance_tracker():
    """Calculate match performance every hour between 10:00-23:00 Thursday-Sunday."""
    clash_utils.calculate_match_performance(False)


@aiocron.crontab('0 0-9 * * 5,6,0,1')
async def morning_match_performance_tracker():
    """Calculate match performance every hour between 00:00-09:00 Friday-Monday."""
    clash_utils.calculate_match_performance(False)


@aiocron.crontab('02 10 * * 1')
async def final_match_performance_check():
    """Calculate match performance after the war concludes on Monday."""
    clash_utils.calculate_match_performance(True)
    db_utils.save_clans_in_race_info(True)
    db_utils.set_war_time_status(False)


#####################################################
#                                                   #
#     _____ _             _     ____        _       #
#    / ____| |           | |   |  _ \      | |      #
#   | (___ | |_ __ _ _ __| |_  | |_) | ___ | |_     #
#    \___ \| __/ _` | '__| __| |  _ < / _ \| __|    #
#    ____) | || (_| | |  | |_  | |_) | (_) | |_     #
#   |_____/ \__\__,_|_|   \__| |____/ \___/ \__|    #
#                                                   #
#####################################################

if __name__ == '__main__':
    bot.run(BOT_TOKEN)
