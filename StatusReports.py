from checks import is_admin, is_leader_command_check, is_admin_command_check, channel_check
from config import *
from discord.ext import commands
from prettytable import PrettyTable
import clash_utils
import db_utils
import discord

class StatusReports(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    """
    Command: !strikes_report

    Get a list of users with at least 1 strike.
    """
    @commands.command()
    @is_leader_command_check()
    @channel_check(COMMANDS_CHANNEL)
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
    @is_leader_command_check()
    @channel_check(COMMANDS_CHANNEL)
    async def decks_report(self, ctx):
        """Get a report of players with decks remaining today."""
        usage_list = clash_utils.get_deck_usage_today()
        vacation_list = db_utils.get_vacation_list()
        table = PrettyTable()
        table.field_names = ["Member", "Decks"]
        embed = discord.Embed(title="Status Report", footer="Users on vacation are not included in this list")

        for player_name, decks_remaining in usage_list:
            if player_name in vacation_list:
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
    @is_leader_command_check()
    @channel_check(COMMANDS_CHANNEL)
    async def fame_report(self, ctx, threshold: int):
        """Get a report of players below specifiec fame threshold. Ignores users on vacation."""
        hall_of_shame = clash_utils.get_hall_of_shame(threshold)
        vacation_list = db_utils.get_vacation_list()
        table = PrettyTable()
        table.field_names = ["Member", "Fame"]
        embed = discord.Embed(title="Status Report", footer="Users on vacation are not included in this list")

        for player_name, fame in hall_of_shame:
            if player_name in vacation_list:
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