from config import *
from credentials import BOT_TOKEN
from discord.ext import commands
from pretty_help import DefaultMenu, PrettyHelp
import aiocron
import asyncio
import bot_utils
import clash_utils
import datetime
import db_utils
import discord

#Cogs
import AutomationTools
import LeaderUtils
import MemberListeners
import MemberUtils
import StatusReports
import Strikes
import UserUpdates
import Vacation


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
bot = commands.Bot(command_prefix='!', help_command=PrettyHelp(navigation=menu, color=discord.Colour.green()), intents=intents)

bot.add_cog(AutomationTools.AutomationTools(bot))
bot.add_cog(LeaderUtils.LeaderUtils(bot))
bot.add_cog(MemberListeners.MemberListeners(bot))
bot.add_cog(MemberUtils.MemberUtils(bot))
bot.add_cog(StatusReports.StatusReports(bot))
bot.add_cog(Strikes.Strikes(bot))
bot.add_cog(UserUpdates.UserUpdates(bot))
bot.add_cog(Vacation.Vacation(bot))


@bot.event
async def on_ready():
    for guild in bot.guilds:
        if guild.name == GUILD_NAME:
            bot_utils.SPECIAL_ROLES[ADMIN_ROLE_NAME] = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)
            bot_utils.SPECIAL_ROLES[NEW_ROLE_NAME] = discord.utils.get(guild.roles, name=NEW_ROLE_NAME)
            bot_utils.SPECIAL_ROLES[CHECK_RULES_ROLE_NAME] = discord.utils.get(guild.roles, name=CHECK_RULES_ROLE_NAME)
            bot_utils.NORMAL_ROLES[VISITOR_ROLE_NAME] = discord.utils.get(guild.roles, name=VISITOR_ROLE_NAME)
            bot_utils.NORMAL_ROLES[MEMBER_ROLE_NAME] = discord.utils.get(guild.roles, name=MEMBER_ROLE_NAME)
            bot_utils.NORMAL_ROLES[ELDER_ROLE_NAME] = discord.utils.get(guild.roles, name=ELDER_ROLE_NAME)
            bot_utils.NORMAL_ROLES[LEADER_ROLE_NAME] = discord.utils.get(guild.roles, name=LEADER_ROLE_NAME)

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


@aiocron.crontab('0 19 * * 4,5,6')
async def automated_reminder_eu():
    """
    Send reminder every Thursday, Friday, and Saturday at 19:00 UTC (Monday and Tuesday at 7pm GMT).
    """
    if db_utils.get_reminder_status():
        await bot_utils.deck_usage_reminder(bot, US_time=False)


@aiocron.crontab('0 19 * * 0')
async def automated_reminder_eu_sunday():
    """
    Send reminder every Sunday at 19:00 UTC if race not completed (Monday and Tuesday at 7pm GMT).
    """
    if db_utils.get_reminder_status() and (not clash_utils.river_race_completed()):
        await bot_utils.deck_usage_reminder(bot, US_time=False)


@aiocron.crontab('0 2 * * 5,6,0')
async def automated_reminder_us():
    """
    Send reminder every Friday, Saturday, and Sunday at 02:00 UTC (Thursday, Friday, and Saturday at 6pm PST).
    """
    if db_utils.get_reminder_status():
        await bot_utils.deck_usage_reminder(bot, US_time=True)


@aiocron.crontab('0 2 * * 1')
async def automated_reminder_us_sunday():
    """
    Send reminder every Monday at 02:00 UTC if race not completed (Sunday at 6pm PST).
    """
    if db_utils.get_reminder_status() and (not clash_utils.river_race_completed()):
        await bot_utils.deck_usage_reminder(bot, US_time=True)


@aiocron.crontab('0 10 * * 0')
async def record_race_completion_status():
    """
    Check if the race was completed on Saturday and save result to db.
    """
    db_utils.set_completed_saturday_status(clash_utils.river_race_completed())


@aiocron.crontab('0 18 * * 1')
async def assign_strikes_and_clear_vacation():
    """
    Assign strikes and clear vacation every Monday 18:00 UTC (Monday 11:00am PDT).
    """
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    vacation_channel = discord.utils.get(guild.channels, name=TIME_OFF_CHANNEL)
    strikes_channel = discord.utils.get(guild.channels, name=STRIKES_CHANNEL)
    completed_saturday = db_utils.is_completed_saturday()
    message = ""

    if completed_saturday:
        message = "River Race completed Saturday. Participants with fewer than 10 decks have received strikes.\n"
    else:
        message = "River Race completed Sunday. Participants with fewer than 14 decks have received strikes.\n"

    if db_utils.get_strike_status():
        users_on_vacation = db_utils.get_users_on_vacation()
        deck_usage_list = db_utils.get_all_user_deck_usage_history()
        active_members = clash_utils.get_active_members_in_clan()
        mention_string = ""
        perfect_week = True
        embed_one = discord.Embed(title="The following users have received strikes:")
        embed_two = discord.Embed(title="The following users have received strikes:")
        field_count = 0

        for player_name, player_tag, deck_usage_history, tracked_since in deck_usage_list:
            if (player_tag not in active_members) or (player_name in users_on_vacation):
                continue

            should_receive_strike, decks_used_in_race = bot_utils.should_receive_strike(deck_usage_history, completed_saturday)

            if not should_receive_strike:
                continue

            perfect_week = False
            member = discord.utils.get(strikes_channel.members, display_name=player_name)

            if (member != None):
                mention_string += f"{member.mention} "

            strikes = db_utils.give_strike(player_tag)

            if field_count < 25:
                embed_one.add_field(name=player_name, value=f"```Decks: {decks_used_in_race}\nStrikes: {strikes}\nDate: {tracked_since}```", inline=False)
                field_count += 1
            else:
                embed_two.add_field(name=player_name, value=f"```Decks: {decks_used_in_race}\nStrikes: {strikes}\nDate: {tracked_since}```", inline=False)

        if perfect_week:
            message += "Everyone completed their battles this week. Good job!"
        else:
            message += mention_string
    else:
        message = "Automated strikes are currently disabled, so no strikes have been given out for the previous River Race."

    db_utils.clear_all_vacation()
    await vacation_channel.send("Vacation status for all users has been set to false. Make sure to use !vacation before the next war if you're going to miss it.")
    await strikes_channel.send(message)

    if not perfect_week:
        await strikes_channel.send(embed=embed_one)

        if field_count == 25:
            await strikes_channel.send(embed=embed_two)


prev_deck_usage_sum = -1
prev_deck_usage = None
reset_occurred = False

@aiocron.crontab('20-58 9 * * *')
async def determine_reset_time():
    """
    Check every minute for a drop in total deck usage today which indicates that the daily reset has occurred. When reset occurs,
    record the number of decks used by each member. If it's Thursday, prepare to start tracking match performance for upcoming
    race. If it's Monday, calculate match performance for the ~30 minutes between the final automated match performance calculation
    and reset time.
    """
    global prev_deck_usage_sum
    global prev_deck_usage
    global reset_occurred

    if reset_occurred:
        return

    active_members = clash_utils.get_active_members_in_clan()
    weekday = datetime.datetime.utcnow().date().weekday()
    usage_list = clash_utils.get_deck_usage_today(active_members=active_members)
    current_sum = 0

    for decks_used in usage_list.values():
        current_sum += decks_used

    if current_sum < prev_deck_usage_sum:
        reset_occurred = True
        reset_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)
        bot_utils.RESET_TIME = reset_time.time()
        db_utils.clean_up_db(active_members=active_members)
        db_utils.record_deck_usage_today(prev_deck_usage)

        if weekday == 0:
            clash_utils.calculate_match_performance(active_members=active_members)
            db_utils.set_war_time_status(False)
        elif weekday == 3:
            db_utils.prepare_for_river_race(reset_time)
    else:
        prev_deck_usage_sum = current_sum
        prev_deck_usage = usage_list


@aiocron.crontab('59 9 * * *')
async def reset_globals():
    """
    Reset global variables needed for daily reset tracking.
    """
    global prev_deck_usage_sum
    global prev_deck_usage
    global reset_occurred

    if not reset_occurred:
        active_members = clash_utils.get_active_members_in_clan()
        weekday = datetime.datetime.utcnow().date().weekday()
        reset_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=1)
        bot_utils.RESET_TIME = reset_time.time()
        db_utils.clean_up_db(active_members=active_members)
        db_utils.record_deck_usage_today(prev_deck_usage)

        if weekday == 0:
            clash_utils.calculate_match_performance(active_members=active_members)
        elif weekday == 3:
            db_utils.prepare_for_river_race(reset_time)

    prev_deck_usage_sum = -1
    prev_deck_usage = None
    reset_occurred = False


@aiocron.crontab('30 7,15,23 * * *')
async def update_members():
    """
    Update all members of the server at 07:30, 15:30, and 23:30 UTC everyday.
    """
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    await bot_utils.update_all_members(guild)


@aiocron.crontab('0 10-23 * * 4,5,6,0')
async def night_match_performance_tracker():
    """
    Calculate match performance every hour between 10:00-23:00 Thursday-Sunday.
    """
    clash_utils.calculate_match_performance()


@aiocron.crontab('0 0-9 * * 5,6,0,1')
async def morning_match_performance_tracker():
    """
    Calculate match performance every hour between 00:00-09:00 Friday-Monday.
    """
    clash_utils.calculate_match_performance()


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

bot.run(BOT_TOKEN)