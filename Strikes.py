from config import *
from discord.ext import commands
from prettytable import PrettyTable
import bot_utils
import clash_utils
import db_utils
import discord
import ErrorHandler

class Strikes(commands.Cog):
    """Commands for updating strike counts."""

    def __init__(self, bot):
        self.bot = bot


    async def strike_helper(self, ctx, player_name: str, player_tag: str, delta: int, member: discord.Member=None):
        """
        Give or remove a strike from a user and send confirmation messages back to leader commands and strikes channels.

        Args:
            player_name(str): User's in game name.
            player_tag(str): User to update strikes for.
            delta(int): Number of strikes to give or remove.
            member(discord.Member): Member object of user if they are on Discord.
        """
        old_strike_count, new_strike_count, old_permanent_strikes, new_permanent_strikes = db_utils.give_strike(player_tag, delta)

        if old_strike_count is None:
            await ctx.send(f"Something went wrong while updating {player_name}'s strikes. This should not happen.")
            return

        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        message = "has received a strike" if delta > 0 else "has had a strike removed"

        embed = discord.Embed(title="Strikes Updated")
        embed.add_field(name=player_name, value=f"```Strikes: {old_strike_count} -> {new_strike_count}\nPermanent Strikes: {old_permanent_strikes} -> {new_permanent_strikes}```")
        await ctx.send(embed=embed)

        if member is None:
            await channel.send(f"{player_name} {message}.  {old_strike_count} -> {new_strike_count}")
        else:
            await channel.send(f"{member.mention} {message}.  {old_strike_count} -> {new_strike_count}")


    """
    Command: !give_strike {member}

    Give specified user 1 strike.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def give_strike(self, ctx, member: discord.Member):
        """Increment specified user's strikes by 1."""
        player_tag = db_utils.get_player_tag(member.id)

        if player_tag is None:
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value=f"{member.display_name} is on Discord but is not in the database. Make sure they've entered their player tag in the welcome channel.")
            await ctx.send(embed=embed)
            return

        await self.strike_helper(ctx, member.display_name, player_tag, 1, member)

    @give_strike.error
    async def give_strike_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            player_tag = db_utils.get_player_tag(error.argument)

            if player_tag is not None:
                await self.strike_helper(ctx, error.argument, player_tag, 1)
            else:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)


    """
    Command: !remove_strike {member}

    Remove 1 strike from specified user.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def remove_strike(self, ctx, member: discord.Member):
        """Decrement specified user's strikes by 1."""
        player_tag = db_utils.get_player_tag(member.id)

        if player_tag is None:
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="An unexpected error has occurred",
                            value=f"{member.display_name} is on Discord but is not in the database. Make sure they've entered their player tag in the welcome channel.")
            await ctx.send(embed=embed)
            return

        await self.strike_helper(ctx, member.display_name, player_tag, -1, member)

    @remove_strike.error
    async def remove_strike_error(self, ctx, error):
        if isinstance(error, commands.errors.MemberNotFound):
            player_tag = db_utils.get_player_tag(error.argument)

            if player_tag is not None:
                await self.strike_helper(ctx, error.argument, player_tag, -1)
            else:
                embed = ErrorHandler.ErrorHandler.member_not_found_embed(False)
                await ctx.send(embed=embed)


    """
    Command: !reset_all_strikes

    Set all members to 0 strikes.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def reset_all_strikes(self, ctx):
        """Reset each member's strikes to 0. Permanent strikes are not affected."""
        db_utils.reset_strikes()
        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        embed = discord.Embed()
        embed.add_field(name="Strikes Reset", value="All users have been set to 0 strikes")
        await channel.send(embed=embed)


    """
    Command: !strikes_report

    Get a list of users with at least 1 strike.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def strikes_report(self, ctx):
        """Get a report of players with strikes."""
        strikes = db_utils.get_users_with_strikes()
        active_members = clash_utils.get_active_members_in_clan()

        active_table = PrettyTable()
        active_table.field_names = ["Member", "Strikes"]
        active_members_have_strikes = False

        non_active_table = PrettyTable()
        non_active_table.field_names = ["Member", "Strikes"]
        non_active_members_have_strikes = False

        for player_tag, player_name, strikes in strikes:
            if player_tag in active_members:
                active_members_have_strikes = True
                active_name = active_members[player_tag]["name"]
                active_table.add_row([active_name, strikes])
            else:
                non_active_members_have_strikes = True
                non_active_table.add_row([player_name, strikes])

        if active_members_have_strikes:
            active_embed = discord.Embed()
            active_embed.add_field(name="Active members with strikes", value="```\n" + active_table.get_string() + "```")

            try:
                await ctx.send(embed=active_embed)
            except:
                await ctx.send("Active members with strikes\n" + "```\n" + active_table.get_string() + "```")

        if non_active_members_have_strikes:
            non_active_embed = discord.Embed()
            non_active_embed.add_field(name="Users not in clan with strikes", value="```\n" + non_active_table.get_string() + "```")

            try:
                await ctx.send(embed=non_active_embed)
            except:
                await ctx.send("Active members with strikes\n" + "```\n" + non_active_table.get_string() + "```")

        if (not active_members_have_strikes) and (not non_active_members_have_strikes):
            embed = discord.Embed()
            embed.add_field(name="Strikes Report", value="No users currently have strikes")
            await ctx.send(embed=embed)
