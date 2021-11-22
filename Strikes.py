from config import *
from discord.ext import commands
import bot_utils
import db_utils
import discord

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
        old_strike_count, new_strike_count, permanent_strikes = db_utils.give_strike(player_tag, delta)

        if old_strike_count is None:
            await ctx.send(f"Something went wrong while updating {player_name}'s strikes. This should not happen.")
            return

        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        message = "has received a strike" if delta > 0 else "has had a strike removed"

        embed = discord.Embed(title="Strikes Updated")
        embed.add_field(name=player_name, value=f"```Strikes: {old_strike_count} -> {new_strike_count}\nPermanent Strikes: {permanent_strikes}```")
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
            await ctx.send(f"{member.display_name} was found on Discord but not in the database. Make sure they've entered their player tag in the welcome channel.")
            return

        await self.strike_helper(ctx, member.display_name, player_tag, 1, member)

    @give_strike.error
    async def give_strike_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!mention_users command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You did not specify a user. Command should be formatted as:  !give_strike <member>")
        elif isinstance(error, commands.errors.MemberNotFound):
            player_tag = db_utils.get_player_tag(error.argument)

            if player_tag is None:
                await ctx.send(f"{error.argument} is not a member of the Discord server and their player name could not be found in the database.")
            else:
                await self.strike_helper(ctx, error.argument, player_tag, 1)
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !give_strike <member>")
            raise error


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
            await ctx.send(f"{member.display_name} was found on Discord but not in the database. Make sure they've entered their player tag in the welcome channel.")
            return

        await self.strike_helper(ctx, member.display_name, player_tag, -1, member)

    @remove_strike.error
    async def remove_strike_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!mention_users command can only be sent in {channel.mention} by Leaders/Admins.")
        elif isinstance(error, commands.errors.MissingRequiredArgument):
            await ctx.send("You did not specify a user. Command should be formatted as:  !remove_strike <member>")
        elif isinstance(error, commands.errors.MemberNotFound):
            player_tag = db_utils.get_player_tag(error.argument)

            if player_tag is None:
                await ctx.send(f"{error.argument} is not a member of the Discord server and their player name could not be found in the database.")
            else:
                await self.strike_helper(ctx, error.argument, player_tag, -1)
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !remove_strike <member>")
            raise error


    """
    Command: !reset_all_strikes

    Set all members to 0 strikes.
    """
    @commands.command()
    @bot_utils.is_leader_command_check()
    @bot_utils.channel_check(COMMANDS_CHANNEL)
    async def reset_all_strikes(self, ctx):
        """Reset each member's strikes to 0."""
        db_utils.reset_strikes()
        channel = discord.utils.get(ctx.guild.channels, name=STRIKES_CHANNEL)
        await channel.send("Strikes for all members have been reset to 0.")

    @reset_all_strikes.error
    async def reset_all_strikes_error(self, ctx, error):
        if isinstance(error, commands.errors.CheckFailure):
            channel = discord.utils.get(ctx.guild.channels, name=COMMANDS_CHANNEL)
            await ctx.send(f"!send_reminder command can only be sent in {channel.mention} by Leaders/Admins.")
        else:
            await ctx.send("Something went wrong. Command should be formatted as:  !reset_all_strikes")
            raise error