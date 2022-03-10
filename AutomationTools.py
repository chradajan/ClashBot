from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import db_utils
import discord

class AutomationTools(commands.Cog):
    """Commands to view/set automation status"""

    def __init__(self, bot):
        self.bot = bot


    """
    Command: !automation_status

    Get current automated reminder/strike status.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def automation_status(self, ctx):
        """Get status for automated strikes and reminders."""
        reminder_status = "ENABLED" if db_utils.get_reminder_status() else "DISABLED"
        strike_status = "ENABLED" if db_utils.get_strike_status() else "DISABLED"

        table = PrettyTable()
        table.field_names = ["Reminders", "Strikes"]
        table.add_row([reminder_status, strike_status])

        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name="Automation Status", value = "```\n" + table.get_string() + "```")
        await ctx.send(embed=embed)


    """
    Command: !set_automated_reminders {status}

    Enable/disable automated reminders.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def set_automated_reminders(self, ctx, status: bool):
        """Set whether automated reminders should be sent."""
        db_utils.set_reminder_status(status)

        if status:
            embed = discord.Embed(color=discord.Color.green())
        else:
            embed = discord.Embed(color=discord.Color.red())

        embed.add_field(name="Automated reminders status updated",
                        value=f"Automated reminders are now {'ENABLED' if status else 'DISABLED'}")
        await ctx.send(embed=embed)


    """
    Command: !set_automated_strikes {status}

    Enable/disable automated strikes.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def set_automated_strikes(self, ctx, status: bool):
        """Set whether automated strikes should be given."""
        db_utils.set_strike_status(status)

        if status:
            embed = discord.Embed(color=discord.Color.green())
        else:
            embed = discord.Embed(color=discord.Color.red())

        embed.add_field(name="Automated strikes status updated",
                        value=f"Automated strikes are now {'ENABLED' if status else 'DISABLED'}")
        await ctx.send(embed=embed)