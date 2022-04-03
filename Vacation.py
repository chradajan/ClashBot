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
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def set_vacation(self, ctx, member: discord.Member, status: bool):
        """Set vacation status for the specified member."""
        channel = discord.utils.get(ctx.guild.channels, name=TIME_OFF_CHANNEL)
        vacation_status = db_utils.update_vacation_for_user(member.id, status)
        vacation_status_string = ("NOT " if not vacation_status else "") + "ON VACATION"
        await channel.send(f"Updated vacation status of {member.mention} to: {vacation_status_string}.")


    """
    Command: !vacation_list

    Print a list of all users currently on vacation.
    """
    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def vacation_list(self, ctx):
        """Get a list of all users currently on vacation."""
        users_on_vacation = db_utils.get_users_on_vacation()
        table = PrettyTable()
        table.field_names = ["Member"]
        embed = discord.Embed()

        for player_name in users_on_vacation.values():
            table.add_row([player_name])

        embed.add_field(name="Vacation List", value="```\n" + table.get_string() + "```")

        try:
            await ctx.send(embed=embed)
        except:
            await ctx.send("Vacation List\n" + "```\n" + table.get_string() + "```")
