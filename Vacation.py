from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import db_utils
import discord

class Vacation(commands.Cog):
    """Commands for setting setting/viewing vacation status of users."""

    def __init__(self, bot):
        self.bot = bot

    """
    Command: !set_vacation {member} {status}

    Toggle the vacation status of the specified user.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def set_vacation(self, ctx, member: discord.Member, status: bool):
        """Set vacation status for the specified member."""
        channel = discord.utils.get(ctx.guild.channels, name=TIME_OFF_CHANNEL)
        vacation_status = db_utils.update_vacation_for_user(member.id, status)
        vacation_status_string = ("NOT " if not vacation_status else "") + "ON VACATION"
        await channel.send(f"Updated vacation status of {member.mention} to: {vacation_status_string}.")

    @set_vacation.error
    async def set_vacation_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            await ctx.send("Member not found. Member names are case sensitive. If member name includes spaces, place quotes around name when issuing command.")
        elif isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"!set_vacation command can only be sent by Leaders/Admins.")
        elif isinstance(error, commands.errors.BadBoolArgument):
            await ctx.send(f"Invalid second argument. Valid statuses: on or off")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !set_vacation <member> <status>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !set_vacation <member> <status>")
            raise error


    """
    Command: !vacation_list

    Print a list of all users currently on vacation.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def vacation_list(self, ctx):
        """Get a list of all users currently on vacation."""
        users_on_vacation = db_utils.get_vacation_list()
        table = PrettyTable()
        table.field_names = ["Member"]
        embed = discord.Embed()

        for user in users_on_vacation:
            table.add_row([user])

        embed.add_field(name="Vacation List", value="```\n" + table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("Vacation List\n" + "```\n" + table.get_string() + "```")

    @vacation_list.error
    async def vacation_list_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            await ctx.send(f"!vacation_list command can only be sent by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !vacation_list")
            raise error