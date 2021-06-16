from config import *
from credentials import BOT_TOKEN
from discord.ext import commands
import aiocron
import asyncio
import bot_utils
import clash_utils
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

# help_command = commands.DefaultHelpCommand(no_category="Clash Bot Commands")
intents = discord.Intents.default()
intents.members = True
# bot = commands.Bot(command_prefix='!', help_command=help_command, intents=intents)
bot = commands.Bot(command_prefix='!', intents=intents)

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


@aiocron.crontab('0 19 * * 1,2')
async def automated_reminder_eu():
    """Send reminder every Monday and Tuesday at 19:00 UTC (Monday and Tuesday at 7pm GMT)."""
    if (db_utils.get_reminder_status()):
        await bot_utils.deck_usage_reminder(bot, US_time=False)


@aiocron.crontab('0 1 * * 2,3')
async def automated_reminder_us():
    """Send reminder every Tuesday and Wednesday at 01:00 UTC (Monday and Tuesday at 6pm PDT)."""
    if (db_utils.get_reminder_status()):
        await bot_utils.deck_usage_reminder(bot, US_time=True)


@aiocron.crontab('32 9 * * 3')
async def assign_strikes_and_clear_vacation():
    """Assign strikes and clear vacation every Wednesday 10:00 UTC (Wednesday 3:00am PDT)."""
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    vacation_channel = discord.utils.get(guild.channels, name=TIME_OFF_CHANNEL)
    strikes_channel = discord.utils.get(guild.channels, name=STRIKES_CHANNEL)
    saved_message = ""

    if db_utils.get_strike_status():
        vacation_list = db_utils.get_vacation_list()
        deck_usage_list = clash_utils.get_river_race_deck_usage()

        member_string = ""
        non_member_string = ""

        for player_name, deck_usage in deck_usage_list:
            if player_name in vacation_list:
                continue

            member = discord.utils.get(strikes_channel.members, display_name=player_name)
            strikes = db_utils.give_strike(player_name)

            if member == None:
                previous_strike_count = 0 if strikes == 0 else strikes - 1
                non_member_string += f"{player_name} - Decks used: {deck_usage},  Strikes: {previous_strike_count} -> {strikes}" + "\n"
            else:
                member_string += f"{member.mention} - Decks used: {deck_usage},  Strikes: {strikes - 1} -> {strikes}" + "\n"

        if (len(member_string) == 0) and (len(non_member_string) == 0):
            saved_message = "Everyone completed their battles this week. Good job!"
        else:
            saved_message = "The following members have received strikes for failing to complete 8 battles:\n" + member_string + non_member_string
    else:
        saved_message = "Automated strikes are currently disabled so no strikes have been given out."

    db_utils.set_saved_message(saved_message)
    db_utils.clear_all_vacation()
    await vacation_channel.send("Vacation status for all users has been set to false. Make sure to use !vacation before the next war if you're going to miss it.")


@aiocron.crontab('0 18 * * 3')
async def send_saved_message():
    """Send saved message of who received automated strikes every Wednesday 18:00 UTC (Wednesday 11:00am PDT)."""
    guild = discord.utils.get(bot.guilds, name=GUILD_NAME)
    strikes_channel = discord.utils.get(guild.channels, name=STRIKES_CHANNEL)
    message = db_utils.get_saved_message()
    db_utils.set_saved_message("")
    await strikes_channel.send(message)


@aiocron.crontab('32 9 * * *')
async def record_decks_used_today():
    """Record number of decks used by each member one minute before daily reset every day."""
    usage_list = clash_utils.get_deck_usage_today()

    for player_name, decks_used in usage_list:
        db_utils.add_deck_usage_today(player_name, decks_used)


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