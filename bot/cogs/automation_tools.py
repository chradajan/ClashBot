"""Automation cog. Handles getting/setting the status of automated strikes/reminders."""

import discord
from discord.ext import commands
from prettytable import PrettyTable

# Utils
import utils.bot_utils as bot_utils
import utils.db_utils as db_utils


class AutomationTools(commands.Cog):
    """Commands to view/set automation status"""

    def __init__(self, bot):
        """Save bot."""
        self.bot = bot

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def automation_status(self, ctx: commands.Context):
        """Get status of automated strikes and reminders."""
        reminder_status = "ENABLED" if db_utils.get_reminder_status() else "DISABLED"
        strike_status = "ENABLED" if db_utils.get_strike_status() else "DISABLED"

        table = PrettyTable()
        table.field_names = ["Reminders", "Strikes"]
        table.add_row([reminder_status, strike_status])

        embed = discord.Embed(color=discord.Color.green())
        embed.add_field(name="Automation Status", value = "```\n" + table.get_string() + "```")
        await ctx.send(embed=embed)

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def set_automated_reminders(self, ctx: commands.Context, status: bool):
        """Set automated reminders on/off."""
        db_utils.set_reminder_status(status)

        if status:
            embed = discord.Embed(color=discord.Color.green())
        else:
            embed = discord.Embed(color=discord.Color.red())

        embed.add_field(name="Automated reminders status updated",
                        value=f"Automated reminders are now {'ENABLED' if status else 'DISABLED'}")
        await ctx.send(embed=embed)

    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.commands_channel_check()
    async def set_automated_strikes(self, ctx: commands.Context, status: bool):
        """Set automated strikes on/off."""
        db_utils.set_strike_status(status)

        if status:
            embed = discord.Embed(color=discord.Color.green())
        else:
            embed = discord.Embed(color=discord.Color.red())

        embed.add_field(name="Automated strikes status updated",
                        value=f"Automated strikes are now {'ENABLED' if status else 'DISABLED'}")
        await ctx.send(embed=embed)
