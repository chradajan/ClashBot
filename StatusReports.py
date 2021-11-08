from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import datetime
import db_utils
import discord

class StatusReports(commands.Cog):
    """Commands to get different status reports."""

    def __init__(self, bot):
        self.bot = bot

    """
    Command: !strikes_report

    Get a list of users with at least 1 strike.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def strikes_report(self, ctx):
        """Get a report of players with strikes."""
        strike_list = db_utils.get_strike_report()
        table = PrettyTable()
        table.field_names = ["Member", "Strikes"]
        embed = discord.Embed(title="Status Report")

        for player_name, strikes in strike_list:
            table.add_row([player_name, strikes])

        embed.add_field(name="Players with at least 1 strike", value = "```\n" + table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("Players with at least 1 strike\n" + "```\n" + table.get_string() + "```")

    @strikes_report.error
    async def strikes_report_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!strikes_report command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !strikes_report")
            raise error


    """
    Command: !decks_report

    Get a list of users and their number of decks remaining today.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def decks_report(self, ctx):
        """Get a report of players with decks remaining today."""
        usage_list = clash_utils.get_remaining_decks_today()
        users_on_vacation = db_utils.get_users_on_vacation()
        table = PrettyTable()
        table.field_names = ["Member", "Decks"]
        embed = discord.Embed(title="Status Report", footer="Users on vacation are not included in this list")

        for player_name, decks_remaining in usage_list:
            if player_name in users_on_vacation:
                continue

            table.add_row([player_name, decks_remaining])

        embed.add_field(name="Players with decks remaining", value = "```\n" + table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("Players with decks remaining\n" + "```\n" + table.get_string() + "```")

    @decks_report.error
    async def decks_report_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!decks_report command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !decks_report")
            raise error


    """
    Command: !fame_report {threshold}

    Get a list of users below a specified fame threshold.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def fame_report(self, ctx, threshold: int):
        """Get a report of players below specific fame threshold. Ignores users on vacation."""
        hall_of_shame = clash_utils.get_hall_of_shame(threshold)
        users_on_vacation = db_utils.get_users_on_vacation()
        table = PrettyTable()
        table.field_names = ["Member", "Fame"]
        embed = discord.Embed(title="Status Report", footer="Users on vacation are not included in this list")

        for player_name, fame in hall_of_shame:
            if player_name in users_on_vacation:
                continue

            table.add_row([player_name, fame])

        embed.add_field(name="Players below fame threshold", value = "```\n" + table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("Players below fame threshold\n" + "```\n" + table.get_string() + "```")

    @fame_report.error
    async def fame_report_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!fame_report command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !fame_report <threshold>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !fame_report <threshold>")
            raise error


    async def player_report_helper(self, ctx, user_data: dict):
        general_info_table = PrettyTable()

        general_info_table.add_row(["Player Name", user_data["player_name"]])
        general_info_table.add_row(["Player Tag", user_data["player_tag"]])
        general_info_table.add_row(["Strikes", user_data["strikes"]])
        general_info_table.add_row(["Discord Name", user_data["discord_name"]])
        general_info_table.add_row(["Clan Name", user_data["clan_name"]])
        general_info_table.add_row(["Clan Tag", user_data["clan_tag"]])
        general_info_table.add_row(["Clan Role", user_data["clan_role"].capitalize()])
        general_info_table.add_row(["On Vacation", "Yes" if user_data["vacation"] else "No"])
        general_info_table.add_row(["Status", user_data["status"]])

        embed = discord.Embed(title="Status Report")
        embed.add_field(name=f"{user_data['player_name']}'s general info", value = "```\n" + general_info_table.get_string(header=False) + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send(f"{user_data['player_name']}'s general info" + "\n" + "```\n" + general_info_table.get_string(header=False) + "```")

        decks_used_today = clash_utils.get_user_decks_used_today(user_data["player_tag"])
        if decks_used_today == None:
            decks_used_today = 0

        usage_history_list = bot_utils.break_down_usage_history(user_data["usage_history"], datetime.datetime.now(datetime.timezone.utc))

        deck_usage_history_table = PrettyTable()
        deck_usage_history_table.field_names = ["Day", "Decks Used"]

        for decks_used, date in usage_history_list:
            deck_usage_history_table.add_row([date, decks_used])

        embed = discord.Embed(title="Status Report")
        embed.set_footer(text=f"{user_data['player_name']} has used {decks_used_today} decks today.")
        embed.add_field(name=f"{user_data['player_name']}'s deck usage history", value = "```\n" + deck_usage_history_table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send(f"{user_data['player_name']} has used {decks_used_today} decks today." + "\n\n" +\
                            f"{user_data['player_name']}'s deck usage history" + "\n" + "```\n" + deck_usage_history_table.get_string() + "```")

        match_performance_embed = bot_utils.create_match_performance_embed(user_data["player_name"], user_data["player_tag"])
        await ctx.send(embed=match_performance_embed)


    """
    Command: !player_report {general_info} {deck_usage_history}

    Get information about a member in the server.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def player_report(self, ctx, member: discord.Member):
        """Get information about a member."""
        player_tag = db_utils.get_player_tag(member.id)

        if player_tag == None:
            await ctx.send(f"{member.display_name} is a member of this Discord server but they were not found in the database. Make sure their nickname matches their in-game player name.")
            return

        user_data = db_utils.get_user_data(player_tag)

        if user_data == None:
            await ctx.send(f"{member.display_name} is a member of this Discord server but they were not found in the database. Make sure their nickname matches their in-game player name.")
            return
        
        await self.player_report_helper(ctx, user_data)

    @player_report.error
    async def player_report_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!player_report command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.MemberNotFound):
            user_data = db_utils.get_user_data(error.argument)
            if user_data != None:
                await self.player_report_helper(ctx, user_data)
            else:
                await ctx.send("Member not found. This could be because there a multiple UNREGISTERED users with identical player_names. Member names are case sensitive. If member name includes spaces, place quotes around name when issuing command.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !player_report <general_info (optional)> <deck_usage_info (optional)>")
            raise error