from checks import is_admin, is_leader_command_check, is_admin_command_check, channel_check
from config import *
from discord.ext import commands
from prettytable import PrettyTable
import db_utils
import discord

class AutomationTools(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    """
    Command: !automation_status

    Get current automated reminder/strike status.
    """
    @commands.command()
    @is_leader_command_check()
    @channel_check(COMMANDS_CHANNEL)
    async def automation_status(self, ctx):
        """Get status for automated strikes and reminders."""
        reminder_status = "ENABLED" if db_utils.get_reminder_status() else "DISABLED"
        strike_status = "ENABLED" if db_utils.get_strike_status() else "DISABLED"

        table = PrettyTable()
        table.field_names = ["Reminders", "Strikes"]
        table.add_row([reminder_status, strike_status])

        embed = discord.Embed(title="Automation Status Report")
        embed.add_field(name="Status", value = "```\n" + table.get_string() + "```")
        await ctx.send(embed=embed)


    @automation_status.error
    async def automation_status_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!automation_status command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !automation_status")
            raise error


    """
    Command: !set_automated_reminders {status}

    Enable/disable automated reminders.
    """
    @commands.command()
    @is_leader_command_check()
    @channel_check(COMMANDS_CHANNEL)
    async def set_automated_reminders(self, ctx, status: bool):
        """Set whether automated reminders should be sent."""
        db_utils.set_reminder_status(status)
        await ctx.channel.send("Automated deck usage reminders are now " + ("ENABLED" if status else "DISABLED") + ".")

    @set_automated_reminders.error
    async def set_automated_reminders_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!set_automated_reminders command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.BadBoolArgument):
            await ctx.send("Invalid argument. Valid statuses are: on or off")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !set_automated_reminders <status>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !set_automated_reminders <status>")
            raise error


    """
    Command: !set_automated_strikes {status}

    Enable/disable automated strikes.
    """
    @commands.command()
    @is_leader_command_check()
    @channel_check(COMMANDS_CHANNEL)
    async def set_automated_strikes(self, ctx, status: bool):
        """Set whether automated strikes should be given."""
        db_utils.set_strike_status(status)
        await ctx.channel.send("Automated strikes for low deck usage are now " + ("ENABLED" if status else "DISABLED") + ".")

    @set_automated_strikes.error
    async def set_automated_strikes_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!set_automated_strikes command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.BadBoolArgument):
            await ctx.send("Invalid argument. Valid statuses are: on or off")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("Missing arguments. Command should be formatted as:  !set_automated_strikes <status>")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !set_automated_strikes <status>")
            raise error