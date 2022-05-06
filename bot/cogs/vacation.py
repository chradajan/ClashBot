"""Vacation cog. Vacation commands for leadership to update vacation status of other users."""

import discord
from discord.ext import commands
from prettytable import PrettyTable

# Utils
import utils.bot_utils as bot_utils
import utils.db_utils as db_utils
from utils.channel_utils import CHANNEL
from utils.logging_utils import LOG


class Vacation(commands.Cog):
    """Commands for setting setting/viewing vacation status of users."""

    def __init__(self, bot):
        """Save bot."""
        self.bot = bot

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def set_vacation(self, ctx: commands.Context, member: discord.Member, status: bool):
        """Set vacation status for the specified member."""
        LOG.command_start(ctx, member=member, status=status)
        vacation_status = db_utils.update_vacation_for_user(member.id, status)
        vacation_status_string = ("NOT " if not vacation_status else "") + "ON VACATION"
        await CHANNEL.time_off().send(f"Updated vacation status of {member.mention} to: {vacation_status_string}.")

        confirmation_embed = discord.Embed(title=(f"Status successfully updated and {member.display_name} "
                                                  f"was notified in #{CHANNEL.time_off().name}."),
                                           color=discord.Color.green())
        await ctx.send(embed=confirmation_embed)
        LOG.command_end()

    @commands.command()
    @bot_utils.is_elder_command_check()
    @bot_utils.commands_channel_check()
    async def vacation_list(self, ctx: commands.Context):
        """Get a list of all users currently on vacation."""
        LOG.command_start(ctx)
        users_on_vacation = db_utils.get_users_on_vacation()

        if users_on_vacation:
            table = PrettyTable()
            table.field_names = ["Member"]

            for player_name in users_on_vacation.values():
                table.add_row([player_name])

            embed = discord.Embed(title="Vacation List", description="```\n" + table.get_string() + "```")
        else:
            embed = discord.Embed(title="No users are currently on vacation")

        await ctx.send(embed=embed)
        LOG.command_end()
